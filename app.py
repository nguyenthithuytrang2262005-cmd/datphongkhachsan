import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import qrcode
from io import BytesIO
import os

# 1. CẤU HÌNH TRANG (Bắt buộc phải đặt ở đầu tiên)
st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide"
)

# Hiển thị Logo nếu có file
if os.path.exists("logo1.jpg"):
    st.image("logo1.jpg", width=200)

# ================= DATABASE (MYSQL - AIVEN) ===================

MYSQL_HOST = "mysql-6ab5bcf-trandinhphuc1702-e8a7.e.aivencloud.com"
MYSQL_PORT = 20874
MYSQL_USER = "avnadmin"
MYSQL_PASSWORD = "AVNS_0L4tfzDCvAVBs0WWRXK"
MYSQL_DB = "defaultdb"

def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        ssl_disabled=False
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Tạo bảng rooms
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        room VARCHAR(10) PRIMARY KEY,
        type VARCHAR(50),
        price INT,
        status VARCHAR(50)
    )
    """)
    
    # Tạo bảng bookings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guest VARCHAR(255),
        phone VARCHAR(50),
        idcard VARCHAR(50),
        room VARCHAR(10),
        checkin VARCHAR(50),
        checkout VARCHAR(50),
        guests INT,
        status VARCHAR(50),
        total INT
    )
    """)
    conn.commit()
    
    # Thêm phòng mặc định nếu cơ sở dữ liệu trống
    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] == 0:
        rooms_data = [
            ("101", "Standard", 500000, "Available"),
            ("102", "Standard", 500000, "Available"),
            ("201", "Deluxe", 700000, "Available"),
            ("202", "Deluxe", 700000, "Available"),
            ("301", "Suite", 1200000, "Available"),
            ("302", "VIP", 1800000, "Maintenance")
        ]
        cur.executemany("INSERT INTO rooms VALUES (%s, %s, %s, %s)", rooms_data)
        conn.commit()
        
    cur.close()
    conn.close()

# Khởi tạo DB
init_db()

# ================= FUNCTIONS ==================

def load_rooms():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM rooms", conn)
    conn.close()
    return df

def load_bookings():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM bookings", conn)
    conn.close()
    return df

def update_room(room_id, status_val):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE rooms SET status = %s WHERE room = %s", (status_val, room_id))
    conn.commit()
    cur.close()
    conn.close()

# ================== HEADER ====================

st.markdown("""
# 🏨 HAPPY HOTEL
### Luxury Hotel Management System
""")

menu = st.sidebar.radio(
    "MENU",
    ["📊 Dashboard",
     "🛏 Room Management",
     "📅 Reservation",
     "🟢 Check In",
     "🔴 Check Out",
     "👥 Guests",
     "📈 Revenue",
     "💬 AI ChatBox"]
)

rooms = load_rooms()
bookings = load_bookings()

# ================= DASHBOARD ==================

