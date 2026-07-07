import glob
import os

from nicegui import ui

import config
import step5_visual_generator
from gui.layout import page_shell
from gui.runner import run_in_background


@ui.page('/visual')
def visual_page():
    content = page_shell('/visual')
    with content:
        ui.label('AI 配圖生成').classes('text-2xl font-bold')
        ui.label('讀取 output_scripts/ 內所有腳本 JSON，透過 Gemini Vision + Imagen 產出 9:16 配圖。').classes('text-slate-400 text-sm')

        pending_container = ui.column().classes('w-full gap-1')
        gallery_container = ui.row().classes('w-full gap-2 flex-wrap')

        def refresh_pending():
            pending_container.clear()
            scripts = glob.glob(os.path.join(config.OUTPUT_SCRIPTS, "*.json"))
            with pending_container:
                if not scripts:
                    ui.label('目前沒有待處理的腳本。').classes('text-slate-400')
                for s in scripts:
                    ui.label(f"📝 {os.path.basename(s)}").classes('text-sm')

        def refresh_gallery():
            gallery_container.clear()
            images = sorted(glob.glob(os.path.join(config.OUTPUT_IMAGES, "*.jpg")))
            with gallery_container:
                for img in images:
                    ui.image(img).classes('w-32 h-56 object-cover rounded')

        def do_generate():
            gen_btn.disable()

            def on_done(result, error):
                gen_btn.enable()
                refresh_pending()
                refresh_gallery()

            ok = run_in_background('AI 配圖生成', step5_visual_generator.run, on_done=on_done)
            if not ok:
                gen_btn.enable()

        with ui.row().classes('items-center gap-2'):
            gen_btn = ui.button('🎨 開始生成', icon='auto_fix_high', on_click=do_generate, color='primary')
            ui.button(icon='refresh', on_click=lambda: (refresh_pending(), refresh_gallery())).props('flat round')

        refresh_pending()
        refresh_gallery()
