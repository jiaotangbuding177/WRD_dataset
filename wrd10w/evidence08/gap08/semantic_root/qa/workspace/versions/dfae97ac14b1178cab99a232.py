#!/usr/bin/env python3
"""Compose Archery Tag promo video from shot images + narration + overlays."""
import json, subprocess, os, sys

D = "/workspace/tmp/archery"
OUT = "/workspace/outputs"
os.makedirs(OUT, exist_ok=True)
FPS = 25
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# shot_no, scripted_dur, overlay png (or None), overlay position, motion style
SHOTS = [
    (1, 5,  "title1.png", "center",  "in"),
    (2, 10, None, None, "out"),
    (3, 5,  None, None, "pan"),
    (4, 15, None, None, "in"),
    (5, 10, None, None, "pan2"),
    (6, 10, "win.png",   "center",  "out"),
    (7, 5,  None, None, "in"),
    (8, 5,  "end.png",   "center",  "in"),
]

def dur_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])

def vf_motion(style, frames):
    # cover-scale to 1920x1080, upscale for zoom headroom, then ken-burns
    base = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,scale=2112:1188"
    cx = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if style == "in":
        z = f"z='1+0.10*on/{frames}'"
    elif style == "out":
        z = f"z='1.10-0.10*on/{frames}'"
    elif style == "pan":
        z = f"z='1.06':x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)'"
    else:  # pan2: right -> left
        z = f"z='1.06':x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)'"
    return f"{base},zoompan={z}:{cx}:d={frames}:s=1920x1080:fps={FPS}"

def overlay_chain(png, frames, idx):
    fade_start = 0.4
    fade_dur = 0.6
    f = (f"[{idx}:v]format=rgba,fade=t=in:st={fade_start}:d={fade_dur}:alpha=1"
         f",fade=t=out:st={frames/FPS-0.5}:d=0.5:alpha=1[t{idx}]")
    pos = "(W-w)/2:(H-h)/2"
    if png == "title1.png":
        pos = "(W-w)/2:H*0.62-h/2"
    return f, f"[vbase][t{idx}]overlay={pos}:enable='gte(t,{fade_start})'"

def build(shot_no, script_dur, png, pos, style):
    audio = f"{D}/nar{shot_no}.wav"
    img = f"{D}/shot{shot_no}.png"
    adur = dur_of(audio)
    dur = max(script_dur, adur + 1.4)
    dur = round(dur, 2)
    frames = int(dur * FPS)

    inputs = ["-loop", "1", "-framerate", str(FPS), "-i", img]
    filters = [f"[0:v]{vf_motion(style, frames)},format=yuv420p[vbase]"]
    maps = ["-map", "[v]", "-map", "[aout]"]
    nxt = 1
    if png:
        inputs += ["-loop", "1", "-i", f"{D}/{png}"]
        f, ov = overlay_chain(png, frames, nxt)
        filters.append(f)
        filters.append(ov)
        filters.append("[vbase]format=yuv420p[v]")
        maps[1] = "[v]"
        nxt += 1
    else:
        filters.append("[vbase]null[v]")
        maps[1] = "[v]"

    inputs += ["-i", audio]
    delay = 600
    a = (f"[{nxt}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
         f"adelay={delay}:all=1,apad,atrim=0:{dur},"
         f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur-0.35}:d=0.35[aout]")
    filters.append(a)

    out = f"{D}/clip{shot_no}.mp4"
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), *maps,
           "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
           "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"SHOT {shot_no} FAILED\n", r.stderr[-3000:]); sys.exit(1)
    print(f"clip{shot_no}: {dur}s (audio {adur:.1f}s)")
    return out

def main():
    clips = [build(*s) for s in SHOTS]
    lst = f"{D}/concat.txt"
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    final = f"{OUT}/攻防箭动画宣传视频.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", "-movflags", "+faststart", final],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("CONCAT FAILED\n", r.stderr[-2000:]); sys.exit(1)
    print("FINAL:", final, dur_of(final), "s")

main()
