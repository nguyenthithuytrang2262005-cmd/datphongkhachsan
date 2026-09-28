import streamlit as st
import sqlite3, pandas as pd
from datetime import date
import plotly.express as px
import qrcode
from io import BytesIO

st.set_page_config(page_title="HAPPY HOTEL", page_icon="🏨", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect("hotel.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS rooms(
room TEXT PRIMARY KEY,
type TEXT,
price INTEGER,
status TEXT)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS bookings(
id INTEGER PRIMARY KEY AUTOINCREMENT,
guest TEXT, phone TEXT,idcard TEXT,
room TEXT,
checkin TEXT,
checkout TEXT,
guests INTEGER,
status TEXT,
total INTEGER)
""")
conn.commit()

# ---------- CREATE 60 ROOMS ----------
if cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
    rooms=[]
    # Standard 101-120
    for i in range(101,121):
        rooms.append((str(i),"Standard",500000,"Available"))
    # Deluxe 201-220
    for i in range(201,221):
        rooms.append((str(i),"Deluxe",700000,"Available"))
    # Suite 301-310
    for i in range(301,311):
        rooms.append((str(i),"Suite",1200000,"Available"))
    # VIP 401-410
    for i in range(401,411):
        rooms.append((str(i),"VIP",1800000,"Available"))

    cur.executemany("INSERT INTO rooms VALUES(?,?,?,?)",rooms)
    conn.commit()

def load_rooms():
    return pd.read_sql("SELECT * FROM rooms",conn)

def load_booking():
    return pd.read_sql("SELECT * FROM bookings",conn)

rooms=load_rooms()
booking=load_booking()

# ================= HEADER =================
st.markdown(
"""
# 🏨 HAPPY HOTEL
### Luxury Hotel Management System
"""
)

menu=st.sidebar.radio("MENU",[
"📊 Dashboard",
"🛏 Rooms",
"📅 Reservation",
"🟢 Check In",
"🔴 Check Out",
"🧹 Housekeeping",
"👥 Guests",
"📈 Revenue"
])

# ================= DASHBOARD =================
if menu=="📊 Dashboard":

    total=len(rooms)
    available=len(rooms[rooms.status=="Available"])
    occupied=len(rooms[rooms.status=="Occupied"])
    cleaning=len(rooms[rooms.status=="Cleaning"])
    occ=round(occupied/total*100,1)

    revenue=booking[booking.status=="Completed"]["total"].sum() if len(booking)>0 else 0

    a,b,c,d=st.columns(4)
    a.metric("Total Rooms",total)
    b.metric("Available",available)
    c.metric("Occupied",occupied)
    d.metric("Occupancy",f"{occ}%")

    e,f=st.columns(2)
    e.metric("Cleaning",cleaning)
    f.metric("Revenue",f"{revenue:,} VND")

    st.divider()

    st.subheader("Room Status")

    colors={
    "Available":"#2ecc71",
    "Occupied":"#e74c3c",
    "Reserved":"#3498db",
    "Cleaning":"#9b59b6",
    "Maintenance":"#f39c12"
    }

    cols=st.columns(5)

    for i,r in rooms.iterrows():
        with cols[i%5]:
            st.markdown(f"""
            <div style='padding:12px;border-radius:12px;
            border:1px solid #ddd;margin-bottom:10px'>
            <h4>{r.room}</h4>
            {r.type}<br>
            <b>{r.price:,}</b><br>
            <span style='color:{colors[r.status]}'>● {r.status}</span>
            </div>
            """,unsafe_allow_html=True)

# ================= ROOM =================
elif menu=="🛏 Rooms":

    st.subheader("60 Room Management")
    st.dataframe(rooms,use_container_width=True)

    st.divider()
    st.subheader("Update Status")

    room=st.selectbox("Room",rooms.room)
    status=st.selectbox("Status",
    ["Available","Reserved","Occupied","Cleaning","Maintenance"])

    if st.button("Update"):
        cur.execute("UPDATE rooms SET status=? WHERE room=?",(status,room))
        conn.commit()
        st.success("Updated")
        st.rerun()

# ================= RESERVATION =================
elif menu=="📅 Reservation":

    st.subheader("New Reservation")

    free=rooms[rooms.status=="Available"]

    name=st.text_input("Guest Name")
    phone=st.text_input("Phone")
    idcard=st.text_input("ID Card")

    guests=st.slider("Guests",1,6,2)

    room=st.selectbox("Available Room",free.room)

    c1,c2=st.columns(2)
    checkin=c1.date_input("Check In",date.today())
    checkout=c2.date_input("Check Out",date.today())

    price=int(rooms[rooms.room==room].price.values[0])

    nights=max((checkout-checkin).days,1)
    total=price*nights

    st.info(f"{nights} night(s) • {total:,} VND")

    st.markdown("### 🤖 AI Recommendation")

    if guests<=2:
        st.success("Recommended: Standard / Deluxe")
    elif guests<=4:
        st.success("Recommended: Deluxe / Suite")
    else:
        st.success("Recommended: VIP")

    if st.button("Reserve Room"):

        cur.execute("""
        INSERT INTO bookings
        (guest,phone,idcard,room,checkin,checkout,guests,status,total)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,(name,phone,idcard,room,
        str(checkin),str(checkout),guests,"Reserved",total))

        cur.execute("UPDATE rooms SET status='Reserved' WHERE room=?",(room,))
        conn.commit()

        st.success("Reservation Successful")

        qr=qrcode.make(f"{name}-{room}-{checkin}")
        buf=BytesIO()
        qr.save(buf)
        st.image(buf,caption="Booking QR")

