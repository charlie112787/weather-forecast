import os
from PIL import Image, ImageDraw

def save_overlay_on_local_image(image_path: str, centers: list[tuple[int, int]], radius: int, out_path: str) -> None:
    """
    在指定圖片上畫上取樣圓，存檔以便檢視。
    """
    try:
        base = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # 畫法：紅色實心圓
        for (cx, cy) in centers:
            if cx is None or cy is None:
                continue
            if cx < 0 or cy < 0 or cx >= base.width or cy >= base.height:
                continue
            bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
            # filled red
            draw.ellipse(bbox, fill=(255, 0, 0, 255))
        img = Image.alpha_composite(base, overlay).convert("RGB")
        # 確保輸出目錄存在
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        # 一律用 PNG 以保留顯示品質
        if not out_path.lower().endswith('.png'):
            out_path = out_path + '.png'
        img.save(out_path)
    except Exception as e:
        print(f"Error processing image: {image_path} - {e}")
        pass

def process_samples(radius: int):
    """
    遍歷 samples 資料夾中的所有圖片，並在每張圖片上繪製半徑為 radius 的紅色圓圈。
    """
    samples_dir = "samples"
    for filename in os.listdir(samples_dir):
        if filename.endswith(".png"):
            image_path = os.path.join(samples_dir, filename)
            # 假設中心點位於圖片中心
            try:
                img = Image.open(image_path)
                width, height = img.size
                center_x = width // 2
                center_y = height // 2
                centers = [(center_x, center_y)]
                out_path = image_path  # 覆蓋原始檔案
                save_overlay_on_local_image(image_path, centers, radius, out_path)
                print(f"Processed {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    process_samples(radius=12)