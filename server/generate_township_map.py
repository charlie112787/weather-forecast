
import json
import os
from core.image_analyzer import project_townships_to_pixels, _download_image
from core.image_url_resolver import resolve_ncdr_daily_rain_url
from draw_circles_on_samples import save_overlay_on_local_image

def generate_map_with_all_townships(radius: int, output_dir: str):
    """
    Generates a CWA map with circles over all townships.
    """
    # 1. Get the latest CWA daily rain map URL
    image_url = resolve_ncdr_daily_rain_url()
    if not image_url:
        print("Could not resolve CWA image URL.")
        return

    # 2. Download the image and get its size
    try:
        image = _download_image(image_url)
        image_size = image.size
        # Save the base image temporarily to be used by the drawing function
        base_image_path = os.path.join(output_dir, "base_cwa_map.png")
        os.makedirs(output_dir, exist_ok=True)
        image.save(base_image_path)
    except Exception as e:
        print(f"Failed to download or save base image: {e}")
        return

    # 3. Load township location data
    try:
        with open("temp/cwa_location_data.json", "r", encoding="utf-8") as f:
            # This is a list of dictionaries, need to parse it
            locations_data = json.load(f)
    except Exception as e:
        print(f"Failed to load location data: {e}")
        return

    # 4. Prepare lon/lat dictionary for the projection function
    township_to_lonlat = {}
    # The json is a list of location dicts
    for location in locations_data:
        name = location.get("LocationName")
        lat = location.get("Latitude")
        lon = location.get("Longitude")
        if name and lat and lon:
            # Assuming the location name is unique
            township_to_lonlat[name] = (float(lon), float(lat))


    # 5. Project lon/lat to pixel coordinates
    try:
        pixel_coords_map = project_townships_to_pixels(township_to_lonlat, image_size)
        centers = list(pixel_coords_map.values())
    except ValueError as e:
        print(f"Error during coordinate projection: {e}")
        print(f"The downloaded image size {image_size} may not be supported.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during projection: {e}")
        return

    # 6. Draw circles on the image
    output_path = os.path.join(output_dir, "township_map.png")
    try:
        save_overlay_on_local_image(base_image_path, centers, radius, output_path)
        print(f"Successfully generated map with {len(centers)} townships.")
        print(f"Output saved to: {output_path}")
    except Exception as e:
        print(f"Failed to draw circles and save the final image: {e}")
    finally:
        # Clean up the temporary base image
        if os.path.exists(base_image_path):
            os.remove(base_image_path)

if __name__ == "__main__":
    OUTPUT_DIRECTORY = "analyzed_images"
    CIRCLE_RADIUS = 12
    generate_map_with_all_townships(radius=CIRCLE_RADIUS, output_dir=OUTPUT_DIRECTORY)
