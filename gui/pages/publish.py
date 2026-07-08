import os

from nicegui import ui

import step8_auto_uploader
from uploaders.base import UploadControl
from gui.layout import page_shell
from gui.runner import run_in_background
from gui.confirm import confirm_api_action

PLATFORM_OPTIONS = {1: 'YouTube Shorts', 2: 'Facebook Reels', 3: 'Instagram Reels', 4: 'TikTok'}


@ui.page('/publish')
def publish_page():
    content = page_shell('/publish')
    with content:
        ui.label('多平台自動發布').classes('text-2xl font-bold')
        ui.label('使用 Playwright 瀏覽器自動化模擬人工發布，執行前請確認已完成登入授權。').classes('text-slate-400 text-sm')

        video_container = ui.column().classes('w-full gap-1')
        checked_videos = {}

        def refresh_videos():
            video_container.clear()
            checked_videos.clear()
            videos = step8_auto_uploader.get_unpublished_video_list()
            with video_container:
                if not videos:
                    ui.label('目前沒有待發布的影片。').classes('text-slate-400')
                for v in videos:
                    with ui.row().classes('items-center gap-2'):
                        cb = ui.checkbox()
                        checked_videos[v] = cb
                        ui.label(os.path.basename(v)).classes('text-sm')

        ui.label('選擇平台：').classes('font-medium mt-2')
        platform_checks = {}
        with ui.row().classes('gap-4'):
            for code, label in PLATFORM_OPTIONS.items():
                platform_checks[code] = ui.checkbox(label)

        ui.button(
            '🔑 首次登入授權模式', icon='key',
            on_click=lambda: run_in_background('登入授權', step8_auto_uploader.launch_login_mode)
        ).props('outline')

        ui.separator()

        control_holder = {'control': None}

        ui.label('⚠️ 人工即時介入 (僅發布進行中可用)：').classes('text-sm text-slate-400')
        with ui.row().classes('items-center gap-2') as control_row:
            skip_btn = ui.button('⏩ 跳過此平台', color='orange')
            retry_btn = ui.button('🔄 強制重試', color='blue')
            wait_btn = ui.button('⏱️ 重置等待', color='grey')
        control_row.visible = False

        def do_skip():
            if control_holder['control']:
                control_holder['control'].skip.set()

        def do_retry():
            if control_holder['control']:
                control_holder['control'].retry.set()

        def do_wait():
            if control_holder['control']:
                control_holder['control'].reset_wait.set()

        skip_btn.on_click(do_skip)
        retry_btn.on_click(do_retry)
        wait_btn.on_click(do_wait)

        result_container = ui.column().classes('w-full gap-2')

        def do_publish():
            selected = [v for v, cb in checked_videos.items() if cb.value]
            targets = [code for code, cb in platform_checks.items() if cb.value]
            if not selected or not targets:
                ui.notify('請至少選擇一部影片與一個平台', type='warning')
                return

            control = UploadControl()
            control_holder['control'] = control
            control_row.visible = True
            publish_btn.disable()
            result_container.clear()

            def on_done(result, error):
                publish_btn.enable()
                control_row.visible = False
                control_holder['control'] = None
                refresh_videos()
                if result:
                    with result_container:
                        for item in result['processed']:
                            with ui.card().classes('w-full'):
                                ui.label(os.path.basename(item['video'])).classes('font-medium')
                                ui.label(item['title']).classes('text-sm text-slate-400')
                                with ui.row().classes('gap-2'):
                                    for platform, ok in item['results'].items():
                                        ui.badge(platform, color='green' if ok else 'red')

            ok = run_in_background(
                '多平台發布', step8_auto_uploader.run,
                selected, targets, control=control, on_done=on_done
            )
            if not ok:
                publish_btn.enable()
                control_row.visible = False

        def ask_publish():
            selected = [v for v, cb in checked_videos.items() if cb.value]
            targets = [code for code, cb in platform_checks.items() if cb.value]
            if not selected or not targets:
                ui.notify('請至少選擇一部影片與一個平台', type='warning')
                return
            confirm_api_action(
                '多平台自動發布',
                [
                    f'行銷文案生成：每部影片呼叫 1 次 Gemini ({len(selected)} 部影片 = {len(selected)} 次)',
                    f'並將實際發布至 {len(targets)} 個平台 (發布動作本身不可逆，請確認影片內容無誤)',
                ],
                do_publish,
            )

        with ui.row().classes('items-center gap-2'):
            publish_btn = ui.button('🚀 開始發布 💰', icon='rocket_launch', on_click=ask_publish, color='primary')
            ui.button(icon='refresh', on_click=refresh_videos).props('flat round')

        refresh_videos()
