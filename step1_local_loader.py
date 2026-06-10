import os
import sqlite3
import shutil
import datetime
import re
import requests
import sys
import config
import json

sys.stdout.reconfigure(encoding='utf-8')

print("=============================")
print("  Batch Local News Loader  ")
print("=============================")

# 1. 初始化路徑
SOURCE_DIR = os.path.join(config.BASE_DIR, "source")
IMPORTED_DIR = os.path.join(SOURCE_DIR, "imported")
LOCAL_IMAGE_DIR = os.path.join(config.ASSETS_DIR, "local_source_images")

for path in [SOURCE_DIR, IMPORTED_DIR, LOCAL_IMAGE_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# 2. 連線資料庫
conn = sqlite3.connect(config.DB_PATH)
cursor = conn.cursor()

# 掃描 source 資料夾下的支援檔案 (.txt, .md, .pdf, .json)
SUPPORTED_EXTENSIONS = ('.txt', '.md', '.pdf', '.json')
input_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(SUPPORTED_EXTENSIONS) and os.path.isfile(os.path.join(SOURCE_DIR, f))]

if not input_files:
    print(f"INFO: Currently '{SOURCE_DIR}' has no support files ({', '.join(SUPPORTED_EXTENSIONS)}).")
    exit()

print(f"Scanning: Found {len(input_files)} files...\n")


def get_category_choice(title):
    print(f"\n[Title]: {title}")
    print("   [1] Finance (財經/國際情勢)")
    print("   [2] Gaming (遊戲/動漫/科技)")
    choice = input("   Choice (1/2, default 1): ").strip()
    return "Gaming" if choice == '2' else "Finance"

def find_local_image(filename_base):
    # 支援常見圖片格式
    extensions = ['.jpg', '.jpeg', '.png', '.webp']
    for ext in extensions:
        img_path = os.path.join(SOURCE_DIR, filename_base + ext)
        if os.path.exists(img_path):
            return img_path
    return None

def extract_image_urls(text):
    # 簡易正則表達式，找出網址中的圖片
    url_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|webp)'
    return re.findall(url_pattern, text)

