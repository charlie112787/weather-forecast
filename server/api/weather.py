from fastapi import APIRouter, HTTPException
from ..core import calculation
from ..scheduler import jobs

router = APIRouter()

@router.get("/{township_name}", summary="Get Combined Forecast for a Township")
async def get_township_forecast(township_name: str):
    """
    Provides a combined forecast (CWA API + NCDR Image Grid) for a specific township.
    The data is based on the last run of the scheduled data fetching job.
    """
    # URL Decode the township name, e.g., from %E8%87%BA%E5%8C%97%E5%B8%82%E4%B8%AD%E6%AD%A3%E5%8D%80 to 臺北市中正區
    from urllib.parse import unquote
    decoded_township_name = unquote(township_name)

    # Get the cached data from the scheduler module
    cwa_data = jobs.get_cached_cwa_data()
    ncdr_grid = jobs.get_cached_ncdr_grid()

    if not cwa_data:
        raise HTTPException(status_code=503, detail="CWA forecast data is not available yet. Please try again in a moment.")

    # Get the combined forecast using the calculation logic
    forecast = calculation.get_forecast_for_township(
        township_name=decoded_township_name, 
        all_cwa_data=cwa_data, 
        ncdr_grid=ncdr_grid
    )

    if not forecast:
        raise HTTPException(status_code=404, detail=f"Forecast for township '{decoded_township_name}' not found.")

    return forecast