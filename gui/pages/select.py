from nicegui import ui

import step1_5_selector
from gui.layout import page_shell
from gui.state import state


@ui.page('/select')
def select_page():
    content = page_shell('/select')
    with content:
        ui.label('總編輯選題台').classes('text-2xl font-bold')

        include_processed = ui.switch('含已處理過的新聞 (重新挑選製作)')
        table_container = ui.column().classes('w-full gap-1')
        checked_ids = {}

        def refresh():
            table_container.clear()
            checked_ids.clear()
            news_list = step1_5_selector.get_pending_news(include_processed=include_processed.value)
            with table_container:
                if not news_list:
                    ui.label('目前沒有可挑選的新聞。').classes('text-slate-400')
                for news_id, category, title in news_list:
                    with ui.row().classes('items-center gap-2 w-full'):
                        cb = ui.checkbox()
                        checked_ids[news_id] = cb
                        ui.badge(category).classes('shrink-0')
                        ui.label(title).classes('text-sm')

        include_processed.on_value_change(refresh)

        def confirm_selection():
            selected = [nid for nid, cb in checked_ids.items() if cb.value]
            if not selected:
                ui.notify('請至少勾選一筆新聞', type='warning')
                return
            result = step1_5_selector.run(selected, log=state.log)
            ui.notify(f"已標記 {result['success']} 筆為已選定！", type='positive')
            refresh()

        with ui.row().classes('items-center gap-2'):
            ui.button('✅ 確認選定', on_click=confirm_selection, color='primary')
            ui.button(icon='refresh', on_click=refresh).props('flat round')

        refresh()
