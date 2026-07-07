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

# 1. 初始化路徑
SOURCE_DIR = os.path.join(config.BASE_DIR, "source")
IMPORTED_DIR = os.path.join(SOURCE_DIR, "imported")
LOCAL_IMAGE_DIR = os.path.join(config.ASSETS_DIR, "local_source_images")
SUPPORTED_EXTENSIONS = ('.txt', '.md', '.pdf', '.json')


def _ensure_dirs():
    for path in [SOURCE_DIR, IMPORTED_DIR, LOCAL_IMAGE_DIR]:
        if not os.path.exists(path):
            os.makedirs(path)


def get_pending_files():
    """掃描 source/ 資料夾下待匯入的支援檔案，回傳檔名清單"""
    _ensure_dirs()
    return [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(SUPPORTED_EXTENSIONS) and os.path.isfile(os.path.join(SOURCE_DIR, f))]


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


def download_image(url, save_filename, log=print):
    try:
        headers = {'User-Agent': config.USER_AGENT if hasattr(config, 'USER_AGENT') else 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            save_path = os.path.join(LOCAL_IMAGE_DIR, save_filename)
            with open(save_path, 'wb') as f:
                f.write(res.content)
            return save_path
    except Exception as e:
        log(f"   WARNING: Download failed [{url}]: {e}")
    return None


def import_file(filename, category=None, get_category=None, log=print):
    """
    匯入單一 source/ 下的檔案至資料庫 (JSON 額外產出 output_scripts/ 腳本檔)。
    category: 直接指定分類 (GUI 已知分類時使用)。
    get_category: 回呼函式 get_category(title) -> category，僅在內容驗證通過後才會被呼叫
                  (CLI 用來還原「先驗證內容、再詢問分類」的原始互動順序)。
    二者擇一提供；皆未提供時預設 "Finance"。
    回傳 dict: {"status": "ok"/"skipped"/"duplicate"/"error", "db_id": ..., "is_json": bool, "message": ...}
    """
    _ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

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
            log(f"⚠️ 讀取 PDF 失敗: {filename}, 錯誤: {e}")
            conn.close()
            return {"status": "error", "message": str(e)}
    elif ext == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # 檢查是否為專案規格 JSON (包含 intro, main_content, outro, visual_prompts, keywords)
            required_keys = ('intro', 'main_content', 'outro', 'visual_prompts', 'keywords')
            if not all(k in json_data for k in required_keys):
                log(f"⚠️ JSON 結構不符合專案規格: {filename}")
                conn.close()
                return {"status": "error", "message": "JSON 結構不符合專案規格"}

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

            if not link_in_json or link_in_json == "local://news":
                link_in_json = f"local://{filename}"
        except Exception as e:
            log(f"⚠️ 讀取 JSON 失敗: {filename}, 錯誤: {e}")
            conn.close()
            return {"status": "error", "message": str(e)}

    if not content:
        log(f"⚠️ 跳過空內容檔案: {filename}")
        conn.close()
        return {"status": "skipped", "message": "空內容"}

    # a. 選取分類 (內容驗證通過才詢問，維持原始互動順序)
    if category is None:
        category = get_category(title) if get_category else "Finance"

    # b. 處理圖片
    # 優先權 1: 同名本地檔案 (使用 img_ext 以防覆蓋 ext 變數)
    local_img = find_local_image(title)
    if local_img:
        img_ext = os.path.splitext(local_img)[1]
        target_img_name = f"{title}{img_ext}"
        target_img_path = os.path.join(LOCAL_IMAGE_DIR, target_img_name)
        shutil.copy2(local_img, target_img_path)
        image_url_in_db = target_img_path
        log(f"   IMAGE: Found local image: {target_img_name}")
    elif ext == '.json' and image_url_in_db:
        # 優先權 2: JSON 內附的圖片 URL/路徑
        log(f"   IMAGE: Using image_url from JSON: {image_url_in_db}")
    else:
        # 優先權 3: 掃描內嵌網址
        urls = extract_image_urls(content)
        if urls:
            log(f"   LINK: Detected image URL, downloading...")
            downloaded_path = download_image(urls[0], f"download_{title}.jpg", log=log)
            if downloaded_path:
                image_url_in_db = downloaded_path
                log(f"   SUCCESS: Image downloaded")

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
        log(f"SUCCESS: Imported to DB [ID: {db_id}]")

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

            log(f"   [JSON LOAD] Generated script files for subsequent modules:")
            log(f"     -> {txt_path}")
            log(f"     -> {json_path}")

        # d. 搬移至 imported (歸檔)
        shutil.move(file_path, os.path.join(IMPORTED_DIR, filename))
        if local_img:
            shutil.move(local_img, os.path.join(IMPORTED_DIR, os.path.basename(local_img)))

        conn.commit()
        conn.close()
        return {"status": "ok", "db_id": db_id, "is_json": ext == '.json'}

    except sqlite3.IntegrityError:
        log(f"ERROR: '{filename}' already imported.")
        # 即使重複，也協助搬移至 imported 以免卡住 source 資料夾
        shutil.move(file_path, os.path.join(IMPORTED_DIR, filename))
        if local_img:
            shutil.move(local_img, os.path.join(IMPORTED_DIR, os.path.basename(local_img)))
        conn.commit()
        conn.close()
        return {"status": "duplicate", "message": "已匯入過"}


def run(category=None, get_category=None, log=print):
    """
    批次匯入 source/ 下所有支援檔案。
    category: 若提供，套用到本次批次的所有檔案 (GUI 單一分類批次匯入使用)。
    get_category: 回呼函式 get_category(title) -> category (CLI 逐檔互動詢問使用)。
    回傳: {"import_count", "json_import_count", "other_import_count", "results": [...]}
    """
    input_files = get_pending_files()

    if not input_files:
        log(f"INFO: Currently '{SOURCE_DIR}' has no support files ({', '.join(SUPPORTED_EXTENSIONS)}).")
        return {"import_count": 0, "json_import_count": 0, "other_import_count": 0, "results": []}

    log(f"Scanning: Found {len(input_files)} files...\n")

    import_count = 0
    json_import_count = 0
    other_import_count = 0
    results = []

    for filename in input_files:
        result = import_file(filename, category=category, get_category=get_category, log=log)
        results.append({"filename": filename, **result})
        if result["status"] == "ok":
            import_count += 1
            if result["is_json"]:
                json_import_count += 1
            else:
                other_import_count += 1

    log(f"\nFINISH: Imported {import_count} local news files. (JSON: {json_import_count}, Others: {other_import_count})")
    return {
        "import_count": import_count,
        "json_import_count": json_import_count,
        "other_import_count": other_import_count,
        "results": results,
    }


def main():
    """CLI 互動版"""
    print("=============================")
    print("  Batch Local News Loader  ")
    print("=============================")

    def ask_category(title):
        print(f"\n[Title]: {title}")
        print("   [1] Finance (財經/國際情勢)")
        print("   [2] Gaming (遊戲/動漫/科技)")
        choice = input("   Choice (1/2, default 1): ").strip()
        return "Gaming" if choice == '2' else "Finance"

    result = run(get_category=ask_category)

    if not result["results"]:
        # 完全沒有檔案可匯入 (對應原始行為：直接結束，不詢問後續模組)
        return

    import pipeline_chain
    if result["other_import_count"] == 0 and result["json_import_count"] > 0:
        # 如果本次只有匯入 JSON，直接詢問是否進行語音合成 (模組3)
        pipeline_chain.offer_voice_only()
    else:
        # 正常流程 (包含非 JSON 檔案的選題與生腳本)
        pipeline_chain.run_and_offer_next(auto_run_selector=True)


if __name__ == "__main__":
    main()
