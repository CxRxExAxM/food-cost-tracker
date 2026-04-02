import { useRef, useState, useEffect, useCallback } from 'react';
import './SignaturePad.css';

/**
 * HTML5 Canvas signature pad component.
 * Mobile-first with touch event handling.
 * Exports signature as base64 PNG.
 */
export default function SignaturePad({
  onSignatureChange,
  width = 400,
  height = 150,
  disabled = false
}) {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);
  const [strokeCount, setStrokeCount] = useState(0);

  // Initialize canvas with white background
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }, []);

  // Get position from mouse or touch event
  const getPosition = useCallback((e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    if (e.touches && e.touches.length > 0) {
      return {
        x: (e.touches[0].clientX - rect.left) * scaleX,
        y: (e.touches[0].clientY - rect.top) * scaleY
      };
    }
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }, []);

  const startDrawing = useCallback((e) => {
    if (disabled) return;
    e.preventDefault();

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const pos = getPosition(e);

    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    setIsDrawing(true);
  }, [disabled, getPosition]);

  const draw = useCallback((e) => {
    if (!isDrawing || disabled) return;
    e.preventDefault();

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const pos = getPosition(e);

    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  }, [isDrawing, disabled, getPosition]);

  const stopDrawing = useCallback((e) => {
    if (!isDrawing) return;
    e?.preventDefault();

    setIsDrawing(false);
    setHasSignature(true);
    setStrokeCount(prev => prev + 1);

    // Export signature after stroke completes
    const canvas = canvasRef.current;
    if (canvas && onSignatureChange) {
      const dataUrl = canvas.toDataURL('image/png');
      onSignatureChange(dataUrl);
    }
  }, [isDrawing, onSignatureChange]);

  const clearSignature = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    setHasSignature(false);
    setStrokeCount(0);
    if (onSignatureChange) {
      onSignatureChange(null);
    }
  }, [onSignatureChange]);

  // Minimum strokes required for valid signature
  const isValid = strokeCount >= 2;

  return (
    <div className={`signature-pad-container ${disabled ? 'disabled' : ''}`}>
      <div className="signature-pad-label">
        <span>Sign below</span>
        {hasSignature && !isValid && (
          <span className="signature-hint">Keep signing...</span>
        )}
        {isValid && (
          <span className="signature-valid">Signature captured</span>
        )}
      </div>

      <div className="signature-pad-wrapper">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className={`signature-canvas ${disabled ? 'disabled' : ''}`}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
        />

        {!hasSignature && !disabled && (
          <div className="signature-placeholder">
            Draw your signature here
          </div>
        )}
      </div>

      <div className="signature-pad-actions">
        <button
          type="button"
          className="btn-clear"
          onClick={clearSignature}
          disabled={!hasSignature || disabled}
        >
          Clear
        </button>
      </div>
    </div>
  );
}
