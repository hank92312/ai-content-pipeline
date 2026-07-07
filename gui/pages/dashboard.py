from nicegui import ui

from gui.layout import page_shell
from gui.data import get_pipeline_overview, next_step_for

NEXT_STEP_LABELS = {
    "select": "▶ 前往選題台",
    "script": "▶ 前往腳本生成",
    "voice": "▶ 前往語音渲染",
    "visual": "▶ 前往配圖生成",
    "video": "▶ 前往影片合成",
    "publish": "▶ 前往多平台發布",
}
NEXT_STEP_ROUTES = {
    "select": "/select",
    "script": "/script",
    "voice": "/voice",
    "visual": "/visual",
    "video": "/video",
    "publish": "/publish",
}


def _stage_dot(done: bool):
    ui.icon('check_circle' if done else 'radio_button_unchecked').classes(
        'text-green-400' if done else 'text-slate-600'
    )


def _render_card(item):
    with ui.card().classes('w-full'):
        with ui.row().classes('items-center justify-between w-full'):
            with ui.column().classes('gap-0'):
                ui.label(f"#{item['id']} · {item['category']}").classes('text-xs text-slate-400')
                ui.label(item['title']).classes('text-base font-medium')

            next_step = next_step_for(item)
            if next_step:
                ui.button(
                    NEXT_STEP_LABELS[next_step],
                    on_click=lambda r=NEXT_STEP_ROUTES[next_step]: ui.navigate.to(r)
                ).props('outline').classes('shrink-0')
            else:
                ui.badge('已發布完成', color='green')

        with ui.row().classes('items-center gap-4 mt-2 flex-wrap'):
            stages = [
                ("選定", item['is_selected'] or item['is_processed']),
                ("腳本", item['has_script']),
                ("語音", item['has_voice']),
                ("配圖", item['has_images']),
                ("影片", item['has_video']),
                ("發布", item['is_published']),
            ]
            for label, done in stages:
                with ui.row().classes('items-center gap-1'):
                    _stage_dot(done)
                    ui.label(label).classes('text-xs text-slate-400')


@ui.page('/')
def dashboard_page():
    content = page_shell('/')
    with content:
        ui.label('管線儀表板').classes('text-2xl font-bold')

        filter_state = {'value': 'all'}
        card_container = ui.column().classes('w-full gap-2')

        def refresh():
            card_container.clear()
            overview = get_pipeline_overview()

            if filter_state['value'] == 'in_progress':
                overview = [i for i in overview if next_step_for(i) is not None]
            elif filter_state['value'] == 'published':
                overview = [i for i in overview if i['is_published']]

            with card_container:
                if not overview:
                    ui.label('目前沒有符合條件的項目。').classes('text-slate-400')
                for item in overview:
                    _render_card(item)

        with ui.row().classes('items-center gap-2'):
            ui.button('全部', on_click=lambda: (filter_state.update(value='all'), refresh())).props('flat')
            ui.button('進行中', on_click=lambda: (filter_state.update(value='in_progress'), refresh())).props('flat')
            ui.button('已發布', on_click=lambda: (filter_state.update(value='published'), refresh())).props('flat')
            ui.button(icon='refresh', on_click=refresh).props('flat round')

        refresh()
