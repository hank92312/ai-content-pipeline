import os

class PlaywrightUploaderBase:
    def __init__(self, page):
        """
        初始化發布器，傳入已經被建立好的 Playwright Page 實例。
        之所以由外部傳入 Playwright context，是為了讓 5 個平台可以共用同一個瀏覽器登入狀態。
        """
        self.page = page

    def upload(self, video_path: str, title: str, tags: str):
        """
        核心上傳邏輯。每個繼承此基礎類別的平台都需要實作這個 function。
        :param video_path: 影片檔案的絕對路徑
        :param title: AI 生成的影片標題
        :param tags: AI 生成的 Hashtag字串 (如 "#AI #科技")
        """
        raise NotImplementedError("請在子類別實作上傳邏輯")
