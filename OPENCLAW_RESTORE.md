# 恢复 WRD58 固定 OpenClaw 环境

同事用一台 **x86_64 主机**运行 OpenClaw 原生容器。Spark 保留 **ARM64 vLLM** 和模型权重。让 x86 主机通过同事可用的私有链路访问 Spark 的模型接口。部署前在 x86 主机检查 `docker version`、`python3 --version` 和 Git。使用 Windows 时，Docker Desktop 必须处在 Linux 容器模式。镜像内已含 OpenClaw 和实验依赖。

| 核对项 | 冻结值 |
|---|---|
| 镜像平台 | `linux/amd64` |
| 加载后 Docker image ID | `sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2` |
| 原生 CLI 输出 | `OpenClaw 2026.9.5 (ec9c1a1)` |
| 镜像文件 | `openclaw-2026.9.5-amd64.tar` |

实际传输件为 3,338,281,472 字节，SHA256 见 [TRANSFER_MANIFEST.json](TRANSFER_MANIFEST.json)。归档已核对 OCI manifest 摘要、配置摘要和 45 个镜像层成员。恢复时使用支持 OCI manifest ID 的 Docker containerd 镜像存储。若旧 Linux Engine 只显示配置 ID `sha256:9ec79be86b47dd8836a1b7e0096a2c6d473d93792f9a0147c431615b8a362393`，先在隔离验收主机确认镜像存储配置，再按下面的固定 manifest ID 核验。便携运行器以该 manifest ID 为准。[Docker containerd 镜像存储](https://docs.docker.com/engine/storage/containerd/)

现有 Docker Desktop 已实核持有上述镜像，`RepoTags` 和 `RepoDigests` 均为空。镜像按 ID 从已安装的 Docker 导出，或使用交接中提供的归档。将归档及其 SHA256 通过双方认可的私有渠道传给同事。Git 交付提供运行入口与交接校验清单。镜像的 Docker `Size` 为 9,929,402,558 字节，给接收端归档和 Docker 镜像存储留足空间，以传输件实际大小为准。

## 在已持有镜像的机器上导出

若拿到交付的归档与 SHA256，可直接进入导入。需要重导出时，在持有该镜像的 Windows 主机执行以下 PowerShell。把当前目录设在具有足够空间的私有位置。`docker image save` 会导出原有镜像层和配置，运行中的容器可继续工作。[Docker image save](https://docs.docker.com/reference/cli/docker/image/save/)

```powershell
$image = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
$archive = 'openclaw-2026.9.5-amd64.tar'
$expected = "$image linux/amd64"
$actual = docker image inspect $image --format '{{.Id}} {{.Os}}/{{.Architecture}}'
if ($LASTEXITCODE -ne 0 -or $actual -ne $expected) { throw 'Frozen image mismatch' }
if (Test-Path -LiteralPath $archive) { throw 'Archive already exists. Verify it or use a fresh directory.' }
docker image save --output $archive $image
if ($LASTEXITCODE -ne 0) { throw 'Docker export failed' }
(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() |
  Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
Get-Item -LiteralPath $archive | Select-Object Name,Length
Get-Content -LiteralPath "$archive.sha256"
```

`.sha256` 文件只写 64 位十六进制 SHA256。若以 Git 交接清单发送哈希，接收方可把清单中的归档 SHA256 单独写入同名 `.sha256`。历史两份 TAR 由不同 Docker 导出路径生成，归档 SHA 可以不同。当前传输以此次文件的 SHA 和加载后的固定镜像 ID 双重核对。

## 在同事的 x86 主机导入并核验

Linux x86 主机执行以下命令。执行前在归档所在目录检查 `uname -m` 为 `x86_64`。若已经持有相同 ID，可从最后两条镜像核验命令开始。[Docker image load](https://docs.docker.com/reference/cli/docker/image/load/)

```bash
set -eu
image='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
archive='openclaw-2026.9.5-amd64.tar'
expected_sha=$(tr -d '\r\n' < "$archive.sha256")
printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check --strict
docker image load --input "$archive"
test "$(docker image inspect "$image" --format '{{.Id}} {{.Os}}/{{.Architecture}}')" = "$image linux/amd64"
docker run --rm --network none --platform linux/amd64 --entrypoint openclaw "$image" --version
```

Windows x86 主机使用 Docker Desktop 时执行以下 PowerShell。

```powershell
$image = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
$archive = 'openclaw-2026.9.5-amd64.tar'
$expectedSha = (Get-Content -LiteralPath "$archive.sha256" -Raw).Trim().ToLowerInvariant()
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedSha) {
  throw 'Archive SHA256 mismatch'
}
docker image load --input $archive
if ($LASTEXITCODE -ne 0) { throw 'Docker import failed' }
$actual = docker image inspect $image --format '{{.Id}} {{.Os}}/{{.Architecture}}'
if ($LASTEXITCODE -ne 0 -or $actual -ne "$image linux/amd64") { throw 'Frozen image mismatch' }
docker run --rm --network none --platform linux/amd64 --entrypoint openclaw $image --version
```

把镜像 ID、平台、OpenClaw 版本和归档校验结果写入运行回执。三项身份均相符再开始原生工具验机。

## 把原生容器接到 Spark

Spark 侧按交接包说明启动一个模型尺寸，监听 Spark 自己的 `127.0.0.1:18758`。如果同事的 **x86 主机可以登录 Spark**，在该 x86 主机的单独终端建立回环转发。将 `SPARK_USER@SPARK_HOST` 替换为同事实际可连接的账户和地址，保持转发终端运行。

```bash
ssh -NT -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18758:127.0.0.1:18758 SPARK_USER@SPARK_HOST
```

在 **同一 x86 主机**另开终端执行 `curl --fail http://127.0.0.1:18758/v1/models`，在 Windows PowerShell 可用 `curl.exe`。8B 服务预期看到 `wrd58-8b-0` 和 `wrd58-8b-26`，切换 14B 后预期看到 `wrd58-14b-0` 和 `wrd58-14b-26`。脚本通过原样转发 relay 接续同一次原生会话。Spark 执行推理，本地 OpenClaw 原生发现和读取 skill、执行工具并送回工具反馈。

- **Windows Docker Desktop** 的容器通过 `host.docker.internal` 访问本机 relay。relay 位于 Windows 本地回环，Spark 上游是 x86 主机的 `127.0.0.1:18758`。[Docker Desktop 网络](https://docs.docker.com/desktop/features/networking/)
- **Linux Docker Engine** 使用交接启动器的 `host-gateway` 映射和 Docker bridge 网关监听。本机回环上的 Spark 上游仍由 relay 访问。Windows 的 Docker Desktop 网络假设不能直接搬到 Linux bridge。运行前用交接启动器核对容器到 relay 的连通性，保持 relay 仅对本机 Docker 网桥可见。[Docker `--add-host` 与 `host-gateway`](https://docs.docker.com/reference/cli/docker/container/run/#add-entries-to-container-hosts-file---add-host)

如果该 x86 主机与 Spark 也没有可用私有链路，先安排一台与 Spark 可连的 x86 主机。已有逐文件交接流程可用于单请求接口验收，完整会话会在每个工具反馈后继续请求推理，人工搬运耗时另记。所有正式比较采用同一连接条件。私有输入和真实原生轨迹用双方认可的受控目录交接。
