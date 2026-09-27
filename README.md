# 企业排污许可与超标处置

汇总监测和工况，判断排放超标并跟踪复测、整改、执法与复查。

## 模块结构

- `app.py`：参数解析、依赖组装和HTTP服务启动。
- `src/domain.py`：数据结构、错误、状态和基础校验。
- `src/rules.py`：状态机、角色矩阵、优先级、期限和关闭不变量。
- `src/repository.py`：SQLite建表、事务、版本控制和审计链。
- `src/service.py`：权限检查、用例编排、并发控制和审计。
- `src/http_api.py`：JSON路由和统一错误响应。
- `src/audit.py`：UTC时间和SHA-256审计事件。
- `static/index.html`：最小演示页。
- `tests/`：完整流程、规则和失败测试。

## 初始化与启动

```bash
python3 app.py --db ./data.db --port 8313
```

默认端口为`8313`，首次启动自动建库。使用`X-Actor`和`X-Role`请求头传递身份。

## 主要接口

- `GET /health`
- `GET /api/items`
- `POST /api/items`
- `GET /api/items/{id}`
- `POST /api/items/{id}/records`：登记整改记录（保持待复核）；主任以`kind=director_signoff`新增唯一一条复查签署
- `POST /api/items/{id}/records/{record_id}/review`：合规员提交`comment`与`expected_version`复核关闭记录
- `POST /api/items/{id}/transition`，必须提交`expected_version`；归档（closed）还需提交`reason`
- `GET /api/audit`

允许角色：operator, compliance_officer, director, viewer。按浓度与许可限值计算超标倍数，异常读数先进入评估；整改记录由合规员复核关闭，旧版本或重复关闭返回冲突；归档前必须所有记录已关闭、主任已签署且审计链完整，登记、复核和归档均记录操作者、时间与原因。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
