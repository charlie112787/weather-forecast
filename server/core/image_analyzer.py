import io
from typing import Optional, Tuple, Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
except ImportError:  # Optional at import time; function will raise if used without install
    pytesseract = None  # type: ignore


def _download_image(image_url: str) -> Image.Image:
    from server import config
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    response = session.get(image_url, timeout=20, verify=getattr(config, "REQUESTS_VERIFY_SSL", True))
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


def _sample_circle_min_max(image: Image.Image, center_xy: Tuple[int, int], radius: int, palette: List[Tuple[int, int, int]], value_map: Dict[Tuple[int, int, int], float]) -> Dict[str, float]:
    """
    Sample pixels in a filled circle around center_xy with given radius.
    Return min/max mapped values (excluding 0 unless only zeros present).
    """
    cx, cy = center_xy
    r2 = radius * radius
    qpf_values: List[float] = []
    for y in range(max(0, cy - radius), min(image.height, cy + radius + 1)):
        dy = y - cy
        dy2 = dy * dy
        # Compute horizontal span for this scanline to avoid sqrt
        # x such that (x-cx)^2 + dy^2 <= r^2  -> |x-cx| <= floor(sqrt(r^2 - dy^2))
        # Iterate full box and check condition to keep code simple and robust
        for x in range(max(0, cx - radius), min(image.width, cx + radius + 1)):
            dx = x - cx
            if dx * dx + dy2 > r2:
                continue
            rgb = image.getpixel((x, y))[:3]
            nearest = _closest_color(rgb, palette)
            v = value_map.get(nearest)
            if v is not None and v > 0:
                qpf_values.append(v)
    if not qpf_values:
        return {"min": 0.0, "max": 0.0}
    return {"min": min(qpf_values), "max": max(qpf_values)}


def save_overlay(image_url: str, centers: List[Tuple[int, int]], radius: int, out_path: str) -> None:
    """
    下載圖片並在指定座標畫上取樣圓，存檔以便檢視。
    """
    try:
        from PIL import ImageDraw
        base = _download_image(image_url).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # 畫法：半透明紅色實心 + 黑色外框 + 十字準星
        for (cx, cy) in centers:
            if cx is None or cy is None:
                continue
            if cx < 0 or cy < 0 or cx >= base.width or cy >= base.height:
                continue
            bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
            # Draw a solid red circle as requested by the user.
            draw.ellipse(bbox, fill=(255, 0, 0, 255))
        img = Image.alpha_composite(base, overlay).convert("RGB")
        # 確保輸出目錄存在
        import os
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        # 一律用 PNG 以保留顯示品質
        if not out_path.lower().endswith('.png'):
            out_path = out_path + '.png'
        img.save(out_path)
    except Exception:
        pass


