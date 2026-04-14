import time
import re
from .base import PlaywrightUploaderBase

class TikTokUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        try:
            print("    [TikTok] 1. 正在前往 TikTok 創作者中心...")
            # TikTok 的上傳頁面有時需要等稍微久一點才能正確載入 React 元件
            self.page.goto("https://www.tiktok.com/creator-center/upload", timeout=60000)
            time.sleep(5)
            
            print("    [TikTok] 2. 尋找並上傳影片檔案...")
            # TikTok 的上傳按鈕通常直接是一組隱藏或透明的 input[type="file"]
            try:
                # 方案 A: 尋找主畫面的 input
                file_input = self.page.locator("input[type='file'][accept*='video']").or_(
                    self.page.locator("input[type='file']")
                ).first
                file_input.wait_for(state="attached", timeout=15000)
                file_input.set_input_files(video_path)
            except Exception as e:
                # 方案 B: 在 iframe 內尋找 (根據不同帳號權重 TikTok 會使用 iframe)
                try:
                    iframe = self.page.frame_locator('iframe[data-tt="Upload_index_iframe"]')
                    file_input = iframe.locator("input[type='file']").first
                    file_input.wait_for(state="attached", timeout=10000)
                    file_input.set_input_files(video_path)
                    print("      ➔ 在 iframe 內成功找到上傳節點。")
                except:
                    print("    [警告] 在畫面上找不到上傳影片的輸入框。正在保存 DOM 分析...")
                    with open("tiktok_home_dom.html", "w", encoding="utf-8") as f:
                        f.write(self.page.content())
                    raise Exception("找不到 TikTok 影片的上傳節點。")

            print("    [TikTok] 3. 等待上傳處理並尋找說明文字輸入框...")
            # 影片上傳後，畫面上會出現編輯器，這可能需要幾秒鐘
            time.sleep(5)
            
            # 使用 Draft.js 或是 contenteditable 的地方
            editor = self.page.locator(".public-DraftEditor-content").or_(
                self.page.locator("div[contenteditable='true']")
            ).or_(
                self.page.locator("div[role='textbox']")
            ).first
            
            try:
                editor.wait_for(state="visible", timeout=30000)
                editor.click(force=True)
                time.sleep(1)
                
                # TikTok 預設會把上傳檔案名稱當作發布影片標題 (!通常會需要砍掉!)
                # 全選後刪除
                self.page.keyboard.press("Control+A")
                time.sleep(0.5)
                self.page.keyboard.press("Backspace")
                time.sleep(0.5)
                
                # 模擬人類鍵盤打字，因為直接填 value TikTok的 React 狀態可能吃不到
                text_to_type = f"{title}\n\n{tags}"
                print("    [TikTok] 4. 開始輸入標題與標籤...")
                self.page.keyboard.type(text_to_type, delay=30)
                time.sleep(2)
            except Exception as e:
                print("    [警告] 找不到文字輸入框或無法寫入。正在保存 DOM 分析...")
                with open("tiktok_upload_dom.html", "w", encoding="utf-8") as f:
                    f.write(self.page.content())
                raise e

            print("    [TikTok] 5. 🚀 確認發布按鈕狀態，執行發布...")
            # TikTok 的發布按鈕
            post_btn = self.page.locator("button, div[role='button']").filter(has_text=re.compile(r"^(發布|發佈|Post)$")).last
            
            print("      ➔ 等待 TikTok 伺服器進行影片處理與狀態檢查...")
            sw = time.time()
            ready_to_post = False
            while time.time() - sw < 360:
                try:
                    # 使用更單純的屬性檢測，TikTok 鎖定發佈時通常會設定 disabled
                    if post_btn.is_enabled():
                        ready_to_post = True
                        break
                except:
                    pass
                time.sleep(5)
            
            if not ready_to_post:
                print("    [警告] 影片處理超時 (已達6分鐘)。嘗試強制點擊。")
                try: self.page.screenshot(path="debug_tiktok_button_timeout.png")
                except: pass
                
            post_btn.click(force=True)
            print("    ✅ 已點擊發佈按鈕！")
            
            # --- 處理「版權檢查仍在進行中，是否繼續發布」的彈窗 ---
            try:
                # 尋找「立即發佈」或「Post now」按鈕
                post_now_btn = self.page.get_by_role("button", name=re.compile(r"^(立即發佈|立即發布|Post now)$"))
                if post_now_btn.is_visible(timeout=5000):
                    print("      ➔ 偵測到「版權檢查進行中」提示彈窗，直接點擊「立即發佈」！")
                    post_now_btn.first.click()
                    time.sleep(2)
            except Exception as e:
                pass
            
            print("      ➔ 等待發布成功通知...")
            
            # 檢查是否成功 (跳出成功提示 Modal 或是網頁跳轉)
            sc = False
            sw = time.time()
            while time.time() - sw < 60:
                success_msg = self.page.locator("text=影片已上傳").or_(
                    self.page.locator("text=上傳成功")
                ).or_(
                    self.page.locator("text=Manage your posts")
                ).or_(
                    self.page.locator("text=管理貼文")
                )
                if success_msg.is_visible(timeout=3000):
                    print("    🎉 發布成功！(出現成功提示訊息)")
                    sc = True
                    break
                
                # 或是網址跳轉回首頁/管理頁面
                if "upload" not in self.page.url:
                    print(f"    🎉 發布成功！(網址已變更: {self.page.url})")
                    sc = True
                    break
                time.sleep(5)
                
            if not sc:
                print("    ⚠️ 等待分享通知超時。請手動檢查。")
                try: self.page.screenshot(path="debug_tiktok_timeout.png")
                except: pass
                return False

            time.sleep(3)
            return True

        except Exception as e:
            print(f"    ❌ [TikTok] 上傳失敗: {e}")
            try: self.page.screenshot(path="debug_tiktok_failed.png")
            except: pass
            input("Press Enter...")
            return False
