"""
CLI 專用的模組串接邏輯 (供 step1_scraper.py / step1_manual_add.py / step1_local_loader.py 共用)。
執行完模組一之後，依序詢問是否接續執行 1.5 選題 -> 模組2 腳本生成 -> 模組3 語音合成。
GUI 不使用本檔案 (GUI 由介面按鈕個別觸發各模組)。
"""
import sys
import subprocess


def run_and_offer_next(auto_run_selector=True):
    """
    auto_run_selector: True 表示先自動執行一次 1.5 選題模組 (符合 scraper/manual_add 的既有行為)，
                        False 則跳過 1.5、直接詢問是否執行模組2 (符合 local_loader 已產出腳本時的路徑)。
    """
    if auto_run_selector:
        print("\n👉 自動接續執行 1.5 挑選模組...")
        subprocess.run([sys.executable, 'step1_5_selector.py'])

    ans2 = input("\n❓ 1.5 模組挑選完畢。是否繼續執行 [模組2: AI產生腳本]？ (y/n，輸入 q 退出): ").strip().lower()
    if ans2 == 'q':
        print("🚪 中途退出。")
        sys.exit(0)
    elif ans2 in ['y', 'yes']:
        print("\n👉 接續執行模組 2...")
        subprocess.run([sys.executable, 'step2_script_generator.py'])

        ans3 = input("\n❓ 模組 2 執行完畢。是否繼續執行 [模組3: 語音合成]？ (y/n，輸入 q 退出): ").strip().lower()
        if ans3 == 'q':
            print("🚪 中途退出。")
            sys.exit(0)
        elif ans3 in ['y', 'yes']:
            print("\n👉 接續執行模組 3...")
            subprocess.run([sys.executable, 'step3_voice_renderer.py'])
            print("\n✅ 所有選定之模組皆執行完畢。")
        else:
            print("⏸️ 結束執行。")
    else:
        print("⏸️ 結束執行。")
