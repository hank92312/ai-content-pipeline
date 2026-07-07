import config
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')


def _ensure_schema(cursor, conn):
    # [自動化小機關]：檢查並新增 is_selected 欄位 (如果還沒有的話)
    try:
        cursor.execute("ALTER TABLE DailyNews ADD COLUMN is_selected INTEGER DEFAULT 0")
        conn.commit()
        print("🔧 資料庫已升級：新增 is_selected (已選定) 欄位。")
    except sqlite3.OperationalError:
        # 如果欄位已經存在，就會觸發這個錯誤，我們直接忽略即可
        pass


def get_pending_news(include_processed=False):
    """撈取可供選題的新聞清單，回傳 [(id, category, title), ...]"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    _ensure_schema(cursor, conn)

    if include_processed:
        # 撈取最近 15 筆已處理過的新聞 (供重新挑選製作)
        cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 1 AND is_selected = 0 ORDER BY id DESC LIMIT 15")
    else:
        cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 0 AND is_selected = 0")

    result = cursor.fetchall()
    conn.close()
    return result


def run(selected_ids, log=print):
    """將指定的新聞 ID 標記為 is_selected = 1，並重置 is_processed 為 0 (以便重新製作)"""
    if not selected_ids:
        log("⚠️ 未提供任何選定的新聞 ID。")
        return {"success": 0, "ids": []}

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    _ensure_schema(cursor, conn)

    log("\n✅ 您選定了以下主題，已標記至資料庫：")
    marked = []
    for db_id in selected_ids:
        cursor.execute("SELECT title FROM DailyNews WHERE id = ?", (db_id,))
        row = cursor.fetchone()
        if row:
            log(f"- {row[0]}")
            cursor.execute("UPDATE DailyNews SET is_selected = 1, is_processed = 0 WHERE id = ?", (db_id,))
            marked.append(db_id)

    conn.commit()
    conn.close()
    log("\n🎉 標記完成！您現在可以去執行 step2 來自動生成劇本了。")
    return {"success": len(marked), "ids": marked}


def main():
    """CLI 互動版"""
    pending = get_pending_news(include_processed=False)

    if not pending:
        print("目前沒有新的新聞需要挑選喔！")
        choice = input("👉 是否要從「已處理過」的新聞中重新挑選並重新製作腳本？(y/n, 預設為 n): ").strip().lower()
        if choice == 'y':
            pending = get_pending_news(include_processed=True)
            if not pending:
                print("資料庫中也沒有任何已處理過的新聞喔！")
                return
        else:
            return

    print("\n=== 📰 新聞挑選清單 ===")
    for index, news in enumerate(pending):
        db_id, category, title = news
        print(f"[{index}] ({category}) {title}")
    print("====================")

    # 讓總編輯輸入想挑選的編號
    user_input = input("\n👉 請輸入您想做成短影音的新聞編號 (使用逗號分隔，例如: 0,2,4): ")

    try:
        selected_indices = [int(i.strip()) for i in user_input.split(',')]
        selected_db_ids = [pending[i][0] for i in selected_indices]
        run(selected_db_ids)
    except Exception as e:
        print(f"❌ 發生錯誤，請確認輸入格式是否正確: {e}")


if __name__ == "__main__":
    main()
