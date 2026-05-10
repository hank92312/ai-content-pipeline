import config
import sqlite3
import requests
from bs4 import BeautifulSoup
import datetime

print("=============================")
print("  📰 手動新增新聞/專題工具  ")
print("=============================")

# 1. 取得使用者貼上的網址
url = input("\n請貼上您想加入的網頁網址 (URL): ").strip()

if not url:
    print("網址不能為空，程式結束。")
    exit()

# 2. 半自動貼心功能：嘗試去該網頁抓取標題與縮圖
print("⏳ 正在連線至網頁嘗試抓取標題與縮圖...")
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
    print(f"⚠️ 自動抓取失敗 ({e})")

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

# 5. 寫入共用的資料庫
today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
conn = sqlite3.connect(config.DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute('''
        INSERT INTO DailyNews (category, title, link, pub_date, image_url)
        VALUES (?, ?, ?, ?, ?)
    ''', (category, title, url, today, image_url))
    conn.commit()
    print(f"\n✅ 成功！已經將此文章加入資料庫。")
    print(f"👉 狀態：分類 [{category}] | 標題: {title}")
except sqlite3.IntegrityError:
    # 這裡一樣保留了 UNIQUE 的防呆機制
    print("\n❌ 新增失敗：這篇網址之前已經加入過資料庫了喔！")
finally:
    conn.close()

# 自動接續執行 1.5 模組
import subprocess
import sys
print("\n👉 自動接續執行 1.5 挑選模組...")
subprocess.run([sys.executable, 'step1_5_selector.py'])

# 詢問是否執行模組2
ans2 = input("\n❓ 1.5 模組挑選完畢。是否繼續執行 [模組2: AI產生腳本]？ (y/n，輸入 q 退出): ").strip().lower()
if ans2 == 'q':
    print("🚪 中途退出。")
    sys.exit(0)
elif ans2 in ['y', 'yes']:
    print("\n👉 接續執行模組 2...")
    subprocess.run([sys.executable, 'step2_script_generator.py'])
    
    # 執行完模組2後，詢問是否執行模組3
    ans3 = input("\n❓ 模組 2 執行完畢。是否繼續執行 [模組3: 語音合成]？ (y/n，輸入 q 退出): ").strip().lower()
    if ans3 == 'q':
        print("🚪 中途退出。")
        sys.exit(0)
    elif ans3 in ['y', 'yes']:
        print("\n👉 接續執行模組 3...")
        subprocess.run([sys.executable, 'step3_voice_renderer.py'])
        print("\n✅ 所有選定之模組皆執行完畢。")
    else:
        print("⏸️ 結束執行。")
else:
    print("⏸️ 結束執行。")