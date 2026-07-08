"""付費 API 操作的共用確認機制：任何會產生 API 費用的按鈕，執行前必須先經過此對話框確認。"""
from nicegui import ui


def confirm_api_action(action_name, detail_lines, on_confirm):
    """
    彈出付費 API 確認對話框。
    action_name: 操作名稱 (如「AI 腳本生成」)
    detail_lines: list[str]，逐行說明本次將呼叫的 API 與規模
    on_confirm: 使用者按下「確認執行」後才會呼叫的函式
    """
    with ui.dialog() as dialog, ui.card().classes('max-w-md'):
        ui.label('💰 此操作將呼叫付費 API').classes('text-lg font-bold text-amber-400')
        ui.label(f'操作：{action_name}').classes('font-medium')
        for line in detail_lines:
            ui.label(f'• {line}').classes('text-sm text-slate-300')
        ui.label('確認執行後才會實際呼叫 API，取消則不產生任何費用。').classes('text-xs text-slate-500 mt-2')
        with ui.row().classes('justify-end gap-2 mt-4 w-full'):
            ui.button('取消', on_click=dialog.close).props('flat')

            def _go():
                dialog.close()
                on_confirm()

            ui.button('確認執行', on_click=_go, color='amber')
    dialog.open()
