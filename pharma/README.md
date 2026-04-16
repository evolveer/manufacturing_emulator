# Pharma Batch Execution Simulator

> Simulated pharma batch execution workflow covering MES order flow, step execution, audit trail, deviations, and release review in a regulated manufacturing context — **wired bidirectionally to ERP, MES, and PCS**.

---

## System Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Pharma Batch Execution Simulator               │
│                        (Streamlit :8501)                        │
│                                                                 │
│  Orders → Batches → Steps → Parameters → Deviations → Review   │
└────────────────────┬────────────────────────────────────────────┘
                     │  Integration Layer (pharma/app/integration/)
          ┌──────────┼──────────┐
          ▼          ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  ERP    │ │  MES    │ │  PCS    │
   │ :5001   │ │ :5002   │ │ :5003   │
   └─────────┘ └─────────┘ └─────────┘
```

### Data Flow by Lifecycle Event

| Pharma Event | ERP Action | MES Action | PCS Action |
|---|---|---|---|
| **Order Created** | Create production order + ensure product | — | — |
| **Order Sent to MES** | Update order → `in_progress` | — | — |
| **Batch Instantiated** | Look up product ID | Create work order + allocate materials | Start machine |
| **Step Started** | — | Update work order → `in_progress` | — |
| **Parameter Captured** | — | Create quality check record | Read sensor snapshot |
| **Step Completed** | — | Increment good count | — |
| **Deviation Opened** | — | Increment reject count | Pull active alarms |
| **Batch Completed** | — | Update work order → `completed` | Stop machine |
| **Batch Released** | Add quantity to product stock; order → `completed` | — | — |
| **Batch Rejected** | Order → `cancelled` | Work order → `on_hold` | — |

All integration calls are **best-effort**: if ERP/MES/PCS are offline, the pharma simulator continues in standalone mode and logs a warning. Set `PHARMA_INTEGRATION_STRICT=true` to make failures raise exceptions.

---

## Quick Start

```bash
# From the repo root – starts all systems including pharma
./start.sh

# Or run pharma standalone
cd pharma
pip install -r requirements.txt
streamlit run app/main.py
```

Access the simulator at **http://localhost:8501**

---

## Module Structure

```
pharma/
├── app/
│   ├── main.py                  ← Streamlit entry point + navigation + health strip
│   ├── domain/
│   │   ├── enums.py             ← Status/category enumerations
│   │   ├── models.py            ← Pydantic domain entities
│   │   └── rules.py             ← Parameter validation & disposition logic
│   ├── integration/
│   │   ├── config.py            ← URL resolution from config.yaml / env vars
│   │   ├── base_client.py       ← Shared HTTP client with health-check
│   │   ├── erp_client.py        ← ERP adapter (products, materials, orders, plans)
│   │   ├── mes_client.py        ← MES adapter (work orders, quality, materials)
│   │   ├── pcs_client.py        ← PCS adapter (machines, sensors, alarms)
│   │   └── orchestrator.py      ← High-level lifecycle event handlers
│   ├── services/
│   │   ├── order_service.py     ← ERP order lifecycle (+ integration hooks)
│   │   ├── batch_service.py     ← MES batch instantiation (+ integration hooks)
│   │   ├── recipe_service.py    ← Master recipe loading
│   │   ├── execution_service.py ← Step execution & parameter capture (+ hooks)
│   │   ├── deviation_service.py ← Non-conformance management
│   │   ├── audit_service.py     ← Immutable audit trail
│   │   └── review_service.py    ← Completeness check & disposition (+ hooks)
│   ├── pages/
│   │   ├── dashboard.py         ← KPI metrics + charts + integration health strip
│   │   ├── orders.py            ← Order creation & MES dispatch
│   │   ├── execution.py         ← Step-by-step batch execution
│   │   ├── deviations.py        ← Deviation management
│   │   ├── audit_trail.py       ← Filterable audit log + CSV export
│   │   ├── review.py            ← Review & release decision
│   │   └── integration.py       ← Live ERP/MES/PCS status + data panels
│   ├── data/
│   │   ├── seed_recipes.json    ← 2 master recipes (tablet, injectable)
│   │   ├── seed_orders.json     ← 3 demo orders
│   │   └── demo_loader.py       ← Pre-built demo scenarios A/B/C
│   └── utils/
│       ├── persistence.py       ← JSON-based storage with reset
│       └── helpers.py           ← Formatting & badge utilities
├── tests/
│   └── test_pharma.py           ← 10 pytest tests (domain + integration offline)
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PHARMA_ERP_HOST` | `localhost` | ERP host |
| `PHARMA_ERP_PORT` | `5001` | ERP port |
| `PHARMA_MES_HOST` | `localhost` | MES host |
| `PHARMA_MES_PORT` | `5002` | MES port |
| `PHARMA_PCS_HOST` | `localhost` | PCS host |
| `PHARMA_PCS_PORT` | `5003` | PCS port |
| `PHARMA_INTEGRATION_TIMEOUT` | `5` | HTTP timeout (seconds) |
| `PHARMA_INTEGRATION_STRICT` | `false` | Raise on integration failure |
| `PHARMA_DATA_DIR` | auto | Override JSON data directory |

---

## Demo Scenarios

| Scenario | Description | Disposition |
|---|---|---|
| **A – Clean Batch** | All 8 steps completed, all parameters in range | Release |
| **B – Minor Deviation** | Temperature excursion in granulation, justified | Release with Comments |
| **C – Critical Hold** | Sterile filtration step skipped, inspection failed | Reject / Hold |

Use the **Reset Demo Data** button in the sidebar to reload all three scenarios.

---

## Running Tests

```bash
cd manufacturing_emulator
PYTHONPATH=. python3 -m pytest pharma/tests/ -v
```

All 10 tests pass in standalone mode (ERP/MES/PCS offline).

---

## Docker

```bash
docker build -t pharma-simulator ./pharma
docker run -p 8501:8501 \
  -e PHARMA_ERP_HOST=host.docker.internal \
  -e PHARMA_MES_HOST=host.docker.internal \
  -e PHARMA_PCS_HOST=host.docker.internal \
  pharma-simulator
```

---

## Why This Matters in Regulated Manufacturing

In a GxP environment, manufacturing software is not just about recording data; it is about enforcing control, ensuring traceability, and managing exceptions across all layers of the manufacturing stack. This simulator demonstrates:

- **Vertical integration:** A single pharma batch event propagates through ERP (financial/stock), MES (scheduling/quality), and PCS (machine/sensor) in real time.
- **Batch Lifecycle Thinking:** Managing states across orders, batches, steps, and deviations.
- **Auditability:** Every critical action is immutably logged with timestamps, users, and before/after values.
- **Exception Management:** Out-of-spec parameters or skipped steps automatically trigger deviations that block release until justified.
- **Resilient Integration:** All upstream calls are best-effort; the pharma layer never fails due to a downstream system being offline.

---

## Known Limitations

This project is intentionally simplified for educational and demonstration purposes.

- **Not GMP Validated:** This software has not undergone computer system validation (CSV).
- **No 21 CFR Part 11 Compliance:** It lacks real electronic signatures and biometric authentication.
- **Simplified Security Model:** Role-based access control is simulated via text inputs.
- **Basic Persistence:** Uses JSON files instead of a relational database.
