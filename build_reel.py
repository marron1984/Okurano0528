#!/usr/bin/env python3
"""Build a 1080x1920 Instagram Reel for 大嵓埜 0528 post.

- Top strip on every shot: brand "北新地･懐石料理 大嵓埜"
- Bottom strip per shot: scene telop (or rich info card on the last shot)
- Slow Ken Burns zoom + blurred background composite
- Crossfade transitions between clips
"""
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT = "/tmp/jpserif.ttf"  # Noto Serif CJK JP Bold — refined Mincho
W, H = 1080, 1920
FPS = 30
XFADE = 0.4
OUT = ROOT / "0528_okurano_reel.mp4"

BRAND = "北新地・懐石料理  大嵓埜"
INFO_LINES = [
    # (text, font_size, y_from_top_of_bottom_strip, dim_white?)
    ("接待・顔合わせのお席に",   62, 30,  False),  # headline
    ("大阪市北区曽根崎新地1-3-23  FOODEARビル3F", 36, 130, True),
    ("TEL  06-6341-3535",        38, 195, True),
    ("昼 11:30〜  /  夜 17:30〜22:00", 36, 260, True),
    ("日祝休  ※6月以降は日祝も昼15時迄営業", 32, 325, True),
]
INFO_STRIP_H = 410  # bottom strip height for the rich info card
NORMAL_STRIP_H = 220

# (image filename, telop, clip_seconds)
SHOTS = [
    ("お部屋_玄_kuro_0001.jpg", "大切な席に、ふさわしい一室を。", 3.2),
    ("イメージ_内観0002.jpg",   "完全個室「玄 ‐ KURO ‐」",       3.2),
    ("お部屋_玄_kuro_0004.jpg", "襖で隔てた、独立した一室",       3.2),
    ("お部屋_玄_kuro_0007.jpg", "落ち着いた設え、品の良い灯り",   3.2),
    ("お部屋_玄_kuro_0014.jpg", "席の余白に、ゆとりを",           3.2),
    ("イメージ_内観0001.jpg",   "人数・用途で選べる、安心感",     3.2),
    ("イメージ_季節のあしらい0008.jpg", "梅雨入り前、紫陽花のいろどり", 3.2),
    ("イメージ_季節のあしらい0001.jpg", "玄関に、季節のあしらい",     3.2),
    ("イメージ_調理0043.jpg",   "職人の手仕事を、一品ずつ",       3.2),
    ("コース全体0022.jpg",      None,                              5.0),  # info card
]

TOP_STRIP_H = 110


def esc(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
         .replace(":", "\\:")
         .replace("'", "\\'")
         .replace(",", "\\,")
    )


def build_clip(idx: int, image: str, telop: str | None, dur: float) -> Path:
    out = ROOT / f"_clip_{idx:02d}.mp4"
    frames = int(dur * FPS)
    zoom_expr = f"min(1.0+0.0006*in\\,1.06)"

    # Common: blurred bg + foreground fit + zoom
    vf_parts = [
        f"[0:v]scale=2400:-2,setsar=1,split=2[bg][fg]",
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=24:1,eq=brightness=-0.22:saturation=0.6[bgb]",
        f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs]",
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2[comp]",
        f"[comp]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}[zp]",
        # Top strip + brand line
        f"color=c=black@0.48:s={W}x{TOP_STRIP_H}:d={dur}:r={FPS}[top]",
        f"[zp][top]overlay=0:0:format=auto[withtop]",
        f"[withtop]drawtext=fontfile={FONT}:text='{esc(BRAND)}':"
        f"x=(w-text_w)/2:y={(TOP_STRIP_H-44)//2}:fontsize=44:fontcolor=white@0.95:"
        f"borderw=2:bordercolor=black@0.6[topdone]",
    ]

    if telop is None:
        # Final shot: full info card
        strip_h = INFO_STRIP_H
        vf_parts.append(
            f"color=c=black@0.62:s={W}x{strip_h}:d={dur}:r={FPS}[bot]"
        )
        vf_parts.append(
            f"[topdone][bot]overlay=0:{H-strip_h}:format=auto[withbot]"
        )
        # Stack drawtext for each line
        current = "withbot"
        for li, (text, fs, yoff, dim) in enumerate(INFO_LINES):
            label = f"l{li}"
            color = "white@0.85" if dim else "white"
            border_alpha = "0.55" if dim else "0.7"
            y = H - strip_h + yoff
            vf_parts.append(
                f"[{current}]drawtext=fontfile={FONT}:text='{esc(text)}':"
                f"x=(w-text_w)/2:y={y}:fontsize={fs}:fontcolor={color}:"
                f"borderw=2:bordercolor=black@{border_alpha}[{label}]"
            )
            current = label
        vf_parts[-1] = vf_parts[-1].rsplit("[", 1)[0] + "[v]"
    else:
        strip_h = NORMAL_STRIP_H
        vf_parts.append(
            f"color=c=black@0.55:s={W}x{strip_h}:d={dur}:r={FPS}[bot]"
        )
        vf_parts.append(
            f"[topdone][bot]overlay=0:{H-strip_h}:format=auto[withbot]"
        )
        vf_parts.append(
            f"[withbot]drawtext=fontfile={FONT}:text='{esc(telop)}':"
            f"x=(w-text_w)/2:y={H-strip_h+(strip_h-58)//2}:fontsize=58:"
            f"fontcolor=white:borderw=2:bordercolor=black@0.75[v]"
        )

    vf = ";".join(vf_parts)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(dur),
        "-i", str(ROOT / image),
        "-filter_complex", vf,
        "-map", "[v]",
        "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart",
        str(out),
    ]
    print(f"→ clip {idx:02d} ({dur}s)", image)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-3000:])
        raise SystemExit(f"ffmpeg failed for clip {idx}")
    return out


def concat_with_xfade(clips_and_durs: list[tuple[Path, float]]) -> None:
    inputs: list[str] = []
    for c, _ in clips_and_durs:
        inputs += ["-i", str(c)]

    parts = []
    last_label = "[0:v]"
    cumulative = clips_and_durs[0][1]
    for i in range(1, len(clips_and_durs)):
        offset = cumulative - XFADE
        out_label = f"[v{i}]"
        parts.append(
            f"{last_label}[{i}:v]xfade=transition=fade:"
            f"duration={XFADE}:offset={offset:.3f}{out_label}"
        )
        last_label = out_label
        cumulative = cumulative + clips_and_durs[i][1] - XFADE

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
    pairs: list[tuple[Path, float]] = []
    for idx, (image, telop, dur) in enumerate(SHOTS, start=1):
        if not (ROOT / image).exists():
            raise SystemExit(f"missing: {image}")
        clip = build_clip(idx, image, telop, dur)
        pairs.append((clip, dur))
    concat_with_xfade(pairs)


if __name__ == "__main__":
    main()
