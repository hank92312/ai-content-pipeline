# 🔄 專案備份與跨設備同步 SOP
*(AI Content Pipeline 標準作業程序書)*

本文件說明如何將本專案備份至 GitHub 並在不同設備（如高效能桌電與無顯卡筆電）之間進行同步與切換。

---

## 📅 準備工作 (只需做一次)

### 1. 建立 GitHub 私人倉庫
1. 登入 [GitHub](https://github.com/)。
2. 點擊 **New repository**。
3. **Repository name**: `ai-content-pipeline` (或自訂名稱)。
4. **Visibility**: 務必選取 **Private (私人)** 🔒。
5. 不要勾選初始化 README 或 .gitignore。
6. 點擊 **Create repository**。

---

## 📤 階段一：初次備份 (在目前的「桌電」操作)

1. 開啟終端機 (PowerShell)，確認路徑在 `D:\AIprojects\`。
2. 執行以下指令綁定並推送到 GitHub：
   ```powershell
   # 綁定您的私人倉庫 (請將網址替換為您的真實倉庫網址)
   git remote add origin https://github.com/您的帳號/ai-content-pipeline.git
   
   # 推送至雲端
   git push -u origin master
   ```

---

## 💻 階段二：切換至「筆電」操作 (第二台設備)

由於 `.gitignore` 設定，大型模型檔案與暫存影音不會推送到雲端，請依循以下步驟：

1. **從 GitHub 下載程式碼：**
   ```powershell
   git clone https://github.com/您的帳號/ai-content-pipeline.git
   ```

2. **手動搬運與框架準備 (重要)：**
   由於 GitHub 排除大型檔案，您必須確保筆電也有 RVC 執行環境。有兩種做法：
   - **做法 A (最推薦)**：使用隨身碟將桌電的 `RVC1006AMD_Intel1` 完整資料夾 (約 4GB) 直接複製到筆電。這能確保環境 100% 一致。
   - **做法 B (輕量遷移)**：如果您已經在筆電下載過一份乾淨的 `RVC1006AMD_Intel1` 框架，則只需搬運您個人的模型檔案 (`.pth` 與 `.index`) 放到對應資料夾即可。

---

## 🏗️ 核心檔案邏輯說明 (必讀)
為了避免混淆，請理解本專案的組成結構：
- **專案腳本 (GitHub 同步)**：包含 `step1` 到 `step7` 等所有 Python 程式碼。這部分體積很小，透過雲端同步即可。
- **RVC 執行框架 (需手動搬運 📦)**：即 `RVC1006AMD_Intel1` 資料夾。這是您的「聲音引擎」，包含上千個 Python 依賴檔以及底層預訓練模型。**沒有這個框架，語音模組絕對無法執行。**
- **您的聲音模型 (核心檔案 ✨)**：即 `AutoChannel_Voice.pth` 與 `.index`。這是您的「聲音靈魂」，只要放入框架中，引擎就能發出您的聲音。

3. **安裝環境：**
   ```powershell
   pip install -r requirements.txt
   ```

4. **正常執行：**
   直接啟動腳本即可。程式碼已具備「硬體偵測機制」，會自動偵測顯卡環境，若無 AMD 顯卡將自動降級為 CPU 運算。

---

## 🔄 階段三：日常雙向同步 (更新程式碼)

如果您在其中一台設備修改了腳本（例如調整了生圖提示詞或語速）：

### 【上傳變更】(在有修改的電腦執行)
```powershell
git add .
git commit -m "更新描述 (例如：調整語速至1.2倍)"
git push
```

### 【拉取更新】(在另一台電腦執行)
```powershell
git pull
```

---

## ⚠️ 注意事項
- **資料庫同步**：`auto_channel.db` 目前被排除在同步外，建議在兩台電腦各自獨立抓取新聞，或手動透過隨身碟搬運資料庫檔案。
- **安全性**：請絕對不要將倉庫設為 Public (公開)，以免您的 API Key 與個人模型外洩。
