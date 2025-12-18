"""
AI Recipe Parser API endpoints.

Handles file upload, parsing, and usage statistics for AI-powered recipe import.
"""

import time
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import JSONResponse

from ..auth import get_current_user
from ..database import get_db
from ..schemas import (
    ParseFileResponse,
    ParsedIngredient,
    ProductMatch,
    YieldInfo,
    UsageStats,
    UsageStatsResponse,
    RateLimitErrorResponse,
    MonthlyLimitErrorResponse,
    CreateRecipeFromParseRequest,
    CreateRecipeFromParseResponse,
)
from ..services.file_processor import extract_text_from_file, validate_file_before_parse
from ..services.recipe_parser import parse_recipe_with_claude, determine_parse_status
from ..services.product_matcher import match_products
from ..services.unit_converter import normalize_quantity, format_quantity_for_display
from ..utils.tier_limits import (
    check_parse_limit,
    check_rate_limit,
    log_parse_attempt,
    get_usage_stats,
)
from ..audit import log_audit
import os


router = APIRouter(prefix="/api", tags=["ai_parse"])


@router.get("/ai-parse/health")
async def ai_parse_health_check():
    """
    Health check for AI parsing service.

    Verifies dependencies and configuration without requiring authentication.
    """

    health = {
        "status": "healthy",
        "dependencies": {},
        "configuration": {}
    }

    # Check Anthropic dependency
    try:
        import anthropic
        health["dependencies"]["anthropic"] = {
            "installed": True,
            "version": anthropic.__version__ if hasattr(anthropic, '__version__') else "unknown"
        }
    except ImportError as e:
        health["dependencies"]["anthropic"] = {
            "installed": False,
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check python-docx dependency
    try:
        import docx
        health["dependencies"]["python-docx"] = {"installed": True}
    except ImportError as e:
        health["dependencies"]["python-docx"] = {
            "installed": False,
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check pypdf dependency
    try:
        import pypdf
        health["dependencies"]["pypdf"] = {"installed": True}
    except ImportError as e:
        health["dependencies"]["pypdf"] = {
            "installed": False,
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check openpyxl dependency
    try:
        import openpyxl
        health["dependencies"]["openpyxl"] = {"installed": True}
    except ImportError as e:
        health["dependencies"]["openpyxl"] = {
            "installed": False,
            "error": str(e)
        }
        health["status"] = "unhealthy"

    # Check API key configuration (don't reveal the actual key)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    health["configuration"]["anthropic_api_key"] = {
        "configured": bool(api_key),
        "length": len(api_key) if api_key else 0
    }

    if not api_key:
        health["status"] = "unhealthy"

    return health


@router.post("/recipes/parse-file", response_model=ParseFileResponse)
async def parse_recipe_file(
    file: UploadFile = File(...),
    outlet_id: int = Form(...),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Parse uploaded recipe document using AI.

    Extracts structured recipe data and matches ingredients to products.

    Required permissions: Chef or Admin role
    """

    start_time = time.time()

    # Log request details for debugging
    print(f"[PARSE] Request received - user: {current_user.get('id')}, outlet: {outlet_id}, file: {file.filename if file else 'None'}")

    # Check permissions
    if current_user['role'] not in ['chef', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="Only Chef and Admin roles can upload recipes"
        )

    # Require outlet_id
    if not outlet_id:
        raise HTTPException(
            status_code=400,
            detail="outlet_id is required"
        )

    organization_id = current_user['organization_id']
    user_id = current_user['id']  # Database column is 'id', not 'user_id'

    with get_db() as conn:
        # Verify outlet belongs to organization
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, organization_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail="Outlet not found or doesn't belong to your organization"
            )

        # Check rate limit (10 uploads/hour)
        within_limit, attempts = check_rate_limit(organization_id, conn)
        if not within_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Too many upload attempts. You've made {attempts} uploads in the past hour. Please wait before trying again.",
                headers={"Retry-After": "3600"}
            )

        # Check monthly parse limit
        can_parse, usage_info = check_parse_limit(organization_id, conn)
        if not can_parse:
            raise HTTPException(
                status_code=429,
                detail=f"Monthly AI parse limit exceeded ({usage_info['used']}/{usage_info['limit']} used). Upgrade to Basic tier for 100 parses/month.",
            )

        # Pre-validate file
        try:
            validation = await validate_file_before_parse(file)
            filename = validation['filename']
            file_type = filename.split('.')[-1].lower()
        except HTTPException as e:
            # Log failed validation (doesn't count toward limit)
            log_parse_attempt(
                organization_id=organization_id,
                user_id=user_id,
                outlet_id=outlet_id,
                filename=file.filename or 'unknown',
                file_type=file.filename.split('.')[-1].lower() if file.filename else 'unknown',
                parse_status='failed',
                conn=conn,
                error_message=str(e.detail),
                parse_time_ms=int((time.time() - start_time) * 1000)
            )
            raise

        # Extract text from file
        try:
            text = await extract_text_from_file(file)
        except HTTPException as e:
            # Log extraction failure
            log_parse_attempt(
                organization_id=organization_id,
                user_id=user_id,
                outlet_id=outlet_id,
                filename=filename,
                file_type=file_type,
                parse_status='failed',
                conn=conn,
                error_message=str(e.detail),
                parse_time_ms=int((time.time() - start_time) * 1000)
            )
            raise

        # Parse with Claude API
        try:
            recipe_data = await parse_recipe_with_claude(text)
        except HTTPException as e:
            # Log AI parsing failure (doesn't count toward limit)
            log_parse_attempt(
                organization_id=organization_id,
                user_id=user_id,
                outlet_id=outlet_id,
                filename=filename,
                file_type=file_type,
                parse_status='failed',
                conn=conn,
                error_message=str(e.detail),
                parse_time_ms=int((time.time() - start_time) * 1000)
            )

            # Return usage stats showing credits weren't used
            _, current_usage = check_parse_limit(organization_id, conn)
            raise HTTPException(
                status_code=e.status_code,
                detail=e.detail
            )

        # Process ingredients: match products and normalize units
        print(f"[PARSE] Processing {len(recipe_data['ingredients'])} ingredients...")
        parsed_ingredients = []
        ingredients_matched = 0

        for idx, ing_data in enumerate(recipe_data['ingredients']):
            print(f"[PARSE] Ingredient {idx + 1}: {ing_data['name']}")
            # Match to common products
            matches = match_products(
                ing_data['name'],
                organization_id,
                conn,
                max_results=3
            )

            # Normalize units
            normalized_qty, normalized_unit, unit_id = normalize_quantity(
                ing_data['quantity'],
                ing_data['unit'],
                conn
            )

            # Determine if needs review
            needs_review = len(matches) == 0 or (len(matches) > 0 and matches[0]['confidence'] < 0.95)

            if matches and matches[0]['confidence'] >= 0.95:
                ingredients_matched += 1

            parsed_ingredients.append(ParsedIngredient(
                parsed_name=ing_data['name'],
                quantity=ing_data['quantity'],
                unit=ing_data['unit'],
                unit_id=None,  # Original unit might not be in DB
                normalized_quantity=normalized_qty,
                normalized_unit=normalized_unit,
                normalized_unit_id=unit_id,
                prep_note=ing_data.get('prep_note'),
                suggested_products=[
                    ProductMatch(**match) for match in matches
                ],
                needs_review=needs_review
            ))

        # Process yield
        yield_info = None
        if recipe_data.get('yield'):
            yield_data = recipe_data['yield']
            norm_qty, norm_unit, unit_id = normalize_quantity(
                yield_data['quantity'],
                yield_data['unit'],
                conn
            )
            yield_info = YieldInfo(
                quantity=yield_data['quantity'],
                unit=yield_data['unit'],
                unit_id=unit_id
            )

        # Determine parse status
        total_ingredients = len(parsed_ingredients)
        parse_status = determine_parse_status(
            recipe_data,
            ingredients_matched,
            total_ingredients
        )

        # Credits are used for success/partial, not for failed
        credits_used = parse_status in ('success', 'partial')

        # Log parse attempt
        parse_id = log_parse_attempt(
            organization_id=organization_id,
            user_id=user_id,
            outlet_id=outlet_id,
            filename=filename,
            file_type=file_type,
            parse_status=parse_status,
            conn=conn,
            ingredients_count=total_ingredients,
            matched_count=ingredients_matched,
            parse_time_ms=int((time.time() - start_time) * 1000)
        )

        print(f"[PARSE] All ingredients processed. Creating response...")

        # Get updated usage stats
        print(f"[PARSE] Fetching updated usage stats...")
        _, updated_usage = check_parse_limit(organization_id, conn)
        print(f"[PARSE] Usage stats: {updated_usage}")

        # Log audit event
        print(f"[PARSE] Logging audit event...")
        try:
            log_audit(
                user_id=user_id,
                organization_id=organization_id,
                action='recipe_parsed_with_ai',
                entity_type='ai_parse_usage',
                entity_id=parse_id,
                changes={
                    'filename': filename,
                    'parse_status': parse_status,
                    'ingredients_count': total_ingredients,
                    'matched_count': ingredients_matched
                },
                ip_address=request.client.host if request else None
            )
            print(f"[PARSE] Audit logged successfully")
        except Exception as e:
            print(f"[PARSE ERROR] Audit logging failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole request if audit logging fails
            print(f"[PARSE] Continuing despite audit log failure...")

        print(f"[PARSE] Creating ParseFileResponse object...")
        print(f"[PARSE] - parse_id: {parse_id}")
        print(f"[PARSE] - recipe_name: {recipe_data['name']}")
        print(f"[PARSE] - ingredients count: {len(parsed_ingredients)}")

        try:
            response = ParseFileResponse(
                parse_id=parse_id,
                recipe_name=recipe_data['name'],
                yield_info=yield_info,
                description=recipe_data.get('description'),
                category=recipe_data.get('category'),
                ingredients=parsed_ingredients,
                usage=UsageStats(**updated_usage),
                credits_used=credits_used
            )
            print(f"[PARSE] Response object created successfully")
            print(f"[PARSE] Returning successful response to client")
            return response
        except Exception as e:
            print(f"[PARSE ERROR] Failed to create response object: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


@router.get("/ai-parse/usage-stats", response_model=UsageStatsResponse)
async def get_ai_parse_usage_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI parse usage statistics for current organization.

    Returns current month usage and recent history.
    """

    organization_id = current_user['organization_id']

    with get_db() as conn:
        stats = get_usage_stats(organization_id, conn)
        return UsageStatsResponse(**stats)


@router.post("/recipes/create-from-parse", response_model=CreateRecipeFromParseResponse)
async def create_recipe_from_parse(
    data: CreateRecipeFromParseRequest,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Create draft recipe from AI parse results.

    Creates recipe with all ingredients and opens in editor for final review.

    Required permissions: Chef or Admin role
    """

    # Check permissions
    if current_user['role'] not in ['chef', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="Only Chef and Admin roles can create recipes"
        )

    organization_id = current_user['organization_id']
    user_id = current_user['id']  # Database column is 'id', not 'user_id'

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify parse_id belongs to this organization
        cursor.execute("""
            SELECT id, filename, parse_status
            FROM ai_parse_usage
            WHERE id = %s AND organization_id = %s
        """, (data.parse_id, organization_id))

        parse_record = cursor.fetchone()
        if not parse_record:
            raise HTTPException(
                status_code=404,
                detail="Parse record not found"
            )

        # Verify outlet belongs to organization
        cursor.execute("""
            SELECT id FROM outlets
            WHERE id = %s AND organization_id = %s
        """, (data.outlet_id, organization_id))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail="Outlet not found"
            )

        # Create recipe
        cursor.execute("""
            INSERT INTO recipes (
                organization_id, outlet_id, name, description, category,
                yield_amount, yield_unit_id, imported_from_ai, import_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
            RETURNING id
        """, (
            organization_id,
            data.outlet_id,
            data.name,
            data.description,
            data.category,
            data.yield_quantity,
            data.yield_unit_id,
            parse_record['filename']
        ))

        recipe_id = cursor.fetchone()['id']

        # Create recipe ingredients
        for ingredient in data.ingredients:
            cursor.execute("""
                INSERT INTO recipe_ingredients (
                    recipe_id, common_product_id, quantity, unit_id, notes
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                recipe_id,
                ingredient.common_product_id,
                ingredient.quantity,
                ingredient.unit_id,
                ingredient.notes
            ))

        # Update parse record with recipe_id
        cursor.execute("""
            UPDATE ai_parse_usage
            SET recipe_id = %s
            WHERE id = %s
        """, (recipe_id, data.parse_id))

        conn.commit()

        # Log audit event
        log_audit(
            user_id=user_id,
            organization_id=organization_id,
            action='recipe_created_from_ai',
            entity_type='recipe',
            entity_id=recipe_id,
            changes={
                'name': data.name,
                'parse_id': data.parse_id,
                'ingredients_count': len(data.ingredients)
            },
            ip_address=request.client.host if request else None
        )

        return CreateRecipeFromParseResponse(
            recipe_id=recipe_id,
            name=data.name,
            status='draft',
            message=f"Recipe created successfully from {parse_record['filename']}"
        )
