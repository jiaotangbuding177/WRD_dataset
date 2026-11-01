# 57实际使用的冷下载验证入口

本次数据提交`331098e32d6ce5df8a83b51af19a09079342b12d`已完成冷核：44个普通Git文件与1个LFS pointer从新bare仓库读取，与本地target逐blob一致；新增AES实体实际下载104626003字节，wire同104626003，SHA/size全部符合pointer。旧05—11本次没有重新下载，只引用此前证明。实际结果见`../../deliveries/20261101_increment57_offline/REMOTE_VERIFICATION.json`。

实际采用以下入口；需要Python的`requests`包：

```sh
python3 plans/20261101_increment57/tooling/verify_remote57_batch.py \
  --repo /path/to/WRD_dataset \
  --base 77ea6a8 \
  --target 331098e32d6ce5df8a83b51af19a09079342b12d \
  --out /data/wrd57_remote_batch_fresh01
```

入口固定SHA复用已审55官方LFS batch下载实现，仅将对象清单收口为57新增pointer的一个OID。Git普通文件使用全新blob:none bare仓库；实体通过GitHub官方LFS batch取得下载动作，在全新外部目录实际下载，核Range、完整SHA256和size，完全不使用本地LFS对象缓存。GCM凭据仅在进程内存，用于官方GitHub batch；signed URL只在内存用于TLS下载，不输出到回执。

原`verify_remote57.py`的官方git-lfs CLI路线保留。首次运行停在partial-clone中`ls-tree -l`逐个恢复旧普通blob size的低效扫描，未形成任何新LFS实体字节，因此保留为未完成attempt，不记PASS。新入口避免这一步，不请求旧LFS实体。

回执提交仅增加普通Git文件；对回执commit另建新bare仓库逐blob冷读，不再次下载已经证明的新AES实体，也不把一次实体下载重复计为多次。
