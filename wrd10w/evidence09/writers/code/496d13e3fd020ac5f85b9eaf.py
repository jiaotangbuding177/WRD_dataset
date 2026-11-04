#!/usr/bin/env python3
"""Build per-shot video clips from generated frames + narration, per storyboard."""
import json, subprocess, sys, os, math

FPS = 25
W, H = 1280, 720
ROOT = "/workspace/outputs"
TMP = "/workspace/tmp/subclips"
os.makedirs(TMP, exist_ok=True)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise SystemExit(f"cmd failed: {' '.join(cmd[:6])}...")

def duration_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def fontfile():
    r = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans CJK SC"], capture_output=True, text=True)
    return r.stdout.strip()

FONT = fontfile()

def kenburns(img, dur, out, mode=0):
    """Animate a still image into a dur-seconds 1280x720 clip (zoom/pan variants)."""
    frames = int(round(dur * FPS))
    D = frames  # zoompan per-frame count
    if mode % 3 == 0:   # zoom in center
        z = f"1+0.14*on/{D-1}"
        x = "(iw-iw/zoom)/2"; y = "(ih-ih/zoom)/2"
    elif mode % 3 == 1: # zoom in toward left (action pull)
        z = f"1+0.18*on/{D-1}"
        x = "(iw-iw/zoom)/4"; y = "(ih-ih/zoom)/2"
    else:               # slow pan right
        z = "1.08"
        x = f"(iw-iw/zoom)*on/{D-1}"; y = "(ih-ih/zoom)/2"
    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
          f"crop={W*2}:{H*2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={D}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-t", f"{dur:.3f}",
         "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "19",
         "-an", out])

def text_filter(text, fontsize, y_expr, start, end):
    alpha = f"if(lt(t,{start}+0.5),0,if(lt(t,{start}+1.0),(t-{start}-0.5)/0.5,if(gt(t,{end}-0.6),max(0,({end}-t)/0.6),1)))"
    return (f"drawtext=fontfile={FONT}:text='{text}':fontsize={fontsize}:"
            f"fontcolor=white:borderw=5:bordercolor=0xE23A3A:shadowx=3:shadowy=3:"
            f"shadowcolor=black@0.6:x=(w-text_w)/2:y={y_expr}:alpha='{alpha}'")

def build_shot(shot):
    sid = shot["id"]
    imgs = [os.path.join(ROOT, "frames", f"{n}.png") for n in shot["images"]]
    for p in imgs:
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            raise SystemExit(f"missing frame: {p}")
    aud = os.path.join(ROOT, "audio", f"n{sid:02d}.wav")
    ndur = duration_of(aud) if os.path.isfile(aud) else 0.0
    dur = max(shot["dur"], ndur + 1.2)
    # split duration across images
    n = len(imgs)
    parts = [dur / n] * n
    # round to frames, fix rounding residue on last part
    pf = [int(round(p * FPS)) for p in parts]
    pf[-1] = int(round(dur * FPS)) - sum(pf[:-1])
    subs = []
    for i, (img, f) in enumerate(zip(imgs, pf)):
        out = os.path.join(TMP, f"s{sid}_{i}.mp4")
        kenburns(img, f / FPS, out, mode=i + sid)
        subs.append(out)
    # concat subclips (same codec/size) then overlays, fades, narration
    full = os.path.join(TMP, f"s{sid}_full.mp4")
    if len(subs) == 1:
        full_in = subs[0]
    else:
        lst = os.path.join(TMP, f"s{sid}.txt")
        with open(lst, "w") as fh:
            for s in subs:
                fh.write(f"file '{s}'\n")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", full])
        full_in = full
    filters = ["fade=t=in:st=0:d=0.3", f"fade=t=out:st={dur-0.35:.2f}:d=0.35"]
    t = shot.get("overlay", "")
    if t:
        if sid == 1:
            filters.append(text_filter(t, 96, "h*0.10", 0.2, dur))
        elif sid == 6:
            filters.append(text_filter(t, 130, "h*0.32", dur * 0.55, dur))
        elif sid == 7:
            filters.append(text_filter(t, 64, "h*0.08", 0.2, dur))
        elif sid == 8:
            filters.append(text_filter(t, 78, "h*0.76", 0.4, dur))
    out = os.path.join(ROOT, "clips", f"shot_{sid}.mp4")
    if ndur > 0:
        ac = (f"[1:a]adelay=400|400,apad[a];"
              f"[0:v]{','.join(filters)}[v];[v][a]vout")
        cmd = ["ffmpeg", "-y", "-i", full_in, "-i", aud,
               "-filter_complex", ac.replace("vout", "out"),
               "-map", "[out]", "-map", "[a]".replace("a", "v") if False else "[out]"],
        # simpler: map labels explicitly below
        cmd = ["ffmpeg", "-y", "-i", full_in, "-i", aud,
               "-filter_complex",
               f"[0:v]{','.join(filters)}[v];[1:a]adelay=400|400,apad[a]",
               "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
               "-c:v", "libx264", "-preset", "fast", "-crf", "19",
               "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
               "-movflags", "+faststart", out]
    else:
        cmd = ["ffmpeg", "-y", "-i", full_in,
               "-vf", ",".join(filters), "-t", f"{dur:.3f}",
               "-c:v", "libx264", "-preset", "fast", "-crf", "19",
               "-movflags", "+faststart", out]
    run(cmd)
    print(f"shot {sid}: dur={dur:.2f}s narration={ndur:.2f}s -> {out}")

def main():
    with open("/workspace/tmp/prompts.json") as f:
        shots = json.load(f)["shots"]
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for s in shots:
        if only and str(s["id"]) not in only:
            continue
        build_shot(s)

if __name__ == "__main__":
    main()
