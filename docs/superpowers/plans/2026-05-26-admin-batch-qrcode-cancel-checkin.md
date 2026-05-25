# Admin Batch QR Code, Export & Cancel Check-in Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add batch token refresh, QR code with seat name labels, batch A4 grid export, and cancel check-in to the admin dashboard.

**Architecture:** All changes are backend-driven in `admin.py` (3 new endpoints + 1 modified). Frontend `Admin.vue` adds buttons and download logic. Pillow handles image generation; no new dependencies needed.

**Tech Stack:** Python, FastAPI, Pillow (via qrcode[pil]), Vue 3, Axios

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/routers/admin.py` | Add `refresh-all-tokens`, `cancel-checkin`, `qrcode-batch` endpoints; modify `qrcode` endpoint to add seat name label |
| `frontend/src/views/Admin.vue` | Add batch action buttons, cancel check-in button on occupied seats, download logic |

---

### Task 1: Refresh All Tokens

**Files:**
- Modify: `backend/routers/admin.py:180-197` (after existing `refresh_seat_token`)
- Modify: `frontend/src/views/Admin.vue:46-47` (seats tab header)
- Modify: `frontend/src/views/Admin.vue:251-254` (add `refreshAllTokens` function)

- [ ] **Step 1: Add backend endpoint `POST /api/admin/seats/refresh-all-tokens`**

In `backend/routers/admin.py`, add after the `refresh_seat_token` function (after line 197):

```python
@router.post("/seats/refresh-all-tokens")
def refresh_all_tokens(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    import secrets
    seats = db.query(Seat).all()
    for seat in seats:
        seat.token = secrets.token_urlsafe(32)
    db.commit()
    # Return updated list
    result = []
    for seat in seats:
        db.refresh(seat)
        assigned_user = db.query(User).filter(User.id == seat.assigned_user_id).first() if seat.assigned_user_id else None
        active_session = db.query(CheckInSession).filter(
            CheckInSession.seat_id == seat.id,
            CheckInSession.check_out_time.is_(None),
        ).first()
        occupant = db.query(User).filter(User.id == active_session.user_id).first() if active_session else None
        result.append(SeatOut(
            id=seat.id,
            name=seat.name,
            seat_type=seat.seat_type,
            token=seat.token,
            assigned_user_id=seat.assigned_user_id,
            assigned_user_name=assigned_user.name if assigned_user else None,
            is_occupied=active_session is not None,
            occupant_name=occupant.name if occupant else None,
            occupant_user_id=occupant.id if occupant else None,
        ))
    return result
```

- [ ] **Step 2: Add frontend button and handler**

In `frontend/src/views/Admin.vue`, replace the seats tab header (line 46-47):

```html
      <!-- Seats Tab -->
      <div v-if="tab === 'seats'">
        <div class="seat-actions">
          <button class="btn-add" @click="showSeatForm = true; editingSeatId = null; seatForm = { name: '', seat_type: 'shared', assigned_user_id: null }">+ 添加座位</button>
          <button class="btn-batch" @click="refreshAllTokens">刷新全部Token</button>
        </div>
```

In the `<script setup>` section, add after the `refreshToken` function (after line 254):

```javascript
async function refreshAllTokens() {
  if (!confirm('确定刷新全部座位的Token？刷新后旧二维码将失效。')) return
  await api.post('/api/admin/seats/refresh-all-tokens')
  alert('全部Token已刷新')
  await loadSeats()
}
```

- [ ] **Step 3: Test manually**

Start the backend and frontend. Log in as admin. Go to seats tab. Click "刷新全部Token". Confirm dialog appears. After clicking OK, seat list reloads with new tokens.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/admin.py frontend/src/views/Admin.vue
git commit -m "feat: add one-click refresh all tokens"
```

---

### Task 2: QR Code with Seat Name Label

**Files:**
- Modify: `backend/routers/admin.py:248-263` (existing `get_seat_qrcode`)

- [ ] **Step 1: Modify the existing `get_seat_qrcode` endpoint**

Replace the entire `get_seat_qrcode` function in `backend/routers/admin.py` (lines 248-263) with:

```python
@router.get("/seats/{seat_id}/qrcode")
def get_seat_qrcode(seat_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from PIL import Image, ImageDraw, ImageFont

    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    url = f"http://localhost:5173/checkin?token={seat.token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Create canvas: QR code + space for text below
    qr_w, qr_h = qr_img.size
    text_height = 40
    canvas = Image.new("RGB", (qr_w, qr_h + text_height), "white")
    canvas.paste(qr_img, (0, 0))

    # Draw seat name centered below QR code
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=20)
    bbox = draw.textbbox((0, 0), seat.name, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (qr_w - text_w) // 2
    text_y = qr_h + 8
    draw.text((text_x, text_y), seat.name, fill="black", font=font)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
```

- [ ] **Step 2: Test manually**

Click "二维码" button on any seat in the admin panel. The QR code image should now show the seat name centered below the QR code.

- [ ] **Step 3: Commit**

```bash
git add backend/routers/admin.py
git commit -m "feat: add seat name label to QR code"
```

---

### Task 3: Batch Export QR Codes as A4 Grid

**Files:**
- Modify: `backend/routers/admin.py` (add `qrcode-batch` endpoint after `get_seat_qrcode`)
- Modify: `frontend/src/views/Admin.vue` (add `exportAllQR` function)

- [ ] **Step 1: Add backend endpoint `GET /api/admin/seats/qrcode-batch`**

In `backend/routers/admin.py`, add after the `get_seat_qrcode` function:

```python
@router.get("/seats/qrcode-batch")
def batch_qrcode(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    import secrets
    import zipfile
    from PIL import Image, ImageDraw, ImageFont

    seats = db.query(Seat).all()
    if not seats:
        raise HTTPException(status_code=400, detail="没有座位可导出")

    def generate_labeled_qr(seat):
        url = f"http://localhost:5173/checkin?token={seat.token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_w, qr_h = qr_img.size
        text_height = 40
        canvas = Image.new("RGB", (qr_w, qr_h + text_height), "white")
        canvas.paste(qr_img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=20)
        bbox = draw.textbbox((0, 0), seat.name, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (qr_w - text_w) // 2
        draw.text((text_x, qr_h + 8), seat.name, fill="black", font=font)
        return canvas

    # A4 at 300 DPI
    page_w, page_h = 2480, 3508
    cols, rows = 3, 3
    per_page = cols * rows
    margin_x, margin_y = 100, 100
    gap_x, gap_y = 50, 70
    cell_w = (page_w - 2 * margin_x - (cols - 1) * gap_x) // cols
    cell_h = (page_h - 2 * margin_y - (rows - 1) * gap_y) // rows

    # Scale QR to fit in cell (leave room for text)
    qr_target_h = cell_h - 80
    qr_target_w = cell_w - 40

    pages = []
    for page_start in range(0, len(seats), per_page):
        page_seats = seats[page_start:page_start + per_page]
        page = Image.new("RGB", (page_w, page_h), "white")
        for idx, seat in enumerate(page_seats):
            row = idx // cols
            col = idx % cols
            labeled_qr = generate_labeled_qr(seat)
            # Resize to fit cell
            scale = min(qr_target_w / labeled_qr.size[0], qr_target_h / labeled_qr.size[1])
            new_size = (int(labeled_qr.size[0] * scale), int(labeled_qr.size[1] * scale))
            labeled_qr = labeled_qr.resize(new_size, Image.LANCZOS)
            # Center in cell
            x = margin_x + col * (cell_w + gap_x) + (cell_w - new_size[0]) // 2
            y = margin_y + row * (cell_h + gap_y) + (cell_h - new_size[1]) // 2
            page.paste(labeled_qr, (x, y))
        pages.append(page)

    if len(pages) == 1:
        buf = io.BytesIO()
        pages[0].save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    # Multiple pages: return ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, page in enumerate(pages):
            page_buf = io.BytesIO()
            page.save(page_buf, format="PNG")
            page_buf.seek(0)
            zf.writestr(f"qrcode_page{i + 1}.png", page_buf.read())
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=qrcodes.zip"})
```

- [ ] **Step 2: Add frontend export button and handler**

In `frontend/src/views/Admin.vue`, in the `seat-actions` div (added in Task 1), add the export button:

```html
        <div class="seat-actions">
          <button class="btn-add" @click="showSeatForm = true; editingSeatId = null; seatForm = { name: '', seat_type: 'shared', assigned_user_id: null }">+ 添加座位</button>
          <button class="btn-batch" @click="refreshAllTokens">刷新全部Token</button>
          <button class="btn-batch" @click="exportAllQR">导出全部二维码</button>
        </div>
```

Add the handler function after `refreshAllTokens`:

```javascript
async function exportAllQR() {
  const res = await api.get('/api/admin/seats/qrcode-batch', { responseType: 'blob' })
  const contentType = res.headers['content-type']
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  if (contentType && contentType.includes('zip')) {
    a.download = '座位二维码.zip'
  } else {
    a.download = '座位二维码.png'
  }
  a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 3: Add CSS for the new buttons**

In the `<style scoped>` section, add after the `.btn-add` styles:

```css
.seat-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.seat-actions .btn-add {
  flex: 1;
  margin-bottom: 0;
}
.btn-batch {
  padding: 0.75rem 1rem;
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.9rem;
}
```

- [ ] **Step 4: Test manually**

Click "导出全部二维码". If <= 9 seats, a PNG downloads. If > 9, a ZIP downloads with multiple page PNGs. Each page shows 3x3 grid of QR codes with seat names.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/admin.py frontend/src/views/Admin.vue
git commit -m "feat: add batch QR code export as A4 grid"
```

---

### Task 4: Cancel Active Check-in

**Files:**
- Modify: `backend/routers/admin.py` (add `cancel-checkin` endpoint after `force_checkout`)
- Modify: `frontend/src/views/Admin.vue` (add cancel button on occupied seats)

- [ ] **Step 1: Add backend endpoint `POST /api/admin/cancel-checkin/{user_id}`**

In `backend/routers/admin.py`, add after the `force_checkout` function (after line 213):

```python
@router.post("/cancel-checkin/{user_id}")
def cancel_checkin(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from models import Cooldown
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    active = db.query(CheckInSession).filter(
        CheckInSession.user_id == user_id,
        CheckInSession.check_out_time.is_(None),
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="该用户当前没有签到")
    # Delete the session so time is not recorded
    db.delete(active)
    # Clear cooldown so user can check in again immediately
    cooldown = db.query(Cooldown).filter(Cooldown.user_id == user_id).first()
    if cooldown:
        db.delete(cooldown)
    db.commit()
    return {"message": f"已取消 {user.name} 的签到"}
```

- [ ] **Step 2: Add cancel button on occupied seats in frontend**

In `frontend/src/views/Admin.vue`, in the seats tab template, replace the `row-actions` div (lines 86-92):

```html
          <div class="row-actions">
            <button @click="editSeat(s)">编辑</button>
            <button @click="refreshToken(s.id)">刷新Token</button>
            <button @click="viewQR(s.id)">二维码</button>
            <button v-if="s.is_occupied" class="warning" @click="cancelCheckin(s)">取消签到</button>
            <button class="danger" @click="deleteSeat(s.id)">删除</button>
          </div>
```

Add the handler function in `<script setup>`:

```javascript
async function cancelCheckin(seat) {
  if (!confirm(`确定取消 ${seat.occupant_name} 的签到？该段签到时间将不被记录。`)) return
  await api.post(`/api/admin/cancel-checkin/${seat.occupant_user_id}`)
  await loadSeats()
}
```

Add CSS for the warning button:

```css
.row-actions button.warning {
  color: #e65100;
  border-color: #e65100;
}
```

- [ ] **Step 3: Test manually**

Check in as a test user. Go to admin seats tab. The occupied seat should show a "取消签到" button. Click it, confirm. The seat becomes unoccupied. Check the test user's attendance - the cancelled session time should NOT appear.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/admin.py frontend/src/views/Admin.vue
git commit -m "feat: add cancel check-in for admin"
```
