# SpaceVoice Internal Module — Revised Implementation Plan

## Overview

Create a **fully private** internal-only module that simulates ~50 client accounts (masked IDs, no company names) with real payment-derived data, usage stats, and 6-month history. **Zero references** to this module appear in the public repo except two minimal generic hooks.

---

## 1. Architecture — Full Isolation

### What lives WHERE

| Layer | Public repo | Private module (`sv_internal/`) |
|-------|-------------|-------------------------------|
| Backend hook | 4-line generic `try/except ImportError` in `main.py` | All models, API routes, seed script, aggregation |
| Frontend hook | Generic "plugin nav" loader in sidebar (no "Income" reference) | Income page, components, charts, API client, nav config |
| `.gitignore` | `/sv_internal/`, `frontend/src/app/dashboard/income/` | N/A (separate private repo) |

### Public repo touch points (2 generic hooks, no "Income" references)

**Hook 1 — `backend/app/main.py`** (after line 251):
```python
# Optional plugin modules
try:
    from sv_internal import plugin_setup
    plugin_setup(app)
except ImportError:
    pass
```

**Hook 2 — `frontend/src/components/app-sidebar.tsx`** (inside admin section):
A generic plugin nav loader — fetches optional nav items from `/api/v1/plugins/nav`. Returns `[]` if endpoint doesn't exist. No hardcoded "Income" label or route. The private module's backend serves this endpoint with its nav items.

```typescript
// Generic plugin nav (returns [] when no plugins installed)
const { data: pluginNav = [] } = useQuery({
  queryKey: ["plugin-nav"],
  queryFn: async () => {
    try {
      const res = await api.get("/api/v1/plugins/nav");
      return res.data;
    } catch { return []; }
  },
  staleTime: Infinity,
});
```

Plugin nav items rendered dynamically in the admin section alongside "Clients" and "Pricing". The icon is resolved from a small icon map (lucide icons keyed by string name).

### Private module location

`SpaceVoice/sv_internal/` — git-ignored in the public repo. Maintained as a separate private GitHub repo. Installed via:
```bash
git clone git@github.com:<org>/spacevoice-internal.git sv_internal
cd backend && pip install -e ../sv_internal
cd ../sv_internal && ./install.sh   # symlinks frontend files into Next.js tree
```

### `install.sh` — Frontend symlink script (in private module)

Creates symlinks so Next.js discovers the Income page without the files existing in the public repo:
```bash
#!/bin/bash
ln -sfn "$(pwd)/frontend/income" "../frontend/src/app/dashboard/income"
ln -sfn "$(pwd)/frontend/lib/api/income.ts" "../frontend/src/lib/api/income.ts"
echo "✓ Internal frontend linked"
```

Both symlink targets are in public `.gitignore`, so `git status` never shows them.

---

## 2. Client Identity — Masked IDs, No Company Names

### Labeling strategy

- **Primary label**: Masked client ID — e.g. `SV-A1B2••`, `SV-••C3D4`
- **Descriptor** (non-identifying): `"Enterprise HVAC"`, `"Medium Plumbing"`, `"Enterprise Electrical"`
- **No company names** stored or displayed anywhere
- The `display_label` field combines both: `"SV-A1B2•• · Enterprise HVAC"`

### Masking logic

The full `client_id` (e.g. `SV-A1B2C3`) is stored internally. The API returns a `masked_id` computed at response time:
```python
def mask_client_id(client_id: str) -> str:
    """SV-A1B2C3 → SV-A1B2••"""
    prefix = client_id[:7]  # "SV-A1B2"
    return f"{prefix}••"
```

Full `client_id` only visible in the detail view (admin drill-down), never in list views or charts.

---

## 3. Data Model — 3 Tables (all in private module)

All models inherit from `Base` (`app.db.base`) and `TimestampMixin`.

