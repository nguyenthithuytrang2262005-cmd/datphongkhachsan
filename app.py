import streamlit as st
import pymysql
import pandas as pd
from datetime import date
import plotly.express as px
import qrcode
from io import BytesIO

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide"
)

# ============================================================
# DATABASE CONFIG - AIVEN MYSQL
# ============================================================
DB_HOST = "mysql-6ab5bcf-trandinhphuc1702-e8a7.e.aivencloud.com"
DB_PORT = 20874
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_0L4tfzDCvAVBs0WWRXK"
DB_NAME = "defaultdb"

# Aiven MySQL normally requires SSL/TLS.
# ssl_verify_cert=False allows the app to connect without a local CA file.
# Traffic is still encrypted by SSL/TLS.
DB_SSL = {
    "ssl_verify_cert": False,
    "ssl_verify_identity": False
}


# ============================================================
# DATABASE FUNCTIONS
# ============================================================
@st.cache_resource
def get_connection():
    """Create and cache the Aiven MySQL connection."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=15,
        read_timeout=30,
        write_timeout=30,
        ssl=DB_SSL
    )


def get_conn():
    """Return a usable connection. Reconnect automatically if needed."""
    try:
        conn = get_connection()
        conn.ping(reconnect=True)
        return conn
    except Exception:
        get_connection.clear()
        conn = get_connection()
        conn.ping(reconnect=True)
        return conn


def execute_query(sql, params=None, fetch=False):
    """Execute INSERT/UPDATE/DELETE or SELECT."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if fetch:
                return cur.fetchall()
            return cur.lastrowid
    except Exception:
        # Retry once after reconnecting
        get_connection.clear()
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if fetch:
                return cur.fetchall()
            return cur.lastrowid


def load_rooms():
    rows = execute_query(
        "SELECT room, type, price, status FROM rooms ORDER BY room",
        fetch=True
    )
    return pd.DataFrame(rows, columns=["room", "type", "price", "status"])


def load_bookings():
    rows = execute_query(
        """
        SELECT id, guest, phone, idcard, room, checkin, checkout,
               guests, status, total
        FROM bookings
        ORDER BY id DESC
        """,
        fetch=True
    )
    return pd.DataFrame(
        rows,
        columns=[
            "id", "guest", "phone", "idcard", "room",
            "checkin", "checkout", "guests", "status", "total"
        ]
    )


def update_room(room, status):
    execute_query(
        "UPDATE rooms SET status=%s WHERE room=%s",
        (status, room)
    )


