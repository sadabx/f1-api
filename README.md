# F1 API

A lightweight Formula 1 data API providing up-to-date season information, race results, and driver/constructor standings through static JSON endpoints.

The API is automatically maintained and updated throughout the season, making it ideal for dashboards, websites, widgets, and other F1-related applications.

---

## Repository Structure

```text
f1-api/
├── api/
│   ├── current.json          # Current or upcoming F1 event details
│   ├── results.json          # Season race results
│   └── standings.json        # Driver and Constructor standings
├── update_api.py             # Data generation script
└── .github/workflows/
    └── run_api.yml           # Automated update workflow
```

---

## Endpoints

### Current Event

```bash
curl https://raw.githubusercontent.com/sadabx/f1-api/main/api/current.json
```

### Race Results

```bash
curl https://raw.githubusercontent.com/sadabx/f1-api/main/api/results.json
```

### Championship Standings

```bash
curl https://raw.githubusercontent.com/sadabx/f1-api/main/api/standings.json
```

---

## Local Setup

```bash
git clone https://github.com/sadabx/f1-api.git
cd f1-api

python update_api.py
```
