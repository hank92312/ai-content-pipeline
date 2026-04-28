import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')


# 1. 連線資料庫
conn = sqlite3.connect('auto_channel.db')
cursor = conn.cursor()

# [自動化小機關]：檢查並新增 is_selected 欄位 (如果還沒有的話)
try:
    cursor.execute("ALTER TABLE DailyNews ADD COLUMN is_selected INTEGER DEFAULT 0")
    conn.commit()
    print("🔧 資料庫已升級：新增 is_selected (已選定) 欄位。")
except sqlite3.OperationalError:
    # 如果欄位已經存在，就會觸發這個錯誤，我們直接忽略即可
    pass

# 2. 優先撈取「還沒被處理過」且「還沒被選定」的新聞
cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 0 AND is_selected = 0")
unprocessed_news = cursor.fetchall()

if not unprocessed_news:
    print("目前沒有新的新聞需要挑選喔！")
    choice = input("👉 是否要從「已處理過」的新聞中重新挑選並重新製作腳本？(y/n, 預設為 n): ").strip().lower()
    if choice == 'y':
        # 撈取最近 15 筆已處理過的新聞
        cursor.execute("SELECT id, category, title FROM DailyNews WHERE is_processed = 1 AND is_selected = 0 ORDER BY id DESC LIMIT 15")
        unprocessed_news = cursor.fetchall()
        if not unprocessed_news:
            print("資料庫中也沒有任何已處理過的新聞喔！")
            conn.close()
            exit()
    else:
        conn.close()
        exit()

print("\n=== 📰 新聞挑選清單 ===")
for index, news in enumerate(unprocessed_news):
    db_id, category, title = news
    print(f"[{index}] ({category}) {title}")
print("====================")
# 3. 讓總編輯輸入想挑選的編號
user_input = input("\n👉 請輸入您想做成短影音的新聞編號 (使用逗號分隔，例如: 0,2,4): ")

try:
    selected_indices = [int(i.strip()) for i in user_input.split(',')]
    
    # 4. 處理輸入並將選定的新聞 ID 收集起來
    selected_db_ids = []
    print("\n✅ 您選定了以下主題，已標記至資料庫：")
    
    for i in selected_indices:
        selected_news = unprocessed_news[i]
        selected_db_ids.append(selected_news[0]) # 收集真實的資料庫 ID
        print(f"- {selected_news[2]}")
        
    # 5. [關鍵升級] 將這些 ID 在資料庫中標記為 is_selected = 1，並重置已處理狀態為 0 (以便重新製作)
    for db_id in selected_db_ids:
        cursor.execute("UPDATE DailyNews SET is_selected = 1, is_processed = 0 WHERE id = ?", (db_id,))
        
    conn.commit()
    print("\n🎉 標記完成！您現在可以去執行 step2 來自動生成劇本了。")
    
except Exception as e:
    print(f"❌ 發生錯誤，請確認輸入格式是否正確: {e}")

conn.close()