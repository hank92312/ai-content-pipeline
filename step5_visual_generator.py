import os
import json
import glob
import requests
import io
import sys
from PIL import Image
from google import genai

sys.stdout.reconfigure(encoding='utf-8')

print("=============================")
print("  🖼️ AI 視覺生圖中心 ")
print("=============================")

# 1. 初始化 Gemini API
# ⚠️ 請將下一行的字串替換為您在 step2 使用的金鑰
API_KEY = "AIzaSyAQD2UcDDAe5b3c9vToTM2pAl99hIKYA7M" 
client = genai.Client(api_key=API_KEY)

# --- 頻道風格提示詞 (可隨時調整) ---
# 控制了產圖的格式 (9:16) 與整體畫風。必須強制二次元/科技感風格，避免生成真實照片。
CHANNEL_STYLE_PROMPT = "The image must be visually stunning, masterpiece, high definition. 2D anime style, cel-shaded illustration, vibrant colors. Cyberpunk or modern high-tech VTuber vibe style. ABSOLUTELY NO photorealism, no photography, no real people. Ensure all characters are drawn in 2D anime style. CRITICAL RULE: ABSOLUTELY NO TEXT, NO CHINESE CHARACTERS, NO WORDS, NO LETTERS on the image. Use pure graphical elements, symbols, or numbers only to avoid gibberish text generation."

SCRIPTS_DIR = "output_scripts"
IMAGES_DIR = "output_images"

os.makedirs(IMAGES_DIR, exist_ok=True)

# 找到所有待處理的腳本中繼檔
json_files = glob.glob(os.path.join(SCRIPTS_DIR, "*.json"))

if not json_files:
    print(f"❌ 在 '{SCRIPTS_DIR}/' 資料夾中找不到資料檔案。")
    print("   請先執行 step2_script_generator.py 生成腳本！")
    exit()

def download_image(url):
    """下載原圖並轉為 PIL Image 供 Gemini 解讀"""
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
        print(f"    ❌ 下載原圖失敗 [{url}]: {e}")
        return None

def analyze_image_with_gemini(pil_image):
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
        print(f"    ❌ 圖像解構失敗: {e}")
        return None

def generate_image_with_imagen(prompt_text, output_path):
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
        print(f"    ❌ 生圖失敗: {e}")
        return False
    return False

for json_path in json_files:
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    print(f"\n🎬 正在處理：{base_name}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    news_sources = data.get("news_sources", [])
    visual_prompts = data.get("visual_prompts", [])
    
    # 限制最多產生 2 張圖 (對應 30 秒影片的最佳配置)
    for i, ai_prompt in enumerate(visual_prompts[:2]):
        print(f"\n  🎨 準備生成第 {i+1} 張配圖...")
        image_description_text = ""
        
        # 若是第一張配圖，且有提供新聞原圖，則先用 Gemini 解構原圖
        if i == 0 and news_sources and news_sources[0].get("image_url"):
            image_url = news_sources[0].get("image_url")
            print(f"  🔍 下載並解構原圖: {image_url}")
            pil_image = download_image(image_url)
            if pil_image:
                print("  🧠 使用 Gemini Vision 解構原圖...")
                desc = analyze_image_with_gemini(pil_image)
                if desc:
                    image_description_text = f"The scene also contains these elements based on original news photo: {desc}."
        
        # 組合終極魔法咒語，並再次強調風格
        final_prompt = f"Subject and context: {ai_prompt}. {image_description_text} {CHANNEL_STYLE_PROMPT}"
        print(f"  🎨 呼叫 Imagen 生成 9:16 新圖...")
        print(f"     => 魔法咒語長度: {len(final_prompt)} 字元")
        
        output_image_path = os.path.join(IMAGES_DIR, f"{base_name}_{i}.jpg")
        success = generate_image_with_imagen(final_prompt, output_image_path)
        
        if success:
            print(f"  ✅ 成功產出圖片：{output_image_path}")
            
print("\n🎉 所有視覺素材處理完畢！可前往 output_images/ 查看成果。")
