import os
import glob
import sys
import time
import json
import threading
import sqlite3
import config
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

from uploaders import (
    YouTubeUploader,
    FacebookUploader,
    InstagramUploader,
    TikTokUploader,
    XiaohongshuUploader
)
from uploaders.base import UploadControl

# 修正 Windows 終端機印出 Emoji 的編碼問題
sys.stdout.reconfigure(encoding='utf-8')

# 使用 config 中的設定
VIDEOS_DIR = config.OUTPUT_VIDEOS
SCRIPTS_DIR = config.OUTPUT_SCRIPTS
USER_DATA_DIR = config.PLAYWRIGHT_SESSION_DIR
GEMINI_API_KEY = config.GEMINI_API_KEY


def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


def get_unpublished_video_list():
    """從資料庫中找出尚未發布 (is_published=0) 的影片檔案列表"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    # 我們只處理已經標記為 is_processed=1 且尚未歸檔 (is_published=0) 的新聞
    cursor.execute("SELECT id, category FROM DailyNews WHERE is_processed = 1 AND is_published = 0")
    records = cursor.fetchall()
    conn.close()

    video_files = []
    for news_id, category in records:
        basename = f"script_{category}_{news_id}"
        video_path = os.path.join(VIDEOS_DIR, f"{basename}_subtitled.mp4")
        if os.path.exists(video_path):
            video_files.append(video_path)
    return video_files


def extract_basename(video_path: str) -> str:
    """從影片名稱中擷取出腳本原始 BaseName (例如 script_Finance_8)"""
    filename = os.path.basename(video_path)
    return filename.replace("_subtitled.mp4", "")


def generate_marketing_copy(script_text: str, log=print):
    """呼叫 Gemini 產生吸睛標題與 Hashtags"""
    client = get_gemini_client()
    sys_instruction = (
        "你是一個頂尖的社群行銷專家，專門負責短影音平台(YouTube Shorts, TikTok, 小紅書, IG Reels)。\n"
        "請根據提供的影片逐字稿，思考出一個極度吸睛、有懸念的短標題 (限20字內)，\n"
        "並提供5-8個最相關、有流量的 Hashtag。\n"
        "請嚴格以 JSON 格式回應，包含 'title' 與 'tags' 兩個欄位，其中 tags 需為字串，每個 tag 以空白分隔（例如 '#AI #科技'）。"
    )

    prompt = f"請看這份逐字稿：\n{script_text}"

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                temperature=0.8,
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        log(f"❌ Gemini API 呼叫失敗: {e}")
        return {"title": "【最新情報】小花的 AI 快報！", "tags": "#AI #科技 #小花的AI情報站"}


def launch_login_mode(log=print):
    """啟動 Playwright 並不關閉，讓使用者手動登入各大平台"""
    log("========================================")
    log("  🔑 啟動【登入授權模式】")
    log("========================================")
    log("即將開啟瀏覽器，請在瀏覽器中手動登入以下平台：")
    log("- YouTube (studio.youtube.com)")
    log("- Facebook (business.facebook.com)")
    log("- Instagram (instagram.com)")
    log("- TikTok (tiktok.com)")
    log("登入完成後，只要把瀏覽器關閉，登入狀態就會自動儲存在本地！\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.new_page()
        page.goto("https://www.google.com")

        log("🌍 瀏覽器已開啟！請開始您的登入作業。登入完畢請直接關閉瀏覽器。")
        try:
            page.wait_for_timeout(999999999)
        except Exception:
            pass
        finally:
            log("💾 瀏覽器已關閉，您的登入狀態已儲存至 playwright_session/。")


def run(video_paths, platforms, control=None, log=print, before_close=None):
    """
    對指定影片清單依序執行多平台自動發布 (Playwright 瀏覽器自動化)。

    video_paths: 欲發布的影片檔案完整路徑清單 (來自 get_unpublished_video_list())
    platforms: 平台代碼清單，1=YouTube 2=Facebook 3=Instagram 4=TikTok
    control: UploadControl 執行個體，供人工即時介入 (跳過/重試/重置等待)。
             未提供則自動建立一個獨立實例 (CLI 由 main() 綁定鍵盤監聽；GUI 需自行建立並用按鈕操作對應 Event)。
    before_close: 選填 callback，於瀏覽器關閉前呼叫 (CLI 用來暫停等待人工覆核；GUI 通常留空，處理完立即釋放瀏覽器)。

    回傳: {"processed": [{"video":..., "title":..., "tags":..., "results": {...}}, ...]}
    """
    if control is None:
        control = UploadControl()

    if not video_paths or not platforms:
        log("❌ 未選擇任何有效的影片或平台，已退出。")
        return {"processed": []}

    log("\n🚀 啟動自動化發布程序...")
    processed = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.new_page()

        for i, selected_video in enumerate(video_paths, 1):
            log(f"\n========================================")
            log(f" 🎬 處理影片 ({i}/{len(video_paths)}): {os.path.basename(selected_video)}")
            log(f"========================================")

            basename = extract_basename(selected_video)
            script_json_path = os.path.join(SCRIPTS_DIR, f"{basename}.json")

            script_text = ""
            if os.path.exists(script_json_path):
                with open(script_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    script_text = f"{data.get('intro', '')} {data.get('main_content', '')} {data.get('outro', '')}"

            log("🧠 正在呼叫 Gemini 生成吸睛標題與 Hashtags...")
            marketing_data = generate_marketing_copy(script_text, log=log)
            title = marketing_data.get("title", "")
            tags = marketing_data.get("tags", "")

            log(f"  📌 標題：{title}")
            log(f"  🏷️ 標籤：{tags}")

            results = {}
            if 1 in platforms:
                results['youtube'] = YouTubeUploader(page, control=control).upload(os.path.abspath(selected_video), title, tags)
            if 2 in platforms:
                results['facebook'] = FacebookUploader(page, control=control).upload(os.path.abspath(selected_video), title, tags)
            if 3 in platforms:
                results['instagram'] = InstagramUploader(page, control=control).upload(os.path.abspath(selected_video), title, tags)
            if 4 in platforms:
                results['tiktok'] = TikTokUploader(page, control=control).upload(os.path.abspath(selected_video), title, tags)

            processed.append({"video": selected_video, "title": title, "tags": tags, "results": results})

        log("\n🎉 所有指定影片發布腳本執行完畢！")
        log("💡 提示：瀏覽器將保持開啟狀態，供您檢查上傳狀態。")
        log("          確認無誤後，請直接手動關閉瀏覽器視窗即可。")

        if before_close:
            before_close()

    return {"processed": processed}


def _start_keyboard_listener(control):
    """CLI 專用：背景執行緒監聽鍵盤 S/R/W，轉換為 UploadControl 事件 (daemon，隨主行程結束)"""
    import msvcrt

    def _listen():
        while True:
            if msvcrt.kbhit():
                try:
                    ch = msvcrt.getch().decode('utf-8').upper()
                except Exception:
                    continue
                if ch == 'S':
                    control.skip.set()
                elif ch == 'R':
                    control.retry.set()
                elif ch == 'W':
                    control.reset_wait.set()
            time.sleep(0.1)

    t = threading.Thread(target=_listen, daemon=True)
    t.start()
    return t


def main():
    """CLI 互動版"""
    print("========================================")
    print("  🚀 模組八：多平台自動發布機器人")
    print("========================================")

    # 1. 尋找可以發布的影片 (排除已歸檔項目)
    video_files = get_unpublished_video_list()
    if not video_files:
        print(f"目前沒有待上傳的影片 (或是影片已歸檔)。")
        print("👉 如果您想登入平台，請輸入 D:")
        choice = input("> ").strip().upper()
        if choice == 'D':
            launch_login_mode()
        return

    # 2. 顯示並讓使用者挑選
    print("📦 發現以下可發布的影片：")
    for idx, vf in enumerate(video_files):
        print(f"[{idx}] {os.path.basename(vf)}")

    print("--------------------")
    print("👉 請輸入您要發布的影片編號 (多筆請用逗號隔開例如 0,2，或輸入 A 全選)")
    print("   或輸入 'D' 進入「首次登入模式」：")
    choice = input("> ").strip().upper()

    if choice == 'D':
        launch_login_mode()
        return

    selected_videos = []
    if choice == 'A':
        selected_videos = video_files
    else:
        for p in choice.split(','):
            try:
                selected_idx = int(p.strip())
                selected_videos.append(video_files[selected_idx])
            except (ValueError, IndexError):
                pass

    if not selected_videos:
        print("❌ 未選擇任何有效的影片，已退出。")
        return

    print(f"\n✅ 已選擇 {len(selected_videos)} 部影片準備發布！")

    # --- 平台選擇介面 ---
    print("\n🌐 請問您要將這些影片發布到哪些平台？")
    print("  [1] YouTube Shorts")
    print("  [2] Facebook Reels")
    print("  [3] Instagram Reels")
    print("  [4] TikTok")
    print("  [6] 🔥 全部發布 (1~4)")
    print("  [Q] 退出取消")

    platforms_choice = input("👉 請輸入選項 (如果是多個可用逗號隔開, 例如: 1,3) > ").strip().upper()

    if platforms_choice == 'Q':
        return

    targets = []
    if '6' in platforms_choice:
        targets = [1, 2, 3, 4]
    else:
        for p in platforms_choice.split(','):
            try:
                targets.append(int(p.strip()))
            except Exception:
                pass

    if not targets:
        print("❌ 未選擇任何有效的平台，已退出。")
        return

    # 啟動鍵盤監聽 (S/R/W)，並綁定至 UploadControl
    control = UploadControl()
    _start_keyboard_listener(control)

    run(
        selected_videos, targets, control=control,
        before_close=lambda: input("\n👉 按下 [Enter] 鍵結束程式...")
    )


if __name__ == "__main__":
    main()