### Table: `sim_clients`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | `uuid.uuid4` |
| `user_id` | int FK → users.id | Nullable, linked to seeded User row |
| `client_id` | String(20), unique | `SV-{6 alphanum}` (matches existing pattern) |
| `client_size` | String(50) | "medium" or "enterprise" |
| `industry` | String(100) | HVAC, Plumbing, Electrical, etc. |
| `descriptor` | String(100) | Non-identifying: "Enterprise HVAC" |
| `status` | String(50) | active / churned / paused |
| `onboarded_at` | DateTime | When client "signed up" |
| **Payment-derived fields (source of truth)** | | |
| `processor` | String(50) | "stripe" |
| `customer_id` | String(100) | "cus_..." (Stripe-format) |
| `subscription_id` | String(100) | "sub_..." |
| `plan_id` | String(100) | "price_..." |
| `billing_cycle` | String(20) | "monthly" or "annual" |
| `next_charge_date` | Date | |
| `last_charge_date` | Date | |
| `last_charge_status` | String(50) | succeeded / failed / pending |
| `payment_method_type` | String(50) | card / ach / wire |
| `billing_currency` | String(10) | "usd" |
| **Revenue (derived from payment processing)** | | |
| `mrr` | Numeric(12,2) | Monthly recurring only (no setup fee) |
| `arr` | Numeric(12,2) | mrr × 12 |
| `setup_fee` | Numeric(10,2) | One-time, tracked separately from MRR |
| `total_first_month` | Numeric(12,2) | mrr + setup_fee |
| `paid_amount` | Numeric(12,2) | Lifetime total from payment processor |
| `refunded_amount` | Numeric(12,2) | Lifetime refunds from processor |
| `chargebacks_amount` | Numeric(12,2) | Lifetime chargebacks from processor |
| `net_revenue` | Numeric(12,2) | paid − refunded − chargebacks |
| **Payment counts (from processor)** | | |
| `invoice_count` | Integer | Total invoices generated |
| `payment_count` | Integer | Total payment attempts |
| `successful_payments` | Integer | Succeeded charges |
| `failed_payments` | Integer | Failed charges |
| **Usage/ops (30-day rolling)** | | |
| `calls_received_30d` | Integer | |
| `calls_handled_30d` | Integer | |
| `avg_call_duration` | Float | Seconds |
| `total_minutes_30d` | Float | |
| **Meta** | | |
| `pricing_tier` | String(50) | Matches pricing_config.tier_id |
| `created_at` / `updated_at` | DateTime | TimestampMixin |

### Table: `sim_client_history`

One row per client per month. 6 months of data seeded.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `client_id` | UUID FK → sim_clients.id | Indexed, CASCADE |
| `month` | Date | First of month (e.g. 2025-08-01) |
| `invoiced_amount` | Numeric(12,2) | From payment processor |
| `paid_amount` | Numeric(12,2) | From payment processor |
| `mrr` | Numeric(12,2) | Recurring only |
| `refunds` | Numeric(10,2) | From processor |
| `chargebacks` | Numeric(10,2) | From processor |
| `net_revenue` | Numeric(12,2) | paid − refunds − chargebacks |
| `calls_handled` | Integer | |
| `total_minutes` | Float | |
| `avg_call_duration` | Float | Seconds |
| `created_at` | DateTime | |
| **Constraint** | UNIQUE(client_id, month) | |

### Table: `sim_income_snapshots`

Pre-computed platform-wide monthly aggregates for fast dashboard loading.

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer PK | |
| `month` | Date | Unique, indexed |
| `total_mrr` | Numeric(14,2) | Sum of active clients' MRR |
| `total_arr` | Numeric(14,2) | total_mrr × 12 |
| `total_revenue` | Numeric(14,2) | All paid amounts |
| `total_setup_fees` | Numeric(12,2) | Sum of one-time fees (separate) |
| `total_refunds` | Numeric(12,2) | |
| `total_chargebacks` | Numeric(12,2) | |
| `total_net_revenue` | Numeric(14,2) | |
| `active_clients` | Integer | |
| `new_clients` | Integer | |
| `churned_clients` | Integer | |
| `avg_revenue_per_client` | Numeric(12,2) | |
| `created_at` | DateTime | |

---

## 4. Private Module Directory Structure

