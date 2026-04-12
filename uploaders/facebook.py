import time
from .base import PlaywrightUploaderBase

class FacebookUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        """
        實作 Facebook Reels 自動上傳。
        基於 DOM 診斷：/reels/create 頁面已直接提供 file input，
        不需要點擊「建立」選單，直接塞入影片即可。
        """
        try:
            print("    [FB Reels] 正在前往 Facebook Reels 上傳頁...")
            self.page.goto("https://business.facebook.com/reels/create")

            # 等待 file input 出現（診斷確認 accept="video/*" 的 input 在頁面上）
            print("    [FB Reels] 1. 偵測到上傳輸入框，送入影片檔案...")
            file_input = self.page.locator("input[accept*='video']").first
            file_input.wait_for(state="attached", timeout=20000)
            file_input.set_input_files(video_path)

            # 等待上傳進度完成（影片上傳需要一段時間）
            print("    [FB Reels] 2. 等待影片上傳完成...")
            # 等待預覽或「下一步」按鈕出現，代表上傳已完成
            next_or_continue = (
                self.page.get_by_role("button", name="下一步")
                .or_(self.page.get_by_role("button", name="Next"))
                .or_(self.page.get_by_role("button", name="繼續"))
                .or_(self.page.get_by_role("button", name="Continue"))
            )
            next_or_continue.wait_for(timeout=120000)  # 最多等 2 分鐘
            next_or_continue.click()
            time.sleep(2)

            # 填寫說明文字（包含標題與 Hashtag）
            print("    [FB Reels] 3. 填寫 Reels 說明...")
            # FB Reels 的說明欄位通常是 contenteditable 的 div 或 textarea
            caption_box = (
                self.page.get_by_label("說明")
                .or_(self.page.get_by_label("Caption"))
                .or_(self.page.get_by_placeholder("說明"))
                .or_(self.page.get_by_role("textbox"))
            )
            caption_box.wait_for(timeout=10000)
            caption_box.click()
            caption_box.fill(f"{title}\n\n{tags}")
            time.sleep(1)

            # 發布
            print("    [FB Reels] 4. 🚀 執行發布！")
            publish_btn = (
                self.page.get_by_role("button", name="發布")
                .or_(self.page.get_by_role("button", name="Publish"))
                .or_(self.page.get_by_role("button", name="分享"))
                .or_(self.page.get_by_role("button", name="Share"))
            )
            publish_btn.wait_for(timeout=10000)
            publish_btn.click()

            # 等待發布成功提示
            time.sleep(8)
            print("    ✅ [FB Reels] 自動上傳流程已跑完！")
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
