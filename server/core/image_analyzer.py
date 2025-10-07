import io
from typing import Optional, Tuple, Dict, List

import requests
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
except ImportError:  # Optional at import time; function will raise if used without install
    pytesseract = None  # type: ignore


def _download_image(image_url: str) -> Image.Image:
    from server import config
    response = requests.get(image_url, timeout=15, verify=getattr(config, "REQUESTS_VERIFY_SSL", True))
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _ensure_tesseract_is_available() -> None:
    if pytesseract is None:
        raise RuntimeError(
            "pytesseract is not installed. Please add 'pytesseract' to requirements and install Tesseract OCR runtime."
        )


def configure_tesseract_cmd(tesseract_cmd_path: Optional[str]) -> None:
    """
    Optionally configure pytesseract binary path at runtime (useful on Windows).
    """
    if pytesseract and tesseract_cmd_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path


def extract_rain_probability_from_image(image_url: str, crop_box: Optional[Tuple[int, int, int, int]] = None) -> Optional[int]:
    """
    Download an image that contains rain probability text and OCR the value as an integer percentage.

    Args:
        image_url: URL of the image to analyze.
        crop_box: Optional crop region (left, upper, right, lower) targeting the text area for OCR.

    Returns:
        An integer percentage (0-100) if parsed successfully, otherwise None.
    """
    _ensure_tesseract_is_available()

    image = _download_image(image_url)
    if crop_box:
        image = image.crop(crop_box)

    # Simple preprocessing for OCR: grayscale, increase contrast, sharpen
    grayscale = ImageOps.grayscale(image)
    enhanced = grayscale.filter(ImageFilter.SHARPEN)

    ocr_text = pytesseract.image_to_string(enhanced)  # type: ignore[attr-defined]
    # Extract first number sequence as percentage
    digits = []
    for ch in ocr_text:
        if ch.isdigit():
            digits.append(ch)
        elif digits:
            break

    if not digits:
        return None

    try:
        value = int("".join(digits))
        if 0 <= value <= 100:
            return value
        return None
    except ValueError:
        return None


def analyze_aqi_from_image(image_url: str, sample_box: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
    """
    Infer AQI qualitative level by sampling color from a designated region.

    The function samples the median color of the region and maps it to standard AQI color bins.

    Args:
        image_url: URL of the AQI map image.
        sample_box: Optional region (left, upper, right, lower) focusing on the legend/target city color.

    Returns:
        One of: "Good", "Moderate", "Unhealthy for Sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"; or None if unknown.
    """
    image = _download_image(image_url)
    if sample_box:
        image = image.crop(sample_box)

    # Downscale and sample a grid to get a robust median color
    small = image.resize((32, 32))
    pixels = list(small.getdata())
    r_values = sorted(p[0] for p in pixels)
    g_values = sorted(p[1] for p in pixels)
    b_values = sorted(p[2] for p in pixels)
    median = (
        r_values[len(r_values) // 2],
        g_values[len(g_values) // 2],
        b_values[len(b_values) // 2],
    )

    return _map_color_to_aqi(median)


def _map_color_to_aqi(rgb: Tuple[int, int, int]) -> Optional[str]:
    r, g, b = rgb

    # Rough color mapping consistent with US EPA AQI colors
    # Good:      Green (~(0-100, 150-255, 0-100))
    # Moderate:  Yellow (~(150-255, 150-255, 0-80))
    # USG:       Orange (~(200-255, 120-180, 0-60))
    # Unhealthy: Red (~(180-255, 0-100, 0-100))
    # Very Unhealthy: Purple (~(150-220, 0-80, 150-220))
    # Hazardous: Maroon (~(100-180, 0-60, 0-60))

    if g > 150 and r < 120 and b < 120:
        return "Good"
    if r > 170 and g > 170 and b < 90:
        return "Moderate"
    if r > 200 and 110 < g < 190 and b < 80:
        return "Unhealthy for Sensitive"
    if r > 180 and g < 110 and b < 110:
        return "Unhealthy"
    if r > 140 and b > 140 and g < 100:
        return "Very Unhealthy"
    if r > 100 and g < 70 and b < 70:
        return "Hazardous"
    return None


def _closest_color(value: Tuple[int, int, int], palette: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    vr, vg, vb = value
    best = None
    best_dist = 1e9
    for pr, pg, pb in palette:
        d = (vr - pr) ** 2 + (vg - pg) ** 2 + (vb - pb) ** 2
        if d < best_dist:
            best_dist = d
            best = (pr, pg, pb)
    assert best is not None
    return best


def analyze_qpf_from_image(image_url: str, sample_xy: Tuple[int, int]) -> Optional[Dict[str, float]]:
    """
    Estimate rainfall intensity (mm/hr) by analyzing a square region and returning the min and max QPF values.
    """
    from server import config
    image = _download_image(image_url)
    x_center, y_center = sample_xy

    box_size = 20
    half_box = box_size // 2

    # Define the bounding box for the area
    left = max(0, x_center - half_box)
    top = max(0, y_center - half_box)
    right = min(image.width, x_center + half_box)
    bottom = min(image.height, y_center + half_box)

    if left >= right or top >= bottom:
        return None

    qpf_values = []
    palette = list(config.QPF_COLOR_MAP.keys())

    # Iterate over all pixels in the bounding box
    for y in range(top, bottom):
        for x in range(left, right):
            rgb = image.getpixel((x, y))[:3]
            nearest_color = _closest_color(rgb, palette)
            qpf_value = config.QPF_COLOR_MAP.get(nearest_color)
            # Exclude 0.0 values from min/max calculation unless it's the only value
            if qpf_value is not None and qpf_value > 0:
                qpf_values.append(qpf_value)

    if not qpf_values:
        # If no rain, return 0.0 for both min and max
        return {"min": 0.0, "max": 0.0}

    # Return the min and max QPF values found in the area
    return {"min": min(qpf_values), "max": max(qpf_values)}

def analyze_ncdr_rain_from_image(image_url: str, sample_xy: Tuple[int, int]) -> Optional[Dict[str, float]]:
    """
    Estimate rainfall intensity (mm/hr) from NCDR images by analyzing a square region 
    and returning the min and max QPF values.
    """
    from server import config
    image = _download_image(image_url)
    x_center, y_center = sample_xy

    box_size = 20
    half_box = box_size // 2

    # Define the bounding box for the area
    left = max(0, x_center - half_box)
    top = max(0, y_center - half_box)
    right = min(image.width, x_center + half_box)
    bottom = min(image.height, y_center + half_box)

    if left >= right or top >= bottom:
        return None

    qpf_values = []
    palette = list(config.NCDR_NOWCAST_COLOR_MAP.keys())

    # Iterate over all pixels in the bounding box
    for y in range(top, bottom):
        for x in range(left, right):
            rgb = image.getpixel((x, y))[:3]
            nearest_color = _closest_color(rgb, palette)
            qpf_value = config.NCDR_NOWCAST_COLOR_MAP.get(nearest_color)
            # Exclude 0.0 values from min/max calculation unless it's the only value
            if qpf_value is not None and qpf_value > 0:
                qpf_values.append(qpf_value)

    if not qpf_values:
        # If no rain, return 0.0 for both min and max
        return {"min": 0.0, "max": 0.0}

    # Return the min and max QPF values found in the area
    return {"min": min(qpf_values), "max": max(qpf_values)}


