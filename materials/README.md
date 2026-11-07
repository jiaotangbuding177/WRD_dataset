# 本轮实际技能制作输入

原会话、提示及冻结清单已直接放入本分支，clone 后即可执行 `stage --materials materials`。

| 文件 | 字节 | SHA256 |
|---|---:|---|
| `DEV_MATERIALS.json` | 10305 | `92c05839fc9bdc755117cdd00feda549ccd9ee1c95a7cce06ac9aa2379ee04b7` |
| `conv_497a2363eddb/producer/workspace/inputs/source.json` | 62997 | `adf496e34aa109450dcf4c1ebf6b9d38f7e94980664660b36cd8e60e4d8dd09c` |
| `conv_497a2363eddb/producer/prompt.txt` | 1579 | `7f0cc85c7f81df3995a771c00c3a2d1fb72a3e8049debc897e75b51e7a212aad` |

制作范围为 EDU 文本来源的对外短文工作流，完整26消息/13轮，结构化附件为空；未提供课程和私有资料不纳入制作。该来源在原冻结中为DEV；原226与正式TEST继续隔离。

清单保留原字节以维持固定SHA，因此仍含历史消费题元数据及旧本机审计路径。当前stage只读取maker源与提示，不读取消费文件或旧路径。另3个原冻结来源的缺件状态保留，本轮不投递；不将候选清单当作已具备的材料。

本轮是同一来源四臂制作。资源试跑和修订发生在制作过程中；独立业务消费延期。
