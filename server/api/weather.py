from fastapi import APIRouter, HTTPException
from server.core import calculation
from server.scheduler import jobs

router = APIRouter()

@router.get("/ping", summary="Health check")
async def ping():
    return {"status": "ok"}


@router.get("/county/{county_name}", summary="Get CWA Forecast for a County")
async def get_county_forecast(county_name: str):
    """
    Provides a CWA forecast for a specific county based on cached data.
    """
    from urllib.parse import unquote
    decoded_county_name = unquote(county_name)

    cwa_county_data = jobs.get_cached_cwa_county_data()
    if not cwa_county_data or 'records' not in cwa_county_data:
        raise HTTPException(status_code=503, detail="CWA county forecast data is not available yet. Please try again in a moment.")

    # Find county
    target = None
    for loc in cwa_county_data['records'].get('location', []):
        if loc.get('locationName') == decoded_county_name:
            target = loc
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Forecast for county '{decoded_county_name}' not found.")

    # Simplify county elements (similar approach to township)
    elements = {}
    for element in target.get('weatherElement', []):
        name = element.get('elementName')
        value = None
        time_arr = element.get('time') or []
        if time_arr and time_arr[0].get('parameter'):
            # County dataset uses 'parameter' instead of 'elementValue'
            param = time_arr[0]['parameter']
            value = param.get('parameterName')
        elements[name] = value

    return {
        "county": decoded_county_name,
        "cwa_forecast": {
            "temperature": elements.get("T"),
            "chance_of_rain_12h": elements.get("PoP12h"),
            "weather_description": elements.get("Wx"),
        },
    }


@router.get("/metrics/images", summary="Get image-derived weather metrics")
async def get_image_metrics():
    metrics = jobs.get_cached_image_metrics()
    if not metrics:
        raise HTTPException(status_code=503, detail="Image metrics are not available yet. Please try again in a moment.")
    return metrics


@router.get("/summary", summary="Get combined summary for a county")
async def get_summary(county_name: str):
    """
    Combines CWA county-level temperature/weather with image-derived PoP6/PoP12 and AQI.
    """
    from urllib.parse import unquote
    decoded_county_name = unquote(county_name)
    print(f"[summary] county={decoded_county_name}")

    # County weather from CWA
    cwa_county_data = jobs.get_cached_cwa_county_data()
    if not cwa_county_data or 'records' not in cwa_county_data:
        raise HTTPException(status_code=503, detail="CWA county forecast data is not available yet. Please try again in a moment.")

    target = None
    for loc in cwa_county_data['records'].get('location', []):
        if loc.get('locationName') == decoded_county_name:
            target = loc
            break
    if not target:
        raise HTTPException(status_code=404, detail=f"Forecast for county '{decoded_county_name}' not found.")

    elements = {}
    for element in target.get('weatherElement', []):
        name = element.get('elementName')
        value = None
        time_arr = element.get('time') or []
        if time_arr and time_arr[0].get('parameter'):
            param = time_arr[0]['parameter']
            value = param.get('parameterName')
        elements[name] = value

    # Image metrics
    metrics = jobs.get_cached_image_metrics() or {}
    qpf_for_county = jobs.get_qpf_for_county(decoded_county_name) or {}

    resp = {
        "county": decoded_county_name,
        "temperature": elements.get("T"),
        "weather_description": elements.get("Wx"),
        "pop12_percent": metrics.get("pop12_percent"),
        "pop6_percent": metrics.get("pop6_percent"),
        "qpf12_mm_per_hr": qpf_for_county.get("qpf12_mm_per_hr"),
        "qpf6_mm_per_hr": qpf_for_county.get("qpf6_mm_per_hr"),
        "aqi_level": metrics.get("aqi_level"),
    }
    print(f"[summary] resp={resp}")
    return resp


@router.get("/debug/townships", summary="Debug: list discovered township names")
async def debug_list_townships(limit: int = 50):
    data = jobs.get_cached_cwa_township_data()
    if not data:
        return {"townships": []}
    names = calculation.list_township_names(data, limit=limit)
    return {"townships": names, "count": len(names)}


@router.get("/{township_name}", summary="Get CWA Forecast for a Township")
async def get_township_forecast(township_name: str):
    """
    Provides a CWA forecast for a specific township based on cached data.
    """
    from urllib.parse import unquote
    decoded_township_name = unquote(township_name)

    cwa_data = jobs.get_cached_cwa_township_data()

    if not cwa_data:
        raise HTTPException(status_code=503, detail="CWA forecast data is not available yet. Please try again in a moment.")

    forecast = calculation.get_forecast_for_township(
        township_name=decoded_township_name, 
        all_cwa_data=cwa_data
    )

    if not forecast:
        raise HTTPException(status_code=404, detail=f"Forecast for township '{decoded_township_name}' not found.")

    return forecast
