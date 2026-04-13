import time
from .base import PlaywrightUploaderBase

class FacebookUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        """
        實作 Facebook Reels 自動上傳。
        基於 DOM 診斷：/reels/create 頁面已直接提供 file input，
        不需要點擊「建立」選單，直接塞入影片即可。
        """
    def upload(self, video_path: str, title: str, tags: str):
        """
        實作 Facebook Reels 自動上傳。
        使用 Meta Business Suite (latest/reels_composer) 介面。
        層級：上傳影片 -> 繼續 -> 繼續 -> 填寫說明 -> 分享
        """
        try:
            print("    [FB Reels] 正在前往 Facebook Reels 建立頁 (Meta Business Suite)...")
            self.page.goto("https://business.facebook.com/latest/reels_composer")
            
            # 1. 偵測上傳輸入框
            print("    [FB Reels] 1. 送入影片檔案...")
            file_input = self.page.locator("input[type='file'][accept*='video']").first
            file_input.wait_for(state="attached", timeout=30000)
            file_input.set_input_files(video_path)

            # 2. 等待上傳進度並點擊「繼續」 (第一步：建立)
            print("    [FB Reels] 2. 等待影片處理完成並點擊【繼續】...")
            # Facebook 介面通常需要點擊兩次「繼續」才能到達發布頁
            next_btn = self.page.get_by_role("button", name="繼續").or_(self.page.get_by_role("button", name="下一步"))
            
            # 等待按鈕進入可點擊狀態 (代表影片上傳基本完成)
            next_btn.wait_for(state="visible", timeout=120000)
            next_btn.click()
            time.sleep(2)

            # 3. 第二步：編輯 (目前略過編輯，直接按繼續)
            print("    [FB Reels] 3. 略過編輯步驟，再次點擊【繼續】...")
            next_btn.wait_for(state="visible", timeout=30000)
            next_btn.click()
            time.sleep(2)

            # 4. 第三步：發布 (填寫說明文字)
            print("    [FB Reels] 4. 填寫 Reels 說明與 Hashtags...")
            # 使用診斷出的 aria-label (繁體中文環境通常為「寫點關於此短片內容...」)
            caption_box = self.page.locator("div[role='textbox'][aria-label*='內容']").or_(self.page.get_by_label("說明"))
            caption_box.wait_for(timeout=20000)
            caption_box.click()
            
            # 對於 contenteditable div，使用 type 模擬真實輸入較安全
            caption_box.fill("") # 先清空
            caption_box.type(f"{title}\n\n{tags}", delay=50)
            time.sleep(1)

            # 5. 最後發布
            print("    [FB Reels] 5. 🚀 執行最後發布！")
            publish_btn = self.page.get_by_role("button", name="分享").or_(self.page.get_by_role("button", name="發布"))
            publish_btn.wait_for(timeout=10000)
            
            # --- 手動暫停檢查點 (可視需求取消註解) ---
            # input("    ⏸️ 操作暫停：請在瀏覽器確認內容後，按 Enter 執行正式發布...")
            
            publish_btn.click()

            # 等待發布成功提示
            print("    ✅ [FB Reels] 自動上傳流程執行完畢！")
            time.sleep(10)
            return True

        except Exception as e:
            print(f"\n    ❌ [FB Reels] 自動化發布失敗！原因: {e}")
            print("    ------------------------------------------------")
            print("    ⚠️  【手動介入提示】")
            print("    程式已為您暫停，瀏覽器視窗將保持開啟以便您檢視錯誤。")
            print("    您可以選擇手動補齊剩餘步驟，或直接關閉瀏覽器。")
            print("    完成檢視後，請在終端機按下【Enter】鍵以繼續處理下一個任務。")
            print("    ------------------------------------------------")
            input("    > 按下 [Enter] 繼續...")
            return False
