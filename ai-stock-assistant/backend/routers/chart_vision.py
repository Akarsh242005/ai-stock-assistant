from utils import sanitize_for_json
'\n============================================================\nChart Vision Router — /api/chart\n============================================================\nEndpoints:\n  POST /api/chart/analyze — upload chart screenshot\n============================================================\n'
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.chart_vision_service import analyze_chart_image
router = APIRouter()
ALLOWED_TYPES = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}
MAX_SIZE_MB = 10

@router.post('/analyze')
async def analyze_chart(file: UploadFile=File(...)):
    """
    Upload a NIFTY / stock chart screenshot for AI analysis.

    Returns:
      - Signal: BUY / SELL / WAIT
      - Trend: Bullish / Bearish / Sideways
      - Confidence score
      - Detected patterns
      - Support/Resistance levels
      - Detailed reasoning
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f'Invalid file type: {file.content_type}. Upload PNG or JPG.')
    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f'File too large. Max size: {MAX_SIZE_MB}MB')
    if len(image_bytes) < 1000:
        raise HTTPException(status_code=400, detail='Image too small or corrupted. Please upload a valid chart screenshot.')
    result = analyze_chart_image(image_bytes)
    return sanitize_for_json({'status': 'success', 'filename': file.filename, **result})