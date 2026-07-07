"""
背景執行輔助工具：在獨立執行緒跑各 step 模組的 run()，
自動處理同步/非同步 (如 step3 的 async run())、全域執行鎖，以及例外訊息廣播。
"""
import asyncio
import inspect
import threading
import traceback

from .state import state


def run_in_background(module_name, target, *args, on_done=None, **kwargs):
    """
    在背景執行緒呼叫 target(*args, log=state.log, **kwargs)。
    module_name: 顯示於「執行中」狀態的模組名稱，同時作為全域執行鎖的持有者標籤。
    on_done(result, error): 執行緒收尾後呼叫 (注意：此 callback 仍在背景執行緒內，
                             若要更新 UI 元件，需搭配 ui.timer 輪詢共用狀態，而非直接操作 UI)。
    回傳: True 表示已成功排入背景執行；False 表示目前已有其他模組在執行中 (未啟動)。
    """
    if not state.try_start(module_name):
        state.log(f"⚠️ 目前已有模組「{state.running_module}」正在執行中，請稍候再試。")
        return False

    def _wrapper():
        result, error = None, None
        try:
            if inspect.iscoroutinefunction(target):
                result = asyncio.run(target(*args, log=state.log, **kwargs))
            else:
                result = target(*args, log=state.log, **kwargs)
        except Exception as e:
            error = e
            state.log(f"❌ [{module_name}] 執行時發生例外：{e}")
            state.log(traceback.format_exc())
        finally:
            state.finish()
            if on_done:
                on_done(result, error)

    t = threading.Thread(target=_wrapper, daemon=True)
    t.start()
    return True
