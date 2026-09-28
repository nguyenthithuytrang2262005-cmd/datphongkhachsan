import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import qrcode
from io import BytesIO
st.image("logo1.jpg")
st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide"
)

# ================= DATABASE ===================

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
id INTEGER PRIMARY KEY AUTOINCREMENT,
guest TEXT,
phone TEXT,
idcard TEXT,
room TEXT,
checkin TEXT,
checkout TEXT,
guests INTEGER,
status TEXT,
total INTEGER
)
""")

conn.commit()

# insert default rooms
if cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
    rooms = [
        ("101","Standard",500000,"Available"),
        ("102","Standard",500000,"Available"),
        ("201","Deluxe",700000,"Available"),
        ("202","Deluxe",700000,"Available"),
        ("301","Suite",1200000,"Available"),
        ("302","VIP",1800000,"Maintenance")
    ]
    cur.executemany("INSERT INTO rooms VALUES(?,?,?,?)", rooms)
    conn.commit()

# ================= FUNCTIONS ==================

def load_rooms():
    return pd.read_sql("SELECT * FROM rooms", conn)

def load_bookings():
    return pd.read_sql("SELECT * FROM bookings", conn)

def update_room(room,status):
    cur.execute("UPDATE rooms SET status=? WHERE room=?",(status,room))
    conn.commit()

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

if menu=="📊 Dashboard":

    total_rooms=len(rooms)
    available=len(rooms[rooms.status=="Available"])
    occupied=len(rooms[rooms.status=="Occupied"])

    revenue=bookings[bookings.status=="Completed"]["total"].sum() if len(bookings)>0 else 0

    c1,c2,c3,c4=st.columns(4)

    c1.metric("Total Rooms",total_rooms)
    c2.metric("Available",available)
    c3.metric("Occupied",occupied)
    occ = round((occupied/total_rooms)*100,1)
    c4.metric("Occupancy",f"{occ}%")

    st.subheader("🏨 Room Categories")

room_types = (
    rooms.groupby("type", as_index=False)
         .agg(
             price=("price", "first"),
             quantity=("room", "count")
         )
)

cols = st.columns(len(room_types))

for i, row in room_types.iterrows():
    with cols[i]:
        st.markdown(f"""
        <div style="padding:18px;border-radius:12px;background:#F5F5F5;
                    text-align:center;">
            <h4>{row['type']}</h4>
            <h3 style="color:#0EA5E9;">{row['price']:,} VND</h3>
            <p>🛏 {row['quantity']} phòng</p>
        </div>
        """, unsafe_allow_html=True)
        with cols[i%3]:
            st.markdown(
                f"""
                <div style='padding:15px;border-radius:12px;
                background:#f5f5f5;margin-bottom:10px'>
                <h3>{row.room}</h3>
                <b>{row.type}</b><br>
                💵 {row.price:,} VND<br>
                <font color='{color_map[row.status]}'>● {row.status}</font>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    st.subheader("Revenue Summary")
    st.metric("Total Revenue",f"{revenue:,} VND")

# =============== ROOM =========================

elif menu=="🛏 Room Categories":

    st.subheader("Room Categories")

    st.dataframe(rooms,use_container_width=True)

    with st.expander("➕ Add Room"):

        r=st.text_input("Room Number")
        t=st.selectbox("Type",["Standard","Deluxe","Suite","VIP"])
        p=st.number_input("Price",100000,5000000,500000)

        if st.button("Add Room"):
            cur.execute("INSERT INTO rooms VALUES(?,?,?,?)",(r,t,p,"Available"))
            conn.commit()
            st.success("Added")
            st.rerun()

    st.divider()

    room_select=st.selectbox("Select Room",rooms.room)

    new_status=st.selectbox("Change Status",
        ["Available","Occupied","Reserved","Cleaning","Maintenance"])

    if st.button("Update Status"):
        update_room(room_select,new_status)
        st.success("Updated")
        st.rerun()

# ============== RESERVATION ===================

