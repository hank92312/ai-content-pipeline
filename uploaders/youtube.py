import time
import os
from .base import PlaywrightUploaderBase

class YouTubeUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        """
        實作 YouTube Studio 的真實自動點擊流程。
        基於 DOM 診斷使用正確的 id="upload-button" 選取器。
        """
        try:
            print("    [YouTube] 正在前往 YouTube Studio...")
            self.page.goto("https://studio.youtube.com/")
            # 1. 點擊右上方「建立」按鈕
            print("    [YouTube] 1. 點擊右上方「建立」按鈕...")
            # 支援中文「建立」與英文「Create」，優先使用唯一 ID #create-icon
            create_btn = self.page.locator("#create-icon, button:has-text('建立'), button:has-text('Create')").first
            create_btn.wait_for(state="visible", timeout=30000)
            create_btn.click()
            time.sleep(1)

            # 2. 點擊選單中的「上傳影片」
            print("    [YouTube] 2. 點擊「上傳影片」選項...")
            upload_option = self.page.locator("tp-yt-paper-item:has-text('上傳影片'), tp-yt-paper-item:has-text('Upload videos')").first
            upload_option.wait_for(state="visible", timeout=10000)
            upload_option.click()
            time.sleep(2)

            # 3. 填入影片檔案 (Playwright 攔截隱藏的 input)
            print("    [YouTube] 3. 正在送入影片檔案...")
            file_input = self.page.locator("input[type='file']").first
            file_input.wait_for(state="attached", timeout=10000)
            file_input.set_input_files(video_path)

            # 3. 等待詳細資料頁面載入並填寫
            print("    [YouTube] 3. 等待填寫頁面載入 (最長 90 秒)...")
            title_box = self.page.locator("#title-textarea #textbox")
            title_box.wait_for(timeout=90000)

            # 清空並填寫標題
            title_box.click()
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Backspace")
            title_box.fill(title)

            # 填寫說明
            desc_box = self.page.locator("#description-textarea #textbox")
            desc_box.fill(f"{title}\n\n{tags}")

            # 4. 設定「非兒童製造」
            print("    [YouTube] 4. 設定受眾 (非兒童打造)...")
            kids_radio = self.page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']")
            kids_radio.scroll_into_view_if_needed()
            kids_radio.click()

            # 5. 連續點擊「下一步」三次
            print("    [YouTube] 5. 正在穿過檢查步驟...")
            next_btn = self.page.locator("#next-button")
            for i in range(3):
                next_btn.wait_for(state="visible", timeout=15000)
                next_btn.click()
                print(f"      - 已通過第 {i+1} 步")
                time.sleep(2)

            # 6. 設定發布狀態為「公開」
            print("    [YouTube] 6. 設定可見度為【公開】...")
            public_radio = self.page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
            public_radio.wait_for(state="visible", timeout=10000)
            public_radio.click()

            # 7. 最終按鈕：發布
            print("    [YouTube] 7. 🚀 執行最終發布！")
            done_btn = self.page.locator("#done-button")
            done_btn.wait_for(state="visible", timeout=10000)
            done_btn.click()

            time.sleep(10)
            print("    ✅ [YouTube] 自動上傳流程已跑完！")
            return True

        except Exception as e:
            print(f"\n    ❌ [YouTube] 自動化發布失敗！原因: {e}")
            print("    ------------------------------------------------")
            print("    ⚠️  【手動介入提示】")
            print("    程式已為您暫停，瀏覽器視窗將保持開啟以便您檢視錯誤。")
            print("    您可以選擇手動補齊剩餘步驟，或直接關閉瀏覽器。")
            print("    完成檢視後，請在終端機按下【Enter】鍵以繼續處理下一個任務。")
            print("    ------------------------------------------------")
            input("    > 按下 [Enter] 繼續...")
            return False
