# 安全操作规则

## 生产环境操作限制

**严格遵守：只能查看，不能修改！**

### ✅ 允许的操作
- 查看日志 (`docker logs`, `cat`, `tail`, `less`)
- 查看状态 (`ps`, `top`, `docker ps`, `systemctl status`)
- 查看配置 (`cat`, `grep`, `find`)
- 查询数据 (`SELECT` 查询)
- 网络检测 (`ping`, `curl`, `netstat`)

### ❌ 禁止的操作
- 删除文件 (`rm`, `rmdir`)
- 修改文件 (`vi`, `echo >`, `sed -i`)
- 重启服务 (`systemctl restart`, `service restart`)
- 停止服务 (`systemctl stop`, `kill`)
- 删除容器/镜像 (`docker rm`, `docker rmi`)
- 修改数据库 (`INSERT`, `UPDATE`, `DELETE`, `DROP`)
- 修改权限 (`chmod`, `chown`)

## 相关服务器
- 堡垒机: jumpserver-internal.digitforce.com:2222
- 目标服务器: 10.10.20.29 (prod-algorithm-n1)
- 容器: sa-gpt

## 记录时间
- 2026-03-01 23:37 GMT+8
