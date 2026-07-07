from nicegui import ui

import config
import step2_script_generator
from gui.layout import page_shell
from gui.runner import run_in_background


@ui.page('/script')
def script_page():
    content = page_shell('/script')
    with content:
        ui.label('AI 腳本生成').classes('text-2xl font-bold')
        ui.label('針對資料庫中所有「已選定」的新聞，逐則呼叫 Gemini 產生短影音腳本。').classes('text-slate-400 text-sm')

        mode_radio = ui.radio({'standard': '標準模式 (約 30 秒)', 'pro': '專業深入報導 (約 60 秒)'}, value='standard').props('inline')

        model_select = ui.select(config.SCRIPT_MODELS_STANDARD, label='模型').classes('w-full')

        def sync_model_options():
            options = config.SCRIPT_MODELS_PRO if mode_radio.value == 'pro' else config.SCRIPT_MODELS_STANDARD
            model_select.options = options
            model_select.value = next(iter(options.values()))
            model_select.update()

        mode_radio.on_value_change(sync_model_options)
        sync_model_options()

        result_container = ui.column().classes('w-full gap-2')

        def do_generate():
            gen_btn.disable()
            result_container.clear()

            def on_done(result, error):
                gen_btn.enable()
                if result:
                    with result_container:
                        ui.label(f"完成：成功 {result['success']} 篇，失敗 {result['failed']} 篇").classes('font-medium')
                        for out in result['outputs']:
                            script = out['script']
                            with ui.card().classes('w-full'):
                                ui.label(f"#{out['id']}").classes('text-xs text-slate-400')
                                ui.label(f"{script['intro']} {script['main_content']} {script['outro']}").classes('text-sm')
                                with ui.row().classes('gap-1 flex-wrap'):
                                    for kw in script.get('keywords', []):
                                        ui.badge(kw, color='amber')

            ok = run_in_background(
                'AI 腳本生成', step2_script_generator.run,
                mode=mode_radio.value, model=model_select.value, on_done=on_done
            )
            if not ok:
                gen_btn.enable()

        gen_btn = ui.button('🧠 開始生成', icon='auto_awesome', on_click=do_generate, color='primary')
