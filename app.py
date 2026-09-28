import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import qrcode
from io import BytesIO
st.image("logo1.jpg")
# ================= PAGE =====================
st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide"
)

st.markdown("""
<style>
.main{
    background:#f5f7fb;
}
.title{
    font-size:38px;
    font-weight:700;
    color:#0B5ED7;
}
.card{
    background:white;
    padding:18px;
    border-radius:15px;
}
</style>
""",unsafe_allow_html=True)

# ================= DATABASE =================

conn = sqlite3.connect("hotel.db",check_same_thread=False)
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
id INTEGER PRIMARY KEY AUTOINCREMENT,
guest TEXT,
phone TEXT,
room TEXT,
room_type TEXT,
checkin DATE,
checkout DATE,
price INTEGER,
total INTEGER,
status TEXT
)
""")

conn.commit()

# =============== CREATE 60 ROOMS =================

if cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]==0:

    rooms=[]

    # Standard 20
    for i in range(101,121):
        rooms.append((str(i),"Standard",500000,"Available"))

    # Superior 15
    for i in range(201,216):
        rooms.append((str(i),"Superior",700000,"Available"))

    # Deluxe 10
    for i in range(301,311):
        rooms.append((str(i),"Deluxe",950000,"Available"))

    # Suite 10
    for i in range(401,411):
        rooms.append((str(i),"Suite",1500000,"Available"))

    # Presidential 5
    for i in range(501,506):
        rooms.append((str(i),"Presidential",3000000,"Available"))

    cur.executemany("INSERT INTO rooms VALUES(?,?,?,?)",rooms)
    conn.commit()

# ================== SIDEBAR ==================

menu=st.sidebar.radio(
    "📋 MENU",
    ["🏠 Dashboard",
     "🛏️ Đặt phòng",
     "✅ Check In",
     "💳 Check Out",
     "🏨 Quản lý phòng",
     "👥 Khách hàng",
     "📈 Doanh thu",
     "🤖 AI Chatbox"]
)

st.markdown("<div class='title'>🏨 HAPPY HOTEL</div>",unsafe_allow_html=True)

# ================= DASHBOARD ==================

if menu=="🏠 Dashboard":

    rooms=pd.read_sql("SELECT * FROM rooms",conn)
    book=pd.read_sql("SELECT * FROM bookings",conn)

    total=len(rooms)
    available=len(rooms[rooms.status=="Available"])
    occupied=len(rooms[rooms.status=="Occupied"])

    revenue=0
    if len(book)>0:
        revenue=book["total"].sum()

    c1,c2,c3,c4=st.columns(4)

    c1.metric("Tổng phòng",total)
    c2.metric("Phòng trống",available)
    c3.metric("Đang sử dụng",occupied)
    c4.metric("Doanh thu",f"{revenue:,} đ")

    st.divider()

    fig=px.pie(
        rooms,
        names="status",
        title="Tình trạng phòng"
    )
    st.plotly_chart(fig,use_container_width=True)

    st.subheader("Danh sách phòng")

    st.dataframe(rooms,use_container_width=True)

# ================= BOOK =======================

elif menu=="🛏️ Đặt phòng":

    st.subheader("🛏️ ĐẶT PHÒNG")

    name=st.text_input("Tên khách")
    phone=st.text_input("Số điện thoại")

    c1,c2=st.columns(2)

    checkin=c1.date_input("Check In",date.today())
    checkout=c2.date_input("Check Out",date.today())

    roomtype=st.selectbox(
        "Hạng phòng",
        ["Standard","Superior","Deluxe","Suite","Presidential"]
    )

    df=pd.read_sql("SELECT * FROM rooms WHERE type=? AND status='Available'",conn,params=(roomtype,))

    if len(df)==0:
        st.error("Hết phòng.")
    else:

        room=st.selectbox("Chọn phòng",df.room)

        price=int(df[df.room==room]["price"].iloc[0])

        nights=max((checkout-checkin).days,1)
        total=price*nights

        st.info(f"Giá: {price:,} đ / đêm")
        st.success(f"Tổng tiền: {total:,} đ")

        if st.button("Xác nhận đặt phòng"):

            cur.execute("""
            INSERT INTO bookings(
            guest,phone,room,room_type,
            checkin,checkout,price,total,status)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,(
            name,phone,room,roomtype,
            str(checkin),str(checkout),
            price,total,"Booked"
            ))

            conn.commit()

            booking_id=cur.lastrowid

            qr=qrcode.make(f"HAPPY HOTEL BOOKING #{booking_id}")

            buf=BytesIO()
            qr.save(buf)

            st.success(f"Đặt phòng thành công! Mã #{booking_id}")
            st.image(buf)

