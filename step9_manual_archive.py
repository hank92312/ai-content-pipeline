import sys
import os
import shutil
import sqlite3
import config

def main():
    # 強制設定 stdout 使用 UTF-8 編碼，避免 Windows cp950 報錯
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    print("========================================")
    print("  📁 模組九：影片完工歸檔中心")
    print("========================================")

    # 1. 讀取資料庫，找出所有已處理 (is_processed=1) 但未發布 (is_published=0) 的新聞
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 1 AND is_published = 0")
    eligible_news = cursor.fetchall()

    # 2. 核對實體檔案是否存在
    to_archive_list = []
    if eligible_news:
        print("🔍 正在核對實體檔案...")
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

    if not to_archive_list:
        print("💡 目前資料庫中沒有「待歸檔」的影片項目。")
        print("   (如果您想強行清空資料夾中的孤兒檔案，請輸入 RESET)")
    else:
        # 3. 顯示選單讓使用者勾選
        print("\n📦 以下影片已完成產製，請選擇要「歸檔」的項目（代表已確認在各平台發布成功）：")
        for idx, item in enumerate(to_archive_list):
            print(f"[{idx}] {item['title']} ({item['video_path']})")
    
    print("--------------------")
    print("👉 請輸入編號 (多筆請用逗號隔開例如 0,2，或輸入 A 全選，RESET 清空暫存，Q 退出)：")
    choice = input("> ").strip().upper()
    
    if choice == 'Q':
        conn.close()
        return

    if choice == 'RESET':
        confirm = input("⚠️  確定要清空所有輸出資料夾嗎？檔案將無法復原！(y/N): ").strip().lower()
        if confirm == 'y':
            cleanup_output_folders()
            # 同時清理資料庫中所有已選定但未發布的項目，讓一切重頭開始
            cursor.execute("UPDATE DailyNews SET is_selected = 0, is_processed = 0 WHERE is_published = 0")
            conn.commit()
            print("✅ 暫存資料夾與資料庫狀態已重置。")
        conn.close()
        return

    if not eligible_news:
        conn.close()
        return
        
    selected_items = []
    if choice == 'A':
        selected_items = to_archive_list
    else:
        for p in choice.split(','):
            try:
                selected_idx = int(p.strip())
                selected_items.append(to_archive_list[selected_idx])
            except (ValueError, IndexError):
                pass

    if not selected_items:
        print("❌ 未選擇任何有效的項目，已退出。")
        conn.close()
        return

    # 4. 執行歸檔 (搬移檔案並更新資料庫)
    print(f"\n🚀 開始歸檔 {len(selected_items)} 個項目...")
    
    # 確保目錄存在
    os.makedirs(config.COMPLETED_VIDEOS_DIR, exist_ok=True)
    os.makedirs(config.COMPLETED_ASSETS_DIR, exist_ok=True)

    for item in selected_items:
        print(f"📦 正在搬移：{item['title']}...")
        
        # A. 搬移影片
        try:
            shutil.move(item['video_path'], os.path.join(config.COMPLETED_VIDEOS_DIR, os.path.basename(item['video_path'])))
        except Exception as e:
            print(f"   ⚠️ 影片搬移失敗: {e}")

        # B. 搬移素材檔案 (json, txt, wav...)
        # 1. 搬移腳本與配音檔案
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
                    print(f"   ✅ 已搬移素材: {filename}")
                except Exception as e:
                    print(f"   ⚠️ 素材 {filename} 搬移失敗: {e}")

        # 2. 搬移配圖 (使用 glob 搜尋動態張數)
        import glob
        image_pattern = os.path.join(config.OUTPUT_IMAGES, f"{item['basename']}_*")
        matching_images = glob.glob(image_pattern)
        for img_src in matching_images:
            img_filename = os.path.basename(img_src)
            try:
                shutil.move(img_src, os.path.join(config.COMPLETED_ASSETS_DIR, img_filename))
                print(f"   ✅ 已搬移配圖素材: {img_filename}")
            except Exception as e:
                print(f"   ⚠️ 配圖素材 {img_filename} 搬移失敗: {e}")

        # 特別處理 assets/ 資料夾中的所有相關檔案 (IDxx.*, IDxx_*.png 等)
        import glob
        asset_pattern = os.path.join(config.ASSETS_DIR, f"ID{item['id']}*")
        related_assets = glob.glob(asset_pattern)
        for src in related_assets:
            filename = os.path.basename(src)
            try:
                shutil.move(src, os.path.join(config.COMPLETED_ASSETS_DIR, filename))
                print(f"   ✅ 已搬移資產素材: {filename}")
            except Exception as e:
                print(f"   ⚠️ 資產素材 {filename} 搬移失敗: {e}")

        # C. 刪除原始無字幕影片 (僅保留上字幕後的歸檔版本)
        raw_video = os.path.join(config.OUTPUT_VIDEOS, f"{item['basename']}.mp4")
        if os.path.exists(raw_video):
            try:
                os.remove(raw_video)
                print(f"   🗑️ 已刪除原始無字幕影片: {os.path.basename(raw_video)}")
            except Exception as e:
                print(f"   ⚠️ 刪除原始影片失敗: {e}")

        # D. 更新資料庫
        cursor.execute("UPDATE DailyNews SET is_published = 1 WHERE id = ?", (item['id'],))
        print(f"   ✅ 資料庫已標記為已發布 (is_published = 1)")

    conn.commit()
    
    # E. 清理未被選中且未處理的舊新聞標題
    print("\n🧹 正在清理資料庫中未被選中的舊新聞標題...")
    try:
        cursor.execute("DELETE FROM DailyNews WHERE is_selected = 0 AND is_processed = 0 AND is_published = 0")
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"   ✅ 已成功清除 {deleted_count} 筆未選中的標題，資料庫已重置。")
    except Exception as e:
        print(f"   ⚠️ 資料庫清理失敗: {e}")

    conn.close()
    print("\n🎉 歸檔作業與資料庫整理完成！")
    print("   目前的資料庫僅保留正在處理或已歸檔的資料，方便下次重新爬蟲。")

def cleanup_output_folders():
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
            print(f"🧹 正在清空: {folder}...")
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"   ❌ 無法刪除 {filename}: {e}")

if __name__ == "__main__":
    main()
