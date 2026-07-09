import glob
import os

from nicegui import ui

import config
import step6_video_assembly
from gui.layout import page_shell
from gui.runner import run_in_background


@ui.page('/video')
def video_page():
    content = page_shell('/video')
    with content:
        ui.label('影片自動生成與字幕壓製').classes('text-2xl font-bold')

        with ui.tabs().classes('w-full') as tabs:
            tab1 = ui.tab('原模式')
            tab2 = ui.tab('素材模式')
            tab3 = ui.tab('去主播素材模式')
            tab4 = ui.tab('客製化模式')

        # 客製化模式的四個來源選項 (預設值對應原 CLI 互動選單「按 Enter」的預設)
        custom_video = {'value': 1}
        custom_image = {'value': 1}
        custom_anchor = {'value': 1}
        custom_music = {'value': 1}

        with ui.tab_panels(tabs, value=tab1).classes('w-full'):
            with ui.tab_panel(tab1):
                ui.label('使用 output_images/ 自動生成之配圖與配音，動態對齊合成。').classes('text-slate-400 text-sm')
            with ui.tab_panel(tab2):
                ui.label('從 assets/ 資料夾抓取「同新聞ID」之影片/圖片/音樂素材製作。').classes('text-slate-400 text-sm')
            with ui.tab_panel(tab3):
                ui.label('同素材模式，但不疊加主播頭像 (適用素材已含主播畫面)。').classes('text-slate-400 text-sm')
            with ui.tab_panel(tab4):
                ui.label('自由選擇各項素材來源：').classes('text-slate-400 text-sm mb-2')
                with ui.column().classes('gap-2 w-full'):
                    ui.select({0: '不增加影片', 1: '從素材資料夾 (去聲)'}, value=1, label='影片來源') \
                        .classes('w-full').bind_value(custom_video, 'value')
                    ui.select({0: '不增加圖片', 1: '從素材資料夾', 2: '模組生成 (output_images)'}, value=1, label='圖片來源') \
                        .classes('w-full').bind_value(custom_image, 'value')
                    ui.select({0: '不加主播頭像', 1: '加上主播頭像'}, value=1, label='主播頭像') \
                        .classes('w-full').bind_value(custom_anchor, 'value')
                    ui.select({0: '不增加音樂', 1: '從素材資料夾 (降音作為 BGM)'}, value=1, label='音樂來源') \
                        .classes('w-full').bind_value(custom_music, 'value')

        # tabs.value 可能是「名稱字串」(點擊後)、tab 物件、或 None (尚未點擊，預設為原模式)。
        # 同時建立兩種對照，查詢時三種情況都能正確解析。
        MODE_BY_NAME = {'原模式': 1, '素材模式': 2, '去主播素材模式': 3, '客製化模式': 4}
        MODE_BY_TAB = {tab1: 1, tab2: 2, tab3: 3, tab4: 4}

        def current_mode():
            v = tabs.value
            if v in MODE_BY_TAB:
                return MODE_BY_TAB[v]
            return MODE_BY_NAME.get(v, 1)

        pending_container = ui.column().classes('w-full gap-1')
        preview_container = ui.column().classes('w-full gap-2')

        def refresh_pending():
            pending_container.clear()
            voices = glob.glob(os.path.join(config.OUTPUT_VOICES, "*_final.wav"))
            with pending_container:
                if not voices:
                    ui.label('目前沒有可用的語音檔 (*_final.wav)。').classes('text-slate-400')
                for v in voices:
                    ui.label(f"🔊 {os.path.basename(v)}").classes('text-sm')

        def refresh_outputs():
            preview_container.clear()
            videos = sorted(glob.glob(os.path.join(config.OUTPUT_VIDEOS, "*_subtitled.mp4")))
            with preview_container:
                if videos:
                    ui.label('已產出影片：').classes('font-medium mt-2')
                for v in videos:
                    with ui.column().classes('gap-1'):
                        ui.label(os.path.basename(v)).classes('text-sm')
                        ui.video(v).classes('w-48')

        def do_assemble():
            mode = current_mode()
            voice_count = len(glob.glob(os.path.join(config.OUTPUT_VOICES, "*_final.wav")))
            if voice_count == 0:
                ui.notify('找不到語音檔 (*_final.wav)，請先完成語音渲染。', type='warning')
                return

            ui.notify(f'開始合成（模式 {mode}），請看下方即時 Log 進度。', type='info')
            assemble_btn.disable()

            def on_done(result, error):
                assemble_btn.enable()
                refresh_pending()
                refresh_outputs()

            ok = run_in_background(
                '影片合成', step6_video_assembly.run,
                mode=mode,
                custom_video=custom_video['value'], custom_image=custom_image['value'],
                custom_anchor=custom_anchor['value'], custom_music=custom_music['value'],
                on_done=on_done,
                total_items=voice_count, item_marker='▶ 正在合成並上字幕：',
            )
            if not ok:
                assemble_btn.enable()

        with ui.row().classes('items-center gap-2'):
            assemble_btn = ui.button('🎬 開始合成', icon='movie_creation', on_click=do_assemble, color='primary')
            ui.button(icon='refresh', on_click=lambda: (refresh_pending(), refresh_outputs())).props('flat round')

        refresh_pending()
        refresh_outputs()