def download_image(url, save_filename):
    try:
        headers = {'User-Agent': config.USER_AGENT if hasattr(config, 'USER_AGENT') else 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            save_path = os.path.join(LOCAL_IMAGE_DIR, save_filename)
            with open(save_path, 'wb') as f:
                f.write(res.content)
            return save_path
    except Exception as e:
        print(f"   WARNING: Download failed [{url}]: {e}")
    return None

import_count = 0
json_import_count = 0
other_import_count = 0

for filename in input_files:
    file_path = os.path.join(SOURCE_DIR, filename)
    title = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    
    # 讀取內容
    content = ""
    json_data = None
    link_in_json = ""
    image_url_in_db = ""
    
    if ext in ('.txt', '.md'):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            content = "\n".join(pages_text).strip()
        except Exception as e:
            print(f"⚠️ 讀取 PDF 失敗: {filename}, 錯誤: {e}")
            continue
    elif ext == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 檢查是否為專案規格 JSON (包含 intro, main_content, outro, visual_prompts, keywords)
            required_keys = ('intro', 'main_content', 'outro', 'visual_prompts', 'keywords')
            if not all(k in json_data for k in required_keys):
                print(f"⚠️ JSON 結構不符合專案規格: {filename}")
                continue
                
            # 將腳本內容組合成 content
            content = f"{json_data['intro']}\n{json_data['main_content']}\n{json_data['outro']}"
            
            # 從 json 取得標題、網址與圖片
            news_sources = json_data.get("news_sources", [])
            if news_sources and isinstance(news_sources, list) and len(news_sources) > 0:
                source_item = news_sources[0]
                if source_item.get("title"):
                    title = source_item["title"]
                if source_item.get("url"):
                    link_in_json = source_item["url"]
                if source_item.get("image_url"):
                    image_url_in_db = source_item["image_url"]
            
            if not link_in_json:
                link_in_json = f"local://{filename}"
        except Exception as e:
            print(f"⚠️ 讀取 JSON 失敗: {filename}, 錯誤: {e}")
            continue
    
    if not content:
        print(f"⚠️ 跳過空內容檔案: {filename}")
        continue
    
    # a. 選取分類
    category = get_category_choice(title)
    
    # b. 處理圖片
    # 優先權 1: 同名本地檔案 (使用 img_ext 以防覆蓋 ext 變數)
    local_img = find_local_image(title)
    if local_img:
        img_ext = os.path.splitext(local_img)[1]
        target_img_name = f"{title}{img_ext}"
        target_img_path = os.path.join(LOCAL_IMAGE_DIR, target_img_name)
        shutil.copy2(local_img, target_img_path)
        image_url_in_db = target_img_path
        print(f"   IMAGE: Found local image: {target_img_name}")
    elif ext == '.json' and image_url_in_db:
        # 優先權 2: JSON 內附的圖片 URL/路徑
        print(f"   IMAGE: Using image_url from JSON: {image_url_in_db}")
    else:
        # 優先權 3: 掃描內嵌網址
        urls = extract_image_urls(content)
        if urls:
            print(f"   LINK: Detected image URL, downloading...")
            downloaded_path = download_image(urls[0], f"download_{title}.jpg")
            if downloaded_path:
                image_url_in_db = downloaded_path
                print(f"   SUCCESS: Image downloaded")
    
    # c. 寫入資料庫
    unique_link = link_in_json if (ext == '.json' and link_in_json) else f"local://{filename}"
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        is_processed_val = 1 if ext == '.json' else 0
        cursor.execute('''
            INSERT INTO DailyNews (category, title, link, pub_date, image_url, content, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (category, title, unique_link, today, image_url_in_db, content, is_processed_val))
        db_id = cursor.lastrowid
        print(f"SUCCESS: Imported to DB [ID: {db_id}]")
        
        if ext == '.json':
            # 我們需要為這個已處理的 JSON 檔案在 output_scripts 目錄下生成 script_{category}_{db_id}.txt 和 script_{category}_{db_id}.json
            os.makedirs(config.OUTPUT_SCRIPTS, exist_ok=True)
            base_filename = f"script_{category}_{db_id}"
            
            # 組合最終腳本
            final_script = f"{json_data['intro']} {json_data['main_content']} {json_data['outro']}"
            
            # 儲存腳本文字檔 (給語音模組使用)
            txt_path = os.path.join(config.OUTPUT_SCRIPTS, f"{base_filename}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(final_script)
                
            # 儲存腳本中繼檔 (.json) (給生圖模組使用)
            json_path = os.path.join(config.OUTPUT_SCRIPTS, f"{base_filename}.json")
            # 修正 news_sources 為正確的 db_id 資訊
            json_data["news_sources"] = [{"id": db_id, "title": title, "image_url": image_url_in_db, "url": unique_link}]
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
                
            print(f"   [JSON LOAD] Generated script files for subsequent modules:")
            print(f"     -> {txt_path}")
            print(f"     -> {json_path}")
            
        # d. 搬移至 imported (歸檔)
        shutil.move(file_path, os.path.join(IMPORTED_DIR, filename))
        if local_img:
            shutil.move(local_img, os.path.join(IMPORTED_DIR, os.path.basename(local_img)))
            
        import_count += 1
        if ext == '.json':
            json_import_count += 1
        else:
            other_import_count += 1
    except sqlite3.IntegrityError:
        print(f"ERROR: '{filename}' already imported.")
        # 即使重複，也協助搬移至 imported 以免卡住 source 資料夾
        shutil.move(file_path, os.path.join(IMPORTED_DIR, filename))
        if local_img:
             shutil.move(local_img, os.path.join(IMPORTED_DIR, os.path.basename(local_img)))

conn.commit()
conn.close()

print(f"\nFINISH: Imported {import_count} local news files. (JSON: {json_import_count}, Others: {other_import_count})")

import subprocess
import sys

# 如果本次只有匯入 JSON，直接詢問是否進行語音合成 (模組3)
if other_import_count == 0 and json_import_count > 0:
    print("\n💡 本次僅匯入已具備腳本的 JSON 檔案，將自動跳過「總編輯選題 (1.5)」與「AI 劇本生成 (2)」步驟。")
    ans3 = input("\n❓ 是否直接執行 [模組3: 語音合成]？ (y/n，輸入 q 退出): ").strip().lower()
    if ans3 == 'q':
        print("🚪 中途退出。")
        sys.exit(0)
    elif ans3 in ['y', 'yes']:
        print("\n👉 接續執行模組 3...")
        subprocess.run([sys.executable, 'step3_voice_renderer.py'])
        print("\n✅ 所有選定之模組皆執行完畢。")
    else:
        print("⏸️ 結束執行。")
else:
    # 正常流程 (包含非 JSON 檔案的選題與生腳本)
    print("\n👉 自動接續執行 1.5 挑選模組...")
    subprocess.run([sys.executable, 'step1_5_selector.py'])

    ans2 = input("\n❓ 1.5 模組挑選完畢。是否繼續執行 [模組2: AI產生腳本]？ (y/n，輸入 q 退出): ").strip().lower()
    if ans2 == 'q':
        print("🚪 中途退出。")
        sys.exit(0)
    elif ans2 in ['y', 'yes']:
        print("\n👉 接續執行模組 2...")
        subprocess.run([sys.executable, 'step2_script_generator.py'])
        
        ans3 = input("\n❓ 模組 2 執行完畢。是否繼續執行 [模組3: 語音合成]？ (y/n，輸入 q 退出): ").strip().lower()
        if ans3 == 'q':
            print("🚪 中途退出。")
            sys.exit(0)
        elif ans3 in ['y', 'yes']:
            print("\n👉 接續執行模組 3...")
            subprocess.run([sys.executable, 'step3_voice_renderer.py'])
            print("\n✅ 所有選定之模組皆執行完畢。")
        else:
            print("⏸️ 結束執行。")
    else:
        print("⏸️ 結束執行。")
