"""
全域執行狀態管理：確保同一時間只有一個管線模組在執行 (避免 DB/檔案競爭)，
並提供 thread-safe 的 log 廣播機制，供背景執行緒與 UI 定時器之間傳遞訊息。
"""
import threading
import queue


class ExecutionState:
    def __init__(self):
        self._lock = threading.Lock()
        self._running_module = None
        self._log_queue = queue.Queue()

    @property
    def is_busy(self) -> bool:
        return self._running_module is not None

    @property
    def running_module(self):
        return self._running_module

    def try_start(self, module_name: str) -> bool:
        """嘗試佔用執行權，成功回傳 True；若已有其他模組執行中則回傳 False"""
        with self._lock:
            if self._running_module is not None:
                return False
            self._running_module = module_name
            return True

    def finish(self):
        with self._lock:
            self._running_module = None

    def log(self, message):
        """供各 step 模組的 log= 參數呼叫；同時印到終端機方便除錯"""
        text = str(message)
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


# 全域單例，供所有頁面共用
state = ExecutionState()
