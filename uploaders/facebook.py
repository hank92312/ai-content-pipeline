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

        while True:
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
                    pub.scroll_into_view_if_needed()
                    pub.click(delay=200)
                else:
                    pub.click(force=True)

                print("    [FB Reels] ⏳ 正在等待上傳與發布處理 (最長 5 分鐘)...")
                print("    [控制鍵] S: 跳過 | R: 重試 | W: 加時")
                
                sc = False
                sw = time.time()
                timeout = 300 # 5 分鐘
                
                while time.time() - sw < timeout:
                    # 偵測成功標誌
                    if "reels_composer" not in self.page.url:
                        print(f"    🎉 [FB Reels] 發布成功 (網址已跳轉)！")
                        sc = True
                        break
                    try:
                        if not pub.is_visible():
                            print("    🎉 [FB Reels] 發布程序已啟動！")
                            sc = True
                            break
                    except: pass
                    
                    # 偵測手動按鍵
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').upper()
                        if key == 'S': return True
                        if key == 'R': raise Exception("User requested retry")
                        if key == 'W': sw = time.time() # Reset

                    time.sleep(5)
                
                if sc:
                    time.sleep(10) # 額外留一點緩衝
                    return True
                else:
                    decision = self.prompt_user_decision("Facebook")
                    if decision == "skip": return True
                    if decision == "retry": continue
                    if decision == "wait": sw = time.time(); continue

            except Exception as e:
                print(f"    ❌ [FB Reels] 自動化失敗: {e}")
                decision = self.prompt_user_decision("Facebook")
                if decision == "skip": return False
                if decision == "retry": continue
                return False
