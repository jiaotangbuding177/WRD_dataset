import importlib.util, os
spec = importlib.util.spec_from_file_location("r", "render.py")
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
os.makedirs("/workspace/tmp/smoke", exist_ok=True)
for i, (fn, dur) in enumerate(zip(r.SCENES, r.SCENE_DUR), 1):
    for frac in (0.25, 0.7):
        img = fn(dur*frac, dur)
        img.save(f"/workspace/tmp/smoke/s{i}_{int(frac*100)}.png")
    print("scene", i, "ok", img.size)
