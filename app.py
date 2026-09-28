
import streamlit as st
import sqlite3
import hashlib
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import html

# ============================================================
# HAPPY HOTEL - Hotel Booking App
# Run:
#   pip install -r requirements.txt
#   streamlit run app.py
# ============================================================

APP_TITLE = "HAPPY HOTEL"
DB_FILE = Path("happy_hotel.db")

st.set_page_config(
    page_title="HAPPY HOTEL | Đặt phòng khách sạn",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- CSS -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Be Vietnam Pro', sans-serif;
}
.stApp {
    background: #f6f8fb;
}
.hero {
    background: linear-gradient(135deg, #0f766e 0%, #14b8a6 50%, #22c55e 100%);
    padding: 34px 38px;
    border-radius: 24px;
    color: white;
    margin-bottom: 22px;
    box-shadow: 0 14px 35px rgba(15,118,110,.20);
}
.hero h1 { font-size: 42px; margin: 0; font-weight: 800; }
.hero p { font-size: 17px; margin: 8px 0 0; opacity: .95; }
.card {
    background: white;
    border: 1px solid #e8edf3;
    border-radius: 18px;
    padding: 20px;
    margin: 8px 0;
    box-shadow: 0 5px 18px rgba(15,23,42,.05);
}
.room-card {
    background: white;
    border-radius: 20px;
    border: 1px solid #e8edf3;
    overflow: hidden;
    box-shadow: 0 8px 25px rgba(15,23,42,.07);
    margin-bottom: 18px;
}
.room-img {
    height: 180px;
    background: linear-gradient(135deg,#ccfbf1,#dbeafe);
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:72px;
}
.room-body { padding: 18px; }
.badge {
    display:inline-block;
    padding:5px 10px;
    border-radius:999px;
    font-size:12px;
    font-weight:700;
    background:#ecfdf5;
    color:#047857;
}
.price { color:#0f766e; font-size:24px; font-weight:800; }
.small { color:#64748b; font-size:13px; }
.chat {
    background:#ffffff;
    border:1px solid #e2e8f0;
    border-radius:18px;
    padding:14px;
}
.kpi {
    background:white;
    border-radius:18px;
    border:1px solid #e8edf3;
    padding:18px;
    text-align:center;
}
.kpi .n { font-size:28px; font-weight:800; color:#0f766e; }
.kpi .l { color:#64748b; font-size:13px; }
.footer {
    text-align:center;
    color:#64748b;
    padding:30px 0 10px;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------- Database -----------------------------
def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
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
        name TEXT NOT NULL,
        room_type TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        capacity INTEGER NOT NULL,
        beds TEXT,
        amenities TEXT,
        icon TEXT DEFAULT '🛏️',
        floor INTEGER DEFAULT 1,
        active INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        room_id INTEGER NOT NULL,
        guest_name TEXT NOT NULL,
        guest_email TEXT NOT NULL,
        guest_phone TEXT NOT NULL,
        check_in TEXT NOT NULL,
        check_out TEXT NOT NULL,
        guests INTEGER NOT NULL,
        nights INTEGER NOT NULL,
        room_total REAL NOT NULL,
        service_fee REAL NOT NULL,
        discount REAL DEFAULT 0,
        total REAL NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT DEFAULT 'Confirmed',
        note TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        room_id INTEGER,
        guest_name TEXT,
        rating INTEGER,
        comment TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        percent REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        min_total REAL DEFAULT 0,
        active INTEGER DEFAULT 1
    )
    """)

    # Demo account
    admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
    demo_pw = hashlib.sha256("123456".encode()).hexdigest()
    cur.execute("INSERT OR IGNORE INTO users(name,email,phone,password,role,created_at) VALUES(?,?,?,?,?,?)",
                ("Quản trị viên", "admin@happyhotel.vn", "0900000000", admin_pw, "admin", datetime.now().isoformat()))
    cur.execute("INSERT OR IGNORE INTO users(name,email,phone,password,role,created_at) VALUES(?,?,?,?,?,?)",
                ("Khách hàng Demo", "demo@happyhotel.vn", "0912345678", demo_pw, "customer", datetime.now().isoformat()))

    rooms = [
        ("Phòng Standard", "Standard", "Không gian ấm cúng, phù hợp cho 1–2 khách.", 650000, 2,
         "1 giường đôi", "WiFi miễn phí, TV, Điều hòa, Nước suối", "🛏️", 2),
        ("Phòng Deluxe", "Deluxe", "Phòng rộng, cửa sổ lớn và góc làm việc.", 950000, 2,
         "1 giường King", "WiFi miễn phí, TV 55\", Minibar, Điều hòa, Bàn làm việc", "🛋️", 3),
        ("Phòng Family", "Family", "Lựa chọn lý tưởng cho gia đình hoặc nhóm bạn.", 1350000, 4,
         "2 giường đôi", "WiFi miễn phí, TV, Minibar, Bồn tắm, Sofa", "👨‍👩‍👧‍👦", 4),
        ("Suite Ocean View", "Suite", "Suite cao cấp với ban công và tầm nhìn tuyệt đẹp.", 2200000, 2,
         "1 giường King", "WiFi Premium, TV 65\", Minibar, Bồn tắm, Ban công, View biển", "🌊", 6),
        ("HAPPY VIP Suite", "VIP", "Không gian sang trọng dành cho trải nghiệm đặc biệt.", 3500000, 3,
         "1 King + Sofa bed", "WiFi Premium, TV 75\", Minibar, Jacuzzi, Ban công, Butler", "👑", 8),
    ]
    count = cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if count == 0:
        cur.executemany("""
            INSERT INTO rooms(name,room_type,description,price,capacity,beds,amenities,icon,floor)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, rooms)

    coupons = [
        ("HAPPY10", 10, 0, 500000),
        ("WELCOME200", 0, 200000, 1000000),
        ("VIP15", 15, 0, 2000000),
    ]
    for c in coupons:
        cur.execute("INSERT OR IGNORE INTO coupons(code,percent,amount,min_total,active) VALUES(?,?,?,?,1)", c)

    conn.commit()
    conn.close()

init_db()

# ----------------------------- Helpers -----------------------------
def money(v):
    return f"{v:,.0f} ₫".replace(",", ".")

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(email):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return row

def available_rooms(check_in, check_out, guests=1, room_type="Tất cả"):
    conn = db()
    params = [check_out.isoformat(), check_in.isoformat(), guests]
    query = """
    SELECT * FROM rooms
    WHERE active=1 AND capacity>=?
      AND id NOT IN (
        SELECT room_id FROM bookings
        WHERE status NOT IN ('Cancelled','Completed')
          AND check_in < ? AND check_out > ?
      )
    """
    # Parameters: capacity, check_out, check_in
    query_params = [guests, check_out.isoformat(), check_in.isoformat()]
    if room_type != "Tất cả":
        query += " AND room_type=?"
        query_params.append(room_type)
    query += " ORDER BY price ASC"
    rows = conn.execute(query, query_params).fetchall()
    conn.close()
    return rows

def room_rating(room_id):
    conn = db()
    row = conn.execute("SELECT AVG(rating) avg, COUNT(*) cnt FROM reviews WHERE room_id=?", (room_id,)).fetchone()
    conn.close()
    if not row["cnt"]:
        return 5.0, 0
    return float(row["avg"]), int(row["cnt"])

def booking_conflict(room_id, check_in, check_out, exclude_id=None):
    conn = db()
    q = """
    SELECT id FROM bookings
    WHERE room_id=? AND status NOT IN ('Cancelled','Completed')
      AND check_in < ? AND check_out > ?
    """
    params = [room_id, check_out.isoformat(), check_in.isoformat()]
    if exclude_id:
        q += " AND id != ?"
        params.append(exclude_id)
    row = conn.execute(q, params).fetchone()
    conn.close()
    return row is not None

def calc_total(room, check_in, check_out, guests, coupon_code=""):
    nights = (check_out - check_in).days
    room_total = room["price"] * nights
    service_fee = room_total * 0.05
    discount = 0
    coupon_message = ""
    if coupon_code:
        conn = db()
        coupon = conn.execute(
            "SELECT * FROM coupons WHERE UPPER(code)=UPPER(?) AND active=1",
            (coupon_code.strip(),)
        ).fetchone()
        conn.close()
        if coupon:
            if room_total + service_fee >= coupon["min_total"]:
                if coupon["percent"] > 0:
                    discount = (room_total + service_fee) * coupon["percent"] / 100
                else:
                    discount = min(coupon["amount"], room_total + service_fee)
                coupon_message = f"Áp dụng mã {coupon['code']} thành công."
            else:
                coupon_message = f"Mã cần đơn tối thiểu {money(coupon['min_total'])}."
        else:
            coupon_message = "Mã giảm giá không hợp lệ."
    total = max(0, room_total + service_fee - discount)
    return nights, room_total, service_fee, discount, total, coupon_message

def create_booking(room_id, user, guest_name, guest_email, guest_phone,
                   check_in, check_out, guests, payment_method, note, coupon):
    conn = db()
    room = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        conn.close()
        return None, "Không tìm thấy phòng."
    if booking_conflict(room_id, check_in, check_out):
        conn.close()
        return None, "Phòng vừa được đặt bởi khách khác. Vui lòng chọn phòng khác."
    nights, room_total, service_fee, discount, total, msg = calc_total(
        room, check_in, check_out, guests, coupon
    )
    code = "HH-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings(
            code,user_id,room_id,guest_name,guest_email,guest_phone,
            check_in,check_out,guests,nights,room_total,service_fee,
            discount,total,payment_method,status,note,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        code,
        user["id"] if user else None,
        room_id, guest_name, guest_email, guest_phone,
        check_in.isoformat(), check_out.isoformat(), guests, nights,
        room_total, service_fee, discount, total,
        payment_method, "Confirmed", note, datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    return code, msg

def get_bookings(email=None):
    conn = db()
    if email:
        rows = conn.execute("""
            SELECT b.*, r.name room_name, r.room_type
            FROM bookings b JOIN rooms r ON b.room_id=r.id
            WHERE b.guest_email=? ORDER BY b.created_at DESC
        """, (email,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT b.*, r.name room_name, r.room_type
            FROM bookings b JOIN rooms r ON b.room_id=r.id
            ORDER BY b.created_at DESC
        """).fetchall()
    conn.close()
    return rows

def get_stats():
    conn = db()
    rooms = conn.execute("SELECT COUNT(*) c FROM rooms WHERE active=1").fetchone()["c"]
    bookings = conn.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"]
    revenue = conn.execute(
        "SELECT COALESCE(SUM(total),0) s FROM bookings WHERE status!='Cancelled'"
    ).fetchone()["s"]
    customers = conn.execute("SELECT COUNT(*) c FROM users WHERE role='customer'").fetchone()["c"]
    conn.close()
    return rooms, bookings, revenue, customers

# ----------------------------- Session -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "Trang chủ"
if "chat" not in st.session_state:
    st.session_state.chat = [
        ("bot", "Xin chào! 👋 Mình là HAPPY Bot. Bạn muốn tìm phòng, hỏi giá, chính sách hay hỗ trợ đặt phòng?")
    ]
if "selected_room" not in st.session_state:
    st.session_state.selected_room = None

# ----------------------------- Chatbot -----------------------------
def chatbot_answer(message):
    m = message.lower().strip()

    if any(x in m for x in ["xin chào", "hello", "hi", "chào"]):
        return "Xin chào! 👋 Mình là HAPPY Bot. Mình có thể tư vấn phòng, giá, ngày ở, mã giảm giá và hướng dẫn bạn đặt phòng."

    if any(x in m for x in ["giá", "bao nhiêu", "price"]):
        return (
            "💰 Giá phòng hiện tại:\n"
            "• Standard: 650.000đ/đêm\n"
            "• Deluxe: 950.000đ/đêm\n"
            "• Family: 1.350.000đ/đêm\n"
            "• Suite Ocean View: 2.200.000đ/đêm\n"
            "• HAPPY VIP Suite: 3.500.000đ/đêm"
        )

    if "standard" in m:
        return "🛏️ Standard: 650.000đ/đêm, tối đa 2 khách, 1 giường đôi. Có WiFi, TV, điều hòa và nước suối."

    if "deluxe" in m:
        return "🛋️ Deluxe: 950.000đ/đêm, tối đa 2 khách, giường King, TV 55\", minibar và bàn làm việc."

    if "family" in m or "gia đình" in m:
        return "👨‍👩‍👧‍👦 Family: 1.350.000đ/đêm, tối đa 4 khách, 2 giường đôi, minibar, bồn tắm và sofa."

    if "suite" in m or "view biển" in m:
        return "🌊 Suite Ocean View: 2.200.000đ/đêm, giường King, ban công, bồn tắm, minibar và view biển."

    if "vip" in m:
        return "👑 HAPPY VIP Suite: 3.500.000đ/đêm, tối đa 3 khách, King + sofa bed, Jacuzzi, ban công và dịch vụ Butler."

    if "check-in" in m or "nhận phòng" in m:
        return "🕑 Giờ nhận phòng tiêu chuẩn là 14:00."

    if "check-out" in m or "trả phòng" in m:
        return "🕛 Giờ trả phòng tiêu chuẩn là 12:00."

    if "hủy" in m or "huỷ" in m:
        return "❌ Bạn có thể hủy đơn trong mục 'Đặt phòng của tôi' bằng email đã dùng khi đặt. Một số trường hợp có thể không được hoàn tiền."

    if "wifi" in m:
        return "📶 Tất cả phòng đều có WiFi miễn phí. Các hạng Suite có WiFi Premium."

    if "ăn sáng" in m or "bữa sáng" in m:
        return "🍳 Bạn có thể ghi chú yêu cầu bữa sáng khi đặt phòng. Dịch vụ và giá có thể thay đổi theo chương trình."

    if "mã" in m or "coupon" in m or "giảm" in m:
        return "🎁 Bạn có thể thử: HAPPY10 giảm 10% cho đơn từ 500.000đ; WELCOME200 giảm 200.000đ cho đơn từ 1.000.000đ; VIP15 giảm 15% cho đơn từ 2.000.000đ."

    if "đặt phòng" in m or "book" in m:
        return "🛎️ Rất đơn giản: chọn 'Tìm phòng' → chọn ngày nhận/trả → chọn phòng → nhập thông tin khách → xác nhận đặt phòng. Không cần tài khoản."

    if "phòng nào" in m or "phòng phù hợp" in m:
        return "😊 Nếu 1–2 khách, bạn có thể chọn Standard hoặc Deluxe. Gia đình/nhóm tối đa 4 người có Family. Muốn view biển hãy chọn Suite Ocean View. Muốn trải nghiệm cao cấp nhất có HAPPY VIP Suite."

    if "liên hệ" in m or "điện thoại" in m or "hotline" in m:
        return "☎️ Hotline HAPPY HOTEL: 1900 6868\n📧 Email: hello@happyhotel.vn\n🕐 Lễ tân: 24/7."

    if "địa chỉ" in m:
        return "📍 HAPPY HOTEL — 123 Đường Biển Vui Vẻ, Việt Nam."

    if "cảm ơn" in m or "thanks" in m:
        return "🥰 Rất vui được hỗ trợ bạn! Chúc bạn có một kỳ nghỉ thật vui tại HAPPY HOTEL."

    return (
        "Mình có thể hỗ trợ bạn về:\n"
        "🏨 Giá phòng\n"
        "🛏️ Tư vấn loại phòng\n"
        "📅 Ngày nhận/trả phòng\n"
        "🎁 Mã giảm giá\n"
        "🛎️ Cách đặt phòng\n"
        "❌ Chính sách hủy\n"
        "☎️ Liên hệ khách sạn\n\n"
        "Bạn thử hỏi: “Phòng nào phù hợp cho gia đình 4 người?”"
    )

def render_chatbot():
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False
    if "chat" not in st.session_state:
        st.session_state.chat = [
            ("bot", "Xin chào! 👋 Mình là HAPPY Bot. Bạn cần mình tư vấn phòng hay hỗ trợ đặt phòng?")
        ]

    # Floating chat CSS
    st.markdown("""
    <style>
    .chat-fab {
        position: fixed;
        right: 28px;
        bottom: 28px;
        width: 64px;
        height: 64px;
        border-radius: 50%;
        background: linear-gradient(135deg,#0f766e,#14b8a6);
        color: white;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:29px;
        box-shadow:0 8px 25px rgba(15,118,110,.35);
        z-index:99999;
        border:3px solid white;
    }
    .chat-header {
        background: linear-gradient(135deg,#0f766e,#14b8a6);
        color:white;
        padding:16px;
        border-radius:18px 18px 0 0;
    }
    .chat-title {font-size:18px;font-weight:800;}
    .chat-status {font-size:12px;opacity:.9;}
    .chat-message-bot {
        background:#f1f5f9;
        padding:10px 13px;
        border-radius:15px 15px 15px 4px;
        margin:7px 0;
        white-space:pre-line;
    }
    .chat-message-user {
        background:#ccfbf1;
        padding:10px 13px;
        border-radius:15px 15px 4px 15px;
        margin:7px 0 7px 28px;
        white-space:pre-line;
    }
    </style>
    """, unsafe_allow_html=True)

    # Use a compact sidebar toggle as the reliable Streamlit control,
    # while styling it like a floating assistant entry point.
    with st.sidebar:
        st.markdown("""
        <div style="
            background:linear-gradient(135deg,#0f766e,#14b8a6);
            color:white;padding:16px;border-radius:18px;
            text-align:center;margin-bottom:10px;">
            <div style="font-size:32px;">💬</div>
            <div style="font-weight:800;font-size:17px;">HAPPY Bot</div>
            <div style="font-size:12px;">Trợ lý đặt phòng 24/7</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "🔴 Đóng chatbot" if st.session_state.chat_open else "💬 Mở HAPPY Bot",
            use_container_width=True,
            key="chat_toggle"
        ):
            st.session_state.chat_open = not st.session_state.chat_open
            st.rerun()

        if st.session_state.chat_open:
            st.markdown(
                '<div class="chat-header"><div class="chat-title">🤖 HAPPY Bot</div>'
                '<div class="chat-status">🟢 Đang hoạt động • Không cần tài khoản</div></div>',
                unsafe_allow_html=True
            )

            for who, msg in st.session_state.chat[-10:]:
                css = "chat-message-bot" if who == "bot" else "chat-message-user"
                icon = "🤖" if who == "bot" else "🧑"
                st.markdown(
                    f'<div class="{css}"><b>{icon}</b> {html.escape(msg).replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True
                )

            st.markdown("**Câu hỏi nhanh:**")
            quick_cols = st.columns(2)
            quick_questions = [
                "💰 Giá phòng",
                "👨‍👩‍👧‍👦 Phòng gia đình",
                "🎁 Mã giảm giá",
                "🛎️ Cách đặt phòng",
            ]
            for i, q in enumerate(quick_questions):
                with quick_cols[i % 2]:
                    if st.button(q, key=f"quick_chat_{i}", use_container_width=True):
                        question = q[2:].strip()
                        st.session_state.chat.append(("user", question))
                        st.session_state.chat.append(("bot", chatbot_answer(question)))
                        st.rerun()

            with st.form("chat_form", clear_on_submit=True):
                text = st.text_input(
                    "Nhập câu hỏi...",
                    placeholder="Ví dụ: phòng nào cho 4 người?"
                )
                submitted = st.form_submit_button("Gửi 💬", use_container_width=True)

            if submitted and text.strip():
                st.session_state.chat.append(("user", text.strip()))
                st.session_state.chat.append(("bot", chatbot_answer(text)))
                st.rerun()

# ----------------------------- Sidebar -----------------------------
with st.sidebar:
    st.markdown("## 🏨 HAPPY HOTEL")
    st.caption("Trải nghiệm đặt phòng vui vẻ & thông minh")
    menu = ["Trang chủ", "Tìm phòng", "Đặt phòng của tôi", "Ưu đãi", "Đánh giá", "Liên hệ"]

    current = st.session_state.page
    selected = st.radio("Điều hướng", menu, index=menu.index(current) if current in menu else 0)
    st.session_state.page = selected

    st.divider()
    st.success("🟢 Đặt phòng không cần tài khoản")
    st.caption("Chỉ cần nhập tên, email và số điện thoại khi đặt phòng.")

    render_chatbot()

# ----------------------------- Home -----------------------------
def home_page():
    st.markdown("""
    <div class="hero">
        <h1>🏨 HAPPY HOTEL</h1>
        <p>Đặt phòng nhanh chóng • Giá minh bạch • Trải nghiệm vui vẻ • Hỗ trợ 24/7</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.metric("⭐ Đánh giá", "4.9/5")
    with c2:
        st.metric("🛏️ Hạng phòng", "5")
    with c3:
        st.metric("💬 Hỗ trợ", "24/7")

    st.markdown("### 🔎 Tìm phòng nhanh")
    with st.container(border=True):
        a,b,c,d = st.columns(4)
        with a:
            ci = st.date_input("Nhận phòng", date.today() + timedelta(days=1), min_value=date.today())
        with b:
            co = st.date_input("Trả phòng", ci + timedelta(days=1), min_value=ci + timedelta(days=1))
        with c:
            guests = st.number_input("Số khách", min_value=1, max_value=10, value=2)
        with d:
            rt = st.selectbox("Hạng phòng", ["Tất cả","Standard","Deluxe","Family","Suite","VIP"])
        if st.button("🔍 Tìm phòng", type="primary", use_container_width=True):
            st.session_state.search = (ci, co, guests, rt)
            st.session_state.page = "Tìm phòng"
            st.rerun()

    st.markdown("### ✨ Phòng nổi bật")
    conn = db()
    featured = conn.execute("SELECT * FROM rooms WHERE active=1 ORDER BY price LIMIT 3").fetchall()
    conn.close()
    cols = st.columns(3)
    for col, room in zip(cols, featured):
        rating, count = room_rating(room["id"])
        with col:
            st.markdown(f"""
            <div class="card">
                <div style="font-size:55px">{room['icon']}</div>
                <h3>{room['name']}</h3>
                <span class="badge">{room['room_type']}</span>
                <p>{room['description']}</p>
                <div class="price">{money(room['price'])}<span class="small"> / đêm</span></div>
                <p>⭐ {rating:.1f} ({count} đánh giá) • 👥 tối đa {room['capacity']} khách</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Đặt {room['name']}", key=f"home_{room['id']}", use_container_width=True):
                st.session_state.selected_room = room["id"]
                st.session_state.page = "Tìm phòng"
                st.session_state.search = (
                    date.today() + timedelta(days=1),
                    date.today() + timedelta(days=2), 2, room["room_type"]
                )
                st.rerun()

# ----------------------------- Search -----------------------------
def search_page():
    st.markdown("## 🔎 Tìm & đặt phòng")
    default_search = st.session_state.get(
        "search",
        (date.today()+timedelta(days=1), date.today()+timedelta(days=2), 2, "Tất cả")
    )
    ci0, co0, g0, rt0 = default_search
    a,b,c,d = st.columns(4)
    with a: ci = st.date_input("Nhận phòng", ci0, min_value=date.today(), key="s_ci")
    with b: co = st.date_input("Trả phòng", co0, min_value=ci + timedelta(days=1), key="s_co")
    with c: guests = st.number_input("Số khách", 1, 10, int(g0), key="s_guests")
    with d: rt = st.selectbox("Hạng phòng", ["Tất cả","Standard","Deluxe","Family","Suite","VIP"],
                             index=["Tất cả","Standard","Deluxe","Family","Suite","VIP"].index(rt0) if rt0 in ["Tất cả","Standard","Deluxe","Family","Suite","VIP"] else 0)
    if co <= ci:
        st.error("Ngày trả phòng phải sau ngày nhận phòng.")
        return

    rooms = available_rooms(ci, co, guests, rt)
    st.info(f"🎯 Tìm thấy **{len(rooms)}** phòng phù hợp cho {guests} khách, {(co-ci).days} đêm.")

    if not rooms:
        st.warning("Không còn phòng phù hợp trong khoảng thời gian này. Hãy thử ngày khác hoặc hạng phòng khác.")
        return

    for room in rooms:
        rating, count = room_rating(room["id"])
        with st.container():
            st.markdown(f"""
            <div class="room-card">
                <div class="room-img">{room['icon']}</div>
                <div class="room-body">
                    <span class="badge">{room['room_type']}</span>
                    <h2>{room['name']}</h2>
                    <p>{room['description']}</p>
                    <p>🛏️ {room['beds']} &nbsp; • &nbsp; 👥 {room['capacity']} khách &nbsp; • &nbsp; 🏢 Tầng {room['floor']}</p>
                    <p>🧰 {room['amenities']}</p>
                    <p>⭐ {rating:.1f}/5 ({count} đánh giá)</p>
                    <div class="price">{money(room['price'])}<span class="small"> / đêm</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            x,y = st.columns([3,1])
            with x:
                st.caption(f"Tổng tiền phòng { (co-ci).days } đêm: {money(room['price']*(co-ci).days)}")
            with y:
                if st.button("🛎️ Đặt phòng", key=f"book_{room['id']}", type="primary", use_container_width=True):
                    st.session_state.selected_room = room["id"]
                    st.session_state.booking_dates = (ci, co, guests)
                    st.session_state.page = "Thanh toán"
                    st.rerun()

# ----------------------------- Booking / Payment -----------------------------
def booking_page():
    room_id = st.session_state.get("selected_room")
    if not room_id:
        st.info("Bạn chưa chọn phòng.")
        return

    conn = db()
    room = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    conn.close()
    if not room:
        st.error("Không tìm thấy phòng.")
        return

    ci0, co0, g0 = st.session_state.get(
        "booking_dates",
        (date.today()+timedelta(days=1), date.today()+timedelta(days=2), 2)
    )

    st.markdown("## 🛎️ Hoàn tất đặt phòng")
    left, right = st.columns([1.25, 1])

    with left:
        st.markdown(f"""
        <div class="card">
            <div style="font-size:60px">{room['icon']}</div>
            <h2>{room['name']}</h2>
            <span class="badge">{room['room_type']}</span>
            <p>{room['description']}</p>
            <p>🛏️ {room['beds']} • 👥 tối đa {room['capacity']} khách</p>
            <p>🧰 {room['amenities']}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("booking_form"):
            a,b = st.columns(2)
            with a:
                ci = st.date_input("Ngày nhận", ci0, min_value=date.today())
            with b:
                co = st.date_input("Ngày trả", co0, min_value=ci + timedelta(days=1))
            guests = st.number_input("Số khách", 1, room["capacity"], int(min(g0, room["capacity"])))
            guest_name = st.text_input("Tên khách", placeholder="Nguyễn Văn A")
            guest_email = st.text_input("Email", placeholder="you@example.com")
            guest_phone = st.text_input("Số điện thoại", placeholder="09xxxxxxxx")
            coupon = st.text_input("Mã giảm giá", placeholder="Ví dụ: HAPPY10")
            payment = st.selectbox("Phương thức thanh toán",
                                   ["Thanh toán tại khách sạn", "Chuyển khoản ngân hàng", "Ví điện tử (demo)"])
            note = st.text_area("Ghi chú đặc biệt", placeholder="Ví dụ: phòng tầng cao, giường phụ...")
            agree = st.checkbox("Tôi xác nhận thông tin đặt phòng là chính xác.")
            submit = st.form_submit_button("💳 Xác nhận đặt phòng", type="primary", use_container_width=True)

        if submit:
            if co <= ci:
                st.error("Ngày trả phải sau ngày nhận.")
            elif not guest_name or not guest_email or not guest_phone:
                st.error("Vui lòng điền đầy đủ thông tin khách.")
            elif not agree:
                st.error("Bạn cần xác nhận thông tin.")
            else:
                code, msg = create_booking(
                    room["id"], None, guest_name, guest_email, guest_phone,
                    ci, co, guests, payment, note, coupon
                )
                if code:
                    st.session_state.last_booking = code
                    st.success(f"🎉 Đặt phòng thành công! Mã đặt phòng: **{code}**")
                    if msg:
                        st.info(msg)
                    st.balloons()
                    st.session_state.page = "Đặt phòng của tôi"
                    st.rerun()
                else:
                    st.error(msg)

    with right:
        nights, room_total, service_fee, discount, total, msg = calc_total(
            room, ci0, co0, g0, ""
        )
        # Recalculate preview with default dates; actual form data is calculated after submit.
        st.markdown("### 🧾 Tạm tính")
        st.markdown(f"""
        <div class="card">
            <p>Giá phòng/đêm <b>{money(room['price'])}</b></p>
            <p>Số đêm <b>{nights}</b></p>
            <p>Tiền phòng <b>{money(room_total)}</b></p>
            <p>Phí dịch vụ 5% <b>{money(service_fee)}</b></p>
            <hr>
            <h2 style="color:#0f766e">{money(total)}</h2>
            <span class="small">Chưa áp dụng mã giảm giá nhập trong biểu mẫu.</span>
        </div>
        """, unsafe_allow_html=True)
        st.info("🔒 Đây là bản demo: không xử lý thẻ ngân hàng thật. Phương thức thanh toán chỉ mô phỏng.")

# ----------------------------- My bookings -----------------------------
def my_bookings_page():
    st.markdown("## 🧳 Tra cứu đặt phòng")
    st.caption("Không cần tài khoản. Nhập đúng email đã dùng khi đặt phòng để xem các đơn của bạn.")

    email = st.text_input("📧 Email đặt phòng", placeholder="you@example.com")
    if st.button("🔎 Tra cứu", type="primary", use_container_width=True):
        st.session_state.lookup_email = email.strip().lower()

    lookup = st.session_state.get("lookup_email", "")
    if not lookup:
        st.info("Nhập email rồi bấm 'Tra cứu'.")
        return

    rows = get_bookings(lookup)
    if not rows:
        st.warning("Không tìm thấy đặt phòng nào với email này.")
        return

    for b in rows:
        status_icon = {"Confirmed":"🟢", "Cancelled":"🔴", "Completed":"🔵"}.get(b["status"], "🟡")
        with st.expander(f"{status_icon} {b['code']} • {b['room_name']} • {money(b['total'])}"):
            a,bcol,c = st.columns(3)
            a.write(f"**Nhận phòng:** {b['check_in']}")
            bcol.write(f"**Trả phòng:** {b['check_out']}")
            c.write(f"**Trạng thái:** {b['status']}")
            st.write(f"👥 {b['guests']} khách • 🌙 {b['nights']} đêm")
            st.write(f"💳 {b['payment_method']}")
            st.write(f"💰 Tiền phòng: {money(b['room_total'])} • Phí: {money(b['service_fee'])} • Giảm: {money(b['discount'])}")
            st.write(f"**Tổng thanh toán: {money(b['total'])}**")
            if b["note"]:
                st.write(f"📝 {b['note']}")

            if b["status"] == "Confirmed":
                if st.button("❌ Hủy đặt phòng", key=f"cancel_{b['id']}"):
                    conn = db()
                    conn.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (b["id"],))
                    conn.commit()
                    conn.close()
                    st.success("Đã hủy đặt phòng.")
                    st.rerun()

# ----------------------------- Offers -----------------------------
def offers_page():
    st.markdown("## 🎁 Ưu đãi HAPPY HOTEL")
    offers = [
        ("HAPPY10", "Giảm 10%", "Giảm 10% trên tiền phòng + phí dịch vụ cho đơn từ 500.000đ."),
        ("WELCOME200", "Giảm 200.000đ", "Giảm 200.000đ cho đơn từ 1.000.000đ."),
        ("VIP15", "Giảm 15%", "Ưu đãi 15% cho đơn từ 2.000.000đ."),
    ]
    for code, title, desc in offers:
        st.markdown(f"""
        <div class="card">
            <span class="badge">{code}</span>
            <h2>🎁 {title}</h2>
            <p>{desc}</p>
            <p>Nhập mã ở bước đặt phòng.</p>
        </div>
        """, unsafe_allow_html=True)

# ----------------------------- Reviews -----------------------------
def reviews_page():
    st.markdown("## ⭐ Đánh giá của khách hàng")
    conn = db()
    rows = conn.execute("""
        SELECT rv.*, r.name room_name
        FROM reviews rv LEFT JOIN rooms r ON rv.room_id=r.id
        ORDER BY rv.created_at DESC
    """).fetchall()
    rooms = conn.execute("SELECT * FROM rooms WHERE active=1").fetchall()
    conn.close()

    st.markdown("### Viết đánh giá")
    with st.form("review"):
        guest_name = st.text_input("Tên hiển thị")
        room_id = st.selectbox("Hạng phòng", [r["id"] for r in rooms],
                               format_func=lambda x: next(r["name"] for r in rooms if r["id"] == x))
        rating = st.slider("Số sao", 1, 5, 5)
        comment = st.text_area("Nhận xét")
        submit = st.form_submit_button("Gửi đánh giá")
    if submit:
        if not guest_name.strip() or not comment.strip():
            st.error("Vui lòng nhập tên và nội dung đánh giá.")
        else:
            conn = db()
            conn.execute("""
                INSERT INTO reviews(booking_id,room_id,guest_name,rating,comment,created_at)
                VALUES(?,?,?,?,?,?)
            """, (None, room_id, guest_name.strip(), rating, comment.strip(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            st.success("Cảm ơn bạn đã đánh giá HAPPY HOTEL!")
            st.rerun()

    st.markdown("### Khách nói gì?")
    if not rows:
        st.info("Chưa có đánh giá.")
    for r in rows:
        st.markdown(f"""
        <div class="card">
            <b>{html.escape(r['guest_name'] or 'Khách HAPPY HOTEL')}</b>
            <span class="small"> • {html.escape(r['room_name'] or '')}</span>
            <p style="font-size:18px">{'⭐'*r['rating']}</p>
            <p>{html.escape(r['comment'] or '')}</p>
        </div>
        """, unsafe_allow_html=True)

# ----------------------------- Contact -----------------------------
def contact_page():
    st.markdown("## 📞 Liên hệ HAPPY HOTEL")
    a,b = st.columns(2)
    with a:
        st.markdown("""
        <div class="card">
        <h3>🏨 HAPPY HOTEL</h3>
        <p>📍 123 Đường Biển Vui Vẻ, Việt Nam</p>
        <p>☎️ Hotline: <b>1900 6868</b></p>
        <p>📧 hello@happyhotel.vn</p>
        <p>🕐 Lễ tân: 24/7</p>
        </div>
        """, unsafe_allow_html=True)
    with b:
        with st.form("contact"):
            name = st.text_input("Họ tên")
            email = st.text_input("Email")
            message = st.text_area("Nội dung cần hỗ trợ")
            submit = st.form_submit_button("Gửi yêu cầu", use_container_width=True)
        if submit:
            if not name or not email or not message:
                st.error("Vui lòng điền đầy đủ thông tin.")
            else:
                st.success("Đã tiếp nhận yêu cầu. HAPPY HOTEL sẽ liên hệ lại sớm.")

# ----------------------------- Admin -----------------------------
def admin_page():
    st.info("Chế độ quản trị đã được ẩn trong phiên bản không cần tài khoản.")
    return

    st.markdown("## ⚙️ HAPPY HOTEL — Quản trị")
    rooms, bookings, revenue, customers = get_stats()
    a,b,c,d = st.columns(4)
    for col, n, label in [
        (a, rooms, "Phòng hoạt động"),
        (b, bookings, "Tổng đặt phòng"),
        (c, money(revenue), "Doanh thu"),
        (d, customers, "Khách hàng"),
    ]:
        with col:
            st.markdown(f'<div class="kpi"><div class="n">{n}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Đặt phòng", "🛏️ Phòng", "👥 Khách hàng"])

    with tab1:
        rows = get_bookings()
        if rows:
            data = [{
                "Mã": r["code"], "Khách": r["guest_name"], "Phòng": r["room_name"],
                "Nhận": r["check_in"], "Trả": r["check_out"], "Khách": r["guests"],
                "Tổng": money(r["total"]), "Trạng thái": r["status"]
            } for r in rows]
            st.dataframe(data, use_container_width=True, hide_index=True)
            codes = [r["code"] for r in rows if r["status"] == "Confirmed"]
            if codes:
                code = st.selectbox("Chọn mã để cập nhật", codes)
                status = st.selectbox("Trạng thái mới", ["Confirmed","Completed","Cancelled"])
                if st.button("Cập nhật trạng thái"):
                    conn = db()
                    conn.execute("UPDATE bookings SET status=? WHERE code=?", (status, code))
                    conn.commit()
                    conn.close()
                    st.success("Đã cập nhật.")
                    st.rerun()
        else:
            st.info("Chưa có đặt phòng.")

    with tab2:
        conn = db()
        room_rows = conn.execute("SELECT * FROM rooms ORDER BY id").fetchall()
        conn.close()
        st.dataframe([{
            "ID": r["id"], "Tên": r["name"], "Loại": r["room_type"],
            "Giá": money(r["price"]), "Sức chứa": r["capacity"], "Active": bool(r["active"])
        } for r in room_rows], use_container_width=True, hide_index=True)

        st.markdown("### Thêm phòng")
        with st.form("add_room"):
            n1,n2 = st.columns(2)
            name = n1.text_input("Tên phòng")
            rtype = n2.selectbox("Loại", ["Standard","Deluxe","Family","Suite","VIP"])
            desc = st.text_area("Mô tả")
            n3,n4,n5 = st.columns(3)
            price = n3.number_input("Giá/đêm", 100000, 100000000, 1000000, step=50000)
            capacity = n4.number_input("Sức chứa", 1, 20, 2)
            floor = n5.number_input("Tầng", 1, 100, 1)
            beds = st.text_input("Giường", "1 giường đôi")
            amenities = st.text_input("Tiện nghi", "WiFi, TV, Điều hòa")
            icon = st.text_input("Emoji", "🛏️")
            add = st.form_submit_button("Thêm phòng")
        if add:
            if not name:
                st.error("Tên phòng là bắt buộc.")
            else:
                conn = db()
                conn.execute("""
                    INSERT INTO rooms(name,room_type,description,price,capacity,beds,amenities,icon,floor)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, (name,rtype,desc,price,capacity,beds,amenities,icon,floor))
                conn.commit()
                conn.close()
                st.success("Đã thêm phòng.")
                st.rerun()

    with tab3:
        conn = db()
        users = conn.execute("SELECT id,name,email,phone,role,created_at FROM users ORDER BY id DESC").fetchall()
        conn.close()
        st.dataframe([dict(x) for x in users], use_container_width=True, hide_index=True)

# ----------------------------- Main router -----------------------------
if st.session_state.page == "Trang chủ":
    home_page()
elif st.session_state.page == "Tìm phòng":
    search_page()
elif st.session_state.page == "Thanh toán":
    booking_page()
elif st.session_state.page == "Đặt phòng của tôi":
    my_bookings_page()
elif st.session_state.page == "Ưu đãi":
    offers_page()
elif st.session_state.page == "Đánh giá":
    reviews_page()
elif st.session_state.page == "Liên hệ":
    contact_page()
elif st.session_state.page == "⚙️ Quản trị":
    admin_page()
else:
    home_page()

st.markdown("""
<div class="footer">
    🏨 <b>HAPPY HOTEL</b> • Booking system • Không cần tài khoản • Built with Streamlit + SQLite<br>
    © 2026 HAPPY HOTEL
</div>
""", unsafe_allow_html=True)
