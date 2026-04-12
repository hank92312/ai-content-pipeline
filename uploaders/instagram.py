import time
from .base import PlaywrightUploaderBase

class InstagramUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        try:
            print("    [IG Reels] 正在前往 Instagram...")
            self.page.goto("https://www.instagram.com/")
            time.sleep(3)
            
            print("    [IG Reels] 影片已選擇，準備填寫資料：")
            print(f"      ➔ 標題: {title}")
            print(f"      ➔ 說明: {tags}")
            
            print("    ✅ [IG Reels] (模擬測試) 上傳腳本已觸發！")
            time.sleep(2)
        except Exception as e:
            print(f"    ❌ [IG Reels] 上傳失敗: {e}")
