import os

from nicegui import ui

import step9_manual_archive
from gui.layout import page_shell
from gui.state import state


@ui.page('/archive')
def archive_page():
    content = page_shell('/archive')
    with content:
        ui.label('完工歸檔中心').classes('text-2xl font-bold')
        ui.label('確認已在各平台發布成功後，將影片與素材整組搬移至 completed_archives/。').classes('text-slate-400 text-sm')

        video_container = ui.column().classes('w-full gap-1')
        checked = {}

        def refresh():
            video_container.clear()
            checked.clear()
            items = step9_manual_archive.get_unarchived_videos()
            with video_container:
                if not items:
                    ui.label('目前沒有待歸檔的影片。').classes('text-slate-400')
                for item in items:
                    with ui.row().classes('items-center gap-2'):
                        cb = ui.checkbox()
                        checked[item['id']] = cb
                        ui.label(f"#{item['id']} {item['title']}").classes('text-sm')

        def do_archive():
            ids = [nid for nid, cb in checked.items() if cb.value]
            if not ids:
                ui.notify('請至少勾選一筆項目', type='warning')
                return
            result = step9_manual_archive.run(ids, log=state.log)
            ui.notify(f"已歸檔 {len(result['archived'])} 筆，並清除 {result['deleted_old_news']} 筆舊新聞紀錄。", type='positive')
            refresh()

        with ui.row().classes('items-center gap-2'):
            ui.button('📦 確認歸檔', on_click=do_archive, color='primary')
            ui.button(icon='refresh', on_click=refresh).props('flat round')

        refresh()

        ui.separator()

        ui.label('⚠️ 危險操作').classes('text-lg font-bold text-red-400 mt-4')
        ui.label('清空所有輸出資料夾 (output_scripts/voices/images/videos, assets/) 且無法復原，僅在需要重頭開始時使用。').classes('text-slate-400 text-sm')

        def confirm_clear():
            with ui.dialog() as dialog, ui.card():
                ui.label('確定要清空所有輸出資料夾嗎？').classes('font-bold')
                ui.label('此操作將刪除 output_scripts/、output_voices/、output_images/、output_videos/、assets/ 內的所有檔案，且無法復原！').classes('text-sm text-red-400')
                with ui.row().classes('justify-end gap-2 mt-4'):
                    ui.button('取消', on_click=dialog.close).props('flat')

                    def do_clear():
                        step9_manual_archive.clear_all_outputs(log=state.log)
                        ui.notify('已清空所有輸出資料夾。', type='warning')
                        dialog.close()

                    ui.button('確定清空', on_click=do_clear, color='red')
            dialog.open()

        ui.button('🗑️ 清空所有輸出資料夾', on_click=confirm_clear, color='red').props('outline')
