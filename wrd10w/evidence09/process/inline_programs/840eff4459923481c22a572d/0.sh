#!/bin/bash
set -e
TTS() {
  python /opt/eval-adapter/ecnu_tools.py speech --text "$1" --output "/workspace/tmp/archery/nar$2.wav" && echo "nar$2 OK" || echo "nar$2 FAILED"
}
TTS "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！" 1
TTS "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！" 2
TTS "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！" 3
TTS "躲！射！接箭复活！利用掩体走位，团队配合最重要！" 4
TTS "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！" 5
TTS "最后关头，一箭定胜负！团队合作才是王道！" 6
TTS "全程佩戴面罩，安全第一，享受快乐对战！" 7
TTS "想玩吗？组队来一场吧！" 8
