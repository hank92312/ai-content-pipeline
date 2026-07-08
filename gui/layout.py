"""共用頁面外殼：側邊導覽列 + 頂部執行狀態 + 底部即時 Log 面板。"""
from nicegui import ui

from .state import state

PAGES = [
    ("儀表板", "/", "dashboard"),
    ("資料蒐集", "/collect", "cloud_download"),
    ("選題台", "/select", "checklist"),
    ("腳本生成", "/script", "edit_note"),
    ("語音渲染", "/voice", "mic"),
    ("配圖生成", "/visual", "image"),
    ("影片合成", "/video", "movie"),
    ("多平台發布", "/publish", "publish"),
    ("歸檔", "/archive", "archive"),
]


def page_shell(active_path: str):
    """
    建立共用頁面外殼，回傳一個 ui.column 容器；呼叫端在 `with page_shell(...):` 區塊內放頁面內容。
    """
    ui.dark_mode().enable()
    ui.colors(primary='#7c3aed')

    with ui.header().classes('items-center justify-between bg-slate-900'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('smart_toy').classes('text-2xl')
            ui.label('小花的AI情報站 — 內容自動化控制台').classes('text-lg font-bold')

        with ui.column().classes('items-end gap-0'):
            status_badge = ui.badge('閒置', color='grey').classes('text-sm')
            progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-48 mt-1')
            progress_bar.visible = False
            progress_label = ui.label('').classes('text-xs text-slate-400')

        def _fmt(seconds):
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            return f'{m}:{s:02d}'

        def _update_status():
            if state.is_busy:
                status_badge.text = f'🟡 執行中：{state.running_module}'
                status_badge.props('color=orange')
                current, total, elapsed, remaining = state.progress
                progress_bar.visible = True
                if total > 0:
                    progress_bar.props(remove='indeterminate')
                    progress_bar.value = current / total
                    remain_txt = f'・剩餘約 {_fmt(remaining)}' if remaining is not None else ''
                    progress_label.text = f'{current}/{total}・已耗時 {_fmt(elapsed)}{remain_txt}'
                else:
                    progress_bar.props('indeterminate')
                    progress_bar.value = 0
                    progress_label.text = f'已耗時 {_fmt(elapsed)}（處理中，總筆數未知）'
            else:
                status_badge.text = '🟢 閒置'
                status_badge.props('color=grey')
                progress_bar.visible = False
                progress_label.text = ''
        ui.timer(1.0, _update_status)

    with ui.left_drawer(fixed=True).classes('bg-slate-900') as drawer:
        for label, path, icon in PAGES:
            is_active = (path == active_path)
            with ui.link(target=path).classes('no-underline w-full'):
                with ui.row().classes(
                    'items-center gap-2 p-3 rounded-lg w-full ' +
                    ('bg-primary text-white' if is_active else 'text-slate-200 hover:bg-slate-700')
                ):
                    ui.icon(icon)
                    ui.label(label)

    content = ui.column().classes('w-full max-w-5xl mx-auto p-4 gap-4')

    with ui.footer().classes('bg-slate-950 p-0'):
        with ui.expansion('📜 即時 Log', icon='terminal').classes('w-full text-white bg-slate-950'):
            log_view = ui.log(max_lines=500).classes('w-full h-48 bg-black text-green-400 font-mono text-xs')

            def _poll_logs():
                for line in state.drain_logs():
                    log_view.push(line)
            ui.timer(0.5, _poll_logs)

    return content
