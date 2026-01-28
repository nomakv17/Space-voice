# SpaceVoice Internal Module

Private analytics module for SpaceVoice. Simulates ~50 client accounts with masked IDs, payment data, and usage stats.

## Installation

```bash
# Clone into SpaceVoice directory (already git-ignored)
git clone git@github.com:<org>/spacevoice-internal.git sv_internal

# Install Python package
cd backend && pip install -e ../sv_internal

# Link frontend files and install recharts
cd ../sv_internal && ./install.sh
```

## Uninstallation

```bash
cd sv_internal && ./uninstall.sh
pip uninstall sv-internal
rm -rf sv_internal
```

## Features

- **Income Dashboard**: `/dashboard/income` - MRR, ARR, revenue charts, client table
- **Masked Client IDs**: List views show `SV-A1B2••`, full IDs only in detail view
- **6-Month History**: Per-client and platform-wide monthly data
- **Seed Data**: `POST /api/v1/internal/seed` generates 50 simulated clients

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/plugins/nav` | Sidebar nav items |
| GET | `/api/v1/internal/clients` | List clients (masked) |
| GET | `/api/v1/internal/clients/{id}` | Client detail |
| GET | `/api/v1/internal/clients/{id}/history` | Client history |
| GET | `/api/v1/internal/income/summary` | Platform totals |
| GET | `/api/v1/internal/income/history` | Platform history |
| POST | `/api/v1/internal/seed` | Seed data |
