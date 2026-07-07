import os
import time
import threading


class UploadControl:
    """
    人工即時介入的控制旗標 (thread-safe)。
    CLI 由背景執行緒監聽鍵盤 S/R/W 設定對應旗標；GUI 由按鈕直接設定。
    skip: 跳過目前平台   retry: 強制重試目前平台   reset_wait: 重置等待計時
    """
    def __init__(self):
        self.skip = threading.Event()
        self.retry = threading.Event()
        self.reset_wait = threading.Event()


class PlaywrightUploaderBase:
    def __init__(self, page, control=None):
        """
        初始化發布器，傳入已經被建立好的 Playwright Page 實例。
        control: UploadControl 執行個體，未提供則自動建立一個獨立實例 (不會被任何鍵盤/GUI 觸發)。
        """
        self.page = page
        self.control = control if control is not None else UploadControl()

    def upload(self, video_path: str, title: str, tags: str):
        """核心上傳邏輯。每個繼承此基礎類別的平台都需要實作這個 function。"""
        raise NotImplementedError("請在子類別實作上傳邏輯")

    def check_control_key(self):
        """非阻塞檢查是否有人工即時介入指令，回傳 'skip'/'retry'/'wait'/None，並清除已觸發的旗標"""
        if self.control.skip.is_set():
            self.control.skip.clear()
            return "skip"
        if self.control.retry.is_set():
            self.control.retry.clear()
            return "retry"
        if self.control.reset_wait.is_set():
            self.control.reset_wait.clear()
            return "wait"
        return None

    def prompt_user_decision(self, platform: str):
        """當自動化遇到卡頓或超時，由人工按鍵 (CLI) 或按鈕 (GUI) 決定下一步。"""
        print(f"\n    ⚠️  [{platform}] 需要手動確認！")
        print("    ------------------------------------------------")
        print("    👉 請按下對應按鍵/按鈕：")
        print("       [S] Skip  - 跳過此平台，處理下一個")
        print("       [R] Retry - 重新啟動此平台的上傳")
        print("       [W] Wait  - 繼續等待 (重置 2 分鐘計時)")
        print("    ------------------------------------------------")

        while True:
            decision = self.check_control_key()
            if decision:
                return decision
            time.sleep(0.1)