def compute_affine_from_three_points(
    src1: Tuple[float, float], src2: Tuple[float, float], src3: Tuple[float, float],
    dst1: Tuple[float, float], dst2: Tuple[float, float], dst3: Tuple[float, float],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Compute 2D affine transform mapping src -> dst using three non-collinear points.
    Returns matrix rows (a, b, tx), (c, d, ty) so that:
      x' = a*x + b*y + tx
      y' = c*x + d*y + ty
    """
    x1, y1 = src1; x2, y2 = src2; x3, y3 = src3
    u1, v1 = dst1; u2, v2 = dst2; u3, v3 = dst3

    # Solve linear system for a,b,tx and c,d,ty separately
    def solve(u1, u2, u3):
        # Matrix M = [[x1, y1, 1],[x2, y2, 1],[x3, y3, 1]] * [a,b,tx]^T = [u1,u2,u3]^T
        D = x1*(y2*1 - y3*1) - y1*(x2*1 - x3*1) + 1*(x2*y3 - x3*y2)
        if D == 0:
            raise ValueError("Source points are collinear")
        # Corrected determinants for a and b using Cramer's rule
        Da = u1 * (y2 - y3) - y1 * (u2 - u3) + 1 * (u2 * y3 - u3 * y2)
        Db = x1 * (u2 - u3) - u1 * (x2 - x3) + 1 * (x2 * u3 - x3 * u2)
        Dt = x1*(y2*u3 - y3*u2) - y1*(x2*u3 - x3*u2) + u1*(x2*y3 - x3*y2)
        a = Da / D
        b = Db / D
        t = Dt / D
        return a, b, t

    a, b, tx = solve(u1, u2, u3)
    c, d, ty = solve(v1, v2, v3)
    return (a, b, tx), (c, d, ty)


def apply_affine(matrix: Tuple[Tuple[float, float, float], Tuple[float, float, float]],
                 xy: Tuple[float, float]) -> Tuple[int, int]:
    (a, b, tx), (c, d, ty) = matrix
    x, y = xy
    x2 = a * x + b * y + tx
    y2 = c * x + d * y + ty
    return int(round(x2)), int(round(y2))


# --- Taiwan geographic anchor points (lon, lat) ---
_GEOGRAPHIC_ANCHORS: Dict[str, Tuple[float, float]] = {
    "North": (121.538, 25.297),  # Fuguijiao Cape
    "East": (122.00, 25.009),   # Sandiajiao Cape
    "South": (120.855, 21.904),  # Eluanbi
}


def _affine_for_cwa_image(size: Tuple[int, int]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """
    根據台灣本島最北、最東、最南三個點的像素座標，建立 (lon,lat)->(x,y) 的仿射轉換矩陣。
    size: (width,height) 僅用來區分兩組不同錨點。
    """
    width, height = size

    # Get geographic coordinates for the anchors
    lonlat_north = _GEOGRAPHIC_ANCHORS["North"]
    lonlat_east = _GEOGRAPHIC_ANCHORS["East"]
    lonlat_south = _GEOGRAPHIC_ANCHORS["South"]

    if (width, height) == (450, 810):
        # User-provided pixel coordinates for 450x810 map
        p_north = (335, 5)
        p_east = (435, 73)
        p_south = (189, 803)
    elif (width, height) == (315, 642):
        # User-provided pixel coordinates for 315x642 map
        p_north = (237, 0)
        p_east = (311, 55)
        p_south = (132, 637)
    else:
        # Fallback or error for unsupported sizes
        raise ValueError(f"Unsupported CWA image size for affine transform: {size}")

    # Define source (lon, lat) and destination (pixel x, y) points
    src1, src2, src3 = lonlat_north, lonlat_east, lonlat_south
    dst1, dst2, dst3 = p_north, p_east, p_south

    return compute_affine_from_three_points(src1, src2, src3, dst1, dst2, dst3)


def project_townships_to_pixels(
    township_to_lonlat: Dict[str, Tuple[float, float]],
    size: Tuple[int, int],
) -> Dict[str, Tuple[int, int]]:
    """
    將鄉鎮中心點 (lon,lat) 批次投影到指定 CWA 圖片尺寸的像素座標。
    需要使用者提供的三錨點已內建，城市中心經緯度使用近似值。

    township_to_lonlat: { "臺北市中正區": (lon,lat), ... }
    size: (450,810) 或 (315,642)
    """
    matrix = _affine_for_cwa_image(size)
    result: Dict[str, Tuple[int, int]] = {}
    for town, lonlat in township_to_lonlat.items():
        # 使用 (lon,lat) -> (x,y)
        x, y = apply_affine(matrix, (lonlat[0], lonlat[1]))
        result[town] = (x, y)
    return result


def build_pixel_maps_from_township_coords(township_coords: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, Tuple[int, int]]]:
    """
    將使用者提供的 TOWNSHIP_COORDS (value 內含 'lon','lat') 轉為兩種尺寸的像素座標映射。

    輸入格式：
      {
        "臺北市中正區": {"lat": 25.04, "lon": 121.51},
        ...
      }

    回傳格式：
      {
        "450x810": { "臺北市中正區": (x,y), ... },
        "315x642": { "臺北市中正區": (x,y), ... }
      }
    """
    # 整理成 (lon,lat)
    lonlat_map: Dict[str, Tuple[float, float]] = {}
    for name, coord in township_coords.items():
        lat = coord.get('lat')
        lon = coord.get('lon')
        if lat is None or lon is None:
            continue
        lonlat_map[name] = (float(lon), float(lat))

    pixels_450x810 = project_townships_to_pixels(lonlat_map, (450, 810))
    pixels_315x642 = project_townships_to_pixels(lonlat_map, (315, 642))

    return {
        "450x810": pixels_450x810,
        "315x642": pixels_315x642,
    }

def analyze_qpf_from_image(image_url: str, sample_xy: Tuple[int, int]) -> Optional[Dict[str, float]]:
    """
    Estimate rainfall intensity (mm/hr) by analyzing a square region and returning the min and max QPF values.
    """
    from server import config
    image = _download_image(image_url)
    palette = list(config.QPF_COLOR_MAP.keys())
    return _sample_circle_min_max(image, sample_xy, radius=12, palette=palette, value_map=config.QPF_COLOR_MAP)

def analyze_ncdr_rain_from_image(image_url: str, sample_xy: Tuple[int, int]) -> Optional[Dict[str, float]]:
    """
    Estimate rainfall intensity (mm/hr) from NCDR images by analyzing a square region 
    and returning the min and max QPF values.
    """
    from server import config
    image = _download_image(image_url)
    palette = list(config.NCDR_NOWCAST_COLOR_MAP.keys())
    return _sample_circle_min_max(image, sample_xy, radius=12, palette=palette, value_map=config.NCDR_NOWCAST_COLOR_MAP)