elif menu=="📅 Reservation":

    st.subheader("New Reservation")

    available_rooms=rooms[rooms.status=="Available"]

    if len(available_rooms)==0:
        st.error("No available room")
        st.stop()

    name=st.text_input("Guest Name")
    phone=st.text_input("Phone")
    idcard=st.text_input("ID Card")

    guests=st.slider("Guests",1,6,2)

    room=st.selectbox("Choose Room",available_rooms.room)

    c1,c2=st.columns(2)
    checkin=c1.date_input("Check In",date.today())
    checkout=c2.date_input("Check Out",date.today())

    price=int(rooms[rooms.room==room].price.values[0])

    nights=max((checkout-checkin).days,1)
    total=price*nights

    st.info(f"{nights} night(s) | Total = {total:,} VND")

    # AI Recommendation
    st.markdown("### 🤖 Smart Recommendation")

    if guests<=2:
        st.success("Recommended: Standard / Deluxe")
    elif guests<=4:
        st.success("Recommended: Deluxe / Suite")
    else:
        st.success("Recommended: VIP")

    if st.button("Reserve"):

        cur.execute("""
        INSERT INTO bookings
        (guest,phone,idcard,room,checkin,checkout,guests,status,total)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (name,phone,idcard,room,
        str(checkin),str(checkout),guests,"Reserved",total))

        update_room(room,"Reserved")

        conn.commit()

        st.success("Reservation Successful!")

        # QR
        qr=qrcode.make(f"{name}-{room}-{checkin}")
        buf=BytesIO()
        qr.save(buf)
        st.image(buf)

# ============== CHECKIN =======================

elif menu=="🟢 Check In":

    reserved=bookings[bookings.status=="Reserved"]

    st.subheader("Check In")

    if len(reserved)==0:
        st.info("No reservation")
    else:

        book_id=st.selectbox(
            "Booking ID",
            reserved.id
        )

        row=reserved[reserved.id==book_id].iloc[0]

        st.write(f"**Guest:** {row.guest}")
        st.write(f"Room: {row.room}")

        if st.button("Check In"):

            cur.execute("""
            UPDATE bookings
            SET status='Checked In'
            WHERE id=?
            """,(int(book_id),))

            update_room(row.room,"Occupied")
            conn.commit()

            st.success("Checked In")
            st.rerun()

# ============== CHECKOUT ======================

elif menu=="🔴 Check Out":

    staying=bookings[bookings.status=="Checked In"]

    st.subheader("Check Out")

    if len(staying)==0:
        st.info("No guest staying")

    else:

        bid=st.selectbox("Booking",staying.id)

        row=staying[staying.id==bid].iloc[0]

        st.write(f"Guest: {row.guest}")
        st.write(f"Room: {row.room}")

        st.metric("Total Payment",f"{row.total:,} VND")

        minibar=st.number_input("MiniBar",0,5000000,0)
        laundry=st.number_input("Laundry",0,5000000,0)

        final=row.total+minibar+laundry

        st.metric("Grand Total",f"{final:,} VND")

        if st.button("Complete Check Out"):

            cur.execute("""
            UPDATE bookings
            SET status='Completed',
            total=?
            WHERE id=?
            """,(int(final),int(bid)))

            update_room(row.room,"Cleaning")

            conn.commit()

            st.success("Check Out Completed")
            st.rerun()

# ============== GUEST =========================

elif menu=="👥 Guests":

    st.subheader("Guest List")

    keyword=st.text_input("Search")

    df=bookings.copy()

    if keyword!="":
        df=df[df.guest.str.contains(keyword,case=False)]

    st.dataframe(df,use_container_width=True)

    csv=df.to_csv(index=False).encode()

    st.download_button(
        "⬇ Export CSV",
        csv,
        "guests.csv",
        "text/csv"
    )

# ============== REVENUE =======================

elif menu=="📈 Revenue":

    st.subheader("Revenue Analytics")

    df=bookings[bookings.status=="Completed"]

    if len(df)==0:
        st.info("No revenue yet")
    else:

        df["checkin"]=pd.to_datetime(df["checkin"])

        daily=df.groupby(df["checkin"].dt.date)["total"].sum().reset_index()

        fig=px.line(
            daily,
            x="checkin",
            y="total",
            markers=True,
            title="Daily Revenue"
        )

        st.plotly_chart(fig,use_container_width=True)

        st.dataframe(df,use_container_width=True)
        
        # ============== AI CHATBOX =======================

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
            price_list = rooms.groupby("type")["price"].first()
            reply = "### 💵 Bảng giá phòng\n"
            for t, p in price_list.items():
                reply += f"- **{t}**: {p:,} VND/đêm\n"

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
            rev = bookings[bookings.status=="Completed"]["total"].sum()
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
