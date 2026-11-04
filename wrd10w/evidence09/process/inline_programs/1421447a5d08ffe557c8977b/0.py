import asyncio, edge_tts, sys

NARS = [
 (1, "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！"),
 (2, "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！"),
 (3, "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！"),
 (4, "躲！射！接箭复活！利用掩体走位，团队配合最重要！"),
 (5, "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！"),
 (6, "最后关头，一箭定胜负！团队合作才是王道！"),
 (7, "全程佩戴面罩，安全第一，享受快乐对战！"),
 (8, "想玩吗？组队来一场吧！"),
]

async def gen(n, text):
    c = edge_tts.Communicate(text, voice="zh-CN-YunjianNeural", rate="+8%", volume="+10%")
    await c.save(f"/workspace/tmp/archery/nar{n}.mp3")
    print(f"nar{n} OK", flush=True)

async def main():
    for n, t in NARS:
        for attempt in range(3):
            try:
                await gen(n, t); break
            except Exception as e:
                print(f"nar{n} attempt{attempt}: {e}", flush=True)
                await asyncio.sleep(2)
        else:
            print(f"nar{n} FAILED", flush=True); sys.exit(1)

asyncio.run(main())
