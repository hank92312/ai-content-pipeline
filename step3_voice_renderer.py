import asyncio
import os
import glob
import sys
import edge_tts
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 修正 Windows 終端機印出 Emoji 的編碼問題
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
#  🎙️  模組三：語音渲染中心
#  小花的AI情報站 - AI Content Pipeline
# ============================================================
#
#  【模式切換說明】
#  將 VOICE_MODE 設定為以下其中一個值：
#    "edge-tts" → 過渡期：直接使用微軟 edge-tts 的聲音輸出
#    "rvc"      → 正式期：先用 edge-tts 生成基礎音，再透過 RVC 推理轉換為蔡小花專屬音色
# ============================================================

VOICE_MODE = "rvc"

# --- edge-tts 設定 ---
# 可選語音列表 (台灣中文)：
#   zh-TW-YunJheNeural     → 沉穩男聲 ✅ 改回男聲作為基底
#   zh-TW-HsiaoChenNeural  → 親切自然女聲
#   zh-TW-HsiaoYuNeural    → 活潑俏皮女聲
EDGE_TTS_VOICE = "zh-TW-YunJheNeural"
EDGE_TTS_RATE  = "+25%"  # 調整：依照使用者要求，語速調快至約 1.2 倍
EDGE_TTS_PITCH = "+0Hz"  # 音調微調

# --- RVC 設定 ---
# RVC模型存於 RVC1006AMD_Intel1 資料夾。在此指定檔名即可 (需位於 assets/weights)。
RVC_MODEL_NAME    = "AutoChannel_Voice.pth"  
RVC_INDEX_PATH    = ""   # 如果有 .index 檔案可以設定絕對路徑，沒有就留空
RVC_F0_UP_KEY     = "2"  # 調整：提高 2 以增加活潑感 (原為 1)

# --- 路徑設定 ---
import config
SCRIPTS_DIR = config.OUTPUT_SCRIPTS
VOICES_DIR  = config.OUTPUT_VOICES


# ============================================================
#  核心功能一：edge-tts 文字轉語音
# ============================================================
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: print(f"   ⚠️  [{retry_state.attempt_number}/5] 連線失敗，將在 {retry_state.next_action.sleep} 秒後重試...")
)
async def generate_tts_audio(text: str, output_path: str, output_subs_path: str):
    """使用 edge-tts 將文字轉換為 .wav 音檔，同時儲存時間軸中繼檔"""
    import json
    communicate = edge_tts.Communicate(
        text=text,
        voice=EDGE_TTS_VOICE,
        rate=EDGE_TTS_RATE,
        pitch=EDGE_TTS_PITCH
    )
    
    subs_data = []
    
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                # offset 和 duration 是以 100 奈秒 (100-nanoseconds) 為單位
                # 轉為秒數： 100ns = 1e-7 seconds
                start_sec = chunk["offset"] / 10000000.0
                duration_sec = chunk["duration"] / 10000000.0
                subs_data.append({
                    "start": start_sec,
                    "duration": duration_sec,
                    "text": chunk["text"]
                })
                
    with open(output_subs_path, "w", encoding="utf-8") as f:
        json.dump(subs_data, f, ensure_ascii=False, indent=2)


# ============================================================
#  核心功能二：RVC 音色轉換
# ============================================================
def apply_rvc_conversion(input_wav: str, output_wav: str):
    """
    將 edge-tts 生成的基礎音檔，透過 RVC 模型推理，轉換為「蔡小花」的專屬音色。
    """
    import subprocess
    
    # 指向本地的 RVC 資料夾與 Python
    rvc_dir = os.path.abspath("RVC1006AMD_Intel1")
    python_exe = os.path.join(rvc_dir, "runtime", "python.exe")
    infer_cli = os.path.join(rvc_dir, "tools", "infer_cli.py")
    
    cmd = [
        python_exe, infer_cli,
        "--f0up_key", RVC_F0_UP_KEY,
        "--input_path", os.path.abspath(input_wav),
        "--opt_path", os.path.abspath(output_wav),
        "--model_name", RVC_MODEL_NAME,
        "--f0method", "rmvpe",
        "--index_rate", "0.75" if RVC_INDEX_PATH else "0",
        "--dml", # 啟動 AMD GPU (DirectML) 硬體加速
    ]
    if RVC_INDEX_PATH and os.path.exists(RVC_INDEX_PATH):
        cmd.extend(["--index_path", os.path.abspath(RVC_INDEX_PATH)])
        
    print(f"      [RVC] 啟動轉換程序: 模型={RVC_MODEL_NAME}, 音調偏移={RVC_F0_UP_KEY}")
    try:
        # 第一階段嘗試：硬體加速
        subprocess.run(cmd, cwd=rvc_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"      ⚠️ 硬體加速 (DML) 失敗或缺乏支援，將嘗試切換至 CPU 模型運算...")
        try:
            # 拔除 --dml 參數
            if "--dml" in cmd:
                cmd.remove("--dml")
            subprocess.run(cmd, cwd=rvc_dir, check=True)
        except subprocess.CalledProcessError as e2:
            print(f"      ❌ RVC 轉換雙重失敗，將回退至 edge-tts 原始音源。詳細錯誤: {e2}")
            import shutil
            shutil.copy(input_wav, output_wav)


