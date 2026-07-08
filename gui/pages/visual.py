import glob
import json
import os

from nicegui import ui

import config
import step5_visual_generator
from gui.layout import page_shell
from gui.runner import run_in_background
from gui.confirm import confirm_api_action


def _count_pending_images():
    """統計待處理腳本 JSON 內的 visual_prompts 總數 (即 Imagen 將被呼叫的張數)"""
    total_images = 0
    total_scripts = 0
    for json_path in glob.glob(os.path.join(config.OUTPUT_SCRIPTS, "*.json")):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            total_images += len(data.get("visual_prompts", []))
            total_scripts += 1
        except Exception:
            pass
    return total_scripts, total_images


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

            _, total_images = _count_pending_images()
            ok = run_in_background(
                'AI 配圖生成', step5_visual_generator.run, on_done=on_done,
                total_items=total_images, item_marker='🎨 準備生成第',
            )
            if not ok:
                gen_btn.enable()

        def ask_generate():
            scripts, images = _count_pending_images()
            if images == 0:
                ui.notify('目前沒有待處理的腳本，不會呼叫任何 API。', type='warning')
                return
            confirm_api_action(
                'AI 配圖生成',
                [
                    f'Imagen 4 生圖：共 {images} 張 (來自 {scripts} 份腳本，每張皆計費，為全管線最高費用項目)',
                    '每份腳本的第 1 張若附新聞原圖，另加 1 次 Gemini Vision 解析呼叫',
                ],
                do_generate,
            )

        with ui.row().classes('items-center gap-2'):
            gen_btn = ui.button('🎨 開始生成 💰', icon='auto_fix_high', on_click=ask_generate, color='primary')
            ui.button(icon='refresh', on_click=lambda: (refresh_pending(), refresh_gallery())).props('flat round')

        refresh_pending()
        refresh_gallery()
