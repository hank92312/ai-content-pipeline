import os
import sqlite3
import shutil
import datetime
import re
import requests
import config

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

# 掃描 source 資料夾下的 .txt 檔案
txt_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.txt') and os.path.isfile(os.path.join(SOURCE_DIR, f))]

if not txt_files:
    print(f"INFO: Currently '{SOURCE_DIR}' has no .txt files.")
    exit()

print(f"Scanning: Found {len(txt_files)} files...\n")

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

for filename in txt_files:
    file_path = os.path.join(SOURCE_DIR, filename)
    title = os.path.splitext(filename)[0]
    
    # 讀取內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print(f"⚠️ 跳過空檔案: {filename}")
        continue
    
    # a. 選取分類
    category = get_category_choice(title)
    
    # b. 處理圖片
    image_url_in_db = ""
    
    # 優先權 1: 同名本地檔案
    local_img = find_local_image(title)
    if local_img:
        ext = os.path.splitext(local_img)[1]
        target_img_name = f"{title}{ext}"
        target_img_path = os.path.join(LOCAL_IMAGE_DIR, target_img_name)
        shutil.copy2(local_img, target_img_path)
        image_url_in_db = target_img_path
        print(f"   IMAGE: Found local image: {target_img_name}")
    else:
        # 優先權 2: 掃描內嵌網址
        urls = extract_image_urls(content)
        if urls:
            print(f"   LINK: Detected image URL, downloading...")
            downloaded_path = download_image(urls[0], f"download_{title}.jpg")
            if downloaded_path:
                image_url_in_db = downloaded_path
                print(f"   SUCCESS: Image downloaded")
    
    # c. 寫入資料庫
    unique_link = f"local://{filename}"
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute('''
            INSERT INTO DailyNews (category, title, link, pub_date, image_url, content)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (category, title, unique_link, today, image_url_in_db, content))
        print(f"SUCCESS: Imported to DB [ID: {cursor.lastrowid}]")
        
        # d. 搬移至 imported (歸檔)
        shutil.move(file_path, os.path.join(IMPORTED_DIR, filename))
        if local_img:
            shutil.move(local_img, os.path.join(IMPORTED_DIR, os.path.basename(local_img)))
            
        import_count += 1
    except sqlite3.IntegrityError:
        print(f"ERROR: '{filename}' already imported.")
        # 即使重複，也協助搬移至 imported 以免卡住 source 資料夾
        shutil.move(file_path, os.path.join(IMPORTED_DIR, filename))
        if local_img:
             shutil.move(local_img, os.path.join(IMPORTED_DIR, os.path.basename(local_img)))

conn.commit()
conn.close()

print(f"\nFINISH: Imported {import_count} local news files.")

# 自動接續執行 1.5 模組
import subprocess
import sys
print("\n👉 自動接續執行 1.5 挑選模組...")
subprocess.run([sys.executable, 'step1_5_selector.py'])

# 詢問是否執行模組2
ans2 = input("\n❓ 1.5 模組挑選完畢。是否繼續執行 [模組2: AI產生腳本]？ (y/n，輸入 q 退出): ").strip().lower()
if ans2 == 'q':
    print("🚪 中途退出。")
    sys.exit(0)
elif ans2 in ['y', 'yes']:
    print("\n👉 接續執行模組 2...")
    subprocess.run([sys.executable, 'step2_script_generator.py'])
    
    # 執行完模組2後，詢問是否執行模組3
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