if menu == "📊 Dashboard":

    total_rooms = len(rooms)
    available = len(rooms[rooms.status == "Available"])
    occupied = len(rooms[rooms.status == "Occupied"])

    revenue = bookings[bookings.status == "Completed"]["total"].sum() if len(bookings) > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Rooms", total_rooms)
    c2.metric("Available", available)
    c3.metric("Occupied", occupied)
    c4.metric("Occupancy", f"{round((occupied/total_rooms)*100, 1) if total_rooms > 0 else 0}%")

    st.divider()

    # ROOM CATEGORIES
    st.subheader("🏨 Room Categories")

    if not rooms.empty:
        room_types = rooms.groupby("type")["price"].first().reset_index()
        cols = st.columns(len(room_types))

        for i, row in room_types.iterrows():
            with cols[i]:
                st.markdown(f"""
                <div style="padding:16px;border-radius:12px;background:#F8F9FA;text-align:center">
                    <h4>{row['type']}</h4>
                    <h3>{row['price']:,} VND</h3>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Revenue Summary")
    st.metric("Total Revenue", f"{revenue:,} VND")

# ================= ROOM MANAGEMENT =================

elif menu == "🛏 Room Management":

    st.subheader("Room Management")
    st.dataframe(rooms, use_container_width=True)

    with st.expander("➕ Add Room"):
        r = st.text_input("Room Number")
        t = st.selectbox("Type", ["Standard", "Deluxe", "Suite", "VIP"])
        p = st.number_input("Price", 100000, 5000000, 500000)

        if st.button("Add Room"):
            if r:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO rooms VALUES (%s, %s, %s, %s)", (r, t, p, "Available"))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Added successfully!")
                st.rerun()
            else:
                st.error("Please input Room Number!")

    st.divider()

    if not rooms.empty:
        room_select = st.selectbox("Select Room", rooms.room)
        new_status = st.selectbox("Change Status",
            ["Available", "Occupied", "Reserved", "Cleaning", "Maintenance"])

        if st.button("Update Status"):
            update_room(room_select, new_status)
            st.success("Updated successfully!")
            st.rerun()

# ================= RESERVATION =================

elif menu == "📅 Reservation":

    st.subheader("New Reservation")
    available_rooms = rooms[rooms.status == "Available"]

    if len(available_rooms) == 0:
        st.error("No available rooms")
        st.stop()

    name = st.text_input("Guest Name")
    phone = st.text_input("Phone")
    idcard = st.text_input("ID Card")

    guests = st.slider("Guests", 1, 6, 2)
    room = st.selectbox("Choose Room", available_rooms.room)

    c1, c2 = st.columns(2)
    checkin = c1.date_input("Check In", date.today())
    checkout = c2.date_input("Check Out", date.today())

    price = int(rooms[rooms.room == room].price.values[0])
    nights = max((checkout - checkin).days, 1)
    total = price * nights

    st.info(f"{nights} night(s) | Total = {total:,} VND")

    # AI Recommendation
    st.markdown("### 🤖 Smart Recommendation")
    if guests <= 2:
        st.success("Recommended: Standard / Deluxe")
    elif guests <= 4:
        st.success("Recommended: Deluxe / Suite")
    else:
        st.success("Recommended: VIP")

    if st.button("Reserve"):
        if name and phone:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO bookings
            (guest, phone, idcard, room, checkin, checkout, guests, status, total)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, phone, idcard, room, str(checkin), str(checkout), guests, "Reserved", total))
            conn.commit()
            cur.close()
            conn.close()

            update_room(room, "Reserved")
            st.success("Reservation Successful!")

            # QR Code Generation
            qr = qrcode.make(f"Guest: {name} | Room: {room} | Check-in: {checkin}")
            buf = BytesIO()
            qr.save(buf)
            st.image(buf)
        else:
            st.error("Please fill in Guest Name and Phone Number!")

# ================= CHECK IN =================

elif menu == "🟢 Check In":

    reserved = bookings[bookings.status == "Reserved"]
    st.subheader("Check In")

    if len(reserved) == 0:
        st.info("No active reservations")
    else:
        book_id = st.selectbox("Booking ID", reserved.id)
        row = reserved[reserved.id == book_id].iloc[0]

        st.write(f"**Guest:** {row.guest}")
        st.write(f"**Room:** {row.room}")

        if st.button("Check In"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            UPDATE bookings
            SET status = 'Checked In'
            WHERE id = %s
            """, (int(book_id),))
            conn.commit()
            cur.close()
            conn.close()

            update_room(row.room, "Occupied")
            st.success("Checked In Successfully!")
            st.rerun()

# ================= CHECK OUT =================