```
sv_internal/                              # Separate private git repo
├── pyproject.toml                        # pip-installable: name = "sv-internal"
├── install.sh                            # Symlinks frontend files into Next.js tree
├── uninstall.sh                          # Removes symlinks
├── README.md
├── .gitignore
│
├── sv_internal/                          # Python package
│   ├── __init__.py                       # plugin_setup(app) — registers routes + models
│   ├── models/
│   │   ├── __init__.py                   # Re-exports all models
│   │   ├── sim_client.py                 # SimClient model
│   │   ├── sim_client_history.py         # SimClientHistory model
│   │   └── sim_income_snapshot.py        # SimIncomeSnapshot model
│   ├── api/
│   │   ├── __init__.py
│   │   ├── clients.py                    # Client list/detail/history endpoints
│   │   ├── income.py                     # Income summary/history endpoints
│   │   └── plugins.py                    # GET /api/v1/plugins/nav (serves nav items)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── seed.py                       # Generate 50 clients + 6-month history
│   │   └── aggregation.py               # Compute platform-level income snapshots
│   └── migrations/
│       └── 100_create_sim_tables.py      # Alembic migration
│
└── frontend/                             # Symlinked into Next.js tree by install.sh
    ├── income/                           # → frontend/src/app/dashboard/income/
    │   ├── page.tsx                      # Income page (main view)
    │   └── components/
    │       ├── income-stats-cards.tsx     # 6 revenue stat cards
    │       ├── mrr-chart.tsx             # MRR over time (Recharts AreaChart)
    │       ├── revenue-chart.tsx         # Revenue breakdown (Recharts BarChart)
    │       ├── client-table.tsx          # Client list with masked IDs
    │       └── client-detail.tsx         # Detail dialog with full metrics
    └── lib/
        └── api/
            └── income.ts                # → frontend/src/lib/api/income.ts
```

---

## 5. Migration & Seed Strategy

### Migration
- `Base.metadata.create_all` in `main.py` lifespan auto-creates tables when models are imported via `plugin_setup()` (dev convenience)
- Formal Alembic migration `100_create_sim_tables.py` for production (symlinked into `backend/migrations/versions/`)

### Seed Script: `sv_internal/services/seed.py`

Callable via `POST /api/v1/internal/seed` (admin) or CLI.

**50 clients breakdown:**
- 35 enterprise (MRR $2,000–$15,000)
- 15 medium (MRR $200–$2,000)
- 2–3 churned, 1 paused, rest active

**Data generation — payment processor as source of truth:**

1. **Client identity**: Generate `client_id` via existing `generate_client_id()` pattern (`SV-{6 alphanum}`). Build descriptor from size + industry (e.g. "Enterprise HVAC"). No company names.

2. **Payment data (Stripe-like)**:
   - `customer_id = f"cus_{secrets.token_hex(12)}"`
   - `subscription_id = f"sub_{secrets.token_hex(12)}"`
   - `plan_id = f"price_{secrets.token_hex(8)}"`
   - `billing_cycle`: 80% monthly, 20% annual
   - `payment_method_type`: 70% card, 20% ach, 10% wire
   - `last_charge_status`: active→"succeeded", churned→"failed"

3. **MRR (clean, no setup fee mixed in)**:
   - Enterprise: random in $2,000–$15,000 (weighted toward $4,000–$8,000)
   - Medium: random in $200–$2,000
   - `arr = mrr * 12`
   - `setup_fee`: enterprise $500–$2,000, medium $0–$500 (tracked separately)
   - `total_first_month = mrr + setup_fee`

4. **6-month history per client**:
   - Base MRR with 1–3% monthly growth
   - Seasonal variation (Q4 slightly higher for HVAC)
   - `invoiced_amount = mrr` (or mrr + setup_fee for month 1)
   - `paid_amount` = invoiced minus occasional failures
   - Refund events: ~5% of months, $50–$500
   - Chargeback events: ~2% of months, $100–$300
   - `net_revenue = paid_amount - refunds - chargebacks`
   - `calls_handled`: correlated to MRR (enterprise 200–2000/mo, medium 20–200/mo)
   - Churned clients: MRR drops to $0 in month 5 or 6

5. **Lifetime aggregates** (summed from history):
   - `paid_amount`, `refunded_amount`, `chargebacks_amount`, `net_revenue`
   - `invoice_count = months_active`, `payment_count`, `successful_payments`, `failed_payments`

6. **30-day stats**: Copied from most recent month's history

7. **Matching User rows**: Creates `User` records (non-superuser, onboarding complete) with email `{client_id.lower()}@client.spacevoice.ai` so clients appear in admin views naturally.

8. **Platform snapshots**: After seeding all clients, compute `sim_income_snapshots` for each month.

---

## 6. Backend API Design (all in private module)

