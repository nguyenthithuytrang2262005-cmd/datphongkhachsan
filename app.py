import streamlit as st
import sqlite3
import hashlib
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

# ============================================================
# HAPPY HOTEL - HOTEL BOOKING APP
# Streamlit + SQLite, no external API required
# ============================================================

st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "happy_hotel.db"

# ---------- Styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #f6f8fb; }
.block-container { padding-top: 1rem; max-width: 1400px; }
.hero {
    padding: 38px 34px; border-radius: 24px;
    background: linear-gradient(135deg,#0b5cff 0%,#5b8cff 55%,#7c5cff 100%);
    color: white; margin-bottom: 22px;
    box-shadow: 0 12px 35px rgba(30,80,180,.20);
}
.hero h1 { font-size: 42px; margin: 0; font-weight: 800; }
.hero p { font-size: 17px; opacity: .92; }
.card {
    background: white; border: 1px solid #e8ecf2; border-radius: 18px;
    padding: 18px; margin-bottom: 15px;
    box-shadow: 0 5px 18px rgba(24,39,75,.06);
}
.room-img {
    height: 180px; border-radius: 15px; display:flex; align-items:center;
    justify-content:center; font-size:72px;
    background: linear-gradient(135deg,#dceaff,#f1edff);
}
.price { color:#0b5cff; font-size:24px; font-weight:800; }
.small { color:#667085; font-size:13px; }
.badge {
    display:inline-block; padding:5px 10px; border-radius:20px;
    background:#edf4ff; color:#0b5cff; font-size:12px; font-weight:700;
}
.chatbox {
    background:#f7f9fc; border-radius:16px; padding:12px;
    border:1px solid #e5eaf1;
}
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ---------- Database ----------
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'customer',
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        capacity INTEGER NOT NULL,
        beds TEXT NOT NULL,
        size TEXT NOT NULL,
        description TEXT NOT NULL,
        amenities TEXT NOT NULL,
        image_emoji TEXT DEFAULT '🛏️',
        active INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        checkin TEXT NOT NULL,
        checkout TEXT NOT NULL,
        guests INTEGER NOT NULL,
        total REAL NOT NULL,
        status TEXT DEFAULT 'Confirmed',
        special_request TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(room_id) REFERENCES rooms(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_percent REAL NOT NULL,
        max_discount REAL NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)

    cur.execute("SELECT COUNT(*) AS n FROM rooms")
    if cur.fetchone()["n"] == 0:
        rooms = [
            ("Deluxe Garden", "Deluxe", 950000, 2, "1 King", "32 m²",
             "Phòng nghỉ sang trọng hướng vườn, phù hợp cho cặp đôi.",
             "Wi-Fi miễn phí,Smart TV,Điều hòa,Minibar,Bữa sáng,Bồn tắm", "🌿"),
            ("Deluxe Ocean", "Deluxe", 1250000, 2, "1 King", "35 m²",
             "Không gian thoáng với tầm nhìn biển tuyệt đẹp.",
             "Wi-Fi miễn phí,Smart TV,Điều hòa,Minibar,Bữa sáng,Ban công", "🌊"),
            ("Family Suite", "Suite", 1850000, 4, "1 King + 2 Single", "55 m²",
             "Suite rộng rãi dành cho gia đình hoặc nhóm bạn.",
             "Wi-Fi miễn phí,Smart TV,Điều hòa,Minibar,Bữa sáng,Phòng khách,Bồn tắm", "👨‍👩‍👧‍👦"),
            ("Honeymoon Suite", "Suite", 2200000, 2, "1 King", "60 m²",
             "Không gian lãng mạn dành cho kỳ nghỉ đặc biệt.",
             "Wi-Fi miễn phí,Smart TV,Điều hòa,Minibar,Bữa sáng,Bồn tắm,Trang trí lãng mạn", "💖"),
            ("Presidential Villa", "Villa", 4500000, 6, "2 King + 2 Single", "120 m²",
             "Villa riêng tư cao cấp với hồ bơi và không gian sinh hoạt riêng.",
             "Wi-Fi miễn phí,Smart TV,Điều hòa,Minibar,Bữa sáng,Hồ bơi riêng,Phòng khách,Bếp", "👑"),
            ("Standard Cozy", "Standard", 650000, 2, "1 Queen", "24 m²",
             "Lựa chọn tiết kiệm nhưng đầy đủ tiện nghi.",
             "Wi-Fi miễn phí,Smart TV,Điều hòa,Bữa sáng", "🛏️"),
        ]
        cur.executemany("""
            INSERT INTO rooms
            (name,category,price,capacity,beds,size,description,amenities,image_emoji)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, rooms)

    cur.execute("SELECT COUNT(*) AS n FROM coupons")
    if cur.fetchone()["n"] == 0:
        cur.executemany(
            "INSERT INTO coupons(code,discount_percent,max_discount) VALUES (?,?,?)",
            [("HAPPY10", 10, 500000), ("WELCOME15", 15, 700000), ("SUMMER20", 20, 1000000)]
        )

    # Demo admin account
    admin_email = "admin@happyhotel.vn"
    cur.execute("SELECT id FROM users WHERE email=?", (admin_email,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users(full_name,email,phone,password_hash,role,created_at)
            VALUES (?,?,?,?,?,?)
        """, (
            "HAPPY HOTEL Admin", admin_email, "0900000000",
            hash_password("admin123"), "admin", datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def query(sql, params=(), fetch=True):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return rows


def scalar(sql, params=()):
    rows = query(sql, params)
    return rows[0][0] if rows else None


def get_room(room_id):
    rows = query("SELECT * FROM rooms WHERE id=? AND active=1", (room_id,))
    return rows[0] if rows else None


def nights_between(checkin, checkout):
    return max(0, (checkout - checkin).days)


def room_is_available(room_id, checkin, checkout, exclude_booking=None):
    sql = """
        SELECT COUNT(*) FROM bookings
        WHERE room_id=?
        AND status NOT IN ('Cancelled')
        AND date(checkin) < date(?)
        AND date(checkout) > date(?)
    """
    params = [room_id, checkout.isoformat(), checkin.isoformat()]
    if exclude_booking:
        sql += " AND id != ?"
        params.append(exclude_booking)
    return scalar(sql, params) == 0


def format_vnd(value):
    return f"{int(round(value)):,}".replace(",", ".") + " đ"


def booking_code():
    return "HH-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:5].upper()


init_db()

# ---------- Session ----------
defaults = {
    "page": "Trang chủ",
    "user": None,
    "selected_room": None,
    "chat": [],
    "last_booking": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------- Authentication ----------
def login(email, password):
    rows = query(
        "SELECT * FROM users WHERE email=? AND password_hash=?",
        (email.strip().lower(), hash_password(password))
    )
    if rows:
        st.session_state.user = dict(rows[0])
        return True
    return False


def register(full_name, email, phone, password):
    try:
        query("""
            INSERT INTO users(full_name,email,phone,password_hash,created_at)
            VALUES (?,?,?,?,?)
        """, (full_name.strip(), email.strip().lower(), phone.strip(),
              hash_password(password), datetime.now().isoformat()), fetch=False)
        return True
    except sqlite3.IntegrityError:
        return False


def logout():
    st.session_state.user = None
    st.session_state.selected_room = None
    st.session_state.page = "Trang chủ"


# ---------- Header ----------
def go(page):
    st.session_state.page = page
    st.rerun()


with st.sidebar:
    st.markdown("## 🏨 HAPPY HOTEL")
    st.caption("Nền tảng đặt phòng thông minh")

    if st.session_state.user:
        u = st.session_state.user
        st.success(f"Xin chào, {u['full_name']}!")
        st.write(f"📧 {u['email']}")
        if st.button("🏠 Trang chủ", use_container_width=True):
            go("Trang chủ")
        if st.button("🔎 Tìm phòng", use_container_width=True):
            go("Tìm phòng")
        if st.button("📋 Đặt phòng của tôi", use_container_width=True):
            go("Đặt phòng")
        if st.button("💬 Trợ lý HAPPY", use_container_width=True):
            go("Chatbot")
        if st.button("⭐ Đánh giá", use_container_width=True):
            go("Đánh giá")
        if u["role"] == "admin":
            st.divider()
            if st.button("⚙️ Quản trị", use_container_width=True):
                go("Quản trị")
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout()
            st.rerun()
    else:
        st.info("Đăng nhập để quản lý đặt phòng.")
        if st.button("🔐 Đăng nhập", use_container_width=True):
            go("Đăng nhập")
        if st.button("📝 Đăng ký", use_container_width=True):
            go("Đăng ký")

    st.divider()
    st.markdown("### ✨ Tiện ích")
    st.write("📞 Hotline: **1900 6868**")
    st.write("📧 hello@happyhotel.vn")
    st.write("📍 Vũng Tàu, Việt Nam")
    st.caption("© 2026 HAPPY HOTEL")


# ---------- Home ----------
def home_page():
    st.markdown("""
    <div class="hero">
        <h1>HAPPY HOTEL 🏨</h1>
        <p>Đặt phòng dễ dàng • Giá tốt • Trải nghiệm nghỉ dưỡng đáng nhớ</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔎 Tìm phòng phù hợp với bạn")
    c1, c2, c3, c4 = st.columns([1.3,1.3,1,1])
    with c1:
        ci = st.date_input("Nhận phòng", date.today() + timedelta(days=1), min_value=date.today())
    with c2:
        co = st.date_input("Trả phòng", ci + timedelta(days=1), min_value=ci + timedelta(days=1))
    with c3:
        guests = st.number_input("Số khách", 1, 12, 2)
    with c4:
        st.write("")
        st.write("")
        if st.button("🔍 Tìm phòng ngay", type="primary", use_container_width=True):
            st.session_state.search = {"checkin": ci, "checkout": co, "guests": guests}
            go("Tìm phòng")

    st.divider()
    st.markdown("### 🌟 Phòng nổi bật")
    rooms = query("SELECT * FROM rooms WHERE active=1 ORDER BY price ASC LIMIT 4")
    cols = st.columns(4)
    for col, r in zip(cols, rooms):
        with col:
            st.markdown(f'<div class="room-img">{r["image_emoji"]}</div>', unsafe_allow_html=True)
            st.markdown(f"**{r['name']}**")
            st.caption(f"{r['category']} • {r['size']} • tối đa {r['capacity']} khách")
            st.markdown(f'<span class="price">{format_vnd(r["price"])}</span> / đêm', unsafe_allow_html=True)
            if st.button("Xem phòng", key=f"home_room_{r['id']}", use_container_width=True):
                st.session_state.selected_room = r["id"]
                go("Chi tiết phòng")

    st.divider()
    st.markdown("### 💎 Vì sao chọn HAPPY HOTEL?")
    a,b,c,d = st.columns(4)
    for col, icon, title, text_ in [
        (a,"💰","Giá minh bạch","Không phí ẩn"),
        (b,"⚡","Đặt phòng nhanh","Hoàn tất trong vài bước"),
        (c,"🔒","An toàn","Dữ liệu booking được lưu bảo mật"),
        (d,"💬","Hỗ trợ 24/7","Chatbot HAPPY luôn sẵn sàng"),
    ]:
        with col:
            st.markdown(f'<div class="card"><h3>{icon} {title}</h3><p>{text_}</p></div>', unsafe_allow_html=True)


# ---------- Search ----------
def search_page():
    st.title("🔎 Tìm phòng")
    rooms = query("SELECT * FROM rooms WHERE active=1 ORDER BY price")

    with st.expander("🎛️ Bộ lọc", expanded=True):
        a,b,c,d = st.columns(4)
        with a:
            checkin = st.date_input("Nhận phòng", date.today()+timedelta(days=1),
                                    min_value=date.today(), key="search_ci")
        with b:
            checkout = st.date_input("Trả phòng", checkin+timedelta(days=1),
                                     min_value=checkin+timedelta(days=1), key="search_co")
        with c:
            guests = st.number_input("Số khách", 1, 12, 2, key="search_guests")
        with d:
            categories = sorted(set(r["category"] for r in rooms))
            category = st.selectbox("Loại phòng", ["Tất cả"] + categories)

        min_price, max_price = st.slider(
            "Khoảng giá / đêm",
            300000, 5000000, (300000, 5000000), step=50000,
            format="%d đ"
        )

    filtered = [
        r for r in rooms
        if r["capacity"] >= guests
        and min_price <= r["price"] <= max_price
        and (category == "Tất cả" or r["category"] == category)
        and room_is_available(r["id"], checkin, checkout)
    ]

    st.info(f"Tìm thấy **{len(filtered)}** phòng còn trống • {nights_between(checkin, checkout)} đêm")

    if not filtered:
        st.warning("Không có phòng phù hợp. Hãy thử thay đổi ngày, số khách hoặc bộ lọc.")
        return

    for r in filtered:
        with st.container():
            c1,c2,c3 = st.columns([1.2,2.2,1])
            with c1:
                st.markdown(f'<div class="room-img">{r["image_emoji"]}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f"### {r['name']} <span class='badge'>{r['category']}</span>", unsafe_allow_html=True)
                st.write(r["description"])
                st.caption(f"🛏️ {r['beds']}  |  📐 {r['size']}  |  👥 Tối đa {r['capacity']} khách")
                st.caption(" • ".join(r["amenities"].split(",")))
            with c3:
                st.markdown(f'<div class="price">{format_vnd(r["price"])}</div><div class="small">/ đêm</div>', unsafe_allow_html=True)
                total = r["price"] * nights_between(checkin, checkout)
                st.caption(f"Tổng dự kiến: {format_vnd(total)}")
                if st.button("Xem & đặt", key=f"search_{r['id']}", type="primary", use_container_width=True):
                    st.session_state.selected_room = r["id"]
                    st.session_state.booking_dates = {"checkin": checkin, "checkout": checkout, "guests": guests}
                    go("Chi tiết phòng")
            st.divider()


# ---------- Room Detail ----------
def room_detail_page():
    if not st.session_state.selected_room:
        go("Tìm phòng")
    r = get_room(st.session_state.selected_room)
    if not r:
        st.error("Không tìm thấy phòng.")
        return

    st.title(f"{r['image_emoji']} {r['name']}")
    c1,c2 = st.columns([1,1.3])
    with c1:
        st.markdown(f'<div class="room-img" style="height:320px;font-size:120px">{r["image_emoji"]}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"### {r['category']} • {r['size']}")
        st.write(r["description"])
        st.markdown(f"**🛏️ Giường:** {r['beds']}")
        st.markdown(f"**👥 Sức chứa:** {r['capacity']} khách")
        st.markdown(f"**💰 Giá:** <span class='price'>{format_vnd(r['price'])}</span> / đêm", unsafe_allow_html=True)
        st.markdown("**Tiện nghi:**")
        for x in r["amenities"].split(","):
            st.markdown(f"✓ {x}")

    st.divider()
    st.subheader("📅 Đặt phòng")
    if not st.session_state.user:
        st.warning("Vui lòng đăng nhập để đặt phòng.")
        if st.button("Đăng nhập"):
            go("Đăng nhập")
        return

    b = st.session_state.get("booking_dates", {})
    a,bcol,c = st.columns(3)
    with a:
        ci = st.date_input("Nhận phòng", b.get("checkin", date.today()+timedelta(days=1)),
                           min_value=date.today())
    with bcol:
        co = st.date_input("Trả phòng", b.get("checkout", ci+timedelta(days=1)),
                           min_value=ci+timedelta(days=1))
    with c:
        guests = st.number_input("Số khách", 1, r["capacity"], b.get("guests", min(2,r["capacity"])))

    nights = nights_between(ci, co)
    base = r["price"] * nights

    d,e = st.columns([2,1])
    with d:
        coupon = st.text_input("🎟️ Mã giảm giá (HAPPY10, WELCOME15, SUMMER20)").strip().upper()
        special = st.text_area("📝 Yêu cầu đặc biệt", placeholder="Ví dụ: phòng tầng cao, trang trí sinh nhật...")
    discount = 0
    coupon_valid = None
    if coupon:
        rows = query("SELECT * FROM coupons WHERE code=? AND active=1", (coupon,))
        if rows:
            cp = rows[0]
            discount = min(base * cp["discount_percent"]/100, cp["max_discount"])
            coupon_valid = True
        else:
            coupon_valid = False

    total = max(0, base - discount)
    with e:
        st.markdown("### 💳 Tóm tắt")
        st.write(f"Giá phòng: **{format_vnd(base)}**")
        st.write(f"Giảm giá: **-{format_vnd(discount)}**")
        st.markdown(f"### Tổng: {format_vnd(total)}")
        if coupon:
            st.success("Áp dụng mã thành công!") if coupon_valid else st.error("Mã không hợp lệ.")

    if st.button("✅ XÁC NHẬN ĐẶT PHÒNG", type="primary", use_container_width=True):
        if nights < 1:
            st.error("Ngày trả phòng phải sau ngày nhận phòng.")
        elif guests > r["capacity"]:
            st.error("Số khách vượt sức chứa phòng.")
        elif not room_is_available(r["id"], ci, co):
            st.error("Phòng vừa được đặt trong khoảng thời gian này. Vui lòng chọn ngày khác.")
        else:
            code = booking_code()
            query("""
                INSERT INTO bookings
                (booking_code,user_id,room_id,checkin,checkout,guests,total,status,special_request,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (code, st.session_state.user["id"], r["id"], ci.isoformat(),
                  co.isoformat(), guests, total, "Confirmed", special, datetime.now().isoformat()),
                 fetch=False)
            st.session_state.last_booking = code
            st.success(f"🎉 Đặt phòng thành công! Mã đặt phòng: **{code}**")
            st.balloons()
            if st.button("Xem đặt phòng của tôi"):
                go("Đặt phòng")


# ---------- My Bookings ----------
def my_bookings_page():
    if not st.session_state.user:
        go("Đăng nhập")
    st.title("📋 Đặt phòng của tôi")
    rows = query("""
        SELECT b.*, r.name AS room_name, r.image_emoji
        FROM bookings b JOIN rooms r ON b.room_id=r.id
        WHERE b.user_id=? ORDER BY b.created_at DESC
    """, (st.session_state.user["id"],))

    if not rows:
        st.info("Bạn chưa có đặt phòng nào.")
        if st.button("🔎 Tìm phòng"):
            go("Tìm phòng")
        return

    for b in rows:
        status_icon = {"Confirmed":"🟢","Cancelled":"🔴","Completed":"🔵"}.get(b["status"],"🟡")
        with st.expander(f"{status_icon} {b['booking_code']} • {b['room_name']} • {format_vnd(b['total'])}"):
            a,bcol,c = st.columns(3)
            a.write(f"**Nhận phòng:** {b['checkin']}")
            bcol.write(f"**Trả phòng:** {b['checkout']}")
            c.write(f"**Khách:** {b['guests']}")
            st.write(f"**Trạng thái:** {b['status']}")
            if b["special_request"]:
                st.write(f"**Yêu cầu:** {b['special_request']}")
            if b["status"] == "Confirmed":
                if st.button("❌ Hủy đặt phòng", key=f"cancel_{b['id']}"):
                    query("UPDATE bookings SET status='Cancelled' WHERE id=?", (b["id"],), fetch=False)
                    st.success("Đã hủy đặt phòng.")
                    st.rerun()


# ---------- Reviews ----------
def reviews_page():
    st.title("⭐ Đánh giá khách hàng")
    reviews = query("""
        SELECT rv.*, u.full_name, r.name AS room_name
        FROM reviews rv JOIN users u ON rv.user_id=u.id
        JOIN rooms r ON rv.room_id=r.id
        ORDER BY rv.created_at DESC LIMIT 30
    """)
    if reviews:
        for x in reviews:
            st.markdown(
                f'<div class="card"><b>{x["full_name"]}</b> • {x["room_name"]}<br>'
                f'{"⭐"*x["rating"]}<br>{x["comment"]}</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("Chưa có đánh giá.")

    if st.session_state.user:
        st.divider()
        st.subheader("✍️ Viết đánh giá")
        completed = query("""
            SELECT DISTINCT r.id, r.name FROM bookings b
            JOIN rooms r ON b.room_id=r.id
            WHERE b.user_id=? AND b.status IN ('Confirmed','Completed')
        """, (st.session_state.user["id"],))
        if completed:
            labels = {f"{x['name']} (ID {x['id']})":x["id"] for x in completed}
            room_label = st.selectbox("Chọn phòng", list(labels))
            rating = st.slider("Số sao", 1, 5, 5)
            comment = st.text_area("Nhận xét")
            if st.button("Gửi đánh giá", type="primary"):
                if comment.strip():
                    query("""
                        INSERT INTO reviews(user_id,room_id,rating,comment,created_at)
                        VALUES (?,?,?,?,?)
                    """, (st.session_state.user["id"], labels[room_label], rating,
                          comment.strip(), datetime.now().isoformat()), fetch=False)
                    st.success("Cảm ơn bạn đã đánh giá!")
                    st.rerun()
        else:
            st.caption("Bạn cần có đặt phòng để gửi đánh giá.")


# ---------- Chatbot ----------
def bot_reply(message):
    m = message.lower().strip()
    if any(x in m for x in ["xin chào","hello","hi","chào"]):
        return "Xin chào! 👋 Mình là HAPPY, trợ lý ảo của HAPPY HOTEL. Mình có thể giúp bạn tìm phòng, tư vấn giá, mã giảm giá, chính sách và đặt phòng."
    if "giá" in m or "bao nhiêu" in m or "phòng" in m:
        rooms = query("SELECT name, price, capacity FROM rooms WHERE active=1 ORDER BY price")
        text = "Đây là giá phòng hiện tại:\n\n"
        for r in rooms:
            text += f"• **{r['name']}**: {format_vnd(r['price'])}/đêm – tối đa {r['capacity']} khách\n"
        return text
    if "giảm" in m or "coupon" in m or "mã" in m:
        return "Bạn có thể thử các mã: **HAPPY10** (10%), **WELCOME15** (15%), **SUMMER20** (20%). Mức giảm tối đa tùy từng mã."
    if "check-in" in m or "nhận phòng" in m:
        return "Giờ nhận phòng tiêu chuẩn là **14:00**. Nếu bạn muốn nhận phòng sớm, hãy ghi yêu cầu đặc biệt khi đặt phòng hoặc liên hệ lễ tân."
    if "check-out" in m or "trả phòng" in m:
        return "Giờ trả phòng tiêu chuẩn là **12:00**."
    if "hủy" in m:
        return "Bạn có thể vào **Đặt phòng của tôi** và chọn **Hủy đặt phòng** đối với booking đang ở trạng thái Confirmed."
    if "địa chỉ" in m or "ở đâu" in m:
        return "HAPPY HOTEL hiện được thiết kế theo mô hình khách sạn nghỉ dưỡng tại **Vũng Tàu, Việt Nam**."
    if "tiện nghi" in m or "amenities" in m:
        return "Các tiện nghi nổi bật gồm Wi-Fi, Smart TV, điều hòa, minibar, bữa sáng; một số hạng phòng có bồn tắm, ban công, hồ bơi riêng và bếp."
    if "liên hệ" in m or "hotline" in m:
        return "Hotline HAPPY HOTEL: **1900 6868** • Email: **hello@happyhotel.vn**."
    return "Mình chưa hiểu hoàn toàn câu hỏi. Bạn có thể hỏi mình về **giá phòng, phòng trống, mã giảm giá, nhận/trả phòng, hủy booking, tiện nghi hoặc liên hệ khách sạn** nhé. 😊"


def chatbot_page():
    st.title("💬 HAPPY – Trợ lý đặt phòng")
    st.caption("Trợ lý tự động của HAPPY HOTEL • phản hồi tức thì")

    if not st.session_state.chat:
        st.session_state.chat = [{
            "role":"assistant",
            "content":"Xin chào! 👋 Mình là HAPPY. Bạn muốn tìm phòng, hỏi giá hay cần hỗ trợ đặt phòng?"
        }]

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Nhập câu hỏi của bạn...")
    if prompt:
        st.session_state.chat.append({"role":"user","content":prompt})
        reply = bot_reply(prompt)
        st.session_state.chat.append({"role":"assistant","content":reply})
        st.rerun()


# ---------- Login/Register ----------
def login_page():
    st.title("🔐 Đăng nhập")
    c1,c2 = st.columns([1,1])
    with c1:
        email = st.text_input("Email")
        password = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập", type="primary", use_container_width=True):
            if login(email,password):
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Email hoặc mật khẩu không đúng.")
    with c2:
        st.info("Tài khoản quản trị demo:\n\n**admin@happyhotel.vn**\n\n**admin123**")


def register_page():
    st.title("📝 Tạo tài khoản")
    name = st.text_input("Họ và tên")
    email = st.text_input("Email")
    phone = st.text_input("Số điện thoại")
    password = st.text_input("Mật khẩu", type="password")
    password2 = st.text_input("Nhập lại mật khẩu", type="password")

    if st.button("Tạo tài khoản", type="primary"):
        if not all([name.strip(), email.strip(), password]):
            st.error("Vui lòng điền đầy đủ thông tin bắt buộc.")
        elif password != password2:
            st.error("Mật khẩu nhập lại không khớp.")
        elif len(password) < 6:
            st.error("Mật khẩu cần ít nhất 6 ký tự.")
        elif register(name,email,phone,password):
            st.success("Đăng ký thành công! Bạn có thể đăng nhập.")
        else:
            st.error("Email đã tồn tại.")


# ---------- Admin ----------
def admin_page():
    if not st.session_state.user or st.session_state.user["role"] != "admin":
        st.error("Bạn không có quyền truy cập.")
        return

    st.title("⚙️ Bảng điều khiển quản trị")
    total_users = scalar("SELECT COUNT(*) FROM users WHERE role='customer'")
    total_bookings = scalar("SELECT COUNT(*) FROM bookings")
    confirmed = scalar("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'")
    revenue = scalar("SELECT COALESCE(SUM(total),0) FROM bookings WHERE status!='Cancelled'")

    a,b,c,d = st.columns(4)
    a.metric("👤 Khách hàng", total_users)
    b.metric("📋 Tổng booking", total_bookings)
    c.metric("🟢 Booking đang xác nhận", confirmed)
    d.metric("💰 Doanh thu", format_vnd(revenue))

    st.divider()
    tab1,tab2,tab3 = st.tabs(["📋 Booking","🏨 Phòng","🎟️ Mã giảm giá"])

    with tab1:
        rows = query("""
            SELECT b.id,b.booking_code,u.full_name,u.email,r.name AS room_name,
                   b.checkin,b.checkout,b.guests,b.total,b.status
            FROM bookings b
            JOIN users u ON b.user_id=u.id
            JOIN rooms r ON b.room_id=r.id
            ORDER BY b.created_at DESC
        """)
        if rows:
            st.dataframe([dict(x) for x in rows], use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có booking.")

    with tab2:
        rooms = query("SELECT * FROM rooms ORDER BY id")
        for r in rooms:
            c1,c2,c3 = st.columns([3,2,1])
            c1.write(f"**{r['name']}** — {format_vnd(r['price'])}")
            c2.write(f"{r['category']} • {r['capacity']} khách")
            c3.write("Đang hoạt động" if r["active"] else "Đã ẩn")
            if st.button("Ẩn/Hiện", key=f"toggle_{r['id']}"):
                query("UPDATE rooms SET active=? WHERE id=?", (0 if r["active"] else 1, r["id"]), fetch=False)
                st.rerun()

    with tab3:
        coupons = query("SELECT * FROM coupons")
        st.dataframe([dict(x) for x in coupons], use_container_width=True, hide_index=True)


# ---------- Router ----------
page = st.session_state.page

if page == "Trang chủ":
    home_page()
elif page == "Tìm phòng":
    search_page()
elif page == "Chi tiết phòng":
    room_detail_page()
elif page == "Đặt phòng":
    my_bookings_page()
elif page == "Đánh giá":
    reviews_page()
elif page == "Chatbot":
    st.subheader("🤖 HAPPY HOTEL AI")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Xin chào! Tôi là trợ lý HAPPY HOTEL. Tôi có thể tư vấn hạng phòng, giá và giờ check-in."
        }
    ]

# Hiển thị lịch sử
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Nhập tin nhắn
prompt = st.chat_input("Nhập câu hỏi...")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    text = prompt.lower()

    if "giá" in text:
        reply = """**Bảng giá HAPPY HOTEL**

- Standard: 500.000đ
- Superior: 650.000đ
- Deluxe: 850.000đ
- Executive: 1.100.000đ
- Suite: 1.500.000đ
- Presidential: 2.500.000đ"""
    elif "check in" in text or "check-in" in text:
        reply = "🕑 Check-in từ **14:00** mỗi ngày."
    elif "check out" in text or "check-out" in text:
        reply = "🕛 Check-out trước **12:00**."
    elif "wifi" in text:
        reply = "📶 WiFi miễn phí toàn khách sạn."
    else:
        reply = "Cảm ơn bạn! Tôi có thể hỗ trợ đặt phòng, giá, tiện ích và thủ tục lưu trú."

    st.session_state.messages.append(
        {"role": "assistant", "content": reply}
    )

    st.rerun()
elif page == "Đăng nhập":
    login_page()
elif page == "Đăng ký":
    register_page()
elif page == "Quản trị":
    admin_page()
else:
    home_page()

