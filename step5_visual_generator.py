import os
import json
import glob
import requests
import io
import sys
import config
from PIL import Image
from google import genai

sys.stdout.reconfigure(encoding='utf-8')

# --- 頻道風格提示詞 (可隨時調整) ---
# 控制了產圖的格式 (9:16) 與整體畫風。必須強制二次元/科技感風格，避免生成真實照片。
CHANNEL_STYLE_PROMPT = "The image must be visually stunning, masterpiece, high definition. 2D anime style, cel-shaded illustration, vibrant colors. Cyberpunk or modern high-tech VTuber vibe style. ABSOLUTELY NO photorealism, no photography, no real people. Ensure all characters are drawn in 2D anime style. CRITICAL RULE: ABSOLUTELY NO TEXT, NO CHINESE CHARACTERS, NO WORDS, NO LETTERS on the image. Use pure graphical elements, symbols, or numbers only to avoid gibberish text generation."


def download_image(url, log=print):
    """取得圖片：支援 http(s) 網路連結或本地檔案路徑"""
    if not url:
        return None

    # 檢查是否為本地路徑
    if os.path.exists(url):
        try:
            return Image.open(url)
        except Exception as e:
            log(f"    ❌ 讀取本地圖片失敗 [{url}]: {e}")
            return None

    # 反之視為網路連結
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        log(f"    ❌ 下排原圖失敗 (非本地檔案，試圖從網路抓取時報錯) [{url}]: {e}")
        return None


def analyze_image_with_gemini(client, pil_image, log=print):
    """使用 Gemini 2.5 Flash 來「看」原圖，並產出文字描述"""
    try:
        # 要求解構時不要使用真實照片相關字眼，只純述核心要素
        prompt = "Describe the contents of this image (subjects, actions, objects, environment) as a pure creative scene description. Do NOT use words like 'photo', 'photograph', 'realistic', 'camera', or 'real life'. Focus only on WHAT is in the scene so it can be completely redrawn in a stylized anime format."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, pil_image]
        )
        return response.text
    except Exception as e:
        log(f"    ❌ 圖像解構失敗: {e}")
        return None


def generate_image_with_imagen(client, prompt_text, output_path, log=print):
    """呼叫 Imagen 4 根據提示詞產出 9:16 的圖片"""
    try:
        # 使用 Imagen 4 模型與新的 GenAI 套件配置寫法
        from google.genai import types
        result = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt_text,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
                output_mime_type="image/jpeg",
            )
        )
        # 將產生的圖片轉寫入硬碟
        for generated_image in result.generated_images:
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            image.save(output_path, "JPEG")
            return True
    except Exception as e:
        log(f"    ❌ 生圖失敗: {e}")
        return False
    return False


def run(log=print):
    """讀取 output_scripts/ 下所有腳本 JSON，依 visual_prompts 呼叫 Imagen 產出配圖"""
    os.makedirs(config.OUTPUT_IMAGES, exist_ok=True)

    # 找到所有待處理的腳本中繼檔
    json_files = glob.glob(os.path.join(config.OUTPUT_SCRIPTS, "*.json"))

    if not json_files:
        log(f"❌ 在 '{config.OUTPUT_SCRIPTS}/' 資料夾中找不到資料檔案。")
        log("   請先執行 step2_script_generator.py 生成腳本！")
        return {"success": 0, "failed": 0, "outputs": []}

    # 1. 初始化 Gemini API
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    success_count = 0
    failed_count = 0
    outputs = []

    for json_path in json_files:
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        log(f"\n🎬 正在處理：{base_name}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        news_sources = data.get("news_sources", [])
        visual_prompts = data.get("visual_prompts", [])

        # 根據腳本提供的提示詞數量產生圖片 (支援 30秒 2張 或 60秒 4張)
        for i, ai_prompt in enumerate(visual_prompts):
            log(f"\n  🎨 準備生成第 {i+1} 張配圖...")
            image_description_text = ""

            # 若是第一張配圖，且有提供新聞原圖，則先用 Gemini 解構原圖
            if i == 0 and news_sources and news_sources[0].get("image_url"):
                image_url = news_sources[0].get("image_url")
                log(f"  🔍 下載並解構原圖: {image_url}")
                pil_image = download_image(image_url, log=log)
                if pil_image:
                    log("  🧠 使用 Gemini Vision 解構原圖...")
                    desc = analyze_image_with_gemini(client, pil_image, log=log)
                    if desc:
                        image_description_text = f"The scene also contains these elements based on original news photo: {desc}."

            # 組合終極魔法咒語，並再次強調風格
            final_prompt = f"Subject and context: {ai_prompt}. {image_description_text} {CHANNEL_STYLE_PROMPT}"
            log(f"  🎨 呼叫 Imagen 生成 9:16 新圖...")
            log(f"     => 魔法咒語長度: {len(final_prompt)} 字元")

            output_image_path = os.path.join(config.OUTPUT_IMAGES, f"{base_name}_{i}.jpg")
            success = generate_image_with_imagen(client, final_prompt, output_image_path, log=log)

            if success:
                log(f"  ✅ 成功產出圖片：{output_image_path}")
                success_count += 1
                outputs.append({"base_name": base_name, "index": i, "path": output_image_path})
            else:
                failed_count += 1

    log("\n🎉 所有視覺素材處理完畢！可前往 output_images/ 查看成果。")
    return {"success": success_count, "failed": failed_count, "outputs": outputs}


def main():
    """CLI 互動版"""
    print("=============================")
    print("  🖼️ AI 視覺生圖中心 ")
    print("=============================")
    run()


if __name__ == "__main__":
    main()
