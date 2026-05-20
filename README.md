# trans_risk_Agent — V1

交易风控确定性调查流水线（`metric_monitor → dimension_contribution → finding_summary`）。

## 快速开始

```bash
cd v1
pip install -r requirements.txt
docker compose up -d
python tools/seed/seed_from_pkl.py
python scripts/run_investigation.py
```

详见 [v1/README.md](./v1/README.md)。
