"""供 GUI 儀表板使用的管線狀態查詢邏輯 (讀取 DB + 掃描 output 資料夾)。"""
import glob
import os
import sqlite3

import config


def get_pipeline_overview():
    """
    回傳所有 DailyNews 記錄的管線進度總覽 (依 id 由新到舊)。
    每筆: {id, category, title, is_selected, is_processed, is_published,
           has_script, has_voice, has_images, has_video}
    """
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, title, is_selected, is_processed, is_published FROM DailyNews ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    overview = []
    for news_id, category, title, is_selected, is_processed, is_published in rows:
        basename = f"script_{category}_{news_id}"
        has_script = os.path.exists(os.path.join(config.OUTPUT_SCRIPTS, f"{basename}.json"))
        has_voice = os.path.exists(os.path.join(config.OUTPUT_VOICES, f"{basename}_final.wav"))
        has_images = len(glob.glob(os.path.join(config.OUTPUT_IMAGES, f"{basename}_*"))) > 0
        has_video = os.path.exists(os.path.join(config.OUTPUT_VIDEOS, f"{basename}_subtitled.mp4"))

        overview.append({
            "id": news_id,
            "category": category,
            "title": title,
            "is_selected": bool(is_selected),
            "is_processed": bool(is_processed),
            "is_published": bool(is_published),
            "has_script": has_script,
            "has_voice": has_voice,
            "has_images": has_images,
            "has_video": has_video,
        })
    return overview


def next_step_for(item):
    """依進度判斷下一步應執行哪個模組，回傳模組代碼字串或 None (代表已全部完成)"""
    if not item["is_selected"] and not item["is_processed"]:
        return "select"
    if not item["has_script"]:
        return "script"
    if not item["has_voice"]:
        return "voice"
    if not item["has_images"]:
        return "visual"
    if not item["has_video"]:
        return "video"
    if not item["is_published"]:
        return "publish"
    return None
