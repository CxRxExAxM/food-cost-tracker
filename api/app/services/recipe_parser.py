"""
Claude API integration for recipe parsing.

Extracts structured recipe data from unstructured text using AI.
"""

import json
import os
from typing import Dict, Optional
from fastapi import HTTPException


async def parse_recipe_with_claude(text: str) -> Dict:
    """
    Parse recipe text using Claude API.

    Sends document text to Claude and receives structured JSON with:
    - Recipe name
    - Yield (quantity + unit)
    - Description (optional)
    - Category (optional)
    - Ingredients list (name, quantity, unit, prep_note)

    Args:
        text: Extracted text from document

    Returns:
        Dict with structured recipe data

    Raises:
        HTTPException: If Claude API fails or returns invalid data
    """

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="AI parsing not configured. ANTHROPIC_API_KEY environment variable required."
        )

    try:
        import anthropic
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Anthropic package not installed. Install with: pip install anthropic"
        )

    # Build structured prompt
    prompt = build_recipe_parsing_prompt(text)

    try:
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)

        # Call Claude API
        print(f"[CLAUDE] Calling API with {len(text)} chars of text")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0,  # Deterministic for structured extraction
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        print(f"[CLAUDE] API call successful, stop_reason: {message.stop_reason}")

        # Extract response text
        if not message.content or len(message.content) == 0:
            raise HTTPException(
                status_code=500,
                detail="AI returned empty response"
            )

        response_text = message.content[0].text

        # Log the response for debugging
        print(f"[CLAUDE] Raw response length: {len(response_text)}")
        print(f"[CLAUDE] Raw response (first 500 chars): {response_text[:500]}")

        # Parse JSON response
        try:
            recipe_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Claude might have wrapped JSON in markdown code blocks
            if "```json" in response_text or "```" in response_text:
                # Extract JSON from markdown code block
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
                if json_match:
                    recipe_data = json.loads(json_match.group(1))
                else:
                    print(f"[CLAUDE ERROR] Could not extract JSON from markdown. Full response: {response_text}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"AI returned JSON wrapped in unexpected format"
                    )
            else:
                print(f"[CLAUDE ERROR] Invalid JSON response. Full response: {response_text}")
                raise HTTPException(
                    status_code=500,
                    detail=f"AI returned invalid JSON: {str(e)}"
                )

        # Validate structure
        validate_recipe_data(recipe_data)

        return recipe_data

    except anthropic.APIError as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI service temporarily unavailable: {str(e)}"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid response format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing recipe: {str(e)}"
        )


def build_recipe_parsing_prompt(text: str) -> str:
    """
    Build optimized prompt for Claude to extract recipe data.

    Args:
        text: Recipe document text

    Returns:
        Formatted prompt string
    """

    prompt = f"""You are a recipe extraction assistant. Parse the following recipe text and extract structured data.

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations, ONLY the JSON object.

Required JSON format:
{{
  "name": "recipe name",
  "yield": {{"quantity": 2.0, "unit": "quart"}},
  "description": "brief description (optional)",
  "category": "category name (optional, e.g., Sauces, Entrees, Desserts)",
  "ingredients": [
    {{
      "name": "ingredient name",
      "quantity": 10.0,
      "unit": "LB",
      "prep_note": "chopped (optional)"
    }}
  ]
}}

Extraction rules:
1. Extract the recipe name (required)
2. Extract yield with quantity and unit (e.g., "2 quart", "4 portions", "1 gallon")
3. Extract each ingredient with:
   - name: Core ingredient name (e.g., "cucumber", "olive oil")
   - quantity: Numeric value (convert fractions to decimals, e.g., 1/2 = 0.5)
   - unit: Standard unit abbreviation (LB, OZ, GAL, QT, PT, CUP, TBSP, TSP, EA, etc.)
   - prep_note: Preparation instruction if mentioned (e.g., "diced", "sliced", "fresh")
4. If description or category are present in the text, include them
5. Normalize units to standard abbreviations:
   - Pounds -> LB
   - Ounces -> OZ
   - Gallons -> GAL
   - Quarts -> QT
   - Tablespoons -> TBSP
   - Teaspoons -> TSP
   - Each/piece -> EA
6. For ranges (e.g., "2-3 cups"), use the average (2.5)
7. If no clear unit, use "EA" (each)

Recipe text:
{text}

Return JSON:"""

    return prompt


def validate_recipe_data(data: Dict) -> None:
    """
    Validate that Claude returned proper recipe structure.

    Args:
        data: Parsed recipe data

    Raises:
        HTTPException: If data is invalid
    """

    # Check required fields
    if 'name' not in data or not data['name']:
        raise HTTPException(
            status_code=400,
            detail="Could not extract recipe name from document"
        )

    if 'ingredients' not in data or not data['ingredients']:
        raise HTTPException(
            status_code=400,
            detail="Could not extract ingredients from document"
        )

    if not isinstance(data['ingredients'], list):
        raise HTTPException(
            status_code=400,
            detail="Invalid ingredients format"
        )

    # Validate yield if present
    if 'yield' in data and data['yield']:
        yield_data = data['yield']
        if not isinstance(yield_data, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid yield format"
            )

        if 'quantity' not in yield_data or 'unit' not in yield_data:
            raise HTTPException(
                status_code=400,
                detail="Yield must have quantity and unit"
            )

        try:
            float(yield_data['quantity'])
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Yield quantity must be numeric"
            )

    # Validate each ingredient
    for i, ingredient in enumerate(data['ingredients']):
        if not isinstance(ingredient, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient {i+1} has invalid format"
            )

        if 'name' not in ingredient or not ingredient['name']:
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient {i+1} missing name"
            )

        if 'quantity' not in ingredient:
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient {i+1} ({ingredient['name']}) missing quantity"
            )

        if 'unit' not in ingredient:
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient {i+1} ({ingredient['name']}) missing unit"
            )

        # Validate quantity is numeric
        try:
            float(ingredient['quantity'])
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient {i+1} ({ingredient['name']}) has invalid quantity: {ingredient['quantity']}"
            )


def determine_parse_status(
    recipe_data: Dict,
    ingredients_matched: int,
    total_ingredients: int
) -> str:
    """
    Determine if parse should be marked as 'success' or 'partial'.

    Success criteria:
    - Has recipe name
    - Has at least 1 ingredient
    - Has yield information
    - >50% of ingredients have product matches

    Args:
        recipe_data: Parsed recipe data from Claude
        ingredients_matched: Number of ingredients with product matches
        total_ingredients: Total number of ingredients

    Returns:
        'success' or 'partial'
    """

    has_name = bool(recipe_data.get('name'))
    has_ingredients = bool(recipe_data.get('ingredients'))
    has_yield = bool(recipe_data.get('yield'))

    match_rate = ingredients_matched / total_ingredients if total_ingredients > 0 else 0

    # Success if has all core data and decent match rate
    if has_name and has_ingredients and has_yield and match_rate > 0.5:
        return 'success'

    # Partial if missing some data but still useful
    if has_name and has_ingredients:
        return 'partial'

    # This shouldn't happen due to validation, but fallback
    return 'failed'
