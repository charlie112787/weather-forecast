import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from core import calculation
from scheduler import jobs
from core import codes
from services import discord_sender
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/ping", summary="Health check")
async def ping():
	return {"status": "ok"}


@router.get("/all", summary="Get all weather data in the final JSON format")
async def get_all_weather_data():
    """
    Provides a combined JSON output of all weather data.
    """
    final_json = jobs.get_cached_weather_data()
    if not final_json:
        raise HTTPException(status_code=503, detail="The final JSON data is not available yet. Please try again in a moment.")
    return final_json


@router.get("/county/{county_name}", summary="Get CWA Forecast for a County")
async def get_county_forecast(county_name: str):
    """
    Provides a CWA forecast for a specific county based on cached data.
    """
    from urllib.parse import unquote
    decoded_county_name = unquote(county_name)
    logger.info(f"Fetching forecast for county: {decoded_county_name}")
    
    try:
        cwa_county_data = jobs.get_cached_weather_data().get('county_weather')
        if not cwa_county_data:
            logger.error("CWA county data not available")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Data unavailable",
                    "message": "CWA county forecast data is not available yet. Please try again in a moment.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Find county
        target = cwa_county_data.get(decoded_county_name)

        if not target:
            logger.error(f"County forecast not found: {decoded_county_name}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "County not found",
                    "county": decoded_county_name,
                    "message": f"Could not find forecast data for county '{decoded_county_name}'. Please check the county name or code.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Simplify county elements (similar approach to township)
        elements = target

        result = {
            "county": decoded_county_name,
            "cwa_forecast": {
                "temperature": elements.get("T"),
                "chance_of_rain_12h": elements.get("PoP12h"),
                "weather_description": elements.get("Wx"),
            },
        }
        logger.info(f"Successfully fetched forecast for county: {decoded_county_name}")
        return result

    except Exception as e:
        logger.error(f"Unexpected error while fetching county forecast: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request.",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/metrics/images", summary="Get image-derived weather metrics")
async def get_image_metrics():
    metrics = jobs.CACHED_IMAGE_METRICS
    if not metrics:
        raise HTTPException(status_code=503, detail="Image metrics are not available yet. Please try again in a moment.")
    return metrics


@router.get("/summary", summary="Get combined summary for a county")
async def get_summary(county_name: str = "", county_code: str = "") -> Dict[str, Any]:
    """
    Combines CWA county-level temperature/weather with image-derived PoP6/PoP12 and AQI.
    """
    logger.info(f"Getting weather summary for county_name='{county_name}' code='{county_code}'")
    
    try:
        from urllib.parse import unquote
        if county_code:
            decoded_county_name = codes.COUNTY_CODE_TO_NAME.get(county_code, county_code)
        else:
            decoded_county_name = unquote(county_name)
        logger.info(f"Looking up county: {decoded_county_name}")

        # County weather from CWA
        cwa_county_data = jobs.get_cached_weather_data().get('county_weather')
        if not cwa_county_data:
            logger.error("CWA county data not available")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Data unavailable",
                    "message": "CWA county forecast data is not available yet. Please try again in a moment.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        target = cwa_county_data.get(decoded_county_name)
                
        if not target:
            logger.error(f"County not found: {decoded_county_name}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "County not found",
                    "county": decoded_county_name,
                    "message": f"Could not find forecast data for county '{decoded_county_name}'. Please check the county name or code.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        elements = target

        # Image metrics from the consolidated cache
        image_metrics = jobs.CACHED_IMAGE_METRICS.get(decoded_county_name) or {}
        # 兼容不同鍵名（作業程序可能存為 daily_rain/nowcast）
        daily_rain = image_metrics.get("ncdr_daily_rain") or image_metrics.get("daily_rain")
        nowcast = image_metrics.get("ncdr_nowcast") or image_metrics.get("nowcast")

        resp = {
            "county": decoded_county_name,
            "temperature": elements.get("T"),
            "weather_description": elements.get("Wx"),
            "qpf12_max_mm_per_hr": image_metrics.get("qpf12_max_mm_per_hr"),
            "qpf12_min_mm_per_hr": image_metrics.get("qpf12_min_mm_per_hr"),
            "qpf6_max_mm_per_hr": image_metrics.get("qpf6_max_mm_per_hr"),
            "qpf6_min_mm_per_hr": image_metrics.get("qpf6_min_mm_per_hr"),
            "aqi_level": image_metrics.get("aqi_level"),
            "ncdr_nowcast": nowcast,
            "ncdr_daily_rain": daily_rain,
        }
        logger.info(f"Successfully fetched summary for county: {decoded_county_name}")
        return resp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching county summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request.",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/debug/townships", summary="Debug: list discovered township names")
async def debug_list_townships(limit: int = 50):
    data = jobs.get_cached_weather_data().get('township_weather')
    if not data:
        return {"townships": []}
    names = list(data.keys())[:limit]
    return {"townships": names, "count": len(data)}


@router.get("/codes", summary="List supported county/township codes")
async def list_codes():
    return {
        "counties": codes.COUNTY_NAME_TO_CODE,
        "townships": codes.TOWNSHIP_NAME_TO_CODE,
    }


@router.get("/", summary="Get CWA Forecast for a Township")
async def get_township_forecast(township_name: str = "", township_code: str = ""):
    """
    Provides a CWA forecast for a specific township based on cached data.
    """
    logger.info(f"Getting township forecast for name='{township_name}' code='{township_code}'")
    
    try:
        from urllib.parse import unquote
        if township_code:
            decoded_township_name = codes.TOWNSHIP_CODE_TO_NAME.get(township_code, township_code)
            logger.info(f"Looking up township by code: {township_code} -> {decoded_township_name}")
        else:
            decoded_township_name = unquote(township_name)
            logger.info(f"Looking up township by name: {decoded_township_name}")

        township_map = jobs.get_cached_weather_data().get('township_weather')
        forecast = None
        
        if township_map:
            forecast = calculation.get_forecast_for_township(
                township_name=decoded_township_name,
                township_map=township_map
            )
        else:
            # Fallback: try to parse directly from full records if map not ready
            logger.warning("Township map not available, falling back to full records")
            cwa_full = jobs.CACHED_CWA_TOWNSHIP_DATA
            if cwa_full:
                forecast = calculation.get_forecast_for_township_from_records(
                    township_name=decoded_township_name,
                    all_cwa_data=cwa_full,
                )

        if not forecast:
            logger.error(f"Township forecast not found: {decoded_township_name}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Township not found",
                    "township": decoded_township_name,
                    "message": f"Could not find forecast data for township '{decoded_township_name}'. Please check the township name or code.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Attach county-derived metrics from the consolidated image metrics cache
        county_name = codes.resolve_county_from_township_name(decoded_township_name)
        image_metrics = jobs.CACHED_IMAGE_METRICS.get(county_name) or {}
        # 兼容不同鍵名（作業程序可能存為 daily_rain/nowcast）
        daily_rain = image_metrics.get("ncdr_daily_rain") or image_metrics.get("daily_rain")
        nowcast = image_metrics.get("ncdr_nowcast") or image_metrics.get("nowcast")

        response = {
            **forecast,
            "qpf12_max_mm_per_hr": image_metrics.get("qpf12_max_mm_per_hr"),
            "qpf12_min_mm_per_hr": image_metrics.get("qpf12_min_mm_per_hr"),
            "qpf6_max_mm_per_hr": image_metrics.get("qpf6_max_mm_per_hr"),
            "qpf6_min_mm_per_hr": image_metrics.get("qpf6_min_mm_per_hr"),
            "aqi_level": image_metrics.get("aqi_level"),
            "ncdr_nowcast": nowcast,
            "ncdr_daily_rain": daily_rain,
        }
        
        # Format and send to Discord
        message = f"""
        **Weather Report for {response['township']}**

        **CWA Forecast:**
        - Temperature: {response['cwa_forecast']['temperature']}
        - Weather: {response['cwa_forecast']['weather_description']}
        - 12h Rain Chance: {response['cwa_forecast'].get('chance_of_rain_12h', 'N/A')}

        **Image Analysis:**
        - QPF 12h (min/max): {response.get('qpf12_min_mm_per_hr', 'N/A')} / {response.get('qpf12_max_mm_per_hr', 'N/A')}
        - QPF 6h (min/max): {response.get('qpf6_min_mm_per_hr', 'N/A')} / {response.get('qpf6_max_mm_per_hr', 'N/A')}
        - AQI Level: {response.get('aqi_level', 'N/A')}
        """
        await asyncio.to_thread(discord_sender.send_to_discord, message)

        logger.info(f"Successfully fetched forecast for township: {decoded_township_name}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching township forecast: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request.",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post("/notify/township/{township_name}", summary="Send township summary to Discord")
async def notify_township(township_name: str):
    """
    Send a township's weather forecast summary to Discord.
    """
    logger.info(f"Sending township forecast notification for: {township_name}")
    
    try:
        from urllib.parse import unquote
        decoded_township_name = unquote(township_name)

        township_map = jobs.get_cached_weather_data().get('township_weather')
        if not township_map:
            logger.error("Township map not available")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Data unavailable",
                    "message": "Township map is not available yet. Please try again in a moment.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        forecast = calculation.get_forecast_for_township(
            township_name=decoded_township_name,
            township_map=township_map,
        )
        if not forecast:
            logger.error(f"Township forecast not found: {decoded_township_name}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Township not found",
                    "township": decoded_township_name,
                    "message": f"Could not find forecast data for township '{decoded_township_name}'. Please check the township name.",
                    "timestamp": datetime.now().isoformat()
                }
            )

        county_name = codes.resolve_county_from_township_name(decoded_township_name)
        image_metrics = jobs.CACHED_IMAGE_METRICS.get(county_name) or {}

        msg = (
            f"天氣摘要 - {decoded_township_name}\n"
            f"溫度: {forecast['cwa_forecast'].get('temperature')}\n"
            f"天氣概況: {forecast['cwa_forecast'].get('weather_description')}\n"
            f"12小時降雨機率(鄉): {forecast['cwa_forecast'].get('chance_of_rain_12h')}\n"
            f"12小時降雨強度(縣, mm/hr): {image_metrics.get('qpf12_min_mm_per_hr')} - {image_metrics.get('qpf12_max_mm_per_hr')}\n"
            f"6小時降雨強度(縣, mm/hr): {image_metrics.get('qpf6_min_mm_per_hr')} - {image_metrics.get('qpf6_max_mm_per_hr')}\n"
            f"AQI 等級(縣): {image_metrics.get('aqi_level')}\n"
        )

        try:
            await asyncio.to_thread(discord_sender.send_to_discord, msg)
            logger.info(f"Successfully sent Discord notification for township: {decoded_township_name}")
            return {"ok": True}
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Discord notification failed",
                    "message": "Failed to send notification to Discord. Please try again later.",
                    "timestamp": datetime.now().isoformat()
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in notify_township: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request.",
                "timestamp": datetime.now().isoformat()
            }
        )