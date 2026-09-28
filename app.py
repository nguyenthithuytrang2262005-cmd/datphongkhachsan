
import streamlit as st
import sqlite3
import hashlib
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd

# =========================================================
# HAPPY HOTEL - HOTEL BOOKING APP
# Run: streamlit run app.py
# =========================================================

st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "happy_hotel.db"

# -----------------------------
# Theme / CSS
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f6fbff 0%, #fffaf4 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f3d56 0%, #145374 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    .hero {
        padding: 34px;
        border-radius: 24px;
        color: white;
        background:
          linear-gradient(120deg, rgba(5,48,69,.92), rgba(24,119,143,.82)),
          url("https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1600&q=80");
        background-size: cover;
        background-position: center;
        box-shadow: 0 12px 35px rgba(0,0,0,.12);
        margin-bottom: 24px;
    }
    .hero h1 { font-size: 46px; margin: 0; }
    .hero p { font-size: 18px; opacity: .95; }
    .card {
        background: white;
        border-radius: 18px;
        padding: 18px;
        margin: 8px 0;
        box-shadow: 0 5px 20px rgba(0,0,0,.07);
        border: 1px solid #edf2f5;
    }
    .price { color: #0d7a68; font-size: 24px; font-weight: 800; }
    .badge {
        display:inline-block; padding:5px 10px; border-radius:20px;
        background:#e8f8f3; color:#08745e; font-weight:700; font-size:12px;
    }
    .deal {
        background: linear-gradient(135deg,#fff0d7,#ffe2a9);
        border-radius:18px; padding:20px; border:1px solid #ffd27a;
    }
    .success-box {
        background:#eafaf2; border:1px solid #a9e5c5;
        border-radius:15px; padding:16px;
    }
    .danger-box {
        background:#fff0f0; border:1px solid #ffc4c4;
        border-radius:15px; padding:16px;
    }
    .section-title {
        font-size: 28px; font-weight: 800; color:#103e52;
        margin: 12px 0 8px;
    }
    .small { color:#6c7a86; font-size:13px; }
    div.stButton > button {
        border-radius: 12px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Database
# -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'customer',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            floor INTEGER,
            capacity INTEGER NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            amenities TEXT,
            image TEXT,
            status TEXT DEFAULT 'available'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            room_id INTEGER,
            guest_name TEXT NOT NULL,
            guest_email TEXT,
            guest_phone TEXT,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            guests INTEGER NOT NULL,
            nights INTEGER NOT NULL,
            room_price REAL NOT NULL,
            services_price REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            total REAL NOT NULL,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending',
            booking_status TEXT DEFAULT 'confirmed',
            special_request TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            user_id INTEGER,
            room_id INTEGER,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT,
            percent REAL DEFAULT 0,
            amount REAL DEFAULT 0,
            min_total REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            expires_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender TEXT,
            message TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Seed admin
    cur.execute("SELECT id FROM users WHERE email=?", ("admin@happyhotel.vn",))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users(full_name,email,phone,password,role,created_at)
            VALUES(?,?,?,?,?,?)
        """, (
            "Quản trị viên HAPPY HOTEL",
            "admin@happyhotel.vn",
            "0900000000",
            hash_password("admin123"),
            "admin",
            datetime.now().isoformat(timespec="seconds")
        ))

    # Seed customer
    cur.execute("SELECT id FROM users WHERE email=?", ("guest@happyhotel.vn",))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users(full_name,email,phone,password,role,created_at)
            VALUES(?,?,?,?,?,?)
        """, (
            "Khách hàng mẫu",
            "guest@happyhotel.vn",
            "0911111111",
            hash_password("123456"),
            "customer",
            datetime.now().isoformat(timespec="seconds")
        ))

    # Seed rooms
    cur.execute("SELECT COUNT(*) AS c FROM rooms")
    if cur.fetchone()["c"] == 0:
        rooms = [
            ("101","Standard",1,2,650000,"Phòng tiêu chuẩn ấm cúng, phù hợp cặp đôi.",
             "WiFi, TV 43 inch, Điều hòa, Máy sấy, Nước suối",
             "https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=900&q=80"),
            ("102","Standard",1,2,690000,"Phòng tiêu chuẩn có cửa sổ hướng thành phố.",
             "WiFi, TV 43 inch, Điều hòa, Minibar, Máy sấy",
             "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=900&q=80"),
            ("201","Deluxe",2,2,950000,"Không gian rộng, nội thất hiện đại.",
             "WiFi, Smart TV, Điều hòa, Minibar, Bồn tắm",
             "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=900&q=80"),
            ("202","Deluxe",2,3,1050000,"Deluxe hướng thành phố, thích hợp gia đình nhỏ.",
             "WiFi, Smart TV, Minibar, Bồn tắm, Bữa sáng",
             "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=900&q=80"),
            ("301","Suite",3,3,1600000,"Suite sang trọng với phòng khách riêng.",
             "WiFi, Smart TV, Sofa, Minibar, Bồn tắm, Bữa sáng",
             "https://images.unsplash.com/photo-1595576508898-0ad5c879a061?auto=format&fit=crop&w=900&q=80"),
            ("302","Suite",3,4,1900000,"Suite gia đình cao cấp, diện tích lớn.",
             "WiFi, Smart TV, Sofa, Minibar, Bồn tắm, Bữa sáng, Ban công",
             "https://images.unsplash.com/photo-1601918774946-25832a4be0d6?auto=format&fit=crop&w=900&q=80"),
            ("401","VIP",4,2,2500000,"Phòng VIP riêng tư với view tuyệt đẹp.",
             "WiFi, Smart TV, Lounge, Minibar, Jacuzzi, Bữa sáng",
             "https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=900&q=80"),
            ("402","VIP",4,4,3200000,"Royal VIP dành cho kỳ nghỉ đặc biệt.",
             "WiFi, Smart TV, Phòng khách, Jacuzzi, Minibar, Butler",
             "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=900&q=80"),
        ]
        cur.executemany("""
            INSERT INTO rooms(room_number,room_type,floor,capacity,price,description,amenities,image)
            VALUES(?,?,?,?,?,?,?,?)
        """, rooms)

    # Seed promotions
    cur.execute("SELECT COUNT(*) AS c FROM promotions")
    if cur.fetchone()["c"] == 0:
        promos = [
            ("HAPPY10","Giảm 10% cho đơn đặt phòng.",10,0,0,1,(date.today()+timedelta(days=365)).isoformat()),
            ("WELCOME200","Giảm 200.000đ cho đơn từ 1.500.000đ.",0,200000,1500000,1,(date.today()+timedelta(days=365)).isoformat()),
            ("WEEKEND15","Ưu đãi cuối tuần 15%.",15,0,0,1,(date.today()+timedelta(days=365)).isoformat()),
        ]
        cur.executemany("""
            INSERT INTO promotions(code,description,percent,amount,min_total,active,expires_at)
            VALUES(?,?,?,?,?,?,?)
        """, promos)

    conn.commit()
    conn.close()

init_db()


# -----------------------------
# Helpers
# -----------------------------
def query(sql, params=(), one=False):
    conn = get_conn()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    if one:
        return rows[0] if rows else None
    return rows

def execute(sql, params=()):
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def money(v):
    return f"{v:,.0f} đ"

def nights_between(check_in, check_out):
    return max(1, (check_out - check_in).days)

def available_rooms(check_in, check_out, guests=1, room_type="Tất cả"):
    sql = """
    SELECT * FROM rooms
    WHERE capacity >= ?
      AND status != 'maintenance'
      AND id NOT IN (
        SELECT room_id FROM bookings
        WHERE booking_status IN ('confirmed','checked_in')
          AND check_in < ?
          AND check_out > ?
      )
    """
    params = [guests, check_out.isoformat(), check_in.isoformat()]
    if room_type != "Tất cả":
        sql += " AND room_type = ?"
        params.append(room_type)
    sql += " ORDER BY price ASC"
    return query(sql, params)

def calc_discount(code, subtotal):
    if not code:
        return 0, ""
    p = query("""
        SELECT * FROM promotions
        WHERE UPPER(code)=UPPER(?) AND active=1
        AND (expires_at IS NULL OR expires_at >= ?)
    """, (code.strip(), date.today().isoformat()), one=True)
    if not p:
        return 0, "Mã giảm giá không hợp lệ hoặc đã hết hạn."
    if subtotal < p["min_total"]:
        return 0, f"Đơn tối thiểu {money(p['min_total'])} để dùng mã này."
    discount = subtotal * p["percent"] / 100 + p["amount"]
    discount = min(discount, subtotal)
    return discount, f"Áp dụng {p['code']}: {p['description']}"

def current_user():
    return None

def logout():
    pass


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 🏨 HAPPY HOTEL")
    st.caption("Nơi kỳ nghỉ bắt đầu bằng một nụ cười 😊")
    st.divider()

    st.success("👋 Chào mừng bạn đến HAPPY HOTEL!")
    st.info("Bạn có thể đặt phòng ngay, không cần tài khoản.")

    menu = [
        "🏠 Trang chủ",
        "🛏️ Tìm phòng",
        "📋 Đặt phòng",
        "🧾 Tra cứu đặt phòng",
        "🎁 Ưu đãi",
        "⭐ Đánh giá",
        "💬 Chatbox",
        "📊 Quản trị",
    ]

    selected = st.radio(
        "Điều hướng",
        menu,
        index=menu.index(next((x for x in menu if x.endswith(st.session_state.page)), menu[0]))
        if any(x.endswith(st.session_state.page) for x in menu) else 0
    )
    st.session_state.page = selected.split(" ",1)[1]

    st.divider()
    st.markdown("---")
    st.caption("✨ Không cần tài khoản để đặt phòng")
    st.caption("📞 Hotline: 1900 6868")
    st.caption("📍 123 Biển Xanh, Việt Nam")


# -----------------------------
# Header
# -----------------------------
def hero():
    st.markdown("""
    <div class="hero">
      <h1>HAPPY HOTEL 🏨</h1>
      <p>Đặt phòng thông minh • Giá tốt • Trải nghiệm đáng nhớ</p>
      <p>✨ Check-in dễ dàng &nbsp; • &nbsp; 🛎️ Dịch vụ 24/7 &nbsp; • &nbsp; 💬 Trợ lý AI</p>
    </div>
    """, unsafe_allow_html=True)


# -----------------------------
# Home
# -----------------------------
def page_home():
    hero()

    st.markdown('<div class="section-title">Tìm phòng nhanh</div>', unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        ci = st.date_input("Ngày nhận phòng", date.today(), min_value=date.today())
    with c2:
        co = st.date_input("Ngày trả phòng", date.today()+timedelta(days=1), min_value=date.today()+timedelta(days=1))
    with c3:
        guests = st.number_input("Số khách", min_value=1, max_value=10, value=2)
    with c4:
        rt = st.selectbox("Loại phòng", ["Tất cả","Standard","Deluxe","Suite","VIP"])

    if st.button("🔎 TÌM PHÒNG", type="primary", use_container_width=True):
        st.session_state.search = {
            "check_in": ci, "check_out": co, "guests": guests, "room_type": rt
        }
        st.session_state.page = "Tìm phòng"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    a,b,c,d = st.columns(4)
    a.metric("🛏️ Phòng", "8")
    b.metric("⭐ Đánh giá", "4.9/5")
    c.metric("😊 Khách hàng", "5.000+")
    d.metric("🕐 Hỗ trợ", "24/7")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">✨ Điểm nổi bật</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    features = [
        ("💰","Giá tốt","Cam kết mức giá cạnh tranh"),
        ("🔒","An toàn","Thông tin đặt phòng được bảo vệ"),
        ("⚡","Nhanh chóng","Đặt phòng chỉ trong vài bước"),
        ("🤖","Trợ lý 24/7","Chatbox hỗ trợ mọi lúc"),
    ]
    for col,(icon,title,desc) in zip(cols,features):
        with col:
            st.markdown(f"""
            <div class="card">
              <div style="font-size:34px">{icon}</div>
              <h3>{title}</h3>
              <p class="small">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">🔥 Phòng được yêu thích</div>', unsafe_allow_html=True)
    rooms = query("SELECT * FROM rooms ORDER BY price LIMIT 4")
    cols = st.columns(4)
    for col,r in zip(cols,rooms):
        with col:
            st.image(r["image"], use_container_width=True)
            st.markdown(f"**{r['room_type']} • Phòng {r['room_number']}**")
            st.caption(r["description"])
            st.markdown(f'<span class="price">{money(r["price"])}</span> / đêm', unsafe_allow_html=True)
            if st.button("Xem & đặt", key=f"home_{r['id']}", use_container_width=True):
                st.session_state.selected_room = r["id"]
                st.session_state.page = "Đặt phòng"
                st.rerun()


# -----------------------------
# Search rooms
# -----------------------------
def page_search():
    st.markdown('<div class="section-title">🛏️ Tìm phòng</div>', unsafe_allow_html=True)

    default = st.session_state.get("search", {})
    c1,c2,c3,c4 = st.columns(4)
    ci = c1.date_input("Nhận phòng", default.get("check_in",date.today()), min_value=date.today())
    co = c2.date_input("Trả phòng", default.get("check_out",date.today()+timedelta(days=1)), min_value=date.today()+timedelta(days=1))
    guests = c3.number_input("Số khách", 1, 10, default.get("guests",2))
    rt = c4.selectbox("Loại phòng", ["Tất cả","Standard","Deluxe","Suite","VIP"],
                      index=["Tất cả","Standard","Deluxe","Suite","VIP"].index(default.get("room_type","Tất cả")))

    if co <= ci:
        st.error("Ngày trả phòng phải sau ngày nhận phòng.")
        return

    rooms = available_rooms(ci, co, guests, rt)
    st.info(f"Tìm thấy **{len(rooms)}** phòng phù hợp • {nights_between(ci,co)} đêm")

    if not rooms:
        st.warning("Không còn phòng phù hợp trong khoảng thời gian này. Hãy thử ngày khác.")
        return

    for r in rooms:
        c1,c2 = st.columns([1,2])
        with c1:
            st.image(r["image"], use_container_width=True)
        with c2:
            st.markdown(f"### {r['room_type']} — Phòng {r['room_number']}")
            st.markdown(f'<span class="badge">Tối đa {r["capacity"]} khách</span>', unsafe_allow_html=True)
            st.write(r["description"])
            st.caption("🛎️ " + r["amenities"])
            st.markdown(f'<span class="price">{money(r["price"])}</span> / đêm', unsafe_allow_html=True)
            st.write(f"💵 Tổng {nights_between(ci,co)} đêm: **{money(r['price']*nights_between(ci,co))}**")
            if st.button("🛎️ Đặt phòng này", key=f"search_book_{r['id']}", type="primary"):
                st.session_state.selected_room = r["id"]
                st.session_state.booking_search = {"check_in":ci,"check_out":co,"guests":guests}
                st.session_state.page = "Đặt phòng"
                st.rerun()
        st.divider()


# -----------------------------
# Booking
# -----------------------------
def page_booking():
    rooms = query("SELECT * FROM rooms ORDER BY price")
    selected_id = st.session_state.get("selected_room")
    default_room = next((r for r in rooms if r["id"] == selected_id), rooms[0] if rooms else None)

    st.markdown('<div class="section-title">📋 Đặt phòng</div>', unsafe_allow_html=True)

    if not default_room:
        st.error("Chưa có phòng.")
        return

    search = st.session_state.get("booking_search", {})
    c1,c2 = st.columns(2)
    with c1:
        ci = st.date_input("Ngày nhận phòng", search.get("check_in",date.today()), min_value=date.today())
    with c2:
        co = st.date_input("Ngày trả phòng", search.get("check_out",date.today()+timedelta(days=1)), min_value=date.today()+timedelta(days=1))

    rooms_available = available_rooms(ci,co,1)
    available_ids = [r["id"] for r in rooms_available]
    room_options = [r for r in rooms if r["id"] in available_ids]
    if not room_options:
        st.error("Không có phòng trống trong khoảng thời gian này.")
        return

    option_labels = [f"Phòng {r['room_number']} • {r['room_type']} • {money(r['price'])}/đêm" for r in room_options]
    selected_index = 0
    for i,r in enumerate(room_options):
        if r["id"] == selected_id:
            selected_index = i
    selected_label = st.selectbox("Chọn phòng", option_labels, index=selected_index)
    room = room_options[option_labels.index(selected_label)]

    c1,c2,c3 = st.columns(3)
    with c1:
        st.image(room["image"], use_container_width=True)
    with c2:
        st.markdown(f"### {room['room_type']}")
        st.write(room["description"])
        st.caption("🛎️ " + room["amenities"])
        st.info(f"Sức chứa: {room['capacity']} khách")
    with c3:
        nights = nights_between(ci,co)
        room_total = room["price"] * nights
        st.metric("Giá phòng", money(room_total))
        st.caption(f"{money(room['price'])} × {nights} đêm")

    st.markdown("### 👤 Thông tin khách")
    c1,c2 = st.columns(2)
    guest_name = c1.text_input("Họ và tên *", placeholder="Nguyễn Văn A")
    guest_email = c2.text_input("Email", placeholder="you@example.com")
    guest_phone = c1.text_input("Số điện thoại *", placeholder="0901234567")
    guests = c2.number_input("Số khách", 1, room["capacity"], min(2,room["capacity"]))

    st.markdown("### 🧺 Dịch vụ thêm")
    x1,x2,x3 = st.columns(3)
    breakfast = x1.checkbox("🍳 Bữa sáng +80.000đ/khách/đêm")
    airport = x2.checkbox("🚗 Đưa đón sân bay +300.000đ")
    extra_bed = x3.checkbox("🛏️ Giường phụ +250.000đ")

    services = 0
    if breakfast: services += 80000 * guests * nights
    if airport: services += 300000
    if extra_bed: services += 250000

    promo_code = st.text_input("🎁 Mã khuyến mãi", placeholder="Ví dụ: HAPPY10")
    discount, promo_msg = calc_discount(promo_code, room_total + services)
    if promo_code:
        if discount:
            st.success(f"{promo_msg} • Tiết kiệm {money(discount)}")
        else:
            st.warning(promo_msg)

    special = st.text_area("📝 Yêu cầu đặc biệt", placeholder="Ví dụ: phòng tầng cao, không hút thuốc...")
    payment = st.radio("💳 Phương thức thanh toán", ["Thanh toán tại khách sạn","Chuyển khoản","Thanh toán online (demo)"])

    subtotal = room_total + services
    total = max(0, subtotal - discount)

    st.markdown("### 💰 Chi tiết thanh toán")
    st.markdown(f"""
    <div class="card">
      <p>Tiền phòng: <b>{money(room_total)}</b></p>
      <p>Dịch vụ: <b>{money(services)}</b></p>
      <p>Giảm giá: <b>- {money(discount)}</b></p>
      <hr>
      <h2>Tổng thanh toán: <span style="color:#08745e">{money(total)}</span></h2>
    </div>
    """, unsafe_allow_html=True)

    agree = st.checkbox("Tôi xác nhận thông tin đặt phòng là chính xác và đồng ý với chính sách của khách sạn.")

    if st.button("🎉 XÁC NHẬN ĐẶT PHÒNG", type="primary", use_container_width=True):
        if not agree:
            st.error("Vui lòng xác nhận thông tin đặt phòng.")
            return
        if not guest_name.strip() or not guest_phone.strip():
            st.error("Vui lòng nhập đầy đủ họ tên và số điện thoại.")
            return

        # Re-check availability before inserting.
        av = available_rooms(ci,co,guests)
        if room["id"] not in [r["id"] for r in av]:
            st.error("Phòng vừa được đặt bởi khách khác. Vui lòng chọn phòng khác.")
            return

        code = "HH-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:5].upper()
        execute("""
            INSERT INTO bookings(
                booking_code,user_id,room_id,guest_name,guest_email,guest_phone,
                check_in,check_out,guests,nights,room_price,services_price,
                discount,total,payment_method,payment_status,booking_status,
                special_request,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            code,None,room["id"],guest_name,guest_email,guest_phone,
            ci.isoformat(),co.isoformat(),guests,nights,room_total,services,
            discount,total,payment,
            "paid" if "online" in payment.lower() else "pending",
            "confirmed",special,datetime.now().isoformat(timespec="seconds")
        ))

        st.session_state.booking_success = {
            "code":code, "room":room["room_number"], "total":total,
            "check_in":ci.isoformat(), "check_out":co.isoformat()
        }
        st.rerun()

    if "booking_success" in st.session_state:
        b = st.session_state.booking_success
        st.balloons()
        st.markdown(f"""
        <div class="success-box">
          <h2>🎉 Đặt phòng thành công!</h2>
          <p>Mã đặt phòng: <b>{b['code']}</b></p>
          <p>Phòng: <b>{b['room']}</b></p>
          <p>Nhận phòng: <b>{b['check_in']}</b> → Trả phòng: <b>{b['check_out']}</b></p>
          <h3>Tổng tiền: {money(b['total'])}</h3>
          <p>Vui lòng lưu mã đặt phòng để tra cứu.</p>
        </div>
        """, unsafe_allow_html=True)


# -----------------------------
# Promotions
# -----------------------------
def page_promotions():
    st.markdown('<div class="section-title">🎁 Ưu đãi đặc biệt</div>', unsafe_allow_html=True)
    promos = query("""
        SELECT * FROM promotions
        WHERE active=1 AND (expires_at IS NULL OR expires_at >= ?)
        ORDER BY percent DESC, amount DESC
    """,(date.today().isoformat(),))

    for p in promos:
        st.markdown(f"""
        <div class="deal">
          <h3>🎟️ {p['code']}</h3>
          <p>{p['description']}</p>
          <b>Mã: {p['code']}</b> &nbsp; | &nbsp;
          Hiệu lực đến: {p['expires_at'] or 'Không giới hạn'}
        </div>
        """, unsafe_allow_html=True)
        st.write("")


# -----------------------------
# Bookings
# -----------------------------
def page_my_bookings():
    st.markdown('<div class="section-title">🧾 Tra cứu đặt phòng</div>', unsafe_allow_html=True)
    st.caption("Không cần tài khoản. Nhập mã đặt phòng và số điện thoại để xem đơn.")

    with st.form("lookup_booking"):
        c1,c2 = st.columns(2)
        booking_code = c1.text_input("Mã đặt phòng", placeholder="Ví dụ: HH-260928-ABCDE")
        phone = c2.text_input("Số điện thoại", placeholder="0901234567")
        submit = st.form_submit_button("🔎 Tra cứu", type="primary")

    if submit:
        b = query("""
            SELECT b.*, r.room_number, r.room_type
            FROM bookings b JOIN rooms r ON b.room_id=r.id
            WHERE UPPER(b.booking_code)=UPPER(?) AND b.guest_phone=?
        """,(booking_code.strip(),phone.strip()),one=True)

        if not b:
            st.error("Không tìm thấy đơn. Vui lòng kiểm tra mã đặt phòng và số điện thoại.")
            return

        status = {
            "confirmed":"Đã xác nhận",
            "checked_in":"Đang lưu trú",
            "completed":"Hoàn tất",
            "cancelled":"Đã hủy"
        }.get(b["booking_status"],b["booking_status"])

        st.markdown(f"""
        <div class="card">
          <h3>🏨 {b['booking_code']}</h3>
          <p>👤 {b['guest_name']} • 📞 {b['guest_phone']}</p>
          <p>🛏️ Phòng {b['room_number']} — {b['room_type']}</p>
          <p>📅 {b['check_in']} → {b['check_out']} • {b['nights']} đêm • {b['guests']} khách</p>
          <p>💳 {b['payment_method']}</p>
          <p>📌 Trạng thái: <b>{status}</b></p>
          <h2 style="color:#08745e">{money(b['total'])}</h2>
        </div>
        """, unsafe_allow_html=True)

        if b["booking_status"] == "confirmed":
            if st.button("❌ Hủy đặt phòng"):
                execute("UPDATE bookings SET booking_status='cancelled' WHERE id=?",(b["id"],))
                st.success("Đã hủy đơn đặt phòng.")
                st.rerun()


# -----------------------------
# Reviews
# -----------------------------
def page_reviews():
    st.markdown('<div class="section-title">⭐ Đánh giá của khách hàng</div>', unsafe_allow_html=True)

    avg = query("SELECT AVG(rating) AS avg, COUNT(*) AS c FROM reviews", one=True)
    c1,c2 = st.columns(2)
    c1.metric("Điểm trung bình", f"{avg['avg']:.1f}/5" if avg["avg"] else "Chưa có")
    c2.metric("Lượt đánh giá", avg["c"])

    st.markdown("### ✍️ Viết đánh giá")
    with st.form("review_form"):
        c1,c2 = st.columns(2)
        booking_code = c1.text_input("Mã đặt phòng")
        phone = c2.text_input("Số điện thoại")
        rating = st.slider("Mức đánh giá",1,5,5)
        comment = st.text_area("Nhận xét")
        submit = st.form_submit_button("Gửi đánh giá", type="primary")

    if submit:
        b = query("""
            SELECT * FROM bookings
            WHERE UPPER(booking_code)=UPPER(?) AND guest_phone=?
        """,(booking_code.strip(),phone.strip()),one=True)
        if not b:
            st.error("Không tìm thấy đơn đặt phòng.")
        elif query("SELECT id FROM reviews WHERE booking_id=?",(b["id"],),one=True):
            st.warning("Đơn này đã được đánh giá.")
        else:
            execute("""
                INSERT INTO reviews(booking_id,user_id,room_id,rating,comment,created_at)
                VALUES(?,?,?,?,?,?)
            """,(b["id"],None,b["room_id"],rating,comment,datetime.now().isoformat(timespec="seconds")))
            st.success("Cảm ơn bạn đã đánh giá HAPPY HOTEL!")
            st.rerun()

    reviews = query("""
        SELECT rv.*, r.room_type
        FROM reviews rv
        LEFT JOIN rooms r ON rv.room_id=r.id
        ORDER BY rv.created_at DESC LIMIT 20
    """)
    for r in reviews:
        stars = "⭐" * r["rating"]
        st.markdown(f"""
        <div class="card">
          <b>{stars}</b> &nbsp; <b>Khách hàng</b>
          <p>{r['comment'] or 'Khách không để lại nhận xét.'}</p>
          <span class="small">{r['room_type'] or ''} • {r['created_at']}</span>
        </div>
        """, unsafe_allow_html=True)


# -----------------------------
# Account
# -----------------------------


# -----------------------------
# Login / Register
# -----------------------------


# -----------------------------
# Chatbox
# -----------------------------
def chatbot_answer(text):
    t = text.lower().strip()

    if any(x in t for x in ["xin chào","hello","hi","chào"]):
        return "Xin chào! 👋 Mình là HAPPY Assistant. Bạn muốn tìm phòng, xem giá hay hỏi về dịch vụ?"
    if any(x in t for x in ["giá","bao nhiêu","price"]):
        rooms = query("SELECT room_type, MIN(price) AS p FROM rooms GROUP BY room_type ORDER BY p")
        return "Giá phòng hiện tại: " + " • ".join([f"{r['room_type']} từ {money(r['p'])}/đêm" for r in rooms]) + "."
    if any(x in t for x in ["standard","tiêu chuẩn"]):
        return "Phòng Standard phù hợp tối đa 2 khách, giá từ 650.000đ/đêm."
    if "deluxe" in t:
        return "Phòng Deluxe có không gian rộng hơn, giá từ 950.000đ/đêm."
    if "suite" in t:
        return "Suite có phòng khách/không gian cao cấp, giá từ 1.600.000đ/đêm."
    if "vip" in t:
        return "Phòng VIP có tiện nghi cao cấp như Jacuzzi/Minibar tùy phòng, giá từ 2.500.000đ/đêm."
    if any(x in t for x in ["wifi","internet"]):
        return "Tất cả các phòng của HAPPY HOTEL đều có WiFi."
    if any(x in t for x in ["bữa sáng","ăn sáng","breakfast"]):
        return "Bữa sáng có thể được thêm khi đặt phòng với giá 80.000đ/khách/đêm."
    if any(x in t for x in ["check-in","nhận phòng"]):
        return "Giờ nhận phòng tiêu chuẩn: 14:00."
    if any(x in t for x in ["check-out","trả phòng"]):
        return "Giờ trả phòng tiêu chuẩn: 12:00."
    if any(x in t for x in ["hủy","cancel"]):
        return "Bạn có thể vào mục 'Đơn đặt phòng' để hủy đơn đang ở trạng thái đã xác nhận."
    if any(x in t for x in ["khuyến mãi","mã","voucher","giảm giá"]):
        return "Bạn có thể dùng mã HAPPY10 để giảm 10%, hoặc WELCOME200 để giảm 200.000đ cho đơn từ 1.500.000đ."
    if any(x in t for x in ["đặt phòng","book","booking"]):
        return "Bạn vào 'Tìm phòng', chọn ngày + số khách, sau đó nhấn 'Đặt phòng này'. Nếu cần mình có thể hướng dẫn từng bước."
    if any(x in t for x in ["địa chỉ","ở đâu","location"]):
        return "HAPPY HOTEL — 123 Biển Xanh, Việt Nam. Hotline 1900 6868."
    if any(x in t for x in ["liên hệ","hotline","điện thoại"]):
        return "Hotline HAPPY HOTEL: 1900 6868. Bộ phận hỗ trợ hoạt động 24/7."
    return "Mình chưa hiểu hoàn toàn câu hỏi. Bạn có thể hỏi: 'giá phòng', 'phòng VIP', 'khuyến mãi', 'giờ check-in', 'đặt phòng' hoặc 'dịch vụ bữa sáng'. 😊"

def page_chat():
    st.markdown('<div class="section-title">💬 HAPPY Assistant</div>', unsafe_allow_html=True)
    st.caption("Trợ lý tư vấn tự động — không cần API key.")

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    prompt = st.chat_input("Nhập câu hỏi của bạn...")
    if prompt:
        st.session_state.chat_messages.append({"role":"user","content":prompt})
        answer = chatbot_answer(prompt)
        st.session_state.chat_messages.append({"role":"assistant","content":answer})
        st.rerun()


# -----------------------------
# Admin
# -----------------------------
def page_admin():
    st.markdown('<div class="section-title">📊 Dashboard quản trị HAPPY HOTEL</div>', unsafe_allow_html=True)
    admin_ok = st.session_state.get("admin_ok", False)
    if not admin_ok:
        with st.form("admin_login"):
            password = st.text_input("Mật khẩu quản trị", type="password")
            submit = st.form_submit_button("🔐 Vào quản trị", type="primary")
        if submit:
            if password == "admin123":
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Mật khẩu quản trị không đúng.")
        return

    total_bookings = query("SELECT COUNT(*) c FROM bookings",one=True)["c"]
    total_revenue = query("SELECT COALESCE(SUM(total),0) s FROM bookings WHERE booking_status!='cancelled'",one=True)["s"]
    total_users = query("SELECT COUNT(*) c FROM users WHERE role='customer'",one=True)["c"]
    occupied = query("""
        SELECT COUNT(*) c FROM bookings
        WHERE booking_status IN ('confirmed','checked_in')
        AND check_in <= ? AND check_out > ?
    """,(date.today().isoformat(),date.today().isoformat()),one=True)["c"]

    a,b,c,d = st.columns(4)
    a.metric("🧾 Đơn đặt",total_bookings)
    b.metric("💰 Doanh thu",money(total_revenue))
    c.metric("👥 Khách hàng",total_users)
    d.metric("🛏️ Đang đặt",occupied)

    st.markdown("### 📈 Doanh thu theo ngày")
    revenue = query("""
        SELECT substr(created_at,1,10) AS day, SUM(total) AS revenue
        FROM bookings
        WHERE booking_status!='cancelled'
        GROUP BY substr(created_at,1,10)
        ORDER BY day
    """)
    if revenue:
        df = pd.DataFrame([dict(x) for x in revenue])
        df["day"] = pd.to_datetime(df["day"])
        df = df.set_index("day")
        st.line_chart(df["revenue"])

    tab1,tab2,tab3 = st.tabs(["🧾 Đơn đặt phòng","🛏️ Phòng","🎁 Khuyến mãi"])

    with tab1:
        bookings = query("""
            SELECT b.booking_code,b.guest_name,b.guest_phone,
                   r.room_number,r.room_type,b.check_in,b.check_out,
                   b.total,b.booking_status,b.payment_status
            FROM bookings b JOIN rooms r ON b.room_id=r.id
            ORDER BY b.created_at DESC
        """)
        if bookings:
            st.dataframe(pd.DataFrame([dict(x) for x in bookings]),use_container_width=True)
        else:
            st.info("Chưa có đơn.")

    with tab2:
        rooms = query("SELECT * FROM rooms ORDER BY room_number")
        st.dataframe(pd.DataFrame([dict(x) for x in rooms]),use_container_width=True)

        with st.expander("➕ Thêm phòng"):
            with st.form("add_room"):
                rn = st.text_input("Số phòng")
                typ = st.selectbox("Loại",["Standard","Deluxe","Suite","VIP"])
                floor = st.number_input("Tầng",1,100,1)
                cap = st.number_input("Sức chứa",1,20,2)
                price = st.number_input("Giá/đêm",100000,100000000,650000,step=50000)
                desc = st.text_input("Mô tả")
                amenities = st.text_input("Tiện nghi")
                image = st.text_input("URL ảnh")
                if st.form_submit_button("Thêm phòng"):
                    try:
                        execute("""
                            INSERT INTO rooms(room_number,room_type,floor,capacity,price,description,amenities,image)
                            VALUES(?,?,?,?,?,?,?,?)
                        """,(rn,typ,floor,cap,price,desc,amenities,image))
                        st.success("Đã thêm phòng.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Số phòng đã tồn tại.")

    with tab3:
        promos = query("SELECT * FROM promotions ORDER BY id DESC")
        st.dataframe(pd.DataFrame([dict(x) for x in promos]),use_container_width=True)


# -----------------------------
# Floating chat teaser
# -----------------------------
def floating_chat():
    with st.expander("💬 HAPPY Assistant — Hỏi nhanh", expanded=False):
        st.write("Bạn có thể hỏi về giá phòng, tiện nghi, khuyến mãi, check-in...")
        p = st.chat_input("Hỏi HAPPY Assistant...", key="floating_chat_input")
        if p:
            st.session_state.chat_messages.append({"role":"user","content":p})
            st.session_state.chat_messages.append({"role":"assistant","content":chatbot_answer(p)})
            st.rerun()


# -----------------------------
# Router
# -----------------------------
page = st.session_state.page

if page == "Trang chủ":
    page_home()
elif page == "Tìm phòng":
    page_search()
elif page == "Đặt phòng":
    page_booking()
elif page == "Ưu đãi":
    page_promotions()
elif page == "Đánh giá":
    page_reviews()
elif page == "Chatbox":
    page_chat()
elif page == "Tra cứu đặt phòng":
    page_my_bookings()
elif page == "Quản trị":
    page_admin()
else:
    page_home()

# Keep chat available across the app.
if page not in ["Chatbox"]:
    floating_chat()

st.markdown("""
<hr>
<div style="text-align:center;color:#81909b;padding:15px">
    <b>🏨 HAPPY HOTEL</b> · Đặt phòng vui vẻ, nghỉ dưỡng hạnh phúc ❤️<br>
    1900 6868 · 123 Biển Xanh · Hỗ trợ 24/7
</div>
""", unsafe_allow_html=True)