def initialize_database():
    """Create tables and default rooms if they do not exist."""
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            room VARCHAR(20) PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            price BIGINT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'Available'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            guest VARCHAR(150) NOT NULL,
            phone VARCHAR(30),
            idcard VARCHAR(50),
            room VARCHAR(20) NOT NULL,
            checkin DATE NOT NULL,
            checkout DATE NOT NULL,
            guests INT NOT NULL DEFAULT 1,
            status VARCHAR(30) NOT NULL DEFAULT 'Reserved',
            total BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_bookings_room (room),
            INDEX idx_bookings_status (status),
            INDEX idx_bookings_checkin (checkin)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    default_rooms = [
        ("101", "Standard", 500000, "Available"),
        ("102", "Standard", 500000, "Available"),
        ("201", "Deluxe", 700000, "Available"),
        ("202", "Deluxe", 700000, "Available"),
        ("301", "Suite", 1200000, "Available"),
        ("302", "VIP", 1800000, "Maintenance")
    ]

    conn = get_conn()
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO rooms (room, type, price, status)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                room = VALUES(room)
            """,
            default_rooms
        )


# ============================================================
# INITIALIZE DATABASE
# ============================================================
try:
    initialize_database()
except Exception as e:
    st.error("❌ Không thể kết nối MySQL Aiven.")
    st.code(str(e))
    st.info(
        "Kiểm tra Host, Port, User, Password, database defaultdb "
        "và SSL/TLS của Aiven."
    )
    st.stop()


# ============================================================
# LOGO
# ============================================================
try:
    st.image("logo1.jpg", width=180)
except Exception:
    pass


# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
    <div style="
        padding: 10px 0 5px 0;
        text-align: center;
    ">
        <h1>🏨 HAPPY HOTEL</h1>
        <h3>Luxury Hotel Management System</h3>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR MENU
# ============================================================
menu = st.sidebar.radio(
    "MENU",
    [
        "📊 Dashboard",
        "🛏 Room Management",
        "📅 Reservation",
        "🟢 Check In",
        "🔴 Check Out",
        "👥 Guests",
        "📈 Revenue",
        "💬 AI ChatBox"
    ]
)


# ============================================================
# LOAD DATA
# ============================================================
rooms = load_rooms()
bookings = load_bookings()


# ============================================================
# DASHBOARD
# ============================================================
if menu == "📊 Dashboard":

    total_rooms = len(rooms)
    available = len(rooms[rooms["status"] == "Available"])
    occupied = len(rooms[rooms["status"] == "Occupied"])

    completed = bookings[bookings["status"] == "Completed"]
    revenue = int(completed["total"].sum()) if len(completed) > 0 else 0

    occupancy = round((occupied / total_rooms) * 100, 1) if total_rooms else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Rooms", total_rooms)
    c2.metric("Available", available)
    c3.metric("Occupied", occupied)
    c4.metric("Occupancy", f"{occupancy}%")

    st.divider()

    st.subheader("🏨 Room Categories")

    if len(rooms) > 0:
        room_types = rooms.groupby("type", as_index=False)["price"].first()
        cols = st.columns(len(room_types))

        for i, row in room_types.iterrows():
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="
                        padding:16px;
                        border-radius:12px;
                        background:#F8F9FA;
                        text-align:center;
                        margin-bottom:10px;
                    ">
                        <h4>{row["type"]}</h4>
                        <h3>{int(row["price"]):,} VND</h3>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.divider()
    st.subheader("Revenue Summary")
    st.metric("Total Revenue", f"{revenue:,} VND")


# ============================================================
# ROOM MANAGEMENT
# ============================================================
elif menu == "🛏 Room Management":

    st.subheader("🛏 Room Management")

    st.dataframe(
        rooms,
        use_container_width=True,
        hide_index=True
    )

    with st.expander("➕ Add Room"):

        r = st.text_input("Room Number")
        t = st.selectbox(
            "Type",
            ["Standard", "Deluxe", "Suite", "VIP"]
        )
        p = st.number_input(
            "Price",
            min_value=100000,
            max_value=5000000,
            value=500000,
            step=50000
        )

        if st.button("Add Room", type="primary"):

            if not r.strip():
                st.error("Vui lòng nhập số phòng.")
            elif r.strip() in rooms["room"].astype(str).tolist():
                st.error("Phòng này đã tồn tại.")
            else:
                try:
                    execute_query(
                        """
                        INSERT INTO rooms (room, type, price, status)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (r.strip(), t, int(p), "Available")
                    )
                    st.success("✅ Đã thêm phòng.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Không thể thêm phòng: {e}")

    st.divider()

    if len(rooms) > 0:
        room_select = st.selectbox(
            "Select Room",
            rooms["room"].tolist()
        )

        new_status = st.selectbox(
            "Change Status",
            [
                "Available",
                "Occupied",
                "Reserved",
                "Cleaning",
                "Maintenance"
            ]
        )

        if st.button("Update Status"):

            update_room(room_select, new_status)

            st.success("✅ Đã cập nhật trạng thái phòng.")
            st.rerun()


