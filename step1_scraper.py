import sqlite3
import feedparser
import sys
import time
import requests
import re
import json
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

sys.stdout.reconfigure(encoding='utf-8')

# ⚠️ 請將下一行的字串替換為您全新申請的真實金鑰！
API_KEY = "AIzaSyAQD2UcDDAe5b3c9vToTM2pAl99hIKYA7M" 
client = genai.Client(api_key=API_KEY)

# 1. 資料庫連線與初始化
conn = sqlite3.connect('auto_channel.db')
cursor = conn.cursor()

# [新增] 自動建立資料表 (若資料庫全空)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS DailyNews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        title TEXT,
        link TEXT UNIQUE,
        pub_date TEXT,
        is_processed INTEGER DEFAULT 0,
        is_selected INTEGER DEFAULT 0,
        image_url TEXT,
        content TEXT
    )
''')
conn.commit()

# [自動化小機關]：檢查並新增 image_url 欄位 (支援模組五產圖)
except sqlite3.OperationalError:
    pass

# [自動化小機關]：檢查並新增 content 欄位 (支援本地新聞稿全文)
try:
    cursor.execute("ALTER TABLE DailyNews ADD COLUMN content TEXT")
    conn.commit()
    print("🔧 資料庫已升級：新增 content 欄位。")
except sqlite3.OperationalError:
    pass

# 2. 定義來源清單與過濾設定
# limit_type 決定合併計算還是個別計算；method 決定使用點閱率或 AI 篩選
sources = [
    {"bucket": "Gaming", "category": "Gaming", "url": "https://gnn.gamer.com.tw/rss.xml"},
    {"bucket": "Finance", "category": "Finance", "url": "https://tw.stock.yahoo.com/rss?category=intl-markets"},
    {"bucket": "Finance", "category": "Finance", "url": "https://tw.stock.yahoo.com/rss?category=taiwan-markets"},
    {"bucket": "Tech3C_TechNews", "category": "Tech3C", "url": "https://technews.tw/feed/"},
    {"bucket": "Tech3C_Cool3c", "category": "Tech3C", "url": "https://www.cool3c.com/feed"},
    {"bucket": "Tech3C_TKBang", "category": "Tech3C", "url": "https://feeds.feedburner.com/techbang"}
]

processing_rules = {
    "Gaming": {"method": "views", "limit": 5, "final_category": "Gaming"},
    "Finance": {"method": "ai", "limit": 5, "final_category": "Finance"},
    "Tech3C_TechNews": {"method": "ai", "limit": 2, "final_category": "Tech3C"},
    "Tech3C_Cool3c": {"method": "ai", "limit": 2, "final_category": "Tech3C"},
    "Tech3C_TKBang": {"method": "ai", "limit": 2, "final_category": "Tech3C"},
}

buckets = {k: [] for k in processing_rules.keys()}

print("=============================")
print("  🕸️ AI 混合爬蟲過濾中心 ")
print("=============================\n")

# --- 輔助函數：獲取巴哈姆特觀看人數 ---
def get_bahamut_views(link):
    try:
        res = requests.get(link, timeout=5)
        # 尋找像是 "1234 人觀看" 的字眼
        match = re.search(r'(\d+)\s*人觀看', res.text)
        if match:
            return int(match.group(1))
    except:
        pass
    return 0

# --- 輔助函數：AI 總編輯挑選 ---
def ai_select_top_n(category, articles, top_n):
    if not articles: return []
    if len(articles) <= top_n: return articles
    
    print(f"    🧠 啟動 AI 總編輯，正從 {len(articles)} 篇中挑選最佳 {top_n} 篇...")
    
    prompt = f"你是一頻道的短影音總編輯。請從以下 {len(articles)} 篇 {category} 新聞中，根據「具備爆點、吸引人」的標準，挑選出最適合製作成短影音的前 {top_n} 篇。請務必只回傳包含被選中編號的 JSON 陣列 (例如: [0, 2, 5])，絕對不要回傳其他多餘文字符號。\n\n"
    for idx, art in enumerate(articles):
        prompt += f"[{idx}] 標題: {art['title']}\n"
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            selected_indices = json.loads(match.group(0))
            return [articles[i] for i in selected_indices if i < len(articles)][:top_n]
    except Exception as e:
        print(f"    ❌ AI 解析失敗: {e}，改用最新文章頂替。")
        
    return articles[:top_n] # 發生意外時直接取最新

# --- 步驟 A：收集與初步過濾 (24小時內) ---
current_time = time.time()
SECONDS_IN_A_DAY = 24 * 60 * 60

for src in sources:
    bucket_id = src["bucket"]
    url = src["url"]
    
    print(f"🔍 掃描來源: {url}")
    feed = feedparser.parse(url)
    
    # 每個來源我們最多先考慮前 20 篇，避免 AI token 爆掉或抓太久
    count = 0
    for entry in feed.entries:
        if count >= 20: break
            
        # 24 小時時效性過濾
        pass_time_check = False
        if 'published_parsed' in entry and entry.published_parsed:
            pub_time = time.mktime(entry.published_parsed)
            if current_time - pub_time <= SECONDS_IN_A_DAY:
                pass_time_check = True
        else:
            # 如果 RSS 沒提供標準時間，無條件先放行
            pass_time_check = True
            
        if not pass_time_check:
            continue
            
        # 嘗試從 RSS 中擷取現成的圖片網址
        image_url = ""
        if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
            image_url = entry.media_thumbnail[0]['url']
        elif 'media_content' in entry and len(entry.media_content) > 0:
            image_url = entry.media_content[0]['url']
        if not image_url and 'description' in entry:
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.description)
            if match:
                image_url = match.group(1)
                
        buckets[bucket_id].append({
            "title": entry.title,
            "link": entry.link,
            "pub_date": entry.get('published', 'Unknown Date'),
            "image_url": image_url
        })
        count += 1
        
# --- 步驟 B：依照混合規則進行深度過濾 ---
final_selected_articles = []

for bucket_id, articles in buckets.items():
    rule = processing_rules[bucket_id]
    final_cat = rule["final_category"]
    
    if not articles:
        continue
        
    print(f"\n⚙️ 處理分組 [{bucket_id}] (共收集 {len(articles)} 篇)")
    
    selected = []
    if rule["method"] == "views":
        print("    📊 模式: 真實點閱率 (優先)")
        # 爬取點閱率
        for art in articles:
            art["views"] = get_bahamut_views(art["link"])
        # 由大到小排序
        articles.sort(key=lambda x: x["views"], reverse=True)
        selected = articles[:rule["limit"]]
    else:
        print("    🤖 模式: AI 總編輯")
        selected = ai_select_top_n(final_cat, articles, rule["limit"])
        
    # 打上最終的系統分類標籤
    for art in selected:
        art["sys_category"] = final_cat
        final_selected_articles.append(art)
        print(f"    ⭐ 晉級: {art['title'][:30]}...")

# --- 步驟 C：深度抓圖與資料庫寫入 ---
print("\n=============================")
print(f"💾 開始深度處理與寫入 (總晉級 {len(final_selected_articles)} 篇)")
new_insert_count = 0

for art in final_selected_articles:
    cat = art["sys_category"]
    title = art["title"]
    link = art["link"]
    pub_date = art["pub_date"]
    image_url = art["image_url"]

    # [深度抓圖升級] 如果 RSS 裡面完全沒有圖片，我們進去網頁抓！
    if not image_url and link:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
            res = requests.get(link, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                og_image = soup.find("meta", property="og:image")
                if og_image and og_image.get("content"):
                    image_url = og_image["content"]
        except Exception as e:
            print(f"  ⚠️ 深度抓圖失敗 [{link}]: {e}")
            
    # 寫入資料庫
    try:
        cursor.execute('''
            INSERT INTO DailyNews (category, title, link, pub_date, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (cat, title, link, pub_date, image_url))
        new_insert_count += 1
    except sqlite3.IntegrityError:
        pass # 重複則略過

conn.commit()
conn.close()

print(f"\n🎉 執行完畢！經過重重過濾，本次共新增了 {new_insert_count} 筆極品精華到資料庫中。")