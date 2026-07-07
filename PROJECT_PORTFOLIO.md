# AI 自動化短影音內容流水線 — 專案詳細說明

> **AI Content Pipeline** ｜ 個人全端自動化專案
> 一套從「新聞蒐集 → AI 腳本 → AI 配音 → AI 配圖 → 自動剪輯 → 多平台發布 → 歸檔」的端到端短影音內容生產系統。
>
> GitHub：`https://github.com/hank92312/ai-content-pipeline`
>
> **實際成品頻道：小花的AI情報站**
> [![YouTube](https://img.shields.io/badge/YouTube-蔡小花的AI情報站-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/@%E8%94%A1%E5%B0%8F%E8%8A%B1%E7%9A%84AI%E6%83%85%E5%A0%B1%E7%AB%99)
> [![Instagram](https://img.shields.io/badge/Instagram-@yourflower180-E4405F?logo=instagram&logoColor=white)](https://www.instagram.com/yourflower180/)
> [![Facebook](https://img.shields.io/badge/Facebook-粉絲專頁-1877F2?logo=facebook&logoColor=white)](https://www.facebook.com/profile.php?id=61573260607447)
> [![TikTok](https://img.shields.io/badge/TikTok-@hank92312-000000?logo=tiktok&logoColor=white)](https://www.tiktok.com/@hank92312)

---

## 1. 專案一句話定位（電梯簡報）

我獨立設計並實作了一條 **9 個模組、可一鍵串接的 AI 內容自動化流水線**：輸入是網路上的財經/科技新聞，輸出是一支帶字幕、配音、配圖、已自動上傳到 YouTube / Facebook / Instagram / TikTok 的直式短影音。整條管線以 **Python + SQLite 狀態機** 為骨幹，整合 **Google Gemini（文字+視覺）、Imagen（生圖）、edge-tts + RVC（語音克隆）、MoviePy（剪輯）、Playwright（瀏覽器自動化發布）**，並針對個人硬體做了 **GPU 加速與 CPU 自動降級** 的工程取捨。

**頻道實例**：「小花的AI情報站」— 虛擬角色「蔡小花」播報硬核財經與 3C 情報。

---

## 2. 解決的問題與設計動機

| 痛點 | 本專案的解法 |
|------|-------------|
| 短影音內容產製耗時（找題 → 寫稿 → 配音 → 剪輯 → 上架，一支動輒數小時） | 拆成 9 個可獨立執行又能自動接續的模組，把人力集中在「選題」與「覆核」兩個判斷點 |
| AI 全自動容易出錯、難控成本 | 導入 **Human-in-the-Loop** 選題台與發布覆核機制；測試時限制單筆生成以控管 Gemini API 額度 |
| 個人裝置算力有限（筆電無顯卡、桌電 AMD GPU） | 所有重運算模組一律「**優先 GPU 加速 → 失敗自動降級 CPU**」，達成跨裝置無縫切換 |
| 各社群平台 API 申請門檻高 | 改用 **Playwright 模擬真人操作** 繞過 API 限制，並加入鍵盤即時介入機制 |

> 設計哲學：**不是追求「無人值守的全自動」，而是「人機協作的高效半自動」**——把 AI 用在判斷與生成（寫稿、生圖、解析），把確定性流程交給程式碼（路由、狀態管理、檔案搬移）。

---

## 3. 系統架構總覽

### 3.1 資料流（端到端）

```
 [RSS / 手動 / 本地稿件]                                                     
          │  模組1 / 1.5                                                     
          ▼                                                                  
 ┌──────────────────────┐   is_selected / is_processed / is_published       
 │  SQLite: auto_channel │ ◀────────── 狀態機（單一事實來源）────────────┐   
 │  DailyNews 資料表      │                                              │   
 └──────────────────────┘                                              │   
          │ 模組2                                                        │   
          ▼                                                              │   
   AI 腳本生成 (Gemini) ──► output_scripts/  (TXT + JSON 中繼檔)         │   
          │ 模組3                                                        │   
          ▼                                                              │   
   語音渲染 edge-tts ─► RVC 音色轉換 ─► output_voices/ (final.wav+subs)  │   
          │ 模組5                                                        │   
          ▼                                                              │   
   配圖生成 Gemini Vision + Imagen ──► output_images/ (9:16)            │   
          │ 模組6                                                        │   
          ▼                                                              │   
   MoviePy 合成 + 字幕壓製 (GPU 編碼) ──► output_videos/ (*_subtitled)   │   
          │ 模組8                                                        │   
          ▼                                                              │   
   Playwright 多平台發布 (YT/FB/IG/TikTok)                               │   
          │ 模組9                                                        │   
          ▼                                                              │   
   歸檔 completed_archives/ ──► is_published = 1 ──────────────────────┘   
```

### 3.2 模組與檔案對照（核心程式碼地圖）

| 模組 | 檔案 | 職責 | 狀態 |
|------|------|------|------|
| 1 資料蒐集 | `step1_scraper.py` | RSS 自動爬蟲（feedparser），UNIQUE 防重複 | ✅ |
| 1 資料蒐集 | `step1_manual_add.py` | 貼網址半自動抓標題（BeautifulSoup） | ✅ |
| 1 資料蒐集 | `step1_local_loader.py` | 本地 `.txt/.md/.pdf/.json` 批次匯入 + 歸檔 | ✅ |
| 1.5 人機協作 | `step1_5_selector.py` | 總編輯選題台，標記 `is_selected` | ✅ |
| 2 腳本生成 | `step2_script_generator.py` | Gemini 生成口播腳本（30s/60s 雙模式） | ✅ |
| 3 語音渲染 | `step3_voice_renderer.py` | edge-tts + RVC 音色轉換 + 字級時間軸 | ✅ |
| 4 虛擬角色 | （`sample.png` 靜態頭像） | 規劃中：Wav2Lip/SadTalker 嘴型同步 | 🚧 |
| 5 配圖生成 | `step5_visual_generator.py` | Gemini Vision 解析 + Imagen 風格化生圖 | ✅ |
| 6 影片合成 | `step6_video_assembly.py` | MoviePy 合成 + 字幕 + 硬體編碼 | ✅ |
| 8 多平台發布 | `step8_auto_uploader.py` + `uploaders/` | Playwright 自動上傳 4 平台 | ✅ |
| 9 歸檔整理 | `step9_manual_archive.py` | 資產整組搬移 + 空間優化 | ✅ |
| 共用 | `config.py` | 全域路徑與參數中央化 | ✅ |

`uploaders/` 套件採策略模式：`base.py`（共用基底）＋ `youtube.py / facebook.py / instagram.py / tiktok.py / xiaohongshu.py`（各平台實作）。

---

## 4. 技術棧（Tech Stack）

### 4.1 核心語言與資料層
| 類別 | 技術 | 用途 |
|------|------|------|
| 語言 | **Python 3.11**（`.venv` 虛擬環境） | 全專案 |
| 資料庫 | **SQLite**（`auto_channel.db`） | 內容狀態機，`DailyNews` 單表管理 `is_selected/is_processed/is_published` |
| 設定管理 | `config.py` + `python-dotenv` | 路徑/參數中央化，`.env` 隔離 API Key |

### 4.2 AI 與生成式服務
| 能力 | 技術／模型 | 說明 |
|------|-----------|------|
| 文字大腦 | **Google Gemini API**（`google-genai` SDK） | 腳本生成、行銷文案；標準/專業模式可切 `gemini-3-flash` / `gemini-3.5-flash` / `gemini-2.5-pro` / `gemini-3.1-pro` |
| 視覺理解 | **Gemini Vision** | 解析新聞原圖，作為重製依據 |
| 影像生成 | **Imagen 4**（`imagen-4.0-generate-001`） | 強制套用二次元/科技感風格、禁止文字亂碼、9:16 比例 |
| 基礎語音 | **edge-tts** | 文字轉語音（語速 +25%），同步輸出字級時間軸 `_subs.json` |
| 音色克隆 | **RVC（VITS 架構）** | 將基礎語音轉成「蔡小花」專屬音色，F0 音調偏移 +2 |

### 4.3 媒體處理與自動化
| 能力 | 技術 | 說明 |
|------|------|------|
| 爬蟲/解析 | `feedparser`、`BeautifulSoup4`、`requests`、`pypdf` | RSS / 網頁 / PDF 多來源匯入 |
| 影片剪輯 | **MoviePy 2.0+**、`Pillow`、`numpy` | 素材動態對齊、字幕動態繪製、關鍵字標色 |
| 瀏覽器自動化 | **Playwright** | 模擬真人發布，含 Session 持久化 |
| 圖形化介面 | **NiceGUI** | 網頁式控制台，背景執行緒處理長任務、即時 Log 廣播 |

### 4.4 硬體加速（工程亮點）
| 模組 | 加速路徑 | 降級策略 |
|------|---------|---------|
| RVC 語音推理 | **DirectML**（AMD/Intel GPU） | → CPU 自動回退 |
| FFmpeg 影片編碼 | **AMD AMF**（h264_amf）／**Intel QuickSync**（h264_qsv） | → CPU `libx264` 無縫降級 |
| 網路穩定性 | edge-tts 以 **tenacity** 指數退避重試最多 5 次 | 提升批次成功率 |

### 4.5 發布平台
**YouTube Shorts ✅｜Facebook Reels ✅｜Instagram Reels ✅（含 9:16 切換）｜TikTok ✅（支援版權檢查跳過）**

---

## 5. 工程亮點

1. **以資料庫作為單一事實來源的狀態機設計**
   全流程靠 `DailyNews` 表的三個布林欄位（`is_selected → is_processed → is_published`）驅動，每個模組只認狀態、不彼此耦合，任何一步都能獨立重跑或中途接續。

2. **硬體相容性優先的降級架構**
   同一份程式碼能在「AMD 桌電」與「無顯卡筆電」間無縫切換——GPU 加速失敗即自動回退 CPU，確保專案在不同硬體環境下皆可無縫運作。

3. **Human-in-the-Loop 的兩個關鍵介入點**
   - 選題台（模組 1.5）：AI 不替我決定做哪則新聞。
   - 發布覆核（模組 8）：上傳過程支援鍵盤即時監聽 **[S] 跳過 / [W] 重置等待 / [R] 強制重試**，失敗時暫停交由人工決策而非崩潰退出。

4. **繞過平台 API 門檻的 Playwright 自動化**
   針對 YouTube/Facebook 實作精確的「成功 Dialog 與網址跳轉偵測」，能應對 12–15MB 影片與慢速網路；執行後保留瀏覽器供人工覆核。

5. **成本與資源治理意識**
   測試時刻意限制 `is_selected` 為單筆以控管 Gemini API 額度；歸檔時自動刪除無字幕原始影片節省空間；偵錯臨時檔統一導向 `debug_logs/` 保持環境整潔。

6. **可維護性**
   `config.py` 中央化路徑與參數、`.env` 隔離金鑰、`.gitignore` 排除大型模型與產出物——程式碼透過 GitHub 同步，大型 RVC 框架與模型（約 4GB）則採手動搬運以避免超出版本控制限制。

---

## 6. 專案目錄結構

```
AIprojects/
├── config.py                  # 全域路徑/參數中央化
├── .env                       # API 金鑰（git 忽略）
├── auto_channel.db            # SQLite 狀態機（git 忽略）
│
├── step1_scraper.py           # 模組1：RSS 爬蟲
├── step1_manual_add.py        # 模組1：手動加題
├── step1_local_loader.py      # 模組1：本地稿件匯入
├── step1_5_selector.py        # 模組1.5：選題台
├── step2_script_generator.py  # 模組2：AI 腳本
├── step3_voice_renderer.py    # 模組3：語音 + RVC
├── step5_visual_generator.py  # 模組5：AI 配圖
├── step6_video_assembly.py    # 模組6：剪輯 + 字幕
├── step8_auto_uploader.py     # 模組8：發布主控
├── step9_manual_archive.py    # 模組9：歸檔
│
├── app.py                     # GUI 主入口 (python app.py)
├── gui/                       # NiceGUI 圖形化控制台
│   ├── state.py / runner.py / layout.py / data.py
│   └── pages/                 # 儀表板 + 8 個模組頁面
│
├── uploaders/                 # 各平台發布策略
│   ├── base.py
│   ├── youtube.py / facebook.py / instagram.py / tiktok.py / xiaohongshu.py
│
├── source/                    # 本地稿件來源（imported/ 歸檔）
├── output_scripts/            # 腳本中繼檔（TXT + JSON）
├── output_voices/             # final.wav + subs.json
├── output_images/             # 9:16 配圖
├── output_videos/             # *_subtitled.mp4 成品
├── completed_archives/        # 已發布整組歸檔
├── assets/                    # 素材模式用 mp4/圖/mp3
├── debug_logs/                # 偵錯臨時檔
├── playwright_session/        # 瀏覽器登入態（git 忽略）
│
├── RVC1006AMD_Intel1/         # RVC 聲音引擎框架（~4GB，手動搬運）
├── SKILL.md                   # 開發架構指南
└── requirements.txt
```

---

## 7. 環境建置與執行

```powershell
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 設定金鑰（.env）
#    GEMINI_API_KEY=your_key_here

# 3. 確保 RVC 框架就位（RVC1006AMD_Intel1/ + 個人 .pth/.index 模型）

# 4. 依模組順序執行（每個模組可獨立啟動、自動接續下一步）
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

也可改用圖形化控制台一次管理整條管線：

```powershell
python app.py   # 啟動 NiceGUI 控制台，預設開啟 http://localhost:8080
```

---

## 8. 影片規格與內容設定

- **格式**：直式短影音（Shorts / Reels），9:16 比例，總長 **30–50 秒**。
- **雙腳本模式**：標準 30 秒（100–120 字 / 2 張圖）、專業 60 秒（200–250 字 / 4 張圖）。
- **動態頭尾**：由 Prompt 要求 AI 生成「3 秒抓眼球」開場與「引導留言訂閱」收尾。
- **字幕**：依腳本 `keywords` 陣列動態標色（電競黃 / 警示紅）。
- **四種影片合成模式**：原模式（模組生成圖）、素材模式（assets 同 ID 素材）、去主播素材模式、客製化模式（交互選擇來源/頭像/BGM）。

---

## 9. 現況與後續規劃（Roadmap）

| 項目 | 狀態 |
|------|------|
| 模組 1, 1.5, 2, 3, 5, 6, 8, 9 | ✅ 已完成並串接 |
| 圖形化控制台（NiceGUI） | ✅ 已完成，含儀表板與 8 個模組頁面 |
| 模組 4 虛擬角色動態驅動（Wav2Lip / SadTalker 嘴型同步） | 🚧 規劃中，目前用靜態去背頭像 |
| edge-tts 斷句停頓感 | 待 RVC 模型成熟後根本性修正 |
| 小紅書（xiaohongshu）發布 | 模組已備，持續調校 |

---

## 10. 我在這個專案中負責的工作（個人貢獻）

這是一個 **從 0 到 1 獨立完成** 的個人專案，我負責：

- **系統架構設計**：定義 9 模組邊界與以資料庫狀態機為核心的解耦架構。
- **全部程式實作**：爬蟲、AI 串接、語音管線、影片剪輯、瀏覽器自動化發布、歸檔。
- **AI 工程**：Prompt 設計（動態頭尾、字數控制、生圖防亂碼）、多模型切換策略、Gemini Vision + Imagen 串接。
- **效能工程**：DirectML / AMF / QSV 硬體加速與 CPU 降級、tenacity 重試機制。
- **工程治理**：設定中央化、金鑰隔離、`.gitignore` 排除大型檔案、Git 版本管理。

---

