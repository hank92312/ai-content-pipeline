import sys
import os
import shutil
import sqlite3
import glob
import config

# 強制設定 stdout 使用 UTF-8 編碼，避免 Windows cp950 環境下 emoji 報錯
# (放在模組層級而非僅限 main()，確保 GUI 直接呼叫 run() 等函式時同樣安全)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def get_unarchived_videos():
    """查詢資料庫中「已處理但未發布」且對應字幕影片檔案確實存在的清單"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 1 AND is_published = 0")
    eligible_news = cursor.fetchall()
    conn.close()

    to_archive_list = []
    for news_id, category, title in eligible_news:
        basename = f"script_{category}_{news_id}"
        video_name = f"{basename}_subtitled.mp4"
        video_path = os.path.join(config.OUTPUT_VIDEOS, video_name)

        if os.path.exists(video_path):
            to_archive_list.append({
                "id": news_id,
                "category": category,
                "title": title,
                "basename": basename,
                "video_path": video_path
            })
    return to_archive_list


def run(archive_ids, log=print):
    """
    將指定 id 清單的新聞影片與素材整組歸檔至 completed_archives/，並標記 is_published = 1。
    歸檔完成後，會一併清理資料庫中未被選中且未處理的舊新聞。
    回傳: {"archived": [已歸檔的 id 清單], "deleted_old_news": 清除的舊新聞筆數}
    """
    all_items = get_unarchived_videos()
    items_by_id = {item["id"]: item for item in all_items}
    selected_items = [items_by_id[i] for i in archive_ids if i in items_by_id]

    if not selected_items:
        log("❌ 未選擇任何有效的項目，已退出。")
        return {"archived": [], "deleted_old_news": 0}

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    log(f"\n🚀 開始歸檔 {len(selected_items)} 個項目...")

    # 確保目錄存在
    os.makedirs(config.COMPLETED_VIDEOS_DIR, exist_ok=True)
    os.makedirs(config.COMPLETED_ASSETS_DIR, exist_ok=True)

    archived_ids = []
    for item in selected_items:
        log(f"📦 正在搬移：{item['title']}...")

        # A. 搬移影片
        try:
            shutil.move(item['video_path'], os.path.join(config.COMPLETED_VIDEOS_DIR, os.path.basename(item['video_path'])))
        except Exception as e:
            log(f"   ⚠️ 影片搬移失敗: {e}")

        # B. 搬移素材檔案 (json, txt, wav...)
        assets_to_check = [
            (config.OUTPUT_SCRIPTS, f"{item['basename']}.json"),
            (config.OUTPUT_SCRIPTS, f"{item['basename']}.txt"),
            (config.OUTPUT_VOICES, f"{item['basename']}.wav"),
            (config.OUTPUT_VOICES, f"{item['basename']}_final.wav"),
            (config.OUTPUT_VOICES, f"{item['basename']}_tts.wav"),
            (config.OUTPUT_VOICES, f"{item['basename']}_subs.json"),
        ]

        for folder, filename in assets_to_check:
            src = os.path.join(folder, filename)
            if os.path.exists(src):
                try:
                    shutil.move(src, os.path.join(config.COMPLETED_ASSETS_DIR, filename))
                    log(f"   ✅ 已搬移素材: {filename}")
                except Exception as e:
                    log(f"   ⚠️ 素材 {filename} 搬移失敗: {e}")

        # 搬移配圖 (使用 glob 搜尋動態張數)
        image_pattern = os.path.join(config.OUTPUT_IMAGES, f"{item['basename']}_*")
        matching_images = glob.glob(image_pattern)
        for img_src in matching_images:
            img_filename = os.path.basename(img_src)
            try:
                shutil.move(img_src, os.path.join(config.COMPLETED_ASSETS_DIR, img_filename))
                log(f"   ✅ 已搬移配圖素材: {img_filename}")
            except Exception as e:
                log(f"   ⚠️ 配圖素材 {img_filename} 搬移失敗: {e}")

        # 特別處理 assets/ 資料夾中的所有相關檔案 (IDxx.*, IDxx_*.png 等)
        asset_pattern = os.path.join(config.ASSETS_DIR, f"ID{item['id']}*")
        related_assets = glob.glob(asset_pattern)
        for src in related_assets:
            filename = os.path.basename(src)
            try:
                shutil.move(src, os.path.join(config.COMPLETED_ASSETS_DIR, filename))
                log(f"   ✅ 已搬移資產素材: {filename}")
            except Exception as e:
                log(f"   ⚠️ 資產素材 {filename} 搬移失敗: {e}")

        # C. 刪除原始無字幕影片 (僅保留上字幕後的歸檔版本)
        raw_video = os.path.join(config.OUTPUT_VIDEOS, f"{item['basename']}.mp4")
        if os.path.exists(raw_video):
            try:
                os.remove(raw_video)
                log(f"   🗑️ 已刪除原始無字幕影片: {os.path.basename(raw_video)}")
            except Exception as e:
                log(f"   ⚠️ 刪除原始影片失敗: {e}")

        # D. 更新資料庫
        cursor.execute("UPDATE DailyNews SET is_published = 1 WHERE id = ?", (item['id'],))
        log(f"   ✅ 資料庫已標記為已發布 (is_published = 1)")
        archived_ids.append(item['id'])

    conn.commit()

    # E. 清理未被選中且未處理的舊新聞標題
    log("\n🧹 正在清理資料庫中未被選中的舊新聞標題...")
    deleted_count = 0
    try:
        cursor.execute("DELETE FROM DailyNews WHERE is_selected = 0 AND is_processed = 0 AND is_published = 0")
        deleted_count = cursor.rowcount
        conn.commit()
        log(f"   ✅ 已成功清除 {deleted_count} 筆未選中的標題，資料庫已重置。")
    except Exception as e:
        log(f"   ⚠️ 資料庫清理失敗: {e}")

    conn.close()
    log("\n🎉 歸檔作業與資料庫整理完成！")
    log("   目前的資料庫僅保留正在處理或已歸檔的資料，方便下次重新爬蟲。")

    return {"archived": archived_ids, "deleted_old_news": deleted_count}


def cleanup_output_folders(log=print):
    """強行清空暫存資料夾的所有內容"""
    folders = [
        config.OUTPUT_SCRIPTS,
        config.OUTPUT_VOICES,
        config.OUTPUT_IMAGES,
        config.OUTPUT_VIDEOS,
        config.ASSETS_DIR
    ]
    for folder in folders:
        if os.path.exists(folder):
            log(f"🧹 正在清空: {folder}...")
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    log(f"   ❌ 無法刪除 {filename}: {e}")


def clear_all_outputs(log=print):
    """
    ⚠️ 危險操作：清空所有輸出資料夾內容，並重置資料庫中未發布項目的選定/處理狀態。
    呼叫前必須自行完成二次確認 (GUI 需彈窗確認；CLI 於 main() 內已內建確認)。
    """
    cleanup_output_folders(log=log)

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE DailyNews SET is_selected = 0, is_processed = 0 WHERE is_published = 0")
    conn.commit()
    conn.close()
    log("✅ 暫存資料夾與資料庫狀態已重置。")


def main():
    """CLI 互動版"""
    print("========================================")
    print("  📁 模組九：影片完工歸檔中心")
    print("========================================")

    to_archive_list = get_unarchived_videos()

    if not to_archive_list:
        print("💡 目前資料庫中沒有「待歸檔」的影片項目。")
        print("   (如果您想強行清空資料夾中的孤兒檔案，請輸入 RESET)")
    else:
        print("\n📦 以下影片已完成產製，請選擇要「歸檔」的項目（代表已確認在各平台發布成功）：")
        for idx, item in enumerate(to_archive_list):
            print(f"[{idx}] {item['title']} ({item['video_path']})")

    print("--------------------")
    print("👉 請輸入編號 (多筆請用逗號隔開例如 0,2，或輸入 A 全選，RESET 清空暫存，Q 退出)：")
    choice = input("> ").strip().upper()

    if choice == 'Q':
        return

    if choice == 'RESET':
        confirm = input("⚠️  確定要清空所有輸出資料夾嗎？檔案將無法復原！(y/N): ").strip().lower()
        if confirm == 'y':
            clear_all_outputs()
        return

    if not to_archive_list:
        return

    selected_ids = []
    if choice == 'A':
        selected_ids = [item['id'] for item in to_archive_list]
    else:
        for p in choice.split(','):
            try:
                selected_idx = int(p.strip())
                selected_ids.append(to_archive_list[selected_idx]['id'])
            except (ValueError, IndexError):
                pass

    run(selected_ids)


if __name__ == "__main__":
    main()
