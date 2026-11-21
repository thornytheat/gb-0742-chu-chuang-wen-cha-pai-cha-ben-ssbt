# 橱窗温差排查本

博物馆保管员用本台核查展柜上下层传感器，确认探头迁移后仍能对准同柜读数，再按柜时归档梯度证据、连续异常和报警工单。

## 启动

```sh
docker compose up --build -d
```

打开 `http://localhost:18431`。接口文档在 `/docs`，健康探针在 `/healthz`。容器归卷数据库保存在 `glass_records` 命名卷。需要演示新库时，可另设 Compose 项目名或本地 `MUSEUM_DB` 文件。

在本机用 Python 3.12 启动。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 18431
```

## 排查入口

| 页面 | 操作 |
|---|---|
| 点位采信 | 查读数格式、统计隔离行、按迟报或重复筛选 |
| 探头迁移 | 按探头号和测量时刻查部署，核对迁移与冲突时窗 |
| 时窗配准 | 查同柜上下层配对、时差和未用记录 |
| 垂直梯度 | 选柜时，查看剖面、签名梯度和置信区间，点探头追到原行 |
| 异常持续 | 查持续或瞬时段，由证据索引返回相关柜时 |
| 值班单勾稽 | 守恒核对柜时，查工单处置和未报的异常段 |
| 证据归卷 | 查规则版次和摘要、换历史、复算原档及导出 |

首次启动自动归卷值班混合样例。全稳校验样例共有 3 个稳定柜时。截断图档样例用于检查失败处理。顶部控件提供运行、重跑、证据下载和打印。剖面中默认显示首个柜时，可点柜时签切换，再点上下探头聚焦其原行。

```sh
python -m pytest -q
```

容器内可运行 `docker compose exec -T app pytest -q`。输入样例在 `sample_data/`，数据定义见 [字段与规则](docs/DATA-DICTIONARY.md)，反例与覆盖位置见 [深度登记](docs/DEPTH.md)。
