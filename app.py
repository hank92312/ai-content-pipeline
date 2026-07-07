"""
AI 自動化短影音內容流水線 — 圖形化控制台
啟動方式：python app.py
"""
from nicegui import ui

import gui.pages.dashboard  # noqa: F401
import gui.pages.collect  # noqa: F401
import gui.pages.select  # noqa: F401
import gui.pages.script  # noqa: F401
import gui.pages.voice  # noqa: F401
import gui.pages.visual  # noqa: F401
import gui.pages.video  # noqa: F401
import gui.pages.publish  # noqa: F401
import gui.pages.archive  # noqa: F401

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="小花的AI情報站 — 控制台", port=8080, reload=False)
