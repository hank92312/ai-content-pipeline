import glob
import os

from nicegui import ui

import config
import step3_voice_renderer
from gui.layout import page_shell
from gui.runner import run_in_background


@ui.page('/voice')
def voice_page():
    content = page_shell('/voice')
    with content:
        ui.label('語音渲染').classes('text-2xl font-bold')
        ui.label('讀取 output_scripts/ 內所有腳本，使用 edge-tts 產生基礎音檔並經 RVC 轉換為專屬音色。').classes('text-slate-400 text-sm')

        pending_container = ui.column().classes('w-full gap-1')
        preview_container = ui.column().classes('w-full gap-2')

        def refresh_pending():
            pending_container.clear()
            scripts = glob.glob(os.path.join(config.OUTPUT_SCRIPTS, "*.txt"))
            with pending_container:
                if not scripts:
                    ui.label('目前沒有待處理的腳本。').classes('text-slate-400')
                for s in scripts:
                    ui.label(f"📝 {os.path.basename(s)}").classes('text-sm')

        def refresh_outputs():
            preview_container.clear()
            voices = sorted(glob.glob(os.path.join(config.OUTPUT_VOICES, "*_final.wav")))
            with preview_container:
                if voices:
                    ui.label('已產出音檔：').classes('font-medium mt-2')
                for v in voices:
                    with ui.row().classes('items-center gap-2'):
                        ui.label(os.path.basename(v)).classes('text-sm w-64')
                        ui.audio(v).classes('h-8')

        def do_render():
            render_btn.disable()

            def on_done(result, error):
                render_btn.enable()
                refresh_pending()
                refresh_outputs()

            ok = run_in_background('語音渲染', step3_voice_renderer.run, on_done=on_done)
            if not ok:
                render_btn.enable()

        with ui.row().classes('items-center gap-2'):
            render_btn = ui.button('🎙️ 開始渲染', icon='mic', on_click=do_render, color='primary')
            ui.button(icon='refresh', on_click=lambda: (refresh_pending(), refresh_outputs())).props('flat round')

        refresh_pending()
        refresh_outputs()