All endpoints registered by `plugin_setup()`. Admin-only.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/internal/clients` | List clients (masked IDs + descriptors). Filter: status, size. Sort: mrr, client_id |
| `GET` | `/api/v1/internal/clients/{id}` | Full client detail — all payment/revenue/usage fields. Selecting a client populates outcomes + metrics |
| `GET` | `/api/v1/internal/clients/{id}/history` | 6-month history (month, invoiced, paid, mrr, refunds, chargebacks, net_revenue, calls) |
| `GET` | `/api/v1/internal/income/summary` | Platform totals: total_mrr, total_arr, net_revenue, active_clients, mrr_growth_pct, total_setup_fees, avg_revenue_per_client |
| `GET` | `/api/v1/internal/income/history` | Platform monthly history (6 months from `sim_income_snapshots`) |
| `POST` | `/api/v1/internal/seed` | Idempotent seed trigger |
| `GET` | `/api/v1/plugins/nav` | Returns nav items for sidebar: `[{name, href, icon, color}]` |

### Response models

**Client list response** (masked by default):
```python
class SimClientListResponse(BaseModel):
    id: str                    # UUID
    masked_id: str             # "SV-A1B2••"
    descriptor: str            # "Enterprise HVAC"
    display_label: str         # "SV-A1B2•• · Enterprise HVAC"
    client_size: str
    status: str
    mrr: float
    setup_fee: float           # Separate from MRR
    net_revenue: float
    calls_handled_30d: int
    last_charge_status: str
    pricing_tier: str
```

**Client detail response** (full data on selection):
```python
class SimClientDetailResponse(BaseModel):
    # Identity
    id: str
    client_id: str             # Full ID (admin detail only)
    masked_id: str
    descriptor: str
    client_size: str
    industry: str
    status: str
    onboarded_at: str

    # Payment-derived (source of truth)
    processor: str
    customer_id: str
    subscription_id: str
    plan_id: str
    billing_cycle: str
    next_charge_date: str
    last_charge_date: str
    last_charge_status: str
    payment_method_type: str
    billing_currency: str

    # Revenue (MRR separate from setup fee)
    mrr: float
    arr: float
    setup_fee: float
    total_first_month: float
    paid_amount: float
    refunded_amount: float
    chargebacks_amount: float
    net_revenue: float

    # Payment counts
    invoice_count: int
    payment_count: int
    successful_payments: int
    failed_payments: int

    # Usage/ops
    calls_received_30d: int
    calls_handled_30d: int
    avg_call_duration: float
    total_minutes_30d: float

    pricing_tier: str
