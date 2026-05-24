#!/usr/bin/env python3
"""Build a 1080x1920 Instagram Reel for 大嵓埜 0528 post.

10 shots, ~3.2s each + 0.4s crossfade => ~28.4s total.
Each shot: blurred background + scaled foreground + slow Ken Burns zoom + JP telop.
"""
import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT = "/tmp/jpmincho.ttf"  # IPAMincho — elegant ryōtei feel
W, H = 1080, 1920
FPS = 30
CLIP_SEC = 3.2
CLIP_FRAMES = int(CLIP_SEC * FPS)  # 96
XFADE = 0.4
OUT = ROOT / "0528_okurano_reel.mp4"

# (image filename, telop)
SHOTS = [
    ("お部屋_玄_kuro_0001.jpg", "大切な席に、ふさわしい一室を。"),
    ("イメージ_内観0002.jpg",   "完全個室「玄 ‐ KURO ‐」"),
    ("お部屋_玄_kuro_0004.jpg", "襖で隔てた、独立した一室"),
    ("お部屋_玄_kuro_0007.jpg", "落ち着いた設え、品の良い灯り"),
    ("お部屋_玄_kuro_0014.jpg", "席の余白に、ゆとりを"),
    ("イメージ_内観0001.jpg",   "人数・用途で選べる、安心感"),
    ("イメージ_季節のあしらい0008.jpg", "梅雨入り前、紫陽花のいろどり"),
    ("イメージ_季節のあしらい0001.jpg", "床の間に、季節の生花"),
    ("イメージ_調理0043.jpg",   "職人の手仕事を、一品ずつ"),
    ("コース全体0022.jpg",      "接待・顔合わせのお席に｜大嵓埜"),
]


def esc_drawtext(s: str) -> str:
    # Escape characters that have meaning in drawtext text= value
    return (
        s.replace("\\", "\\\\")
         .replace(":", "\\:")
         .replace("'", "\\'")
         .replace(",", "\\,")
    )


def build_clip(idx: int, image: str, telop: str) -> Path:
    out = ROOT / f"_clip_{idx:02d}.mp4"
    telop_esc = esc_drawtext(telop)

    # zoom from 1.00 to ~1.06 over the clip duration
    zoom_expr = f"min(1.0+0.0007*in\\,1.06)"

    vf = (
        f"[0:v]scale=2400:-2,setsar=1,split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=24:1,eq=brightness=-0.20:saturation=0.65[bgb];"
        f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2[comp];"
        f"[comp]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}[zp];"
        # subtle dark gradient strip at bottom for telop legibility
        f"color=c=black@0.55:s={W}x260:d={CLIP_SEC}:r={FPS}[strip];"
        f"[zp][strip]overlay=0:{H-300}:format=auto[withstrip];"
        f"[withstrip]drawtext=fontfile={FONT}:text='{telop_esc}':"
        f"x=(w-text_w)/2:y={H-220}:fontsize=58:fontcolor=white:"
        f"borderw=2:bordercolor=black@0.75:line_spacing=14[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(CLIP_SEC),
        "-i", str(ROOT / image),
        "-filter_complex", vf,
        "-map", "[v]",
        "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart",
        str(out),
    ]
    print("→", " ".join(shlex.quote(c) for c in cmd[:6]), "...", out.name)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-3000:])
        raise SystemExit(f"ffmpeg failed for clip {idx}")
    return out


def concat_with_xfade(clips: list[Path]) -> None:
    # Build a chained xfade filtergraph
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]

    # Each clip is CLIP_SEC long. Crossfade XFADE seconds.
    # Offset[i] for joining clip i+1 to running = (i+1)*CLIP_SEC - (i+1)*XFADE
    # i.e. running_duration so far - XFADE
    parts = []
    last_label = "[0:v]"
    cumulative = CLIP_SEC  # duration of running so far
    for i in range(1, len(clips)):
        offset = cumulative - XFADE
        out_label = f"[v{i}]"
        parts.append(
            f"{last_label}[{i}:v]xfade=transition=fade:"
            f"duration={XFADE}:offset={offset:.3f}{out_label}"
        )
        last_label = out_label
        cumulative = cumulative + CLIP_SEC - XFADE

    filtergraph = ";".join(parts)
    print(f"Total reel duration: ~{cumulative:.2f}s")

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filtergraph,
        "-map", last_label,
        "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart",
        str(OUT),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-4000:])
        raise SystemExit("concat ffmpeg failed")
    print(f"✓ wrote {OUT}")


def main() -> None:
    clips: list[Path] = []
    for idx, (image, telop) in enumerate(SHOTS, start=1):
        if not (ROOT / image).exists():
            raise SystemExit(f"missing: {image}")
        clips.append(build_clip(idx, image, telop))
    concat_with_xfade(clips)


if __name__ == "__main__":
    main()
