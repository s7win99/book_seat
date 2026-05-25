# Batch QR Code Refresh & Export Design

## Overview

Admin dashboard needs three new features:
1. One-click refresh all seat tokens
2. Batch export seat QR codes as printable A4 grid sheets with seat name labels
3. Cancel a user's active check-in (time not recorded in attendance)

## Approach

Backend-driven: use Pillow to generate QR code images with text labels and compose them into A4 grid pages. Frontend only triggers API calls and downloads.

---

## Feature 1: Refresh All Tokens

### Backend

**New endpoint:** `POST /api/admin/seats/refresh-all-tokens`

- Requires admin role
- Iterates all seats, generates new `secrets.token_urlsafe(32)` for each
- Commits all changes in one transaction
- Returns updated seat list (same format as `GET /api/admin/seats`)

### Frontend

- Add a "刷新全部Token" button next to the "+ 添加座位" button in the seats tab
- On click: show `confirm()` dialog ("确定刷新全部座位的Token？刷新后旧二维码将失效。")
- On confirm: call `POST /api/admin/seats/refresh-all-tokens`, then reload seat list
- Show success alert after completion

---

## Feature 2: QR Code with Seat Name Label

### Backend

**Modify existing endpoint:** `GET /api/admin/seats/{seat_id}/qrcode`

Current behavior: returns bare QR code PNG.

New behavior:
1. Generate QR code image (same as current)
2. Create a larger canvas with white background
3. Paste QR code centered in the upper portion
4. Draw seat name text below the QR code using Pillow's ImageDraw
5. Return the composite PNG

Image dimensions: QR code (200x200) + padding + text area = approximately 200x260 pixels.

Font: use Pillow's default bitmap font (no external font file needed). Font size ~20px, centered horizontally.

---

## Feature 3: Batch Export QR Codes

### Backend

**New endpoint:** `GET /api/admin/seats/qrcode-batch`

Parameters: none (exports all seats)

Logic:
1. Fetch all seats from database
2. For each seat, generate a labeled QR code (same as Feature 2)
3. Compose pages: 3x3 grid per page, A4 size at 300 DPI (2480 x 3508 pixels)
4. Grid cell size: approximately 700x900 pixels each, with padding between cells
5. Each cell contains: QR code image (centered) + seat name text below
6. If total seats <= 9: return single PNG directly
7. If total seats > 9: generate multiple pages, package as ZIP file (`qrcode_page1.png`, `qrcode_page2.png`, ...), return with `media_type="application/zip"`

### Frontend

- Add a "导出全部二维码" button next to the "刷新全部Token" button
- On click: call `GET /api/admin/seats/qrcode-batch` with `responseType: 'blob'`
- Check response Content-Type:
  - `image/png`: trigger direct download as `座位二维码.png`
  - `application/zip`: trigger download as `座位二维码.zip`

---

## A4 Page Layout

```
Page size: 2480 x 3508 pixels (A4 at 300 DPI)
Grid: 3 columns x 3 rows
Cell size: ~720 x 1020 pixels
Horizontal: 100px edge margin, 50px gap between cells (100 + 720 + 50 + 720 + 50 + 720 + 100 = 2460, centered)
Vertical: 100px edge margin, 70px gap between cells (100 + 1020 + 70 + 1020 + 70 + 1020 + 100 = 3300, centered)

┌──────────────────────────────────────┐
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  ██████  │ │  ██████  │ │  ██████  │  │
│  │  QR Code │ │  QR Code │ │  QR Code │  │
│  │  ██████  │ │  ██████  │ │  ██████  │  │
│  │          │ │          │ │          │  │
│  │ 座位 A   │ │ 座位 B   │ │ 座位 C   │  │
│  └──────────┘ └──────────┘ └──────────┘  │
│                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  ██████  │ │  ██████  │ │  ██████  │  │
│  │  QR Code │ │  QR Code │ │  QR Code │  │
│  │  ██████  │ │  ██████  │ │  ██████  │  │
│  │          │ │          │ │          │  │
│  │ 座位 D   │ │ 座位 E   │ │ 座位 F   │  │
│  └──────────┘ └──────────┘ └──────────┘  │
│                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  ██████  │ │  ██████  │ │  ██████  │  │
│  │  QR Code │ │  QR Code │ │  QR Code │  │
│  │  ██████  │ │  ██████  │ │  ██████  │  │
│  │          │ │          │ │          │  │
│  │ 座位 G   │ │ 座位 H   │ │ 座位 I   │  │
│  └──────────┘ └──────────┘ └──────────┘  │
└──────────────────────────────────────┘
```

Empty cells (when seats < 9 per page) remain white.

---

## Feature 4: Cancel Active Check-in

### Difference from Force Checkout

- **Force checkout** (`POST /api/admin/force-checkout/{user_id}`): ends the session normally, `check_out_time` is set, time counts towards attendance
- **Cancel check-in** (`POST /api/admin/cancel-checkin/{user_id}`): deletes the session entirely, time does NOT count towards attendance

### Backend

**New endpoint:** `POST /api/admin/cancel-checkin/{user_id}`

- Requires admin role
- Finds the user's active session (`check_out_time IS NULL`)
- If no active session, return 404 "该用户当前没有签到"
- Deletes the session record from the database
- Also deletes the user's cooldown record so they can check in again immediately
- Returns `{"message": "已取消 {username} 的签到"}`

### Frontend

In the seats tab, for seats that are currently occupied (`is_occupied === true`):

- Show a "取消签到" button next to existing action buttons
- On click: show `confirm()` dialog ("确定取消 {occupant_name} 的签到？该段签到时间将不被记录。")
- On confirm: call `POST /api/admin/cancel-checkin/{occupant_user_id}`
- Reload seat list after success

---

## Files Changed

| File | Change |
|------|--------|
| `backend/routers/admin.py` | Add `refresh-all-tokens`, `qrcode-batch`, `cancel-checkin` endpoints; modify `qrcode` endpoint to add label |
| `frontend/src/views/Admin.vue` | Add refresh/export/cancel buttons in seats tab; add download logic; show cancel button on occupied seats |

## Dependencies

- `Pillow` (already available via `qrcode[pil]` which is installed)
- `zipfile` (Python stdlib, no install needed)

## Error Handling

- Token refresh: if any seat fails, the entire transaction rolls back (SQLAlchemy default)
- QR export: if no seats exist, return 400 with message "没有座位可导出"