elif menu == "🔴 Check Out":

    staying = bookings[bookings.status == "Checked In"]
    st.subheader("Check Out")

    if len(staying) == 0:
        st.info("No guests currently staying")
    else:
        bid = st.selectbox("Booking ID", staying.id)
        row = staying[staying.id == bid].iloc[0]

        st.write(f"**Guest:** {row.guest}")
        st.write(f"**Room:** {row.room}")

        st.metric("Room Payment", f"{row.total:,} VND")

        minibar = st.number_input("MiniBar Service", 0, 5000000, 0)
        laundry = st.number_input("Laundry Service", 0, 5000000, 0)

        final = row.total + minibar + laundry
        st.metric("Grand Total", f"{final:,} VND")

        if st.button("Complete Check Out"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            UPDATE bookings
            SET status = 'Completed', total = %s
            WHERE id = %s
            """, (int(final), int(bid)))
            conn.commit()
            cur.close()
            conn.close()

            update_room(row.room, "Cleaning")
            st.success("Check Out Completed!")
            st.rerun()

# ================= GUESTS =================

elif menu == "👥 Guests":

    st.subheader("Guest List")
    keyword = st.text_input("Search Guest Name")

    df = bookings.copy()
    if keyword != "" and not df.empty:
        df = df[df.guest.str.contains(keyword, case=False, na=False)]

    st.dataframe(df, use_container_width=True)

    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇ Export CSV",
            csv,
            "guests.csv",
            "text/csv"
        )

# ================= REVENUE =================

elif menu == "📈 Revenue":

    st.subheader("Revenue Analytics")
    df = bookings[bookings.status == "Completed"]

    if len(df) == 0:
        st.info("No revenue recorded yet")
    else:
        df["checkin"] = pd.to_datetime(df["checkin"])
        daily = df.groupby(df["checkin"].dt.date)["total"].sum().reset_index()

        fig = px.line(
            daily,
            x="checkin",
            y="total",
            markers=True,
            title="Daily Revenue Trend"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

# ================= AI CHATBOX =================

elif menu == "💬 AI ChatBox":

    st.subheader("💬 HAPPY HOTEL AI Assistant")
    st.caption("Trợ lý ảo hỗ trợ khách hàng và lễ tân 24/7")

    # Lưu lịch sử chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 Xin chào! Tôi là trợ lý của HAPPY HOTEL. Tôi có thể giúp đặt phòng, giá phòng, check-in/check-out và thông tin khách sạn."
            }
        ]

    # Hiển thị lịch sử
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Nhập câu hỏi của bạn...")

    if prompt:
        st.session_state.messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.write(prompt)

        text = prompt.lower()

        # AI trả lời theo dữ liệu khách sạn
        if "giá" in text or "price" in text:
            if not rooms.empty:
                price_list = rooms.groupby("type")["price"].first()
                reply = "### 💵 Bảng giá phòng\n"
                for t, p in price_list.items():
                    reply += f"- **{t}**: {p:,} VND/đêm\n"
            else:
                reply = "Chưa có thông tin bảng giá."

        elif "phòng trống" in text or "available" in text:
            av = rooms[rooms.status == "Available"]
            if len(av) == 0:
                reply = "Hiện tại không còn phòng trống."
            else:
                reply = "### 🟢 Phòng đang trống\n"
                for _, r in av.iterrows():
                    reply += f"- Phòng **{r.room}** ({r.type})\n"

        elif "check in" in text:
            reply = "🟢 Giờ Check-in: **14:00**"

        elif "check out" in text:
            reply = "🔴 Giờ Check-out: **12:00**"

        elif "wifi" in text:
            reply = "📶 Wifi: **HAPPYHOTEL_FREE**\nMật khẩu: **happy123**"

        elif "địa chỉ" in text:
            reply = "📍 HAPPY HOTEL - 123 Đường Biển, Vũng Tàu"

        elif "liên hệ" in text or "sdt" in text:
            reply = "☎ Hotline: **0909 888 999**"

        elif "doanh thu" in text:
            rev = bookings[bookings.status == "Completed"]["total"].sum() if len(bookings) > 0 else 0
            reply = f"💰 Tổng doanh thu hiện tại: **{rev:,} VND**"

        else:
            reply = (
                "Tôi có thể hỗ trợ:\n\n"
                "• 💵 Giá phòng\n"
                "• 🛏 Phòng còn trống\n"
                "• 📅 Đặt phòng\n"
                "• 🟢 Giờ Check-in\n"
                "• 🔴 Giờ Check-out\n"
                "• 📶 Wifi\n"
                "• 💰 Doanh thu"
            )

        st.session_state.messages.append(
            {"role": "assistant", "content": reply}
        )

        with st.chat_message("assistant"):
            st.markdown(reply)
