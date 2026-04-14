"""
Facebook / Meta Business Suite DOM 診斷工具
執行後會用已登入的 session 開啟 Meta Business Suite，
截圖並印出頁面所有按鈕 HTML，找出正確的上傳選取器
"""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

USER_DATA_DIR = "./playwright_session"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        channel="chrome",
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = browser.new_page()
    
    # 前往 Meta Business Suite 的 Reels 發布頁面
    page.goto("https://business.facebook.com/reels/create")
    print("[診斷] 等待頁面載入 (8秒)...")
    page.wait_for_timeout(8000)
    
    page.screenshot(path="fb_debug.png")
    print("[診斷] 截圖已儲存至 fb_debug.png")
    
    # 印出頁面 URL（確認是否被重新導向）
    print(f"\n[診斷] 目前頁面 URL: {page.url}")
    print(f"[診斷] 頁面標題: {page.title()}")
    
    # 印出所有按鈕
    print("\n[診斷] 頁面上可見的 button 與連結清單：")
    buttons = page.locator("button, [role='button'], a[href]").all()
    for i, btn in enumerate(buttons[:25]):
        try:
            outer = btn.evaluate("el => el.outerHTML")
            print(f"  [{i}] {outer[:250]}")
        except:
            pass

    # 也嘗試尋找 input[type=file]
    print("\n[診斷] 頁面上的 file input 元素：")
    inputs = page.locator("input[type='file']").all()
    if inputs:
        for i, inp in enumerate(inputs):
            try:
                outer = inp.evaluate("el => el.outerHTML")
                print(f"  [file-{i}] {outer[:300]}")
            except:
                pass
    else:
        print("  (目前頁面無 file input，可能需要先點擊某個「建立」或「發布」按鈕)")

    print("\n[診斷] 完成！請按 Enter 關閉瀏覽器。")
    input("> ")
    browser.close()
