"""
全域執行狀態管理：確保同一時間只有一個管線模組在執行 (避免 DB/檔案競爭)，
並提供 thread-safe 的 log 廣播機制，供背景執行緒與 UI 定時器之間傳遞訊息。
同時追蹤執行進度 (已耗時、已知總數時的 目前/總數)，供畫面顯示進度條使用。
"""
import threading
import queue
import time


class ExecutionState:
    def __init__(self):
        self._lock = threading.Lock()
        self._running_module = None
        self._log_queue = queue.Queue()
        self._total_items = 0
        self._current_item = 0
        self._item_marker = None
        self._start_time = None

    @property
    def is_busy(self) -> bool:
        return self._running_module is not None

    @property
    def running_module(self):
        return self._running_module

    def try_start(self, module_name: str, total_items: int = 0, item_marker: str = None) -> bool:
        """
        嘗試佔用執行權，成功回傳 True；若已有其他模組執行中則回傳 False。
        total_items: 若可預先得知本次要處理的總筆數 (例如已選定的新聞數)，
                     傳入後畫面會顯示「目前/總數」的確定進度條與預估剩餘時間。
                     未知 (預設 0) 時畫面顯示跑動的不確定進度條，至少能確認仍在執行。
        item_marker: 每處理完一筆時，該模組 log() 訊息開頭固定會出現的字串 (例如 "🎬 正在處理：")，
                     用來自動累計 current_item 進度；不需要精準比對，僅供顯示參考。
        """
        with self._lock:
            if self._running_module is not None:
                return False
            self._running_module = module_name
            self._total_items = total_items
            self._current_item = 0
            self._item_marker = item_marker
            self._start_time = time.time()
            return True

    def finish(self):
        with self._lock:
            self._running_module = None
            self._total_items = 0
            self._current_item = 0
            self._item_marker = None
            self._start_time = None

    def log(self, message):
        """供各 step 模組的 log= 參數呼叫；同時印到終端機方便除錯，並依 item_marker 累計進度"""
        text = str(message)
        if self._item_marker and text.lstrip().startswith(self._item_marker):
            self._current_item += 1
        self._log_queue.put(text)
        print(text)

    def drain_logs(self):
        """非阻塞取出目前佇列中所有訊息，供 UI 定時器輪詢拉取"""
        lines = []
        while True:
            try:
                lines.append(self._log_queue.get_nowait())
            except queue.Empty:
                break
        return lines

    @property
    def progress(self):
        """回傳 (目前筆數, 總筆數, 已耗時秒數, 預估剩餘秒數或 None)"""
        if not self._start_time:
            return 0, 0, 0, None
        elapsed = time.time() - self._start_time
        current, total = self._current_item, self._total_items
        remaining = None
        if total > 0 and current > 0:
            remaining = (elapsed / current) * max(total - current, 0)
        return current, total, elapsed, remaining


# 全域單例，供所有頁面共用
state = ExecutionState()
