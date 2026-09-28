import streamlit as st
import pandas as pd
from datetime import date
import sqlite3, uuid
import plotly.express as px
import qrcode
from io import BytesIO
st.image("logo1.jpg")
st.set_page_config(page_title="HAPPY HOTEL", page_icon="🏨", layout="wide")
DB="hotel.db"
conn=sqlite3.connect(DB,check_same_thread=False)
cur=conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS rooms(
room TEXT PRIMARY KEY, type TEXT, price INT, status TEXT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS bookings(
id TEXT PRIMARY KEY, guest TEXT, phone TEXT, room TEXT,
checkin TEXT, checkout TEXT, total INT, status TEXT)""")
conn.commit()

if cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]==0:
    cfg=[("Standard",12,500000),("Superior",10,650000),("Deluxe",14,850000),
         ("Deluxe Twin",8,900000),("Suite",10,1400000),("Presidential",6,2500000)]
    n=101
    for t,c,p in cfg:
        for _ in range(c):
            cur.execute("INSERT INTO rooms VALUES(?,?,?,?)",(str(n),t,p,"Available"))
            n+=1
    conn.commit()

st.sidebar.title("🏨 HAPPY HOTEL")
menu=st.sidebar.radio("Menu",["Dashboard","Đặt phòng","Check In","Check Out","Quản lý phòng","Lịch sử","Chatbox"])

rooms=pd.read_sql("SELECT * FROM rooms",conn)
books=pd.read_sql("SELECT * FROM bookings",conn)

if menu=="Dashboard":
    st.title("📊 HAPPY HOTEL Dashboard")
    c1,c2,c3=st.columns(3)
    c1.metric("Tổng phòng",len(rooms))
    c2.metric("Đang sử dụng",(rooms.status=="Occupied").sum())
    c3.metric("Doanh thu",f"{books.total.sum():,} đ")
    fig=px.pie(rooms,names="status",title="Trạng thái phòng")
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(rooms,use_container_width=True)

elif menu=="Đặt phòng":
    st.title("🛎️ Đặt phòng")
    av=rooms[rooms.status=="Available"]
    with st.form("book"):
        guest=st.text_input("Họ tên")
        phone=st.text_input("SĐT")
        room=st.selectbox("Phòng",av.room)
        ci=st.date_input("Nhận phòng",date.today())
        co=st.date_input("Trả phòng",date.today())
        ok=st.form_submit_button("Đặt phòng")
    if ok:
        price=int(rooms.loc[rooms.room==room,"price"].iloc[0])
        nights=max((co-ci).days,1)
        total=price*nights
        bid=str(uuid.uuid4())[:8]
        cur.execute("INSERT INTO bookings VALUES(?,?,?,?,?,?,?,?)",
                    (bid,guest,phone,room,str(ci),str(co),total,"Reserved"))
        cur.execute("UPDATE rooms SET status='Reserved' WHERE room=?",(room,))
        conn.commit()
        st.success(f"Đặt thành công #{bid}")
        qr=qrcode.make(f"HAPPY HOTEL|{bid}|{guest}|{room}|{total}")
        buf=BytesIO(); qr.save(buf)
        st.image(buf.getvalue(),caption="QR xác nhận")

elif menu=="Check In":
    st.title("✅ Check In")
    rs=books[books.status=="Reserved"]
    if len(rs)==0: st.info("Không có đặt phòng.")
    else:
        bid=st.selectbox("Booking",rs.id)
        if st.button("Check In"):
            room=rs.loc[rs.id==bid,"room"].iloc[0]
            cur.execute("UPDATE bookings SET status='Checked In' WHERE id=?",(bid,))
            cur.execute("UPDATE rooms SET status='Occupied' WHERE room=?",(room,))
            conn.commit(); st.success("Check in thành công")

elif menu=="Check Out":
    st.title("🧾 Check Out")
    ck=books[books.status=="Checked In"]
    if len(ck)==0: st.info("Không có khách.")
    else:
        bid=st.selectbox("Khách",ck.id)
        row=ck[ck.id==bid].iloc[0]
        st.write(row)
        if st.button("Thanh toán & Check Out"):
            cur.execute("UPDATE bookings SET status='Completed' WHERE id=?",(bid,))
            cur.execute("UPDATE rooms SET status='Cleaning' WHERE room=?",(row.room,))
            conn.commit(); st.success(f"Thu {row.total:,} đ")

elif menu=="Quản lý phòng":
    st.title("🛏️ Quản lý phòng")
    edit=st.selectbox("Phòng",rooms.room)
    status=st.selectbox("Trạng thái",["Available","Reserved","Occupied","Cleaning"])
    if st.button("Cập nhật"):
        cur.execute("UPDATE rooms SET status=? WHERE room=?",(status,edit)); conn.commit(); st.success("Đã cập nhật")
    st.dataframe(pd.read_sql("SELECT * FROM rooms",conn),use_container_width=True)

elif menu=="Lịch sử":
    st.title("📑 Lịch sử")
    df=pd.read_sql("SELECT * FROM bookings",conn)
    st.dataframe(df,use_container_width=True)
    st.download_button("📥 Xuất CSV",df.to_csv(index=False).encode(),"booking_history.csv","text/csv")

elif menu=="Chatbox":
    st.title("💬 HAPPY AI")
    if "chat" not in st.session_state: st.session_state.chat=[]
    for r,m in st.session_state.chat:
        with st.chat_message(r): st.write(m)
    q=st.chat_input("Hỏi về phòng...")
    if q:
        st.session_state.chat.append(("user",q))
        text=q.lower()
        if "suite" in text: a="Suite phù hợp cho 2–4 khách, giá 1.400.000đ/đêm."
        elif "deluxe" in text: a="Deluxe là lựa chọn phổ biến nhất với giường Queen."
        elif "giá" in text: a="Standard 500k • Superior 650k • Deluxe 850k • Suite 1.4tr."
        else: a="Xin chào! Tôi có thể tư vấn hạng phòng, giá và tình trạng phòng."
        st.session_state.chat.append(("assistant",a))
        st.rerun()