# ============================================================
#  主流程
# ============================================================
async def main():
    print("=" * 50)
    print(f"  🎙️  語音渲染中心 - 模式：【{VOICE_MODE.upper()}】")
    print("=" * 50)

    # 建立輸出資料夾
    os.makedirs(VOICES_DIR, exist_ok=True)

    # 找到所有待處理的腳本
    script_files = glob.glob(os.path.join(SCRIPTS_DIR, "*.txt"))

    if not script_files:
        print(f"❌ 在 '{SCRIPTS_DIR}/' 資料夾中找不到任何腳本檔案。")
        print("   請先執行 step2_script_generator.py 生成腳本！")
        return

    print(f"🔍 找到 {len(script_files)} 個待處理腳本。\n")

    for script_path in script_files:
        # 取得檔名 (不含副檔名)，例如 "script_Finance_47"
        base_name = os.path.splitext(os.path.basename(script_path))[0]
        
        # 讀取腳本內容
        with open(script_path, 'r', encoding='utf-8') as f:
            script_text = f.read().strip()

        if not script_text:
            print(f"  ⚠️  [{base_name}] 腳本內容為空，跳過。")
            continue

        print(f"🎬 正在處理：{base_name}")
        print(f"   📝 腳本預覽：{script_text[:40]}...")

        # --- 步驟 A：edge-tts 生成基礎音檔 ---
        tts_wav_path = os.path.join(VOICES_DIR, f"{base_name}_tts.wav")
        subs_json_path = os.path.join(VOICES_DIR, f"{base_name}_subs.json")
        print(f"   🔊 [Step A] edge-tts 生成基礎音檔與字幕時間軸...")
        try:
            await generate_tts_audio(script_text, tts_wav_path, subs_json_path)
            print(f"   ✅ 基礎音檔與時間軸已儲存：{tts_wav_path} & .json")
        except Exception as e:
            print(f"   ❌ edge-tts 生成失敗：{e}")
            continue

        # --- 步驟 B：根據模式決定是否進行 RVC 音色轉換 ---
        final_wav_path = os.path.join(VOICES_DIR, f"{base_name}_final.wav")
        
        if VOICE_MODE == "rvc":
            print(f"   🎨 [Step B] RVC 音色轉換 (蔡小花)...")
            try:
                apply_rvc_conversion(tts_wav_path, final_wav_path)
                print(f"   ✅ 蔡小花音色音檔已儲存：{final_wav_path}")
            except Exception as e:
                print(f"   ❌ RVC 轉換失敗：{e}")
        else:
            # edge-tts 模式：直接將 TTS 音檔作為最終產出
            import shutil
            shutil.copy(tts_wav_path, final_wav_path)
            print(f"   ✅ [edge-tts 模式] 最終音檔：{final_wav_path}")

        print()

    print("🎉 所有腳本語音渲染完畢！")
    print(f"   輸出位置：{os.path.abspath(VOICES_DIR)}/")
    print()
    if VOICE_MODE == "edge-tts":
        print("💡 提示：待蔡小花聲音模型訓練完成後，")
        print("         請填寫腳本上方的 RVC_MODEL_PATH 等設定，")
        print("         並將 VOICE_MODE 改為 'rvc' 即可切換至專屬音色！")


if __name__ == "__main__":
    asyncio.run(main())
