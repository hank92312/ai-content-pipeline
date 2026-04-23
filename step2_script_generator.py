import json
import os
import sys
import sqlite3
import config
from google import genai
from google.genai import types

sys.stdout.reconfigure(encoding='utf-8')

print("=============================")
print("  🧠 AI 劇本生成中心 (最新 GenAI 套件版) ")
print("=============================")

# 1. 初始化最新的 Gemini API 
client = genai.Client(api_key=config.GEMINI_API_KEY)

# 2. 連線資料庫
conn = sqlite3.connect(config.DB_PATH)
cursor = conn.cursor()

# 3. 撈取「已選定 (is_selected = 1)」且「未處理 (is_processed = 0)」的新聞
# 加入 IFNULL 為了相容之前的資料，若沒圖片就給空字串
cursor.execute("SELECT id, category, title, IFNULL(image_url, ''), IFNULL(content, '') FROM DailyNews WHERE is_processed = 0 AND is_selected = 1")
selected_news = cursor.fetchall()

if not selected_news:
    print("目前沒有待處理的「已選定」新聞。請先執行 step1_5_selector.py 進行選題！")
    exit()

# 3.5 選擇生成模式
print("\n請選擇腳本生成模式：")
print("[1] 標準模式 (約 30 秒，使用 gemini-2.5-flash，適合快速短影音)")
print("[2] 專業深入報導 (約 60 秒，內容更豐富完整)")
mode_choice = input("請輸入選項 (1 或 2，預設為 1): ").strip()
is_pro_mode = (mode_choice == "2")

target_model = 'gemini-2.5-flash'
if is_pro_mode:
    print("\n請選擇專業模式要使用的模型：")
    print("[1] gemini-2.5-pro (穩定高階)")
    print("[2] gemini-3-flash (新一代快速)")
    print("[3] gemini-3.1-pro (最新一代高階)")
    model_choice = input("請輸入選項 (1, 2 或 3，預設為 1): ").strip()
    if model_choice == "2":
        target_model = 'gemini-3-flash'
    elif model_choice == "3":
        target_model = 'gemini-3.1-pro'
    else:
        target_model = 'gemini-2.5-pro'
    print(f"\n=> 已選擇模型：{target_model}")

# 4. 針對「每一則」新聞自動生成對應的腳本
for news in selected_news:
    db_id, category, title, image_url, content = news
    print(f"\n🎬 正在產製 [{category}] 類別的影片腳本 (新聞ID: {db_id})...")
    
    tone = "專業、充滿自信且帶有一點懸疑感" if category == "Finance" else "熱情、激動、像個資深玩家"
    
    video_length = "60" if is_pro_mode else "30"
    word_limit = "200 到 250" if is_pro_mode else "100 到 120"
    main_content_limit = "不超過 150 字，請進行更深入的專業分析與多角度報導" if is_pro_mode else "不超過 60 字"
    image_count = 4 if is_pro_mode else 2
    image_prompts_desc = f"""1. 你必須在 `visual_prompts` 陣列中提供「剛好 {image_count} 個」不同的英文生圖提示詞 (Prompts)。
       - 第 1 個提示詞：針對新聞事件本身（開場重點）的畫面設計。
       - 第 2 個提示詞：針對後續發展、或呼喚觀眾情緒的相關畫面設計。"""
    if is_pro_mode:
        image_prompts_desc += """
       - 第 3 個提示詞：針對專業分析或技術細節的畫面設計。
       - 第 4 個提示詞：針對結尾或展望未來的畫面設計。"""
    image_prompts_desc += """\n       （請確保提示詞包含 "2D anime style, visually stunning" 等以貼合頻道風格。結尾強烈要求加上 "No text, no letters, no words" 避免產出亂碼文字）"""
    
    prompt = f"""
    你現在是「蔡小花」，一位在「小花的AI情報站」擁有百萬訂閱的短影音 Vtuber。
    【角色設定】：
    - 外型與風格：二次元科技風，具備反差萌。
    - 專長：流暢且自帶吐槽或幽默感地播報硬核財經與 3C 情報。
    - 語氣：{tone}，絕對要像真人在說話，口語化，不要生硬地唸新聞稿。
    
    請幫我將以下【這 1 則】{category} 領域的新聞標題，轉化為一段約 {video_length} 秒內的短影音完整腳本。
    【字數極度限制】：請確保輸出的文案口白（intro + main_content + outro）總中文字數在 {word_limit} 字之間，以符合 {video_length} 秒短影音的最佳節奏！
    
    【今日新聞標題】：
    {title}
    
    【今日新聞內容（背景參考）】：
    {content if content else "(無完整內容，請僅依據標題發揮)"}
    
    【腳本結構與寫作要求】
    1. 開場白 (intro)：不要用死板的「歡迎回到...」。請根據新聞最勁爆的點，動態生成「三秒內抓住眼球」的破題開場。
    2. 主內容 (main_content)：將新聞重點流暢地講故事，{main_content_limit}。
    3. 收尾句 (outro)：根據此新聞內容，拋出一個問題引導觀眾留言，並自然地呼籲訂閱。
    
    【配圖與特效要求】
    {image_prompts_desc}
    2. 你必須在 `keywords` 陣列中提供 2 到 4 個「高潮重點字或詞彙」（直接從你寫的文案中擷取）。這些字將會在影片中以黃色或紅色高亮顯示！請挑選最具情緒或最勁爆的詞！
    
    【重點規則】
    必須嚴格回傳以下的 JSON 格式，且絕不能包含 markdown (```json 等)。
    
    {{
        "intro": "...",
        "main_content": "...",
        "outro": "...",
        "visual_prompts": ["畫面一的英文提示詞...", "畫面二的英文提示詞..."{', "畫面三...", "畫面四..."' if is_pro_mode else ''}],
        "keywords": ["重點詞一", "重點詞二", "重點詞三"]
    }}
    """

    try:
        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        script_data = json.loads(response.text)
        
        # 組合最終腳本 (動態開場 + 主內容 + 動態結尾)
        final_script = f"{script_data['intro']} {script_data['main_content']} {script_data['outro']}"
        
        # 儲存腳本文字檔 (給語音模組使用)
        base_filename = f"script_{category}_{db_id}"
        txt_path = f"output_scripts/{base_filename}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(final_script)
            
        # 儲存腳本中繼檔 (.json) (給生圖模組使用)
        json_path = f"output_scripts/{base_filename}.json"
        script_data["news_sources"] = [{"id": db_id, "title": title, "image_url": image_url}]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ 生成成功！({len(final_script)} 字) -> {txt_path} & .json")
        print(f"【🎙️ 預覽】：{final_script[:50]}...")
        
        # 5. 更新資料庫狀態 (標記已處理並重置選定狀態)
        cursor.execute("UPDATE DailyNews SET is_processed = 1, is_selected = 0 WHERE id = ?", (db_id,))
            
    except Exception as e:
        print(f"❌ [ID: {db_id}] 腳本生成失敗: {e}")

conn.commit()
conn.close()
print("\n🎉 所有選定新聞皆已處理完畢！")