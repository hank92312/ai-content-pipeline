import os
import time
import msvcrt

class PlaywrightUploaderBase:
    def __init__(self, page):
        """
        初始化發布器，傳入已經被建立好的 Playwright Page 實例。
        """
        self.page = page

    def upload(self, video_path: str, title: str, tags: str):
        """核心上傳邏輯。每個繼承此基礎類別的平台都需要實作這個 function。"""
        raise NotImplementedError("請在子類別實作上傳邏輯")

    def prompt_user_decision(self, platform: str):
        """當自動化遇到卡頓或超時，由使用者按鍵決定下一步。"""
        print(f"\n    ⚠️  [{platform}] 需要手動確認！")
        print("    ------------------------------------------------")
        print("    👉 請在鍵盤按下：")
        print("       [S] Skip  - 跳過此平台，處理下一個")
        print("       [R] Retry - 重新啟動此平台的上傳")
        print("       [W] Wait  - 繼續等待 (重置 2 分鐘計時)")
        print("    ------------------------------------------------")
        
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch().decode('utf-8').upper()
                if ch == 'S': return "skip"
                if ch == 'R': return "retry"
                if ch == 'W': return "wait"
            time.sleep(0.1)
