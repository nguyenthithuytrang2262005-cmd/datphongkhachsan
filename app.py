import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import uuid
import plotly.express as px

st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide"
)

# ==========================
# DATABASE
# ==========================
conn = sqlite3.connect("hotel.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS rooms(
room TEXT PRIMARY KEY,
type TEXT,
price INTEGER,
status TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS bookings(
id TEXT,
name TEXT,
phone TEXT,
room TEXT,
room_type TEXT,
checkin TEXT,
checkout TEXT,
nights INTEGER,
total INTEGER,
status TEXT
)
""")
conn.commit()

# Tạo phòng lần đầu
if cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
    rooms = []

    # 20 Standard
    for i in range(101, 121):
        rooms.append((str(i), "Standard", 500000, "Available"))

    # 10 Deluxe
    for i in range(201, 211):
        rooms.append((str(i), "Deluxe", 800000, "Available"))

    # 5 Suite
    for i in range(301, 306):
        rooms.append((str(i), "Suite", 1200000, "Available"))

    # 5 VIP Villa
    for i in range(401, 406):
        rooms.append((str(i), "VIP Villa", 2500000, "Available"))

    cur.executemany("INSERT INTO rooms VALUES(?,?,?,?)", rooms)
    conn.commit()

# ==========================
# HEADER
# ==========================
st.markdown("""
# 🏨 HAPPY HOTEL
### *Luxury Hotel Booking System*
""")

menu = st.sidebar.radio(
    "📋 MENU",
    ["🏠 Trang chủ","🛏 Đặt phòng","📖 Booking của tôi","📊 Dashboard","💬 Chatbox Lễ tân"]
)

# ==========================
# HOME
# ==========================
if menu=="🏠 Trang chủ":

    st.image("https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1200")

    st.markdown("## Chào mừng đến HAPPY HOTEL ✨")

    c1,c2,c3,c4=st.columns(4)

    rooms = pd.read_sql("SELECT * FROM rooms", conn)

    standard = len(rooms[rooms["type"] == "Standard"])
    deluxe   = len(rooms[rooms["type"] == "Deluxe"])
    suite    = len(rooms[rooms["type"] == "Suite"])
    vip       = len(rooms[rooms["type"] == "VIP Villa"])

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Tổng phòng", len(rooms))
c2.metric("Standard", standard)
c3.metric("Deluxe", deluxe)
c4.metric("Suite", suite)
c5.metric("VIP Villa", vip)

st.markdown("---")
st.subheader("🌟 Dịch vụ nổi bật")

    a,b,c=st.columns(3)

    a.info("🍽 Buffet sáng miễn phí")
    b.info("🏊 Hồ bơi vô cực")
    c.info("🚗 Đưa đón sân bay")

    st.markdown("---")

    st.subheader("Các hạng phòng")

    col1,col2=st.columns(2)

    with col1:
        st.image("https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800")
        st.write("### Standard")
        st.write("500.000 VNĐ/đêm")

        st.image("https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800")
        st.write("### Suite")
        st.write("1.200.000 VNĐ/đêm")

    with col2:
        st.image("https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800")
        st.write("### Deluxe")
        st.write("800.000 VNĐ/đêm")

        st.image("https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800")
        st.write("### VIP Villa")
        st.write("2.500.000 VNĐ/đêm")

# ==========================
# BOOK ROOM
# ==========================
elif menu=="🛏 Đặt phòng":

    st.header("🛏 Đặt phòng")

    name=st.text_input("Họ tên")
    phone=st.text_input("Số điện thoại")

    c1,c2=st.columns(2)

    with c1:
        checkin=st.date_input("Check-in",date.today())

    with c2:
        checkout=st.date_input("Check-out",date.today())

    room_type=st.selectbox("Loại phòng",["Standard","Deluxe","Suite","VIP Villa"])

    if st.button("🔍 Kiểm tra phòng trống"):

        df=pd.read_sql("SELECT * FROM rooms WHERE type=?",conn,params=(room_type,))

        booked=pd.read_sql("""
        SELECT room FROM bookings
        WHERE status='Booked'
        AND NOT(
        checkout<=?
        OR checkin>=?
        )
        """,conn,params=(str(checkin),str(checkout)))

        available=df[~df.room.isin(booked.room)]

        if len(available)==0:
            st.error("Hết phòng!")
        else:
            st.success("Có phòng trống")
            st.dataframe(available)

            room=st.selectbox("Chọn phòng",available.room)

            nights=(checkout-checkin).days

            if nights<=0:
                st.warning("Ngày không hợp lệ")

            else:
                price=int(available[available.room==room].price.iloc[0])
                subtotal=price*nights
                vat=int(subtotal*0.08)
                total=subtotal+vat

                st.markdown("### 💰 Hoá đơn")

                st.write(f"Số đêm: {nights}")
                st.write(f"Tiền phòng: {subtotal:,} VNĐ")
                st.write(f"VAT 8%: {vat:,}")
                st.success(f"Tổng cộng: {total:,} VNĐ")

                if st.button("✅ Xác nhận đặt phòng"):

                    bid="BK"+uuid.uuid4().hex[:8].upper()

                    cur.execute("""
                    INSERT INTO bookings VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,(bid,name,phone,room,room_type,
                    str(checkin),str(checkout),nights,total,"Booked"))

                    conn.commit()

                    st.balloons()
                    st.success(f"Đặt phòng thành công! Mã: {bid}")

