# 提交后的独立远端复核

本页准备复核方法；实际结果以最终`REMOTE_VERIFICATION.json`回执为准。脚本不执行push，也不启动训练。

在root完成审核、提交和推送之后，使用最终commit SHA与一个此前不存在的仓库外输出目录：

```sh
python3 plans/20261101_increment57/tooling/verify_remote57.py \
  --repo /path/to/WRD_dataset \
  --base 77ea6a8 \
  --target FINAL_COMMIT_SHA \
  --out /data/wrd57_remote_verify_fresh01
```

脚本会执行以下独立核验：

1. 使用全新bare仓库，`GIT_LFS_SKIP_SMUDGE=1`并以`--filter=blob:none`从origin取得指定commit；对base到target的ACMR路径逐个读取远端Git blob，以SHA256/size对照本地**target commit**，不以工作区文本或已有普通blob缓存冒充远端证明。
2. 识别新增57目录中的AES LFS pointer，固定pointer OID和size。采用全新仓库外`lfs.storage`，仅对这些精确文件路径执行`git lfs fetch ... origin target`；拒绝非57或非AES的新增LFS实体，默认要求恰好一个。
3. 对新下载实体实算完整SHA256和size，并确认存储中没有旧05—11或其他LFS对象。不调用全库`lfs pull`、`--all`或旧包下载。
4. 旧05—11只引用此前`deliveries/20261101_full_data_and_plan/REMOTE_VERIFICATION.json`的证明，不声称本次重新下载了旧1.3GB。

使用正常Git Credential Manager完成Git/Git-LFS认证。脚本不读取或打印token、密钥或signed URL；所有子进程stderr均不回显，错误仅报告退出码。输出为新目录中的`REMOTE_VERIFICATION57.json`。Git提交成功、本地LFS对象存在以及普通Git blob可读都不替代新增AES实体的真实远端下载验证。
