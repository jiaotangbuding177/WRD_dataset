#!/bin/bash
set -u
LOG=/workspace/tmp/gen_assets.log
: > $LOG
IMG_OUT=/workspace/outputs/frames
AUD_OUT=/workspace/outputs/audio

gen_image() {
  local name=$1; shift
  if [ -s "$IMG_OUT/$name.png" ]; then echo "[skip] $name" >> $LOG; return 0; fi
  python /opt/eval-adapter/ecnu_tools.py image --text "$1" --output "$IMG_OUT/$name.png" >> $LOG 2>&1 \
    && echo "[ok] $name" >> $LOG || echo "[FAIL] $name" >> $LOG
}

gen_speech() {
  local name=$1; shift
  if [ -s "$AUD_OUT/$name.wav" ]; then echo "[skip] $name" >> $LOG; return 0; fi
  python /opt/eval-adapter/ecnu_tools.py speech --text "$1" --output "$AUD_OUT/$name.wav" >> $LOG 2>&1 \
    && echo "[ok] $name" >> $LOG || echo "[FAIL] $name" >> $LOG
}

# images (12)
gen_image 01a "卡通Q版游戏宣传画，明亮的室内运动场，红队和蓝队Q版卡通小人物各五人分列左右对峙，中间安全中立区，充气障碍物和箭靶，色彩鲜艳，红蓝对立配色，广角构图，游戏宣传海报风格"
gen_image 01b "卡通Q版特写，反曲弓拉弦特写，一支带泡沫箭头的箭飞出，带动态速度线轨迹，明亮色彩，红蓝配色，游戏宣传片风格"
gen_image 02a "卡通游戏俯视图，篮球场一半大小的射箭竞技场地，左半边红队区域，右半边蓝队区域，中间黄色安全中立区，充气障碍物和箭靶，两侧卡通小人持弓，明亮色彩，游戏地图风格"
gen_image 03a "卡通Q版，红蓝两队卡通小人物从两侧冲刺奔向场地中间抢箭，动感速度线，尘土飞扬，动态动作，明亮红蓝配色，游戏宣传风格"
gen_image 04a "卡通Q版，红队卡通人物躲在充气障碍物后拉弓射箭，蓝队人物侧身闪避，动态动作，速度线，明亮色彩，游戏宣传风格"
gen_image 04b "卡通Q版，蓝队人物精彩接住一支飞来的泡沫箭，金色光芒四射，身后倒地队友被光芒笼罩重新站起复活，可爱风格，非血腥，游戏宣传风格"
gen_image 04c "卡通Q版，一支泡沫箭击中红队人物胸口，人物夸张可爱地向后倒地出局，头顶冒出星星和OUT字样气泡，可爱Q版卡通效果，非血腥，明亮色彩"
gen_image 05a "卡通Q版，多支箭矢飞向对方后场一排三个箭靶，箭靶被击中爆出星星爆炸特效并掉落，动态构图，速度线，明亮色彩，游戏宣传风格"
gen_image 06a "卡通Q版，慢动作史诗对决，两名卡通人物在场地中央对射，两支箭在空中交错飞过，电影感光效，戏剧性构图，红蓝对立配色，游戏宣传风格"
gen_image 06b "卡通Q版，最后一箭命中箭靶，靶子碎裂四溅，红队全队卡通人物跳跃欢呼庆祝，彩带和烟花特效，胜利氛围，明亮色彩"
gen_image 07a "卡通Q版装备特写，防护面罩护臂反曲弓和泡沫箭整齐摆放，旁边一个竖大拇指的笑脸Q版卡通人物，明亮温馨色彩，简洁背景"
gen_image 08a "卡通Q版，红队和蓝队卡通小人物开心握手合影，室内运动场背景，彩带飘落，明亮欢快色彩，游戏宣传结尾画面风格"

# narration (8)
gen_speech n01 "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！"
gen_speech n02 "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！"
gen_speech n03 "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！"
gen_speech n04 "躲！射！接箭复活！利用掩体走位，团队配合最重要！"
gen_speech n05 "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！"
gen_speech n06 "最后关头，一箭定胜负！团队合作才是王道！"
gen_speech n07 "全程佩戴面罩，安全第一，享受快乐对战！"
gen_speech n08 "想玩吗？组队来一场吧！"

echo "DONE" >> $LOG
echo "assets done"