# ================= CHECK IN =================
elif menu=="🟢 Check In":

    reserve=booking[booking.status=="Reserved"]

    st.subheader("Guest Check In")

    if len(reserve)==0:
        st.info("No reservation")

    else:
        bid=st.selectbox("Booking ID",reserve.id)

        r=reserve[reserve.id==bid].iloc[0]

        st.write("**Guest:**",r.guest)
        st.write("Room:",r.room)

        if st.button("Check In"):

            cur.execute("UPDATE bookings SET status='Checked In' WHERE id=?",(int(bid),))
            cur.execute("UPDATE rooms SET status='Occupied' WHERE room=?",(r.room,))
            conn.commit()

            st.success("Checked In")
            st.rerun()

# ================= CHECK OUT =================
elif menu=="🔴 Check Out":

    stay=booking[booking.status=="Checked In"]

    st.subheader("Check Out")

    if len(stay)==0:
        st.info("No guest")

    else:

        bid=st.selectbox("Booking",stay.id)
        r=stay[stay.id==bid].iloc[0]

        st.write("Guest:",r.guest)
        st.write("Room:",r.room)

        minibar=st.number_input("MiniBar",0,5000000,0)
        laundry=st.number_input("Laundry",0,5000000,0)

        final=int(r.total)+minibar+laundry

        st.metric("Grand Total",f"{final:,} VND")

        if st.button("Complete"):

            cur.execute("UPDATE bookings SET total=?,status='Completed' WHERE id=?",(final,int(bid)))
            cur.execute("UPDATE rooms SET status='Cleaning' WHERE room=?",(r.room,))
            conn.commit()

            st.success("Check Out Completed")
            st.rerun()

# ================= HOUSEKEEPING =================
elif menu=="🧹 Housekeeping":

    clean=rooms[rooms.status=="Cleaning"]

    st.subheader("Cleaning Room")

    if len(clean)==0:
        st.info("No cleaning room")

    else:

        room=st.selectbox("Room Cleaning",clean.room)

        if st.button("Finish Cleaning"):

            cur.execute("UPDATE rooms SET status='Available' WHERE room=?",(room,))
            conn.commit()

            st.success("Room Ready")
            st.rerun()

# ================= GUEST =================
elif menu=="👥 Guests":

    st.subheader("Guest List")

    search=st.text_input("Search Guest")

    df=booking.copy()

    if search!="":
        df=df[df.guest.str.contains(search,case=False)]

    st.dataframe(df,use_container_width=True)

    csv=df.to_csv(index=False).encode()
    st.download_button("⬇ Export CSV",csv,"guests.csv","text/csv")

# ================= REVENUE =================
elif menu=="📈 Revenue":

    st.subheader("Revenue Analytics")

    df=booking[booking.status=="Completed"]

    if len(df)==0:
        st.info("No revenue")
    else:

        df["checkin"]=pd.to_datetime(df["checkin"])
        daily=df.groupby(df["checkin"].dt.date)["total"].sum().reset_index()

        fig=px.bar(daily,x="checkin",y="total",text_auto=True,
        title="Daily Revenue")

        st.plotly_chart(fig,use_container_width=True)

        st.dataframe(df,use_container_width=True)
