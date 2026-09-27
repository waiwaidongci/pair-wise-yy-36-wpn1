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
- `POST /api/items/{id}/records`，登记后记录保持待复核（open）
- `POST /api/items/{id}/records/{rid}/review`，合规员提交`comment`和`expected_version`复核关闭；版本过旧或重复关闭返回409
- `POST /api/items/{id}/signoff`，主任提交`comment`复查签署，每个事件仅一条
- `POST /api/items/{id}/transition`，必须提交`expected_version`；归档（closed）还须提交`reason`
- `GET /api/audit`

允许角色：operator, compliance_officer, director, viewer。按浓度与许可限值计算超标倍数，异常读数先进入评估；归档前必须所有整改记录已复核关闭、存在主任复查签署且审计链完整，否则返回409。登记、复核和归档均记录操作者、时间和原因。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
