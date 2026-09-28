import streamlit as st
import sqlite3, pandas as pd, plotly.express as px, qrcode
from io import BytesIO
from datetime import date, datetime
st.image("logo1.jpg")
st.set_page_config(page_title="HAPPY HOTEL", page_icon="🏨", layout="wide")

conn=sqlite3.connect("hotel.db",check_same_thread=False)
c=conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS rooms(no TEXT PRIMARY KEY,type TEXT,price INT,status TEXT)")
c.execute("""CREATE TABLE IF NOT EXISTS bookings(
id INTEGER PRIMARY KEY AUTOINCREMENT,guest TEXT,phone TEXT,room TEXT,
checkin TEXT,checkout TEXT,total INT,status TEXT,payment TEXT)""")
if c.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]==0:
    types=[("Standard",12,500000),("Superior",12,700000),("Deluxe",12,950000),("Suite",12,1500000),("Family",6,1800000),("Presidential",6,3000000)]
    n=101
    for t,count,p in types:
        for _ in range(count):
            c.execute("INSERT INTO rooms VALUES(?,?,?,?)",(str(n),t,p,"Available")); n+=1
    conn.commit()

menu=st.sidebar.radio("HAPPY HOTEL",["🏠 Trang chủ","🛏 Đặt phòng","📋 Quản lý phòng","✅ Check-in","🚪 Check-out","💳 Thanh toán","📊 Dashboard","🤖 ChatBox"])

def load_rooms():
    return pd.read_sql("SELECT * FROM rooms",conn)
def load_bookings():
    return pd.read_sql("SELECT * FROM bookings",conn)

if menu=="🏠 Trang chủ":
    st.title("🏨 HAPPY HOTEL")
    df=load_rooms(); bk=load_bookings()
    a=(df.status=="Available").sum(); o=(df.status=="Occupied").sum()
    c1,c2,c3=st.columns(3)
    c1.metric("Tổng phòng",len(df)); c2.metric("Đang trống",a); c3.metric("Đang ở",o)
    st.dataframe(df,use_container_width=True)

elif menu=="🛏 Đặt phòng":
    st.title("Đặt phòng")
    rooms=load_rooms(); avail=rooms[rooms.status=="Available"]
    with st.form("book"):
        name=st.text_input("Họ tên"); phone=st.text_input("SĐT")
        room=st.selectbox("Phòng",avail.no).tolist
        ci=st.date_input("Nhận",date.today()); co=st.date_input("Trả",date.today())
        pay=st.selectbox("Thanh toán",["Cash","Visa","Momo"])
        ok=st.form_submit_button("Xác nhận")
    if ok:
        p=int(rooms[rooms.no==room].price.iloc[0]); nights=max((co-ci).days,1); total=p*nights
        c.execute("INSERT INTO bookings(guest,phone,room,checkin,checkout,total,status,payment) VALUES(?,?,?,?,?,?,?,?)",(name,phone,room,str(ci),str(co),total,"Booked",pay)); conn.commit()
        st.success(f"Đặt thành công. Tổng {total:,} VNĐ")

elif menu=="📋 Quản lý phòng":
    st.title("Quản lý phòng")
    st.dataframe(load_rooms(),use_container_width=True)

elif menu=="✅ Check-in":
    st.title("Check-in")
    bk=load_bookings(); wait=bk[bk.status=="Booked"]
    if len(wait)==0: st.info("Không có")
    else:
        rid=st.selectbox("Booking",wait.id)
        if st.button("Check-in"):
            room=wait[wait.id==rid].room.iloc[0]
            c.execute("UPDATE bookings SET status='Checked-in' WHERE id=?",(int(rid),))
            c.execute("UPDATE rooms SET status='Occupied' WHERE no=?",(room,))
            conn.commit(); st.success("Thành công")

elif menu=="🚪 Check-out":
    st.title("Check-out")
    bk=load_bookings(); stay=bk[bk.status=="Checked-in"]
    if len(stay)==0: st.info("Không có")
    else:
        rid=st.selectbox("Khách",stay.id)
        if st.button("Check-out"):
            room=stay[stay.id==rid].room.iloc[0]
            c.execute("UPDATE bookings SET status='Completed' WHERE id=?",(int(rid),))
            c.execute("UPDATE rooms SET status='Available' WHERE no=?",(room,))
            conn.commit(); st.success("Hoàn tất")

elif menu=="💳 Thanh toán":
    st.title("Thanh toán & QR")
    bk=load_bookings()
    if len(bk):
        rid=st.selectbox("Hóa đơn",bk.id)
        row=bk[bk.id==rid].iloc[0]
        st.write(row)
        qr=qrcode.make(f"Invoice:{row.id}|{row.guest}|{row.total}")
        buf=BytesIO(); qr.save(buf)
        st.image(buf.getvalue(),caption="QR Invoice")

elif menu=="📊 Dashboard":
    st.title("Dashboard")
    rooms=load_rooms(); bk=load_bookings()
    st.metric("Doanh thu",f"{bk.total.sum():,} VNĐ")
    occ=(rooms.status=="Occupied").sum()/len(rooms)*100
    st.metric("Công suất",f"{occ:.1f}%")
    if len(bk):
        fig=px.bar(bk.groupby("room",as_index=False)["total"].sum(),x="room",y="total",title="Doanh thu theo phòng")
        st.plotly_chart(fig,use_container_width=True)

else:
    st.title("🤖 ChatBox")
    if "chat" not in st.session_state: st.session_state.chat=[]
    for r,m in st.session_state.chat:
        with st.chat_message(r): st.markdown(m)
    p=st.chat_input("Hỏi về đặt phòng...")
    if p:
        st.session_state.chat.append(("user",p))
        ans="Xin chào! Tôi là trợ lý HAPPY HOTEL. Tôi có thể hỗ trợ đặt phòng, giá phòng, check-in và thanh toán."
        if "giá" in p.lower(): ans="Giá từ 500.000đ (Standard) đến 3.000.000đ (Presidential)."
        if "check" in p.lower(): ans="Check-in: 14:00 | Check-out: 12:00."
        st.session_state.chat.append(("assistant",ans)); st.rerun()
