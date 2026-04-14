import os
import shutil
import sqlite3
import config

def main():
    print("========================================")
    print("  📁 模組九：影片完工歸檔中心")
    print("========================================")

    # 1. 讀取資料庫，找出所有已處理 (is_processed=1) 但未發布 (is_published=0) 的新聞
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 1 AND is_published = 0")
    eligible_news = cursor.fetchall()
    
    if not eligible_news:
        print("目前沒有待歸檔的影片（所有處理中的新聞已發布或尚未產製）。")
        conn.close()
        return

    # 2. 核對實體檔案是否存在
    to_archive_list = []
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
        print("未在 output_videos 中找到對應的影片檔案。")
        conn.close()
        return

    # 3. 顯示選單讓使用者勾選
    print("\n📦 以下影片已完成產製，請選擇要「歸檔」的項目（代表已確認在各平台發布成功）：")
    for idx, item in enumerate(to_archive_list):
        print(f"[{idx}] {item['title']} ({item['video_path']})")
    
    print("--------------------")
    print("👉 請輸入編號 (多筆請用逗號隔開例如 0,2，或輸入 A 全選，Q 退出)：")
    choice = input("> ").strip().upper()
    
    if choice == 'Q':
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

        # B. 搬移素材檔案 (json, txt, wav)
        assets = [
            (config.OUTPUT_SCRIPTS, f"{item['basename']}.json"),
            (config.OUTPUT_SCRIPTS, f"{item['basename']}.txt"),
            (config.OUTPUT_VOICES, f"{item['basename']}.wav")
        ]
        
        for folder, filename in assets:
            src = os.path.join(folder, filename)
            if os.path.exists(src):
                try:
                    shutil.move(src, os.path.join(config.COMPLETED_ASSETS_DIR, filename))
                except Exception as e:
                    print(f"   ⚠️ 素材 {filename} 搬移失敗: {e}")

        # C. 更新資料庫
        cursor.execute("UPDATE DailyNews SET is_published = 1 WHERE id = ?", (item['id'],))
        print(f"   ✅ 資料庫已標記為已發布 (is_published = 1)")

    conn.commit()
    conn.close()
    print("\n🎉 歸檔作業完成！這些影片將不再出現在待發布清單中。")

if __name__ == "__main__":
    main()
