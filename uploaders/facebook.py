import time
from .base import PlaywrightUploaderBase

class FacebookUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        def wait_until_enabled(locator, timeout_sec=120):
            start_time = time.time()
            while time.time() - start_time < timeout_sec:
                try:
                    if locator.first.is_enabled():
                        cls = locator.first.get_attribute("class") or ""
                        if "disabled" not in cls.lower(): return True
                except: pass
                time.sleep(2)
            return False

        try:
            print("    [FB Reels] 前往建立頁...")
            self.page.goto("https://business.facebook.com/latest/reels_composer")
            
            print("    [FB Reels] 1. 填寫標題與 Hashtags...")
            cap = self.page.locator("div[role='textbox'][aria-label*='加上文字']").or_(
                self.page.locator("div[role='textbox'][aria-label*='內容']")
            )
            cap.wait_for(state="visible", timeout=30000)
            cap.click()
            cap.fill(f"{title}\n\n{tags}")
            time.sleep(1)

            print("    [FB Reels] 2. 上傳影片...")
            try:
                with self.page.expect_file_chooser(timeout=20000) as fc:
                    btn = self.page.locator("div[role='button']").filter(has_text="新增影片").first
                    btn.wait_for(state="visible", timeout=10000)
                    btn.click()
                fc.value.set_files(video_path)
            except:
                self.page.locator("input[type='file']").first.set_input_files(video_path)

            nxt = self.page.locator("div[role='button']").filter(has_text="繼續")
            
            print("    [FB Reels] 3. 第一步完成，點擊繼續...")
            nxt.first.wait_for(state="visible", timeout=180000)
            wait_until_enabled(nxt, 120)
            nxt.first.click()
            time.sleep(3)

            print("    [FB Reels] 4. 第二步完成，點擊繼續...")
            nxt.first.wait_for(state="visible", timeout=30000)
            nxt.first.click()
            time.sleep(5)

            print("    [FB Reels] 5. 🚀 執行最後發布...")
            
            import re
            pub = self.page.get_by_role("button", name=re.compile(r"^(分享|發佈)$")).last
            pub.wait_for(state="visible", timeout=15000)
            
            if wait_until_enabled(pub, 45):
                print("    [FB Reels] 按鈕已就緒，執行點擊...")
                pub.scroll_into_view_if_needed()
                pub.hover()
                pub.click(delay=200)
            else:
                print("    [FB Reels] 警告：按鈕未顯示為可用，嘗試強制點擊...")
                pub.click(force=True)

            print("    ✅ 已點擊發布！Meta 後台處理可能需要 1~2 分鐘，請耐心等待...")
            
            sw = time.time()
            sc = False
            # 延長等待時間至 120 秒，因為影片發布需要時間處理
            while time.time() - sw < 120:
                # 判斷成功：網址跳轉，或是分享按鈕消失 (代表進入處理中疊層)
                if "reels_composer" not in self.page.url:
                    print(f"    🎉 發布成功 (網址已變更): {self.page.url}")
                    sc = True
                    break
                try:
                    if not pub.is_visible():
                        print("    🎉 發布程序已啟動 (進入處理畫面)！")
                        sc = True
                        break
                except:
                    pass
                time.sleep(5)
            
            if not sc:
                print("    ⚠️ 經過 2 分鐘網址仍未跳轉，請手動確認是否發布成功。")
                try: self.page.screenshot(path="debug_fb_timeout.png")
                except: pass
                # 視為失敗交給後續人工判斷
                return False
                
            # 發布成功後多留 15 秒讓網頁背景任務完成，避免提早關閉瀏覽器導致中斷
            time.sleep(15)
            return True

        except Exception as e:
            print(f"    ❌ 失敗: {e}")
            input("Press Enter...")
            return False
