import os
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()

# --- 基礎目錄設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 輸出目錄
OUTPUT_VIDEOS = os.path.join(BASE_DIR, "output_videos")
OUTPUT_SCRIPTS = os.path.join(BASE_DIR, "output_scripts")
OUTPUT_VOICES = os.path.join(BASE_DIR, "output_voices")
OUTPUT_IMAGES = os.path.join(BASE_DIR, "output_images")

# 歸檔目錄
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
DEBUG_LOGS_DIR = os.path.join(BASE_DIR, "debug_logs")
COMPLETED_ARCHIVE_DIR = os.path.join(BASE_DIR, "completed_archives")
COMPLETED_VIDEOS_DIR = os.path.join(COMPLETED_ARCHIVE_DIR, "videos")
COMPLETED_ASSETS_DIR = os.path.join(COMPLETED_ARCHIVE_DIR, "assets")

# 資料庫
DB_PATH = os.path.join(BASE_DIR, "auto_channel.db")

# 瀏覽器 Session
PLAYWRIGHT_SESSION_DIR = os.path.join(BASE_DIR, "playwright_session")

# --- API 設定 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 全域參數 ---
TTS_SPEED = "+25%"  # 語速加快 25%
GEMINI_MODEL = "gemini-2.5-flash"

# 確保所有輸出目錄都存在
for path in [OUTPUT_VIDEOS, OUTPUT_SCRIPTS, OUTPUT_VOICES, OUTPUT_IMAGES, ARCHIVE_DIR, DEBUG_LOGS_DIR, COMPLETED_ARCHIVE_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)