# ============================================================
# RESERVATION
# ============================================================
elif menu == "📅 Reservation":

    st.subheader("📅 New Reservation")

    available_rooms = rooms[rooms["status"] == "Available"]

    if len(available_rooms) == 0:
        st.error("❌ Hiện tại không còn phòng trống.")
        st.stop()

    name = st.text_input("Guest Name")
    phone = st.text_input("Phone")
    idcard = st.text_input("ID Card")

    guests = st.slider(
        "Guests",
        min_value=1,
        max_value=6,
        value=2
    )

    room = st.selectbox(
        "Choose Room",
        available_rooms["room"].tolist()
    )

    c1, c2 = st.columns(2)

    checkin = c1.date_input(
        "Check In",
        date.today()
    )

    checkout = c2.date_input(
        "Check Out",
        date.today()
    )

    selected_room = rooms[rooms["room"] == room]

    if len(selected_room) > 0:
        price = int(selected_room.iloc[0]["price"])
    else:
        price = 0

    nights = max((checkout - checkin).days, 1)
    total = price * nights

    st.info(
        f"🛏 {nights} night(s) | "
        f"Price = {price:,} VND/night | "
        f"Total = {total:,} VND"
    )

    # Smart Recommendation
    st.markdown("### 🤖 Smart Recommendation")

    if guests <= 2:
        st.success("Recommended: Standard / Deluxe")
    elif guests <= 4:
        st.success("Recommended: Deluxe / Suite")
    else:
        st.success("Recommended: VIP")

    if st.button("Reserve", type="primary"):

        if not name.strip():
            st.error("Vui lòng nhập tên khách.")
        elif checkout <= checkin:
            st.error("Ngày Check Out phải sau ngày Check In.")
        else:
            try:
                booking_id = execute_query(
                    """
                    INSERT INTO bookings
                    (
                        guest,
                        phone,
                        idcard,
                        room,
                        checkin,
                        checkout,
                        guests,
                        status,
                        total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        name.strip(),
                        phone.strip(),
                        idcard.strip(),
                        room,
                        checkin,
                        checkout,
                        guests,
                        "Reserved",
                        total
                    )
                )

                update_room(room, "Reserved")

                st.success(
                    f"✅ Reservation Successful! Booking ID: {booking_id}"
                )

                # QR
                qr_data = (
                    f"HAPPY HOTEL\n"
                    f"Booking ID: {booking_id}\n"
                    f"Guest: {name}\n"
                    f"Room: {room}\n"
                    f"Check-in: {checkin}\n"
                    f"Check-out: {checkout}"
                )

                qr = qrcode.make(qr_data)

                buf = BytesIO()
                qr.save(buf, format="PNG")
                buf.seek(0)

                st.image(
                    buf,
                    caption="Reservation QR Code",
                    width=220
                )

                st.rerun()

            except Exception as e:
                st.error(f"❌ Không thể tạo đặt phòng: {e}")


# ============================================================
# CHECK IN
# ============================================================
elif menu == "🟢 Check In":

    st.subheader("🟢 Check In")

    reserved = bookings[bookings["status"] == "Reserved"]

    if len(reserved) == 0:
        st.info("No reservation")
    else:

        booking_options = reserved["id"].tolist()

        book_id = st.selectbox(
            "Booking ID",
            booking_options
        )

        row = reserved[reserved["id"] == book_id].iloc[0]

        st.write(f"**Guest:** {row['guest']}")
        st.write(f"**Phone:** {row['phone']}")
        st.write(f"**Room:** {row['room']}")
        st.write(f"**Check-in:** {row['checkin']}")
        st.write(f"**Check-out:** {row['checkout']}")
        st.write(f"**Guests:** {row['guests']}")

        if st.button("Check In", type="primary"):

            execute_query(
                """
                UPDATE bookings
                SET status='Checked In'
                WHERE id=%s
                """,
                (int(book_id),)
            )

            update_room(row["room"], "Occupied")

            st.success("✅ Checked In")
            st.rerun()


# ============================================================
# CHECK OUT
# ============================================================
elif menu == "🔴 Check Out":

    st.subheader("🔴 Check Out")

    staying = bookings[bookings["status"] == "Checked In"]

    if len(staying) == 0:
        st.info("No guest staying")
    else:

        bid = st.selectbox(
            "Booking",
            staying["id"].tolist()
        )

        row = staying[staying["id"] == bid].iloc[0]

        st.write(f"**Guest:** {row['guest']}")
        st.write(f"**Room:** {row['room']}")

        st.metric(
            "Room Payment",
            f"{int(row['total']):,} VND"
        )

        minibar = st.number_input(
            "MiniBar",
            min_value=0,
            max_value=5000000,
            value=0,
            step=10000
        )

        laundry = st.number_input(
            "Laundry",
            min_value=0,
            max_value=5000000,
            value=0,
            step=10000
        )

        final = int(row["total"]) + int(minibar) + int(laundry)

        st.metric(
            "Grand Total",
            f"{final:,} VND"
        )

        if st.button("Complete Check Out", type="primary"):

            execute_query(
                """
                UPDATE bookings
                SET status='Completed',
                    total=%s
                WHERE id=%s
                """,
                (final, int(bid))
            )

            update_room(row["room"], "Cleaning")

            st.success("✅ Check Out Completed")
            st.rerun()


# ============================================================
# GUESTS
# ============================================================
elif menu == "👥 Guests":

    st.subheader("👥 Guest List")

    keyword = st.text_input(
        "Search by guest name / phone / ID card / room"
    )

    df = bookings.copy()

    if keyword.strip() != "":
        keyword_lower = keyword.strip().lower()

        if len(df) > 0:
            mask = (
                df["guest"].fillna("").astype(str).str.lower().str.contains(
                    keyword_lower, regex=False
                )
                |
                df["phone"].fillna("").astype(str).str.lower().str.contains(
                    keyword_lower, regex=False
                )
                |
                df["idcard"].fillna("").astype(str).str.lower().str.contains(
                    keyword_lower, regex=False
                )
                |
                df["room"].fillna("").astype(str).str.lower().str.contains(
                    keyword_lower, regex=False
                )
            )

            df = df[mask]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇ Export CSV",
        csv,
        "guests.csv",
        "text/csv"
    )


# ============================================================
# REVENUE
# ============================================================
elif menu == "📈 Revenue":

    st.subheader("📈 Revenue Analytics")

    df = bookings[
        bookings["status"] == "Completed"
    ].copy()

    if len(df) == 0:

        st.info("No revenue yet")

    else:

        df["checkin"] = pd.to_datetime(
            df["checkin"],
            errors="coerce"
        )

        daily = (
            df.dropna(subset=["checkin"])
            .groupby(df["checkin"].dt.date)["total"]
            .sum()
            .reset_index()
        )

        fig = px.line(
            daily,
            x="checkin",
            y="total",
            markers=True,
            title="Daily Revenue"
        )

        fig.update_yaxes(
            tickformat=",",
            title="Revenue (VND)"
        )

        fig.update_xaxes(
            title="Date"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.metric(
            "Total Revenue",
            f"{int(df['total'].sum()):,} VND"
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# AI CHATBOX
# ============================================================
elif menu == "💬 AI ChatBox":

    st.subheader("💬 HAPPY HOTEL AI Assistant")
    st.caption(
        "Trợ lý ảo hỗ trợ khách hàng và lễ tân 24/7"
    )

    if "messages" not in st.session_state:

        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Xin chào! Tôi là trợ lý của HAPPY HOTEL. "
                    "Tôi có thể giúp bạn xem giá phòng, phòng trống, "
                    "giờ check-in/check-out và doanh thu."
                )
            }
        ]

    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input(
        "Nhập câu hỏi của bạn..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        with st.chat_message("user"):
            st.write(prompt)

        text = prompt.lower().strip()

        # ====================================================
        # PRICE
        # ====================================================
        if (
            "giá" in text
            or "price" in text
            or "bao nhiêu tiền" in text
        ):

            price_list = rooms.groupby(
                "type"
            )["price"].first()

            reply = "### 💵 Bảng giá phòng\n"

            for room_type, room_price in price_list.items():
                reply += (
                    f"- **{room_type}**: "
                    f"{int(room_price):,} VND/đêm\n"
                )

        # ====================================================
        # AVAILABLE ROOMS
        # ====================================================
        elif (
            "phòng trống" in text
            or "phòng còn trống" in text
            or "available" in text
        ):

            av = rooms[
                rooms["status"] == "Available"
            ]

            if len(av) == 0:

                reply = "Hiện tại không còn phòng trống."

            else:

                reply = "### 🛏 Phòng đang trống\n"

                for _, r in av.iterrows():

                    reply += (
                        f"- Phòng **{r['room']}** "
                        f"({r['type']}) - "
                        f"{int(r['price']):,} VND/đêm\n"
                    )

        # ====================================================
        # CHECK IN
        # ====================================================
        elif (
            "check in" in text
            or "check-in" in text
            or "nhận phòng" in text
        ):

            reply = "🟢 Giờ Check-in: **14:00**"

        # ====================================================
        # CHECK OUT
        # ====================================================
        elif (
            "check out" in text
            or "check-out" in text
            or "trả phòng" in text
        ):

            reply = "🔴 Giờ Check-out: **12:00**"

        # ====================================================
        # WIFI
        # ====================================================
        elif "wifi" in text:

            reply = (
                "📶 Wifi: **HAPPYHOTEL_FREE**\n\n"
                "Mật khẩu: **happy123**"
            )

        # ====================================================
        # ADDRESS
        # ====================================================
        elif (
            "địa chỉ" in text
            or "địa điểm" in text
        ):

            reply = (
                "📍 HAPPY HOTEL - "
                "123 Đường Biển, Vũng Tàu"
            )

        # ====================================================
        # CONTACT
        # ====================================================
        elif (
            "liên hệ" in text
            or "sdt" in text
            or "số điện thoại" in text
            or "hotline" in text
        ):

            reply = (
                "☎ Hotline: **0909 888 999**"
            )

        # ====================================================
        # REVENUE
        # ====================================================
        elif (
            "doanh thu" in text
            or "revenue" in text
        ):

            rev = bookings[
                bookings["status"] == "Completed"
            ]["total"].sum()

            reply = (
                "💰 Tổng doanh thu hiện tại: "
                f"**{int(rev):,} VND**"
            )

        # ====================================================
        # DEFAULT
        # ====================================================
        else:

            reply = (
                "Tôi có thể hỗ trợ:\n\n"
                "• 💵 Giá phòng\n"
                "• 🛏 Phòng còn trống\n"
                "• 📅 Thông tin đặt phòng\n"
                "• 🟢 Giờ Check-in\n"
                "• 🔴 Giờ Check-out\n"
                "• 📶 Wifi\n"
                "• 📍 Địa chỉ khách sạn\n"
                "• ☎ Hotline\n"
                "• 💰 Doanh thu"
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        with st.chat_message("assistant"):
            st.markdown(reply)