# ================= CHECKIN ====================

elif menu=="✅ Check In":

    st.subheader("CHECK IN")

    book=pd.read_sql("""
    SELECT * FROM bookings
    WHERE status='Booked'
    """,conn)

    if len(book)==0:
        st.info("Không có đặt phòng.")
    else:

        booking=st.selectbox(
            "Booking",
            book.apply(lambda x:f"#{x.id} - {x.guest} - Room {x.room}",axis=1)
        )

        bid=int(booking.split("-")[0].replace("#",""))

        row=book[book.id==bid].iloc[0]

        st.write(row)

        if st.button("Check In"):

            cur.execute("UPDATE bookings SET status='Checked In' WHERE id=?",(bid,))
            cur.execute("UPDATE rooms SET status='Occupied' WHERE room=?",(row.room,))
            conn.commit()

            st.success("Check In thành công!")

# ================= CHECKOUT ===================

elif menu=="💳 Check Out":

    st.subheader("CHECK OUT")

    book=pd.read_sql("""
    SELECT * FROM bookings
    WHERE status='Checked In'
    """,conn)

    if len(book)==0:
        st.info("Không có khách.")
    else:

        booking=st.selectbox(
            "Khách",
            book.apply(lambda x:f"#{x.id}-{x.guest}-Room{x.room}",axis=1)
        )

        bid=int(booking.split("-")[0].replace("#",""))

        row=book[book.id==bid].iloc[0]

        st.write(f"Khách: {row.guest}")
        st.write(f"Phòng: {row.room}")
        st.write(f"Tổng thanh toán: {row.total:,} đ")

        if st.button("Thanh toán & Check Out"):

            cur.execute("UPDATE bookings SET status='Completed' WHERE id=?",(bid,))
            cur.execute("UPDATE rooms SET status='Available' WHERE room=?",(row.room,))
            conn.commit()

            st.success("Hoàn tất Check Out!")

# ================= ROOMS ======================

elif menu=="🏨 Quản lý phòng":

    st.subheader("QUẢN LÝ PHÒNG")

    rooms=pd.read_sql("SELECT * FROM rooms",conn)

    st.dataframe(rooms,use_container_width=True)

# ================= CUSTOMERS ==================

elif menu=="👥 Khách hàng":

    st.subheader("DANH SÁCH KHÁCH")

    df=pd.read_sql("SELECT * FROM bookings",conn)

    st.dataframe(df,use_container_width=True)

# ================= REVENUE ====================

elif menu=="📈 Doanh thu":

    st.subheader("THỐNG KÊ DOANH THU")

    df=pd.read_sql("""
    SELECT checkout,total
    FROM bookings
    WHERE status='Completed'
    """,conn)

    if len(df)==0:
        st.info("Chưa có dữ liệu.")
    else:

        revenue=df.groupby("checkout")["total"].sum().reset_index()

        fig=px.bar(
            revenue,
            x="checkout",
            y="total",
            text_auto=True,
            title="Doanh thu theo ngày"
        )

        st.plotly_chart(fig,use_container_width=True)

        st.dataframe(revenue,use_container_width=True)

# ================= AI CHAT ====================

elif menu=="🤖 AI Chatbox":

    st.subheader("🤖 HAPPY HOTEL AI ASSISTANT")

    if "messages" not in st.session_state:
        st.session_state.messages=[]

    for m in st.session_state.messages:

        with st.chat_message(m["role"]):
            st.write(m["content"])

    prompt=st.chat_input("Hỏi về khách sạn...")

    if prompt:

        st.session_state.messages.append(
            {"role":"user","content":prompt}
        )

        with st.chat_message("user"):
            st.write(prompt)

        text=prompt.lower()

        if "giờ nhận phòng" in text:
            ans="Giờ Check-in là 14:00."

        elif "trả phòng" in text:
            ans="Giờ Check-out trước 12:00."

        elif "suite" in text:
            ans="Suite có giá 1.500.000 VNĐ/đêm."

        elif "deluxe" in text:
            ans="Deluxe có giá 950.000 VNĐ/đêm."

        elif "presidential" in text:
            ans="Presidential có giá 3.000.000 VNĐ/đêm."

        else:
            ans="""Xin chào 👋

Tôi là trợ lý HAPPY HOTEL.

Tôi có thể hỗ trợ:

• Báo giá phòng
• Giờ Check-in / Check-out
• Giải thích hạng phòng
• Hướng dẫn đặt phòng
• Chính sách khách sạn
"""

        with st.chat_message("assistant"):
            st.write(ans)

        st.session_state.messages.append(
            {"role":"assistant","content":ans}
        )
