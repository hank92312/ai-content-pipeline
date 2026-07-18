"""
YouTube Studio DOM 診斷工具
執行後會用您已登入的 session 開啟 YouTube Studio，
截圖並印出頁面標題區的所有按鈕 HTML，讓我們找到正確的選取器
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
    page.goto("https://studio.youtube.com/")
    
    print("[診斷] 等待頁面載入 (7秒)...")
    page.wait_for_timeout(7000)
    
    # 截圖存檔方便我們觀察
    page.screenshot(path="yt_studio_debug.png")
    print("[診斷] 截圖已儲存至 yt_studio_debug.png")
    
    # 印出頁面標題列所有帶有 button role 的元素
    print("\n[診斷] 頁面上可見的 button 元素清單：")
    buttons = page.locator("button, ytcp-button").all()
    for i, btn in enumerate(buttons[:20]):
        try:
            outer = btn.evaluate("el => el.outerHTML")
            print(f"  [{i}] {outer[:200]}")
        except:
            pass

    print("\n[診斷] 完成！請按 Enter 關閉瀏覽器。")
    input("> ")
    browser.close()
