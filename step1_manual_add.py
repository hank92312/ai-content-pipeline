import config
import sqlite3
import requests
from bs4 import BeautifulSoup
import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')


def fetch_page_preview(url, log=print):
    """嘗試連線至網頁抓取標題與 og:image 縮圖，回傳 {"title": str, "image_url": str}"""
    log("⏳ 正在連線至網頁嘗試抓取標題與縮圖...")
    auto_title = ""
    image_url = ""
    try:
        # 加上 headers 偽裝成一般瀏覽器，避免被網站阻擋
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'  # 確保中文不會變亂碼

        # 解析網頁原始碼，找出 <title> 標籤與縮圖
        soup = BeautifulSoup(response.text, 'html.parser')
        if soup.title:
            auto_title = soup.title.string.strip()

        # 擷取 og:image 以供模組五後續作為配圖使用
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_url = og_image["content"]

    except Exception as e:
        log(f"⚠️ 自動抓取失敗 ({e})")

    return {"title": auto_title, "image_url": image_url}


def run(url, title, category="Finance", image_url="", on_duplicate=None, log=print):
    """
    將一筆新聞連結寫入資料庫。若網址已存在 (重複)，依 on_duplicate 回呼函式決定後續處理。

    on_duplicate(existing: dict) -> str，existing 內含 "state" 欄位，依狀態回傳對應動作：
        state == "selected_pending" (已選定、未處理)：回傳 "reset" 或 "keep" (預設)
        state == "new_unselected"   (未選定、未處理)：回傳 "leave" 或 "select" (預設)
        state == "processed"        (已處理過)      ：回傳 "reprocess" 或 "leave" (預設)
    若 on_duplicate 為 None，一律採用上述「預設」動作 (維持現狀/延續選定)。

    回傳: {"status": "inserted"/"duplicate"/"error", "db_id": ..., "action": ...}
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO DailyNews (category, title, link, pub_date, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (category, title, url, today, image_url))
        conn.commit()
        db_id = cursor.lastrowid
        log(f"\n✅ 成功！已經將此文章加入資料庫。")
        log(f"👉 狀態：分類 [{category}] | 標題: {title}")
        conn.close()
        return {"status": "inserted", "db_id": db_id}

    except sqlite3.IntegrityError:
        log("\n⚠️ 偵測到此網址已存在於資料庫中。")
        cursor.execute("SELECT id, category, title, is_selected, is_processed FROM DailyNews WHERE link = ?", (url,))
        existing = cursor.fetchone()

        if not existing:
            log("❌ 查詢現有資料失敗。")
            conn.close()
            return {"status": "error", "db_id": None, "action": None}

        db_id, ext_category, ext_title, is_selected, is_processed = existing
        log(f"👉 目前狀態：分類 [{ext_category}] | 標題: {ext_title}")

        info = {"id": db_id, "category": ext_category, "title": ext_title,
                "is_selected": is_selected, "is_processed": is_processed}

        if is_selected == 1 and is_processed == 0:
            info["state"] = "selected_pending"
            log("💡 該文章已被選定（等待 AI 產生腳本中），但可能因前次執行意外中斷而未完成。")
            action = on_duplicate(info) if on_duplicate else "keep"
            if action == "reset":
                cursor.execute("UPDATE DailyNews SET is_selected = 0 WHERE id = ?", (db_id,))
                conn.commit()
                log("✅ 已重置為「未選定」狀態。它將出現在接下來的 1.5 模組選題清單中。")
            else:
                log("✅ 已保留「選定」狀態。稍後將可直接進行模組 2 腳本生成。")

        elif is_selected == 0 and is_processed == 0:
            info["state"] = "new_unselected"
            log("💡 該文章已在資料庫中，但「尚未被選定」。")
            action = on_duplicate(info) if on_duplicate else "select"
            if action != "leave":
                cursor.execute("UPDATE DailyNews SET is_selected = 1 WHERE id = ?", (db_id,))
                conn.commit()
                log("✅ 已標記為「已選定」狀態。")
            else:
                log("✅ 維持「未選定」狀態。它將出現在接下來的 1.5 模組選題清單中。")

        elif is_processed == 1:
            info["state"] = "processed"
            log("💡 該文章過去已經成功處理完畢（已生成過影片腳本）。")
            action = on_duplicate(info) if on_duplicate else "leave"
            if action == "reprocess":
                cursor.execute("UPDATE DailyNews SET is_selected = 1, is_processed = 0 WHERE id = ?", (db_id,))
                conn.commit()
                log("✅ 已重置為「已選定、未處理」狀態，稍後可直接重新製作腳本。")
            else:
                log("✅ 未做任何變更。")
        else:
            action = None

        conn.close()
        return {"status": "duplicate", "db_id": db_id, "action": action}


def main():
    """CLI 互動版"""
    print("=============================")
    print("  📰 手動新增新聞/專題工具  ")
    print("=============================")

    # 1. 取得使用者貼上的網址
    url = input("\n請貼上您想加入的網頁網址 (URL): ").strip()

    if not url:
        print("網址不能為空，程式結束。")
        return

    # 2. 半自動貼心功能：嘗試去該網頁抓取標題與縮圖
    preview = fetch_page_preview(url)
    auto_title = preview["title"]
    image_url = preview["image_url"]

    # 3. 確認標題
    title = ""
    if auto_title:
        print(f"\n💡 成功抓到標題：【{auto_title}】")
        if image_url:
            print(f"🖼️  成功抓到首圖：【{image_url}】")
        use_auto = input("是否直接使用此標題？ (直接按 Enter 代表是，輸入 N 則手動重新命名): ").strip().upper()
        if use_auto == 'N':
            title = input("📝 請手動輸入標題: ").strip()
        else:
            title = auto_title
    else:
        # 如果真的抓不到，才強迫手動輸入
        title = input("\n📝 無法自動抓取，請手動輸入標題: ").strip()

    # 4. 選擇分類
    print("\n📦 請選擇文章分類:")
    print("[1] Finance (財經/國際情勢)")
    print("[2] Gaming (遊戲/動漫/科技)")
    cat_choice = input("請輸入 1 或 2 (預設為 1): ").strip()
    category = "Gaming" if cat_choice == '2' else "Finance"

    def cli_on_duplicate(existing):
        state = existing["state"]
        if state == "selected_pending":
            ans = input("❓ 是否保留「選定」狀態直接進行後續腳本生成？ (Enter 代表是，輸入 N 則重置為未選定狀態以重新選題): ").strip().upper()
            return "reset" if ans == 'N' else "keep"
        elif state == "new_unselected":
            ans = input("❓ 是否直接將它標記為「已選定」（直接進入腳本生成排程）？ (Enter 代表是，輸入 N 則維持未選定): ").strip().upper()
            return "leave" if ans == 'N' else "select"
        elif state == "processed":
            ans = input("❓ 是否要「重新製作」此文章（重置為已選定、未處理狀態）？ (y/n，預設為 n): ").strip().lower()
            return "reprocess" if ans in ['y', 'yes'] else "leave"
        return "leave"

    # 5. 寫入共用的資料庫
    run(url, title, category, image_url=image_url, on_duplicate=cli_on_duplicate)

    # 自動接續執行 1.5 模組
    import pipeline_chain
    pipeline_chain.run_and_offer_next(auto_run_selector=True)


if __name__ == "__main__":
    main()