# ==========================
# MY BOOKING
# ==========================
elif menu=="📖 Booking của tôi":

    st.header("📖 Quản lý Booking")

    phone=st.text_input("Nhập số điện thoại")

    if st.button("Tìm booking"):

        df=pd.read_sql("""
        SELECT * FROM bookings
        WHERE phone=?
        """,conn,params=(phone,))

        if len(df)==0:
            st.warning("Không tìm thấy")
        else:

            st.dataframe(df)

            booking=df.id.iloc[0]

            if st.button("❌ Huỷ booking"):

                cur.execute("""
                UPDATE bookings
                SET status='Cancelled'
                WHERE id=?
                """,(booking,))

                conn.commit()

                st.success("Đã huỷ!")

# ==========================
# DASHBOARD
# ==========================
elif menu=="📊 Dashboard":

    st.header("📊 Dashboard")

    book=pd.read_sql("SELECT * FROM bookings",conn)

    total=len(book)
    revenue=book[book.status=="Booked"].total.sum()

    c1,c2,c3=st.columns(3)

    c1.metric("Booking",total)
    c2.metric("Doanh thu",f"{revenue:,}")
    c3.metric("Đã huỷ",len(book[book.status=="Cancelled"]))

    if len(book)>0:

        fig=px.pie(
            book,
            names="room_type",
            title="Tỷ lệ loại phòng"
        )
        st.plotly_chart(fig,use_container_width=True)

        fig2=px.bar(
            book.groupby("room_type")["total"].sum().reset_index(),
            x="room_type",
            y="total",
            title="Doanh thu theo loại phòng"
        )
        st.plotly_chart(fig2,use_container_width=True)

# ==========================
# CHATBOX
# ==========================
elif menu=="💬 Chatbox Lễ tân":

    st.header("💬 HAPPY HOTEL Reception")

    if "messages" not in st.session_state:
        st.session_state.messages=[]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt=st.chat_input("Hỏi lễ tân...")

    if prompt:

        st.session_state.messages.append({
            "role":"user",
            "content":prompt
        })

        text=prompt.lower()

        if "giờ nhận" in text or "check in" in text:
            reply="🕑 Check-in từ 14:00. Check-out trước 12:00."

        elif "buffet" in text:
            reply="🍽 Buffet sáng phục vụ 6:30 - 10:00 miễn phí."

        elif "hồ bơi" in text:
            reply="🏊 Hồ bơi mở cửa từ 6:00 đến 21:00."

        elif "wifi" in text:
            reply="📶 Wifi: HAPPY_HOTEL | Mật khẩu: happy2026"

        elif "giá" in text:
            reply="""💰 Bảng giá:

• Standard: 500.000

• Deluxe: 800.000

• Suite: 1.200.000

• VIP Villa: 2.500.000 VNĐ"""

        else:
            reply="""Xin chào 👋

Tôi là lễ tân AI của HAPPY HOTEL.

Tôi có thể hỗ trợ:

- Giá phòng

- Check-in / Check-out

- Buffet

- Wifi

- Hồ bơi"""

        st.session_state.messages.append({
            "role":"assistant",
            "content":reply
        })

        st.rerun()
