import time
import re
from .base import PlaywrightUploaderBase

class InstagramUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        try:
            print("    [IG Reels] 1. 正在前往 Instagram...")
            self.page.goto("https://www.instagram.com/", timeout=60000)
            time.sleep(5)
            
            # 有時候 IG 會跳出「開啟通知」或是「儲存登入資料」的彈窗，按鈕通常是「稍後再說」
            try:
                notnow = self.page.get_by_role("button", name=re.compile(r"^(稍後再說|Not Now)$"))
                if notnow.count() > 0:
                    notnow.first.click()
                    time.sleep(2)
            except:
                pass

            print("    [IG Reels] 2. 點擊「建立」按鈕...")
            # IG 電腦版的側邊欄「建立」按鈕通常是這個 SVG 圖示
            create_btn = self.page.locator("svg[aria-label='新貼文']").or_(
                self.page.locator("svg[aria-label='New post']")
            ).or_(
                self.page.locator("svg[aria-label='建立']")
            )
            
            try:
                # 點擊 SVG 本身或其父元素
                create_btn.first.wait_for(state="visible", timeout=15000)
                create_btn.first.click(force=True)
                time.sleep(3)
            except Exception as e:
                print(f"    [警告] 找不到建立按鈕 SVG。準備儲存 DOM 以供分析...")
                with open("ig_home_dom.html", "w", encoding="utf-8") as f:
                    f.write(self.page.content())
                pass # 繼續往下，萬一畫面已經是上傳畫面
            
            # 若點擊「建立」後沒跳出大框框，而是左側滑出子選單 (貼文 / 直播影片)，我們必須點擊「貼文」
            try:
                # 嚴格匹配「貼文」或「Post」，避免點到左側導覽列的 Reels
                submenu_post = self.page.locator("span, div").filter(has_text=re.compile(r"^(貼文|Post)$"))
                if submenu_post.count() > 0 and submenu_post.first.is_visible(timeout=3000):
                    print("      ➔ 偵測到「建立」子選單，點擊貼文...")
                    submenu_post.first.click()
                    time.sleep(3)
            except Exception as e:
                pass

            print("    [IG Reels] 3. 上傳影片檔案...")

            # 尋找 input type file 直接上傳，或點擊「從電腦選擇」
            try:
                try:
                    with self.page.expect_file_chooser(timeout=8000) as fc:
                        self.page.get_by_role("button", name=re.compile(r"(從電腦選擇|Select from computer)")).click()
                    fc.value.set_files(video_path)
                except:
                    self.page.locator("input[type='file']").first.set_input_files(video_path, timeout=10000)
            except Exception as e:
                print(f"    [警告] 在畫面上找不到上傳影片的輸入框或按鈕。正在保存 DOM 分析...")
                with open("ig_upload_dom.html", "w", encoding="utf-8") as f:
                    f.write(self.page.content())
                raise e
            
            time.sleep(5)

            # 處理可能出現的「影片貼文現在都會以連續短片的形式分享」的彈窗
            try:
                ok_btn = self.page.get_by_role("button", name=re.compile(r"^(確定|OK)$"))
                if ok_btn.is_visible(timeout=3000):
                    print("      ➔ 偵測到 Reels 提示窗，點擊確定。")
                    ok_btn.first.click()
                    time.sleep(1)
            except:
                pass

            print("    [IG Reels] 4. 處理影片顯示比例 (選擇 9:16)...")
            # 點開左下角的顯示比例按鍵
            try:
                crop_btn = self.page.locator("svg[aria-label='選擇「裁切」']").or_(
                    self.page.locator("svg[aria-label='Select crop']")
                ).locator("..")
                
                if crop_btn.count() > 0:
                    crop_btn.first.click()
                    print("      ➔ 已展開裁切比例選單")
                    time.sleep(1)
                    
                    # 強制等待並點選 9:16 選項 (因為彈出選單可能有動畫)
                    try:
                        ratio_916 = self.page.get_by_text("9:16")
                        ratio_916.first.wait_for(state="visible", timeout=5000)
                        ratio_916.first.click(force=True)
                        print("      ➔ ✅ 成功設定為 9:16 比例！")
                        time.sleep(1)
                    except:
                        print("      ➔ ⚠️ 展開選單後找不到 9:16 或點擊超時。")
                else:
                    print("      ➔ ⚠️ 找不到裁切比例展開按鈕 (SVG: 選擇「裁切」)。")
            except Exception as e:
                print(f"      ➔ ⚠️ 設定裁切比例時發生例外狀況: {e}")

            next_btn = self.page.get_by_role("button", name=re.compile(r"^(繼續|下一步|Next)$"))
            next_btn.first.wait_for(state="visible", timeout=10000)
            next_btn.first.click()
            time.sleep(3)

            print("    [IG Reels] 5. 通過編輯封面畫面，點擊下一步...")
            next_btn.first.wait_for(state="visible", timeout=10000)
            next_btn.first.click()
            time.sleep(3)

            print("    [IG Reels] 6. 填寫標題與 Hashtags...")
            cap = self.page.locator("div[role='textbox'][aria-label*='說明文字']").or_(
                self.page.locator("div[role='textbox'][aria-label*='Write a caption']")
            ).or_(
                self.page.locator("div[role='textbox']")
            )
            cap.first.wait_for(state="visible", timeout=15000)
            cap.first.click()
            cap.first.fill(f"{title}\n\n{tags}")
            time.sleep(2)

            print("    [IG Reels] 7. 🚀 執行最後分享...")
            share_btn = self.page.get_by_role("button", name=re.compile(r"^(分享|Share)$")).last
            share_btn.wait_for(state="visible", timeout=10000)
            share_btn.click()

            print("    ✅ 已點擊分享！等待 IG 處理上傳進度，請耐心等待...")
            
            # 等待「你的貼文已分享」、「Your post has been shared.」字樣，或進度條消失
            sw = time.time()
            sc = False
            while time.time() - sw < 150: # IG 網頁版上傳可能需要較長的時間
                try:
                    success_msg = self.page.locator("span").filter(has_text=re.compile(r"^(已經分享你的貼文。|貼文已分享|Your post has been shared.)$"))
                    if success_msg.is_visible():
                        print("    🎉 發布成功！(偵測到成功提示)")
                        sc = True
                        break
                except:
                    pass
                
                # 如果彈窗自動關閉，代表可能也成功了
                try:
                    if not self.page.locator("div[role='dialog']").is_visible():
                        print("    🎉 發布程序彈窗已關閉。")
                        sc = True
                        break
                except:
                    pass
                time.sleep(5)
            
            if not sc:
                print("    ⚠️ 等待分享動畫超時。請手動檢查。")
                try: self.page.screenshot(path="debug_ig_timeout.png")
                except: pass
                return False

            time.sleep(3)
            return True

        except Exception as e:
            print(f"    ❌ [IG Reels] 上傳失敗: {e}")
            try: self.page.screenshot(path="debug_ig.png")
            except: pass
            input("Press Enter...")
            return False
