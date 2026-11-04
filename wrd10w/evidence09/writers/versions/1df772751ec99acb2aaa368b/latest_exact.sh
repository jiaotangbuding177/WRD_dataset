#!/bin/bash
# Generate 8 photorealistic frames for gongfangjian video (user rejected anime version)
set -u
IMG=/opt/eval-adapter/ecnu_tools.py
D=/workspace/project/images

STYLE="真实摄影风格，photorealistic sports photography，真实室内射箭运动馆场地（约半个足球场大小），真实光线，真实人物皮肤与表情，年轻中国人男女混合穿运动服戴护目镜护臂，专用美猎弓箭杆真实箭头为圆形泡沫安全头，红队蓝队颜色对立明亮色彩，动态运动跟拍感，类似游戏宣传片画面，画面禁止卡通动漫渲染禁止3D玩偶感。16:9宽屏横构图。"

python $IMG --text "$STYLE 广阔全景：两队各五名玩家在场地两端对峙，中间隔安全中立区黄色边界线，充气掩体分布在两侧，一名玩家拉弦瞄准特写在前景，箭矢飞出带动态轨迹。" --output $D/shot1.png && echo OK1
python $IMG --text "$STYLE 俯视航拍视角：整个场地划分图，左半场地面红色区域红线，右半场蓝色区域蓝线，中间黄色安全带，两侧各放三个圆形箭靶和充气掩体，场边队员穿戴护具持弓准备。" --output $D/shot2.png && echo OK2
python $IMG --text "$STYLE 开局冲刺瞬间：十名年轻玩家从两侧冲向中线抢箭，动作大幅动态模糊，箭支散放在中线地面上，红蓝运动服交错，低角度跟踪镜头，紧张刺激氛围。" --output $D/shot3.png && echo OK3
python $IMG --text "$STYLE 激烈攻防：红队玩家躲在红色充气掩体后侧身射箭，蓝队玩家侧身闪避来箭，另一名蓝队玩家伸手精彩接住一支泡沫头箭，空中带轻微光效，两米外红队玩家被击中后单膝跪地举手示意出局，无血腥。" --output $D/shot4.png && echo OK4
python $IMG --text "$STYLE 箭靶攻击：多支泡沫头箭精准射向蓝队后场的三个立式圆形箭靶，其中一个靶被击中正在掉落，箭矢空中轨迹清晰，动态特写。" --output $D/shot5.png && echo OK5
python $IMG --text "$STYLE 高潮决胜慢动作：最后一名红队玩家与最后一名蓝队玩家对射，两支箭在空中交错飞过，浅景深慢镜头质感，背景队友紧张注视，一箭命中最后一个靶子瞬间。" --output $D/shot6.png && echo OK6
python $IMG --text "$STYLE 安全装备特写：一名笑容灿烂的年轻女玩家正面特写，清晰展示护目镜和护臂，手持美猎弓，背景虚化的射箭馆，明亮温暖光线。" --output $D/shot7.png && echo OK7
python $IMG --text "$STYLE 结束画面：红队蓝队两队十名玩家在场地中央开心合影，两队队长握手，众人竖大拇指，背后是箭靶和掩体，明亮欢快氛围。" --output $D/shot8.png && echo OK8
echo DONE