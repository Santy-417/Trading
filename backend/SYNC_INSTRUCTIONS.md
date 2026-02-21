# Historical Trade Sync Instructions

## Why Audit Logs Are Empty

Audit logs show closed trades from the database. If empty, it means:
1. No positions have been closed yet
2. Historical trades from MT5 haven't been synced

## Solutions

### Option 1: Close Existing Positions (Easiest)
1. Go to Trading page (`/trading`)
2. Close any open positions via PositionsTable
3. Trades automatically save to database via `order_service.py`
4. Refresh Audit page - trades will appear

### Option 2: Manual Historical Sync (Advanced)
Run the sync script to import closed trades from MT5 history:

```bash
cd backend
python sync_mt5_positions.py
```

**Note:** Currently lines 80-98 are commented out. Uncomment to enable historical sync.

### Option 3: Wait for Natural Trading
As bot trades and closes positions, audit log will populate automatically.

## Verify Backend Fix

Backend serialization fix (TradeResponse) was applied in commit 4ba59db:
- `order_service.py` line 278: Uses `TradeResponse.model_validate(trade)`
- `orders.py` line 117: Has `response_model=TradeListResponse`

Check with:
```bash
curl -H "Authorization: Bearer dev-bypass-token" \
  "http://localhost:8000/api/v1/orders/history?page=1&page_size=10"
```

Expected: JSON with proper field types (numbers, not strings).
