# 完整演化集的真实技能制作入口

本目录只实现材料投递、固定原生OpenClaw启动、共享预算、任务级分发和证据回收；没有自建Agent循环、工具参数修补或宿主代写skills。不会因SKILL.md存在或returncode为0自动判合格。当前实际推理和训练均为0。

工具主机使用固定amd64 OpenClaw，Spark ARM64只运行vLLM。先按主计划恢复完整`corpus/`并核完整清单。以下从`execution/`执行，`../corpus`代表同级恢复目录；如使用其他位置，仅替换`--corpus`和`--selection`绝对路径。Windows将`python3`换成`python`即可，原生容器仍需同事现有的Spark模型连通。

## 只验材料，不跑模型

```bash
python3 local/run_corpus58.py verify --corpus ../corpus --source conv_1695d8fd2aca
python3 local/run_corpus58.py prepare --corpus ../corpus --source conv_1695d8fd2aca --arm wrd58-14b-241 --attempt 1 --out-dir runs
```

prepare会逐SHA核完整会话、资源和索引，真实初始化普通Git工作区并创建初始提交，目标目录为该仓库自有源码`outputs/skill/`。它不会预写SKILL.md。原生consumer直接bind整个workspace到容器`/workspace`，不会过滤`.git`。stage回执保存Git HEAD/objects、真实bind声明和资源SHA；实际容器执行证据在colleague run后产生，CPU检查不冒充运行实测。

重复编号不覆盖。producer可使用已prepare但未dispatch的同一编号；实际派发过的编号必须保全，不自动重新运行。新编号用于明确授权的新attempt，费用独立保留。

## Spark启动一个尺寸

Spark在本目录使用已有v2权重与基座缓存运行：

```bash
mkdir -p receipts
bash spark/serve_wrd58.sh 8b yarn128 0,241 2>&1 | tee receipts/serve_8b_128k.log
```

保留终端。完成8B组后才停止该服务，按同样命令切`14b`。实际模型revision、adapter SHA、vLLM镜像摘要、YaRN128K和引擎seed58进入启动日志；显式设置`VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`。引擎seed不是逐请求seed：固定native包装没有转发request.seed，不宣称逐请求随机数严格配对。

将真实启动日志复制到工具主机`receipts/`。不再跑26、填充OK题或玩具技能烟测。

## 一条命令执行当前尺寸的首3来源

工具主机：

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase first3 --size 8b --startup-log receipts/serve_8b_128k.log --runs runs
```

完成该6次原生制作，再切14B服务并带回日志，执行：

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase first3 --size 14b --startup-log receipts/serve_14b_128k.log --runs runs
```

每任务共同预算为24次HTTP、单回复8192、累计completion32768（含reasoning）、3600秒，先触顶即止。原生finalization、重试和同端点子会话都进同一账。为保留原始HTTP body，admission按8192保守预留，剩余额度不足整个请求上限会拒绝，不通过改写请求凑满额度。未知usage保留预留，和实测明确分账。

四臂首3共12会话结束后生成审核模板：

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase review-template --runs runs --out prefix_review.json
```

审核人依据真实内容、来源、资源运行与自测填写12行。每行`review_status=CONTENT_REVIEWED`、`qualified`、`qualification_count`、`review_evidence`必须对应`producer_result_sha256`；未评估或技术失败不能填模型质量0。实际资源自测与完整WRD效能取舍分别报告。独立业务消费不在本轮启动。

## 有审核证据后执行剩余9来源

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase remaining --size 14b --startup-log receipts/serve_14b_128k.log --runs runs --review prefix_review.json
```

切换8B并更新日志后：

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase remaining --size 8b --startup-log receipts/serve_8b_128k.log --runs runs --review prefix_review.json
```

两241在首3来源都0合格时，入口返回`STOP_PREFIX_BOTH_FINAL_MODELS_ZERO`和退出码3，余9不派发。缺少四臂完整内容审核时拒绝推进。失败任务单列，保全旧结果；同源0/241顺序预先交替，不根据结果换题。

## 单个明确任务的入口

```bash
python3 local/run_corpus58.py producer --corpus ../corpus --source conv_1695d8fd2aca --arm wrd58-14b-241 --attempt 1 --out-dir runs --startup-log receipts/serve_14b_128k.log
```

默认只允许case明确`effect_evaluation_allowed=true`。全1107是素材档案，不能全当未见测试；需要运行已见材料诊断时显式`--allow-seen-diagnostic`并标为SEEN，不改变训练或评测边界。

## 原样带回所有实际产物和记录

```bash
python3 local/package_corpus_return58.py --runs runs --selection ../corpus/EFFECT_FREEZE12.json --receipts receipts --out wrd58-full-maker-return.zip
```

回传ZIP、同名`.zip.sha256`、已填写的`prefix_review.json`。ZIP包含每来源/arm/attempt完整workspace（包括实际skill、版本、自测、Git证据）、原始HTTP/SSE、原生会话、所有失败/预算、实际启动日志及逐文件SHA。打包不运行模型、不补造文件、不把进程退出0当内容通过。

## 已完成CPU核验

`check_corpus_execution58.py`完成12项本机接口检查，含真实隔离Git初始化、固定native挂载声明、资源篡改拒绝、端口独占、原始请求/SSE透传、累计预算与全四臂审核止损。另已用实际冻结12来源×四臂完成48次CPU prepare/verify，全部资源与Git证明通过；没有启动容器或真实模型。CPU测试里的本地假上游不记实际模型能力或新训练数据。
