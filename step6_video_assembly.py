import os
import glob
import shutil
import subprocess
import sys
import json
import tempfile
import time
import numpy as np
import config
from PIL import Image, ImageDraw, ImageFont

# 修正 Windows 終端機印出 Emoji 的編碼問題
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
#  🎬 模組六：影片自動生成與字幕壓製中心
#  小花的AI情報站 - AI Content Pipeline
# ============================================================

try:
    from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, VideoFileClip, CompositeAudioClip
    from moviepy.config import FFMPEG_BINARY
    import moviepy.video.fx as vfx
    import moviepy.audio.fx as afx
    import re
except ImportError:
    print("❌ 找不到 moviepy 套件，請執行: pip install moviepy")
    sys.exit(1)

# --- 路徑與相關設定 ---
VOICES_DIR  = config.OUTPUT_VOICES
IMAGES_DIR  = config.OUTPUT_IMAGES
VIDEOS_DIR  = config.OUTPUT_VIDEOS
SCRIPTS_DIR = config.OUTPUT_SCRIPTS
AVATAR_PATH = config.ASSETS_DIR + "/sample.png"
if not os.path.exists(AVATAR_PATH):
    AVATAR_PATH = "sample.png"  # Fallback to root if not in assets
FONT_PATH   = "C:\\Windows\\Fonts\\msjhbd.ttc"  # 微軟正黑體粗體

TARGET_RESOLUTION = (1080, 1920)  # 直式短影音 9:16
FPS = 24  # 預設幀率


def extract_file_index(filepath: str) -> int:
    """處理像 script_Finance_6_0.jpg 或 ID6_1.mp4 這樣的檔名，抽取出後面的數字，以作為排序基準"""
    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]
    try:
        # 尋找最後一個底線後的數字
        parts = name_no_ext.split("_")
        if len(parts) > 1:
            return int(parts[-1])
        return 0
    except ValueError:
        return 0