```

---

## 7. Frontend UI Design (all in private module)

### Recharts (installed by `install.sh`)
```bash
cd frontend && npm install recharts
```

### Income Page Layout (`income/page.tsx`)

1. **Header**: "Income" title + "Seed Data" button (calls `POST /api/v1/internal/seed`)

2. **Stats cards** (6 cards, matching dashboard styling):
   - Total MRR (DollarSign icon, green) — recurring only, no setup fees
   - Total ARR (TrendingUp, blue)
   - Net Revenue (Banknote, emerald)
   - Active Clients (Building2, violet)
   - MRR Growth % (ArrowUpRight/ArrowDownRight, amber)
   - Setup Fees Collected (Receipt, cyan) — one-time total, clearly separate

3. **Charts row** (2-column grid, lg breakpoint):
   - **MRR Over Time** — Recharts `AreaChart`, 6 months, gradient fill. Pure MRR (no setup fees mixed in)
   - **Revenue Breakdown** — Recharts stacked `BarChart` per month: paid (green) vs refunds (amber) vs chargebacks (red)

4. **Client list table** (full width):
   - Columns: Masked ID, Descriptor, Size, Tier, MRR, Setup Fee, Status, Calls (30d), Last Charge
   - MRR and Setup Fee in separate columns (never combined)
   - Sortable by MRR, status
   - Filter chips: All | Enterprise | Medium | Active | Churned
   - Click row → populates detail panel with full outcomes and metrics

5. **Client Detail Panel** (Radix Dialog on row click):
   - **Top**: `SV-A1B2•• · Enterprise HVAC` + status badge
   - **Payment section**: processor, customer_id, subscription_id, plan_id, billing_cycle, payment_method, last_charge_date, last_charge_status
   - **Revenue section**: MRR, ARR, Setup Fee (labeled "one-time"), total_first_month, net_revenue. Clearly shows MRR is clean of setup fees
   - **Payment counts**: invoices, total payments, successful, failed
   - **Usage**: calls_received_30d, calls_handled_30d, avg_call_duration, total_minutes_30d
   - **6-month history chart**: Recharts `ComposedChart` — Line for MRR trend + Bars for calls_handled

---

## 8. Task List (Priority Order)

### Phase A: Foundation (private module scaffolding)
1. **Create private repo structure** — `sv_internal/` with `pyproject.toml`, `__init__.py`, all subdirectories, `install.sh`, `uninstall.sh`
2. **Define SQLAlchemy models** — `sim_client.py`, `sim_client_history.py`, `sim_income_snapshot.py` with all fields from Section 3
3. **Write Alembic migration** — `100_create_sim_tables.py` for 3 tables with indexes + unique constraints
4. **Add public repo hooks** — 4-line `try/except` in `main.py`, generic plugin nav loader in `app-sidebar.tsx`, `.gitignore` entries for `/sv_internal/`, `frontend/src/app/dashboard/income/`, `frontend/src/lib/api/income.ts`

### Phase B: Backend data layer (private module)
5. **Build seed script** — 50 clients with masked IDs, descriptors, payment data, 6-month history, matching User rows
6. **Build aggregation service** — Compute `sim_income_snapshots` from client history
7. **Build API routes** — 7 endpoints (clients, income, seed, plugin nav) with Pydantic response models

### Phase C: Frontend (private module)
8. **Install Recharts** — Added by `install.sh`
9. **Create API client** — `income.ts` with TS interfaces and fetch functions
10. **Build Income page + components** — Stats cards (MRR separate from setup fee), MRR chart, revenue chart, client table (masked IDs), client detail dialog
11. **Run `install.sh`** — Symlink frontend files into Next.js tree

### Phase D: Verification
12. **End-to-end test** — Seed data, verify all stats/charts render, click client → detail populates with full outcomes and metrics
13. **Verify MRR/setup separation** — Confirm MRR cards and charts show only recurring revenue; setup fees shown separately
14. **Verify masking** — List views show `SV-A1B2••` only; full IDs only in detail view
15. **Verify isolation** — Remove `sv_internal/`, delete symlinks, restart → app runs with zero errors, no trace of Income module

---

## 9. Verification Plan

| Step | Action | Expected |
|------|--------|----------|
| 1 | Start backend with `sv_internal` installed | `/health` returns 200, tables auto-created |
| 2 | `POST /api/v1/internal/seed` as admin | `{"message": "Seeded 50 clients..."}` |
| 3 | `GET /api/v1/internal/clients` | 50 clients with masked IDs, no company names |
| 4 | `GET /api/v1/internal/clients/{id}` | Full detail: payment, revenue, usage — all populated |
| 5 | `GET /api/v1/internal/clients/{id}/history` | 6 monthly records with invoiced, paid, mrr, refunds, chargebacks |
| 6 | `GET /api/v1/internal/income/summary` | Aggregated MRR, ARR, net_revenue, setup_fees (separate) |
| 7 | `GET /api/v1/plugins/nav` | Returns `[{name: "Income", href: "/dashboard/income", ...}]` |
| 8 | Navigate to `/dashboard/income` | Stats cards + charts + client table render |
| 9 | Click a client row | Detail dialog populates all outcomes and metrics |
| 10 | Confirm MRR column ≠ setup fee column | MRR is clean recurring; setup fee is separate one-time |
| 11 | Confirm list shows `SV-A1B2••` not full IDs | Masking works in list, full ID in detail only |
| 12 | Run `uninstall.sh`, remove `sv_internal/`, restart | App runs, sidebar shows no "Income", no errors |
| 13 | `git status` in public repo | Zero changes related to internal module |

---

## Critical Files Modified in Public Repo

| File | Change | Size |
|------|--------|------|
| `backend/app/main.py` | 4-line generic plugin hook (no "Income" reference) | +4 lines |
| `frontend/src/components/app-sidebar.tsx` | Generic plugin nav loader (~15 lines, no "Income" reference) | +15 lines |
| `.gitignore` | Add `/sv_internal/`, `frontend/src/app/dashboard/income/`, `frontend/src/lib/api/income.ts` | +3 lines |

**Total public repo footprint: ~22 lines, zero module-specific references.**
Everything else is in the private `sv_internal/` repo.
