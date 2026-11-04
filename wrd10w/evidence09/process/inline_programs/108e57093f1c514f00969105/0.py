import subprocess, json
lines = [
 ("tts01.wav", "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！"),
 ("tts02.wav", "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！"),
 ("tts03.wav", "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！"),
 ("tts04.wav", "躲！射！接箭复活！利用掩体走位，团队配合最重要！"),
 ("tts05.wav", "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！"),
 ("tts06.wav", "最后关头，一箭定胜负！团队合作才是王道！"),
 ("tts07.wav", "全程佩戴面罩，安全第一，享受快乐对战！"),
 ("tts08.wav", "想玩吗？组队来一场吧！"),
]
for fn, text in lines:
    r = subprocess.run(["python", "/opt/eval-adapter/ecnu_tools.py", "speech", "--text", text, "--output", "tts/"+fn], capture_output=True, text=True)
    print(fn, r.returncode, (r.stdout or r.stderr)[-200:])
