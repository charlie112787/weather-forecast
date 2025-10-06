from fastapi import APIRouter, HTTPException
from server.core import calculation
from server.scheduler import jobs

router = APIRouter()

@router.get("/{township_name}", summary="Get Combined Forecast for a Township")
async def get_township_forecast(township_name: str):
    """
    Provides a combined forecast (CWA API + NCDR Image Radius Scan) for a specific township.
    """
    from urllib.parse import unquote
    decoded_township_name = unquote(township_name)

    cwa_data = jobs.get_cached_cwa_data()
    ncdr_image = jobs.get_cached_ncdr_image()

    if not cwa_data:
        raise HTTPException(status_code=503, detail="CWA forecast data is not available yet. Please try again in a moment.")
    
    forecast = calculation.get_forecast_for_township(
        township_name=decoded_township_name, 
        all_cwa_data=cwa_data, 
        ncdr_image_data=ncdr_image
    )

    if not forecast:
        raise HTTPException(status_code=404, detail=f"Forecast for township '{decoded_township_name}' not found.")
    
    if isinstance(ncdr_image, dict):
        forecast['ncdr_forecast'] = ncdr_image

    return forecast