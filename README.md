# 🎬 AI 自動化短影音內容流水線 (AI Content Pipeline)

> 從「網路新聞」到「已上架的短影音」——一條端到端、人機協作的 AI 內容生產管線。
>
> 輸入財經/科技新聞，自動產出帶字幕、AI 配音、AI 配圖的直式短影音，並一鍵發布至 YouTube / Facebook / Instagram / TikTok。

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-StateMachine-003B57?logo=sqlite&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini%20%2B%20Imagen-4285F4?logo=google&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?logo=playwright&logoColor=white)
![MoviePy](https://img.shields.io/badge/MoviePy-2.0-FF6F00)

---

## 📌 專案簡介

這是一個 **從 0 到 1 獨立開發** 的 AI 內容自動化專案。整條管線拆成 **9 個可獨立執行又能自動接續的模組**，以 **Python + SQLite 狀態機** 為骨幹，把人力集中在「選題」與「發布覆核」兩個判斷點，其餘流程交由程式與 AI 自動完成。

實際營運的頻道：**「小花的AI情報站」**——虛擬角色「蔡小花」播報硬核財經與 3C 情報。

* **影片規格**：直式短影音 (Shorts / Reels)，9:16，總長 30–50 秒
* **設計哲學**：不追求「無人值守的全自動」，而是「人機協作的高效半自動」——AI 負責判斷與生成（寫稿、生圖、解析），程式碼負責確定性流程（狀態管理、路由、檔案搬移）

---

## 🏗️ 系統架構

```
 [RSS / 手動 / 本地稿件]
          │  模組 1 / 1.5
          ▼
 ┌──────────────────────┐   is_selected → is_processed → is_published
 │  SQLite: auto_channel │ ◀──── 狀態機（單一事實來源）────┐
 └──────────────────────┘                                  │
          │ 模組 2   AI 腳本生成 (Gemini)                   │
          ▼                                                  │
   output_scripts/ (TXT + JSON)                              │
          │ 模組 3   語音 edge-tts → RVC 音色轉換            │
          ▼                                                  │
   output_voices/ (final.wav + 字幕時間軸)                   │
          │ 模組 5   配圖 Gemini Vision + Imagen (9:16)      │
          ▼                                                  │
   output_images/                                            │
          │ 模組 6   MoviePy 合成 + 字幕壓製 (GPU 編碼)      │
          ▼                                                  │
   output_videos/ (*_subtitled.mp4)                          │
          │ 模組 8   Playwright 多平台發布                   │
          ▼                                                  │
   YouTube / Facebook / Instagram / TikTok                   │
          │ 模組 9   歸檔 + is_published = 1 ────────────────┘
          ▼
   completed_archives/
```

---

## 🛠️ 技術棧

| 領域 | 技術 |
|------|------|
| **語言 / 資料層** | Python 3.11、SQLite（內容狀態機）、`python-dotenv`（金鑰隔離） |
| **AI 文字 / 視覺** | Google **Gemini API**（腳本與文案）、**Gemini Vision**（解析新聞圖）、**Imagen**（風格化生圖） |
| **語音** | **edge-tts**（基礎 TTS + 字級時間軸）+ **RVC / VITS**（音色克隆） |
| **媒體處理** | **MoviePy 2.0**、Pillow、NumPy（剪輯 / 動態字幕 / 關鍵字標色） |
| **資料蒐集** | feedparser（RSS）、BeautifulSoup4、requests、pypdf |
| **發布自動化** | **Playwright**（模擬真人發布，繞過 API 門檻 + Session 持久化） |
| **硬體加速** | RVC: **DirectML**；FFmpeg: **AMD AMF / Intel QuickSync**；皆「GPU 失敗自動降級 CPU」 |

---

## ✨ 工程亮點

1. **以資料庫為單一事實來源的狀態機**：全流程靠 `DailyNews` 表的三個布林欄位（`is_selected → is_processed → is_published`）驅動，模組之間零耦合，任一步皆可獨立重跑或中途接續。
2. **硬體相容性優先的降級架構**：同一份程式碼能在「AMD 桌電」與「無顯卡筆電」間無縫切換，GPU 加速失敗即自動回退 CPU。
3. **Human-in-the-Loop 兩個介入點**：選題台（AI 不替你決定做哪則）＋ 發布覆核（上傳支援鍵盤即時 `[S]` 跳過 / `[W]` 重置等待 / `[R]` 重試，失敗暫停而非崩潰）。
4. **繞過平台 API 門檻**：以 Playwright 模擬真人發布，並對 YouTube/Facebook 實作精確的「成功 Dialog 與網址跳轉偵測」，可應對慢速網路。
5. **成本與資源治理**：測試時限制單筆生成以控管 Gemini API 額度；edge-tts 以 `tenacity` 指數退避重試最多 5 次；歸檔時自動清理無字幕原始影片節省空間。

---

## 📂 模組與檔案對照

| 模組 | 檔案 | 職責 |
|------|------|------|
| 1 資料蒐集 | `step1_scraper.py` / `step1_manual_add.py` / `step1_local_loader.py` | RSS 爬蟲 / 手動加題 / 本地稿件匯入 (.txt/.md/.pdf/.json) |
| 1.5 人機協作 | `step1_5_selector.py` | 總編輯選題台 |
| 2 腳本生成 | `step2_script_generator.py` | Gemini 生成口播腳本（30s / 60s 雙模式） |
| 3 語音渲染 | `step3_voice_renderer.py` | edge-tts + RVC 音色轉換 |
| 5 配圖生成 | `step5_visual_generator.py` | Gemini Vision + Imagen 風格化生圖 |
| 6 影片合成 | `step6_video_assembly.py` | MoviePy 合成 + 動態字幕 + 硬體編碼 |
| 8 多平台發布 | `step8_auto_uploader.py` + `uploaders/` | Playwright 自動上傳 4 平台（策略模式） |
| 9 歸檔整理 | `step9_manual_archive.py` | 資產整組搬移 + 空間優化 |
| 共用 | `config.py` | 全域路徑與參數中央化 |

---

## 🚀 快速開始

```powershell
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 設定金鑰 (.env)
#    GEMINI_API_KEY=your_key_here

# 3. 確保 RVC 框架就位 (RVC1006AMD_Intel1/ + 個人 .pth/.index 模型)

# 4. 依模組順序執行 (每個模組可獨立啟動、自動接續下一步)
python step1_scraper.py          # 抓新聞
python step1_5_selector.py       # 選題
python step2_script_generator.py # 生腳本
python step3_voice_renderer.py   # 配音
python step5_visual_generator.py # 配圖
python step6_video_assembly.py   # 剪輯
python step8_auto_uploader.py    # 發布
python step9_manual_archive.py   # 歸檔
```

> 程式內建硬體偵測，無顯卡環境會自動降級 CPU，無需改任何設定。

---

## 📖 延伸閱讀

* **[完整作品說明書 (PROJECT_PORTFOLIO.md)](PROJECT_PORTFOLIO.md)** — 含設計動機、完整技術細節、工程取捨與個人貢獻說明
* **[開發架構指南 (SKILL.md)](SKILL.md)** — 各模組設計細節與開發守則

---

## 📌 現況

模組 1, 1.5, 2, 3, 5, 6, 8, 9 ✅ 已完成並串接｜模組 4（虛擬角色嘴型同步）🚧 規劃中（目前用靜態去背頭像）

---

*本專案為個人作品集展示用途。新聞素材僅作範例，版權歸原作者所有。*
