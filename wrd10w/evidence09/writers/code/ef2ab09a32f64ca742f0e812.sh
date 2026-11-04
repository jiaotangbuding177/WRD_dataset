#!/bin/bash
set -u
T=/opt/eval-adapter/ecnu_tools.py
A=/workspace/project/audio
python $T speech --text "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！" --output $A/n1.wav && echo OK1
python $T speech --text "场地分成两半，中间是安全区。每人有一把弓和五支安全泡沫箭，被射中就出局，但接住箭可以复活队友！" --output $A/n2.wav && echo OK2
python $T speech --text "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！" --output $A/n3.wav && echo OK3
python $T speech --text "躲！射！接箭复活！利用掩体走位，团队配合最重要！" --output $A/n4.wav && echo OK4
python $T speech --text "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！" --output $A/n5.wav && echo OK5
python $T speech --text "最后关头，一箭定胜负！团队合作才是王道！" --output $A/n6.wav && echo OK6
python $T speech --text "全程佩戴护目镜，安全第一，享受快乐对战！" --output $A/n7.wav && echo OK7
python $T speech --text "想玩吗？组队来一场吧！就来上海诚弓射箭馆！" --output $A/n8.wav && echo OK8
echo DONE
