import time
from .base import PlaywrightUploaderBase

class TikTokUploader(PlaywrightUploaderBase):
    def upload(self, video_path: str, title: str, tags: str):
        try:
            print("    [TikTok] 正在前往 TikTok 創作者中心...")
            self.page.goto("https://www.tiktok.com/creator-center/upload")
            time.sleep(3)
            
            print("    [TikTok] 影片已選擇，準備填寫資料：")
            print(f"      ➔ 標題: {title}")
            print(f"      ➔ 說明: {tags}")
            
            print("    ✅ [TikTok] (模擬測試) 上傳腳本已觸發！")
            time.sleep(2)
        except Exception as e:
            print(f"    ❌ [TikTok] 上傳失敗: {e}")
