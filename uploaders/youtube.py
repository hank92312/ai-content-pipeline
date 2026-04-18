import time
import os
from .base import PlaywrightUploaderBase

class YouTubeUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        """
        實作 YouTube Studio 的真實自動點擊流程。
        加入手動決策與重試機制。
        """
        while True:
            try:
                print("    [YouTube] 正在前往 YouTube Studio...")
                self.page.goto("https://studio.youtube.com/")
                
                # 1. 點擊「建立」與「上傳」
                create_btn = self.page.locator("#create-icon, button:has-text('建立'), button:has-text('Create')").first
                create_btn.wait_for(state="visible", timeout=30000)
                create_btn.click()
                time.sleep(1)

                upload_option = self.page.locator("tp-yt-paper-item:has-text('上傳影片'), tp-yt-paper-item:has-text('Upload videos')").first
                upload_option.wait_for(state="visible", timeout=10000)
                upload_option.click()
                time.sleep(2)

                # 2. 選擇檔案
                print("    [YouTube] 1. 正在送入影片檔案...")
                file_input = self.page.locator("input[type='file']").first
                file_input.wait_for(state="attached", timeout=10000)
                file_input.set_input_files(video_path)

                # 3. 填寫詳細資料
                print("    [YouTube] 2. 等待詳細資料頁面載入...")
                title_box = self.page.locator("#title-textarea #textbox")
                title_box.wait_for(timeout=90000)

                title_box.click()
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                title_box.fill(title)

                desc_box = self.page.locator("#description-textarea #textbox")
                desc_box.fill(f"{title}\n\n{tags}")

                # 4. 設定受眾
                kids_radio = self.page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']")
                kids_radio.scroll_into_view_if_needed()
                kids_radio.click()

                # 5. 通過檢查步驟
                print("    [YouTube] 3. 正在通過檢查步驟...")
                next_btn = self.page.locator("#next-button")
                for i in range(3):
                    next_btn.wait_for(state="visible", timeout=15000)
                    next_btn.click()
                    time.sleep(2)

                # 6. 公開影片
                print("    [YouTube] 4. 設定可見度為【公開】並點擊發布...")
                public_radio = self.page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
                public_radio.wait_for(state="visible", timeout=10000)
                public_radio.click()

                # 7. 執行最終發布
                done_btn = self.page.locator("#done-button")
                done_btn.wait_for(state="visible", timeout=10000)
                done_btn.click()

                # 8. 關鍵等待：等待成功視窗或進度完成
                print("    [YouTube] ⏳ 正在等待上傳完成 (最長 10 分鐘)...")
                print("    [控制鍵詞] S: 跳過 | R: 重試 | W: 重置計時")
                
                success_found = False
                start_time = time.time()
                timeout = 600 # 10 分鐘
                
                while time.time() - start_time < timeout:
                    # 檢查成功標誌：出現「影片已發布」或者是關閉按鈕
                    if self.page.get_by_text("影片已發布").is_visible() or \
                       self.page.get_by_text("Video published").is_visible() or \
                       self.page.locator("#close-button").first.is_visible():
                        print("    🎉 [YouTube] 上傳成功！偵測到發布完成畫面。")
                        success_found = True
                        break
                    
                    # 偵測手動按鍵
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').upper()
                        if key == 'S': 
                            print("    ⏩ 使用者選擇跳過。")
                            return True
                        if key == 'R': 
                            print("    🔄 使用者選擇重試影片上傳。")
                            raise Exception("User requested retry")
                        if key == 'W':
                            print("    ➕ 已重置等待計時器。")
                            start_time = time.time()
                    
                    time.sleep(2)
                
                if success_found:
                    return True
                else:
                    decision = self.prompt_user_decision("YouTube")
                    if decision == "skip": return True
                    if decision == "retry": continue
                    if decision == "wait": start_time = time.time(); continue

            except Exception as e:
                print(f"\n    ❌ [YouTube] 自動發生錯誤: {e}")
                decision = self.prompt_user_decision("YouTube")
                if decision == "skip": return False
                if decision == "retry": continue
                if decision == "wait": continue
                return False
