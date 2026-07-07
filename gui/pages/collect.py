from nicegui import ui

import step1_scraper
import step1_manual_add
import step1_local_loader
from gui.layout import page_shell
from gui.runner import run_in_background
from gui.state import state


@ui.page('/collect')
def collect_page():
    content = page_shell('/collect')
    with content:
        ui.label('資料蒐集').classes('text-2xl font-bold')

        with ui.tabs().classes('w-full') as tabs:
            tab_rss = ui.tab('RSS 自動爬蟲')
            tab_manual = ui.tab('貼網址')
            tab_local = ui.tab('本地匯入')

        with ui.tab_panels(tabs, value=tab_rss).classes('w-full'):
            # --- RSS 自動爬蟲 ---
            with ui.tab_panel(tab_rss):
                ui.label('自動掃描設定好的 RSS 來源，並用 AI 篩選最具話題性的新聞。').classes('text-slate-400 text-sm')
                rss_btn = ui.button('🔍 開始抓取', icon='cloud_download')

                def do_scrape():
                    rss_btn.disable()

                    def on_done(result, error):
                        rss_btn.enable()

                    ok = run_in_background('資料蒐集 (RSS)', step1_scraper.run, on_done=on_done)
                    if not ok:
                        rss_btn.enable()

                rss_btn.on_click(do_scrape)

            # --- 貼網址 ---
            with ui.tab_panel(tab_manual):
                ui.label('貼上網址，自動嘗試抓取標題與縮圖。').classes('text-slate-400 text-sm')
                url_input = ui.input('網頁網址 (URL)').classes('w-full')
                preview_box = ui.column().classes('w-full')

                title_input = ui.input('標題').classes('w-full')
                category_select = ui.select({'Finance': 'Finance (財經/國際情勢)', 'Gaming': 'Gaming (遊戲/動漫/科技)'}, value='Finance').classes('w-full')
                fetched_image = {'url': ''}

                def do_preview():
                    url = url_input.value.strip()
                    if not url:
                        ui.notify('請先輸入網址', type='warning')
                        return
                    preview = step1_manual_add.fetch_page_preview(url, log=state.log)
                    title_input.value = preview['title']
                    fetched_image['url'] = preview['image_url']
                    preview_box.clear()
                    with preview_box:
                        if preview['image_url']:
                            ui.image(preview['image_url']).classes('w-48')
                        ui.label(f"擷取結果：{preview['title'] or '(無法自動擷取標題，請手動輸入)'}").classes('text-sm text-slate-400')

                ui.button('🔍 嘗試自動擷取標題', on_click=do_preview).props('outline')

                def do_add():
                    url = url_input.value.strip()
                    title = title_input.value.strip()
                    if not url or not title:
                        ui.notify('網址與標題皆為必填', type='warning')
                        return
                    result = step1_manual_add.run(
                        url, title, category=category_select.value,
                        image_url=fetched_image['url'], log=state.log
                    )
                    if result['status'] == 'inserted':
                        ui.notify('新增成功！', type='positive')
                        url_input.value = ''
                        title_input.value = ''
                    elif result['status'] == 'duplicate':
                        ui.notify('此網址已存在於資料庫中，已維持原狀態 (未變更)。', type='warning')
                    else:
                        ui.notify('新增失敗，請查看下方 Log。', type='negative')

                ui.button('➕ 加入資料庫', on_click=do_add, color='primary')

            # --- 本地匯入 ---
            with ui.tab_panel(tab_local):
                ui.label('掃描 source/ 資料夾內的 .txt / .md / .pdf / .json 檔案並匯入。').classes('text-slate-400 text-sm')
                pending_container = ui.column().classes('w-full gap-2')
                batch_category = ui.select(
                    {'Finance': 'Finance (財經/國際情勢)', 'Gaming': 'Gaming (遊戲/動漫/科技)'},
                    value='Finance', label='本批次分類 (適用於所有待匯入檔案)'
                ).classes('w-full')

                def refresh_pending():
                    pending_container.clear()
                    files = step1_local_loader.get_pending_files()
                    with pending_container:
                        if not files:
                            ui.label('source/ 資料夾內目前沒有待匯入檔案。').classes('text-slate-400')
                        else:
                            for f in files:
                                ui.label(f"📄 {f}").classes('text-sm')

                def do_import():
                    import_btn.disable()

                    def on_done(result, error):
                        import_btn.enable()
                        refresh_pending()

                    ok = run_in_background(
                        '本地匯入', step1_local_loader.run,
                        category=batch_category.value, on_done=on_done
                    )
                    if not ok:
                        import_btn.enable()

                import_btn = ui.button('📥 開始匯入', icon='upload_file', on_click=do_import)
                ui.button(icon='refresh', on_click=refresh_pending).props('flat round')

                refresh_pending()