def render_subtitle_image(text, keywords, font_path=FONT_PATH, font_size=58, stroke_width=5):
    """
    使用 Pillow 動態繪製每一句短影音字幕。
    支援多色高亮 (關鍵字: 黃色, 驚嘆號: 紅色)，回傳透明背景的 PIL Image (1080x600)。
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"⚠️ 找不到字體 {font_path}，請確保 Windows 系統含有此字體。")
        font = ImageFont.load_default()

    img = Image.new("RGBA", (1080, 600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    colors = ["white"] * len(text)

    # 1. 關鍵字標色為黃色 (#FFD700)
    for kw in keywords:
        if not kw:
            continue
        start = 0
        while True:
            idx = text.find(kw, start)
            if idx == -1:
                break
            for i in range(idx, idx + len(kw)):
                colors[i] = "#FFD700"
            start = idx + len(kw)

    # 2. 驚嘆號/問號/強調符號標色為紅色 (#FF3333)
    for i, c in enumerate(text):
        if c in ["!", "?", "！", "？", "🔥", "✨"]:
            colors[i] = "#FF3333"

    # 3. 處理自動換行與測量寬度
    lines = []
    current_line = []
    current_line_width = 0
    max_line_width = 950

    for i, c in enumerate(text):
        bbox = font.getbbox(c)
        cw = bbox[2] if bbox else font_size

        if current_line_width + cw > max_line_width:
            lines.append(current_line)
            current_line = []
            current_line_width = 0

        current_line.append((c, colors[i], cw))
        current_line_width += cw

    if current_line:
        lines.append(current_line)

    # 4. 開始置中繪製
    start_y = 50
    for line in lines:
        line_w = sum(cw for _, _, cw in line)
        start_x = (1080 - line_w) // 2

        for char, col, cw in line:
            draw.text((start_x, start_y), char, font=font, fill=col, stroke_width=stroke_width, stroke_fill="black")
            start_x += cw

        start_y += font_size + 20

    return img


def create_subtitle_clip(text, keywords, duration, font_path=FONT_PATH, font_size=58, stroke_width=5):
    """回傳透明背景的 MoviePy ImageClip 版字幕 (保留給仍以 MoviePy 疊字幕的呼叫端)。"""
    img = render_subtitle_image(text, keywords, font_path=font_path, font_size=font_size, stroke_width=stroke_width)
    return ImageClip(np.array(img)).with_duration(duration)


def ffmpeg_slideshow_bg(img_paths, voice_path, bgm_path, duration, out_path, log=print):
    """
    以 ffmpeg 將圖片序列合成為背景影片 (等分時長 + 1 秒交叉淡入轉場)，
    並混入口播與可選 BGM (音量 config.BGM_VOLUME)。
    時間軸與原 MoviePy 合成一致：轉場使背景縮短 (n-1) 秒，尾端以黑幕補滿至音訊長度。
    """
    n = len(img_paths)
    tpi = duration / n

    cmd = [FFMPEG_BINARY, "-y"]
    for p in img_paths:
        cmd += ["-loop", "1", "-t", f"{tpi:.3f}", "-i", p]
    cmd += ["-i", voice_path]
    if bgm_path:
        cmd += ["-stream_loop", "-1", "-i", bgm_path]

    filters = []
    for i in range(n):
        filters.append(f"[{i}:v]scale=1080:1920,setsar=1,fps={FPS},format=yuv420p,settb=AVTB[s{i}]")
    last = "s0"
    for k in range(1, n):
        filters.append(f"[{last}][s{k}]xfade=transition=fade:duration=1:offset={k * (tpi - 1):.3f}[x{k}]")
        last = f"x{k}"
    if n > 1:
        filters.append(f"[{last}]tpad=stop_mode=add:stop_duration={n - 1}:color=black[vbg]")
    else:
        filters.append(f"[{last}]copy[vbg]")

    voice_idx = n
    if bgm_path:
        filters.append(f"[{voice_idx + 1}:a]volume={config.BGM_VOLUME},atrim=0:{duration:.3f}[bgm]")
        filters.append(f"[{voice_idx}:a][bgm]amix=inputs=2:duration=first:normalize=0[abg]")
        audio_map = "[abg]"
    else:
        audio_map = f"{voice_idx}:a"

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[vbg]", "-map", audio_map,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14",
        "-c:a", "aac", "-ac", "2", "-t", f"{duration:.3f}", out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        log(f"  ❌ ffmpeg 背景合成失敗：\n{tail}")
        return False
    return True


def ffmpeg_overlay_encode(bg_path, overlays, out_path, log=print):
    """
    以 ffmpeg 將頭像/字幕 PNG 疊加到背景影片上並完成最終編碼。
    overlays: [{path, x, y, start, end}]，start/end 為 None 代表全程顯示；
    可為空清單 (單純把背景重新編碼輸出)。
    編碼依序嘗試 AMD AMF → Intel QSV → CPU libx264，回傳是否成功。
    """
    cmd_base = [FFMPEG_BINARY, "-y", "-i", bg_path]
    for ov in overlays:
        cmd_base += ["-i", ov["path"]]

    if overlays:
        steps = []
        last = "[0:v]"
        for i, ov in enumerate(overlays):
            out_label = "[vout]" if i == len(overlays) - 1 else f"[v{i + 1}]"
            enable = ""
            if ov["start"] is not None:
                enable = f":enable='between(t,{ov['start']:.3f},{ov['end']:.3f})'"
            steps.append(f"{last}[{i + 1}:v]overlay={ov['x']}:{ov['y']}{enable}{out_label}")
            last = out_label
        cmd_base += ["-filter_complex", ";".join(steps), "-map", "[vout]"]
    else:
        cmd_base += ["-map", "0:v"]

    cmd_base += ["-map", "0:a?", "-c:a", "copy"]

    attempts = [
        ("⚡ 嘗試使用 AMD GPU 硬體加速編碼 (AMF)...", ["-c:v", "h264_amf", "-preset", "balanced"]),
        ("⚡ 嘗試使用 Intel QuickSync (QSV) 硬體加速編碼...", ["-c:v", "h264_qsv", "-global_quality", "25"]),
        ("🐢 使用標準 CPU 模式進行編碼 (這可能需要較長時間)...", ["-c:v", "libx264"]),
    ]
    for msg, video_args in attempts:
        log(f"  {msg}")
        result = subprocess.run(
            cmd_base + video_args + ["-pix_fmt", "yuv420p", out_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            return True
        log("  ⚠️ 此編碼器失敗，嘗試下一項...")

    tail = "\n".join(result.stderr.strip().splitlines()[-5:])
    log(f"  ❌ 所有編碼器皆失敗，最後錯誤訊息：\n{tail}")
    return False


def run(mode=1, custom_video=0, custom_image=0, custom_anchor=0, custom_music=0, log=print):
    """
    影片合成主流程：讀取 output_voices/ 內所有 *_final.wav，依模式組合背景/頭像/字幕後輸出帶字幕影片。

    mode: 1=原模式(模組生成配圖) 2=素材模式 3=去主播素材模式 4=客製化模式
    以下四個參數僅在 mode==4 時生效 (對應原始互動選單的四個子選項，預設皆為 0=不使用)：
      custom_video:  0=不增加影片, 1=從素材資料夾(去聲)
      custom_image:  0=不增加圖片, 1=從素材資料夾, 2=模組生成 (output_images)
      custom_anchor: 0=不加主播頭像, 1=加上
      custom_music:  0=不增加音樂, 1=從素材資料夾 (降音作為 BGM)

    回傳: {"success": 成功支數, "failed": 失敗/跳過支數, "outputs": [產出影片路徑, ...]}
    """
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    voice_files = glob.glob(os.path.join(VOICES_DIR, "*_final.wav"))

    if not voice_files:
        log(f"❌ 在 '{VOICES_DIR}/' 中找不到 *_final.wav 音檔。")
        log("   請確認 step3 已經執行完畢！")
        return {"success": 0, "failed": 0, "outputs": []}

    has_avatar = os.path.exists(AVATAR_PATH)
    if not has_avatar:
        log(f"⚠️ 找不到虛擬頭像檔 '{AVATAR_PATH}'，將純粹播放新聞配圖底檔。")

    success_count = 0
    failed_count = 0
    outputs = []
    run_start = time.time()

    for v_path in voice_files:
        basename = os.path.basename(v_path).replace("_final.wav", "")
        item_start = time.time()
        log(f"\n▶ 正在合成並上字幕：{basename}")

        # 初始化素材變數，確保每輪循環都能正確釋放
        bgm_clip = None
        bg_video = None
        bg_clip = None
        final_clips = []
        slideshow_imgs = None  # 純圖片背景 → 交給 ffmpeg 快速合成，不經過 MoviePy
        slideshow_bgm = None

        audio_clip = AudioFileClip(v_path)
        audio_duration = audio_clip.duration

        # 根據 mode 分流
        if mode == 1:
            # 2. 尋找對應的背景圖
            pattern = os.path.join(IMAGES_DIR, f"{basename}_*.jpg")
            img_paths = glob.glob(pattern)

            if not img_paths:
                log(f"  ❌ 找不到對應此語音的背景圖片：{pattern}")
                log("     跳過這個腳本...")
                failed_count += 1
                continue

            img_paths = sorted(img_paths, key=extract_file_index)
            time_per_image = audio_duration / len(img_paths)
            log(f"  🖼 找到 {len(img_paths)} 張背景圖，每張圖將顯示 {time_per_image:.1f} 秒...")

            # 純圖片背景 → 交給 ffmpeg 快速合成 (xfade 交叉淡入)
            slideshow_imgs = img_paths
        elif mode in [2, 3]:
            # 2 & 3. 素材模式尋找對應的影片、圖片與音效
            m = re.search(r'_(\d+)$', basename)
            if not m:
                log(f"  ❌ 無法從 {basename} 解析新聞ID，跳過素材模式")
                failed_count += 1
                continue
            news_id = m.group(1)

            asset_mp3 = os.path.join("assets", f"ID{news_id}.mp3")

            # --- 搜尋影片素材 ---
            asset_video_paths = []
            for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                # 找序號影片 ID6_1.mp4, ID6_2.mp4...
                pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                asset_video_paths.extend(glob.glob(pattern))

            if not asset_video_paths:
                # 沒找到序號影片，改找單張 ID6.mp4
                for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                    test_path = os.path.join("assets", f"ID{news_id}{ext}")
                    if os.path.exists(test_path):
                        asset_video_paths = [test_path]
                        break

            asset_video_paths = sorted(asset_video_paths, key=extract_file_index)

            # --- 搜尋圖片素材 ---
            asset_img_paths = []
            for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                asset_img_paths.extend(glob.glob(pattern))

            if not asset_img_paths:
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    test_path = os.path.join("assets", f"ID{news_id}{ext}")
                    if os.path.exists(test_path):
                        asset_img_paths = [test_path]
                        break

            asset_img_paths = sorted(asset_img_paths, key=extract_file_index)

            # 檢查是否有任何影像素材 (影片或圖片)
            if not asset_video_paths and not asset_img_paths:
                log(f"  ❌ 找不到 assets 相關影像素材 (ID{news_id}.*), 跳過...")
                failed_count += 1
                continue

            log(f"  🎨 使用素材模式處理影片：ID{news_id} (找到 {len(asset_video_paths)} 個影片, {len(asset_img_paths)} 張圖片)")

            if not asset_video_paths:
                # 純圖片背景 → 交給 ffmpeg 快速合成 (xfade 交叉淡入 + BGM 混音)
                slideshow_imgs = asset_img_paths
                if os.path.exists(asset_mp3):
                    slideshow_bgm = asset_mp3
            else:
                # 有影片素材 → 維持 MoviePy 合成流程
                # 準備音訊 (BGM 是選配)
                if os.path.exists(asset_mp3):
                    bgm_clip = AudioFileClip(asset_mp3)
                    if bgm_clip.duration is not None and bgm_clip.duration < audio_duration:
                        bgm_clip = bgm_clip.with_effects([
                            afx.AudioLoop(duration=audio_duration),
                            afx.MultiplyVolume(config.BGM_VOLUME)
                        ])
                    else:
                        bgm_clip = bgm_clip.with_duration(audio_duration).with_effects([
                            afx.MultiplyVolume(config.BGM_VOLUME)
                        ])
                    final_audio = CompositeAudioClip([bgm_clip, audio_clip]).with_duration(audio_duration)
                else:
                    final_audio = audio_clip

                # --- 準備影像底圖 ---
                video_clips = []
                for v_p in asset_video_paths:
                    try:
                        vc = VideoFileClip(v_p).without_audio().resized(TARGET_RESOLUTION)
                        video_clips.append(vc)
                    except Exception as e:
                        log(f"  ⚠️ 無法讀取影片 {v_p}: {e}")

                if video_clips:
                    # 串接所有影片
                    combined_video = concatenate_videoclips(video_clips, method="compose")

                    if len(asset_img_paths) > 0:
                        # 有影片 + 有圖片 => 影片播到最後5秒接圖片
                        loop_dur = max(0, audio_duration - 5)
                        bg_video_looped = combined_video.with_effects([vfx.Loop(duration=loop_dur)])
                        bg_img = ImageClip(asset_img_paths[0]).with_duration(5).resized(TARGET_RESOLUTION).with_effects([vfx.CrossFadeIn(1.0)])
                        bg_clip = concatenate_videoclips([bg_video_looped, bg_img], padding=-1.0, method="compose")
                    else:
                        # 只有影片 => 直接 Loop 到滿
                        bg_clip = combined_video.with_effects([vfx.Loop(duration=audio_duration)])
                else:
                    # 如果讀取失敗回退到純圖片
                    bg_clip = None

                # 如果影片讀取失敗，使用圖片
                if bg_clip is None and asset_img_paths:
                    if len(asset_img_paths) > 1:
                        time_per_image = audio_duration / len(asset_img_paths)
                        image_clips = []
                        for i, img_path in enumerate(asset_img_paths):
                            clip = ImageClip(img_path).with_duration(time_per_image).resized(TARGET_RESOLUTION)
                            if i > 0:
                                clip = clip.with_effects([vfx.CrossFadeIn(1.0)])
                            image_clips.append(clip)
                        bg_clip = concatenate_videoclips(image_clips, padding=-1.0, method="compose")
                    else:
                        bg_clip = ImageClip(asset_img_paths[0]).with_duration(audio_duration).resized(TARGET_RESOLUTION)

                bg_clip = bg_clip.with_audio(final_audio)
                final_clips = [bg_clip]

        elif mode == 4:
            m = re.search(r'_(\d+)$', basename)
            news_id = m.group(1) if m else None

            log(f"  🎨 使用客製化模式處理影片：{basename}")

            # --- 搜尋影片素材 ---
            asset_video_paths = []
            if custom_video == 1 and news_id:
                for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                    pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                    asset_video_paths.extend(glob.glob(pattern))

                if not asset_video_paths:
                    for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                        test_path = os.path.join("assets", f"ID{news_id}{ext}")
                        if os.path.exists(test_path):
                            asset_video_paths = [test_path]
                            break

                asset_video_paths = sorted(asset_video_paths, key=extract_file_index)

            # --- 準備影片底圖 ---
            bg_video_clip = None
            if asset_video_paths:
                video_clips = []
                for v_p in asset_video_paths:
                    try:
                        vc = VideoFileClip(v_p).without_audio().resized(TARGET_RESOLUTION)
                        video_clips.append(vc)
                    except Exception:
                        pass
                if video_clips:
                    bg_video_clip = concatenate_videoclips(video_clips, method="compose")

            # --- 準備圖片序列 ---
            img_clip_list = []
            if custom_image == 1 and news_id:
                asset_img_paths = []
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                    asset_img_paths.extend(glob.glob(pattern))

                if not asset_img_paths:
                    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                        test_path = os.path.join("assets", f"ID{news_id}{ext}")
                        if os.path.exists(test_path):
                            asset_img_paths = [test_path]
                            break

                if asset_img_paths:
                    img_clip_list = sorted(asset_img_paths, key=extract_file_index)
            elif custom_image == 2:
                pattern = os.path.join(IMAGES_DIR, f"{basename}_*.jpg")
                mod_imgs = glob.glob(pattern)
                if mod_imgs:
                    img_clip_list = sorted(mod_imgs, key=extract_file_index)
                else:
                    log(f"  ⚠️ 無法找到模組生成圖片 {pattern}")

            # --- 檢查素材音樂是否存在 ---
            bgm_path = None
            if custom_music == 1 and news_id:
                asset_mp3 = os.path.join("assets", f"ID{news_id}.mp3")
                if os.path.exists(asset_mp3):
                    bgm_path = asset_mp3
                else:
                    log(f"  ⚠️ 無法找到素材音樂 {asset_mp3}")

            # --- 組合影像底圖 ---
            if bg_video_clip is not None:
                if len(img_clip_list) > 0:
                    # 有影片 + 有圖片 => 影片播到最後5秒接圖片
                    loop_dur = max(0, audio_duration - 5)
                    bg_video_looped = bg_video_clip.with_effects([vfx.Loop(duration=loop_dur)])

                    target_img = img_clip_list[-1]
                    bg_img_clip = ImageClip(target_img).with_duration(5).resized(TARGET_RESOLUTION).with_effects([vfx.CrossFadeIn(1.0)])

                    bg_clip = concatenate_videoclips([bg_video_looped, bg_img_clip], padding=-1.0, method="compose")
                else:
                    # 只有影片 => Loop播滿
                    bg_clip = bg_video_clip.with_effects([vfx.Loop(duration=audio_duration)])
            elif len(img_clip_list) > 0:
                # 只有圖片 => 交給 ffmpeg 快速合成 (均分時長 + xfade 交叉淡入)
                slideshow_imgs = img_clip_list
                slideshow_bgm = bgm_path
            else:
                # 完全沒畫面，給黑屏
                black_frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
                bg_clip = ImageClip(black_frame).with_duration(audio_duration)

            # --- 合聲音樂 (MoviePy 路徑才需要，ffmpeg 路徑已在合成時混音) ---
            if slideshow_imgs is None:
                final_audio = audio_clip
                if bgm_path:
                    bgm_clip = AudioFileClip(bgm_path)
                    if bgm_clip.duration is not None and bgm_clip.duration < audio_duration:
                        bgm_clip = bgm_clip.with_effects([
                            afx.AudioLoop(duration=audio_duration),
                            afx.MultiplyVolume(config.BGM_VOLUME)
                        ])
                    else:
                        bgm_clip = bgm_clip.with_duration(audio_duration).with_effects([
                            afx.MultiplyVolume(config.BGM_VOLUME)
                        ])
                    final_audio = CompositeAudioClip([bgm_clip, audio_clip]).with_duration(audio_duration)

                bg_clip = bg_clip.with_audio(final_audio)
                final_clips = [bg_clip]

        # 4. 準備疊加素材 (頭像 + 字幕圖)。改由 ffmpeg overlay 疊加：
        #    MoviePy 只負責輸出背景 (合成負擔大減)，字幕圖仍用同一套 Pillow 邏輯繪製，畫面完全一致。
        overlay_dir = tempfile.mkdtemp(prefix="step6_overlay_")
        overlays = []

        add_avatar = False
        if mode in [1, 2]:
            add_avatar = has_avatar
        elif mode == 4:
            add_avatar = has_avatar and (custom_anchor == 1)

        if add_avatar:
            log("  🙎‍♀️ 疊加動態/虛擬圖相 (此版本為靜態圖片 sample.png)...")
            av_img = Image.open(AVATAR_PATH).convert("RGBA")
            av_h = round(av_img.height * 680 / av_img.width)
            av_img = av_img.resize((680, av_h), Image.LANCZOS)
            avatar_png = os.path.join(overlay_dir, "avatar.png")
            av_img.save(avatar_png)
            overlays.append({
                "path": avatar_png,
                "x": "main_w-overlay_w", "y": "main_h-overlay_h",
                "start": None, "end": None,
            })

        # 5. 處理動態字幕
        subs_json_path = os.path.join(VOICES_DIR, f"{basename}_subs.json")
        script_json_path = os.path.join(SCRIPTS_DIR, f"{basename}.json")

        if not os.path.exists(subs_json_path):
            log(f"  ⚠️ 找不到字幕時間軸檔：{subs_json_path}，本次影片將不會有字幕。")
        else:
            keywords = []
            if os.path.exists(script_json_path):
                with open(script_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    keywords = data.get("keywords", [])

            with open(subs_json_path, 'r', encoding='utf-8') as f:
                subs_data = json.load(f)

            log(f"  📝 處理中 {len(subs_data)} 句動態字幕...")

            for i, sub in enumerate(subs_data):
                sub_img = render_subtitle_image(sub["text"], keywords)
                sub_png = os.path.join(overlay_dir, f"sub_{i}.png")
                sub_img.save(sub_png)
                overlays.append({
                    "path": sub_png,
                    "x": "(main_w-overlay_w)/2", "y": "1350",
                    "start": sub["start"], "end": sub["start"] + sub["duration"],
                })

        # 6. 生成最終合成並輸出
        # 直接使用 _subtitled.mp4 名稱，不再產出無字幕版本
        out_path = os.path.join(VIDEOS_DIR, f"{basename}_subtitled.mp4")
        log(f"  🎥 開始寫入最終帶字幕影片: {out_path} ...\n")

        final_video = None
        temp_bg = os.path.join(overlay_dir, "bg_temp.mp4")
        stage1_ok = True

        if slideshow_imgs is not None:
            # 純圖片背景：ffmpeg 直接產生背景 (xfade 轉場 + 混音)，速度最快
            log("  🎞 階段 1/2：ffmpeg 產生背景影片 (圖片轉場 + 混音)...")
            stage1_ok = ffmpeg_slideshow_bg(
                slideshow_imgs, v_path, slideshow_bgm, audio_duration, temp_bg, log=log,
            )
        elif overlays:
            # 影片類背景：MoviePy 快速寫出高品質背景中繼檔 (時長對齊音訊，尾端不足處為黑幕)
            final_video = CompositeVideoClip(final_clips, size=TARGET_RESOLUTION).with_duration(audio_duration)
            log("  🎞 階段 1/2：輸出背景影片 (快速中繼檔)...")
            final_video.write_videofile(
                temp_bg, fps=FPS, codec="libx264", audio_codec="aac",
                preset="ultrafast", ffmpeg_params=["-crf", "14"], logger="bar",
            )

        if not stage1_ok:
            log(f"  ❌ 背景合成失敗，跳過 {basename} (耗時 {time.time() - item_start:.1f} 秒)")
            failed_count += 1
            audio_clip.close()
            shutil.rmtree(overlay_dir, ignore_errors=True)
            continue

        if slideshow_imgs is not None or overlays:
            log("  🎞 階段 2/2：ffmpeg 疊加頭像/字幕並編碼...")
            if not ffmpeg_overlay_encode(temp_bg, overlays, out_path, log=log):
                log(f"  ❌ 最終編碼失敗，跳過 {basename} (耗時 {time.time() - item_start:.1f} 秒)")
                failed_count += 1
                if final_video:
                    final_video.close()
                audio_clip.close()
                shutil.rmtree(overlay_dir, ignore_errors=True)
                continue
        else:
            # 沒有任何疊加物 (無頭像也無字幕) 且非圖片背景：維持原本 MoviePy 直接輸出 + 編碼降級鏈
            final_video = CompositeVideoClip(final_clips, size=TARGET_RESOLUTION)
            success = False
            try:
                log("  ⚡ 嘗試使用 AMD GPU 硬體加速編碼 (AMF)...")
                final_video.write_videofile(out_path, fps=FPS, codec="h264_amf", audio_codec="aac", preset="balanced", logger="bar")
                success = True
            except Exception:
                log("  ⚠️ AMD AMF 不支援，嘗試下一項...")

            if not success:
                try:
                    log("  ⚡ 嘗試使用 Intel QuickSync (QSV) 硬體加速編碼...")
                    # QSV 使用 global_quality 來控制品質，20-25 為平衡點
                    final_video.write_videofile(
                        out_path,
                        fps=FPS,
                        codec="h264_qsv",
                        audio_codec="aac",
                        logger="bar",
                        ffmpeg_params=["-global_quality", "25"]
                    )
                    success = True
                except Exception:
                    log("  ⚠️ Intel QSV 不支援，切換至標準 CPU 模式...")

            if not success:
                log("  🐢 使用標準 CPU 模式進行編碼 (這可能需要較長時間)...")
                final_video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", logger="bar")

        # 7. 釋放記憶體與關閉所有檔案控制代碼，避免 WinError 6 錯誤
        log(f"  🧹 正在清理暫存資源...")

        # 刪除疊加素材與背景中繼檔
        shutil.rmtree(overlay_dir, ignore_errors=True)

        # 關閉最終組合影片 (純 ffmpeg 路徑不會建立 MoviePy 合成物件)
        if final_video:
            final_video.close()

        # 逐一關閉所有加入組合的片段 (包含字幕、頭像、背景)
        for clip in final_clips:
            try:
                clip.close()
            except Exception:
                pass

        # 關閉額外開啟的檔案
        if bgm_clip:
            try:
                bgm_clip.close()
            except Exception:
                pass
        if bg_video:
            try:
                bg_video.close()
            except Exception:
                pass

        # 關閉原始音檔
        audio_clip.close()

        # 如果有 concatenated 的背景，也嘗試釋放其內部的 clips
        if bg_clip:
            try:
                bg_clip.close()
            except Exception:
                pass

        # 強制進行垃圾回收，幫助 Windows 釋放 Handle
        import gc
        gc.collect()

        item_elapsed = time.time() - item_start
        log(f"  ⏱ {basename} 合成完畢，耗時 {item_elapsed:.1f} 秒")

        success_count += 1
        outputs.append(out_path)

    run_elapsed = time.time() - run_start
    log(f"\n🎉 所有影片合成暨字幕壓製完畢！總耗時 {run_elapsed:.1f} 秒 (成功 {success_count} 支，失敗 {failed_count} 支)")
    return {"success": success_count, "failed": failed_count, "outputs": outputs, "elapsed": run_elapsed}


def main():
    """CLI 互動版"""
    print("========================================")
    print("  🎬 AI 影片自動生成與字幕壓製中心")
    print("========================================")

    mode = 1
    custom_video = 0  # 0: 不增加, 1: 素材(去聲)
    custom_image = 0  # 0: 不增加, 1: 素材, 2: 模組生成
    custom_anchor = 0  # 0: 不加, 1: 加上
    custom_music = 0  # 0: 不增加, 1: 素材(降音)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--mode=2":
            mode = 2
        elif sys.argv[1] == "--mode=3":
            mode = 3
        elif sys.argv[1] == "--mode=4":
            mode = 4
    elif len(sys.argv) <= 1:
        print("\n請選擇影片製作模式：")
        print("1: 原模式 (自動分配生成的圖片和配音製作)")
        print("2: 素材模式 (從 assets 資料夾找取同新聞ID的素材製作影片)")
        print("3: 去主播素材模式 (素材模式，但不疊加 sample.png)")
        print("4: 客製化模式 (自由選擇各項來源)")
        ans = input("請選擇 (1, 2, 3 或 4，預設 1): ").strip()
        if ans == "2":
            mode = 2
        elif ans == "3":
            mode = 3
        elif ans == "4":
            mode = 4
            print("\n【客製化模式設定】")
            print("▶ 影片來源：")
            print("  1: 從素材資料夾 (去除本身聲音)")
            print("  0: 不增加影片")
            cv = input("請選擇 (預設 1): ").strip()
            custom_video = 0 if cv == "0" else 1

            print("\n▶ 圖片來源：")
            print("  1: 從素材資料夾")
            print("  2: 模組生成 (output_images)")
            print("  0: 不增加圖片")
            ci = input("請選擇 (預設 1): ").strip()
            custom_image = int(ci) if ci in ["0", "1", "2"] else 1

            print("\n▶ 主播圖片 (sample.png)：")
            print("  1: 加上")
            print("  0: 不加上")
            ca = input("請選擇 (預設 1): ").strip()
            custom_anchor = 0 if ca == "0" else 1

            print("\n▶ 音樂來源：")
            print("  1: 從素材資料夾 (降低音量作為 BGM)")
            print("  0: 不增加音樂")
            cm = input("請選擇 (預設 1): ").strip()
            custom_music = 0 if cm == "0" else 1

    run(mode=mode, custom_video=custom_video, custom_image=custom_image, custom_anchor=custom_anchor, custom_music=custom_music)


if __name__ == "__main__":
    main()
