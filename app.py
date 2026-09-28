import streamlit as st
import sqlite3, pandas as pd, plotly.express as px, qrcode
from datetime import date, datetime
from io import BytesIO

st.set_page_config(page_title="HAPPY HOTEL", page_icon="🏨", layout="wide")

conn=sqlite3.connect("hotel.db",check_same_thread=False); c=conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS rooms(no TEXT PRIMARY KEY, type TEXT, price INT, status TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,phone TEXT,room TEXT,cin TEXT,cout TEXT,nights INT,total INT,status TEXT)")
conn.commit()
if c.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]==0:
    cfg=[("Standard",10,500000),("Superior",10,650000),("Deluxe",12,850000),("Executive",10,1100000),("Suite",10,1500000),("Presidential",8,2500000)]
    n=101
    for t,qty,p in cfg:
        for _ in range(qty):
            c.execute("INSERT INTO rooms VALUES(?,?,?,?)",(str(n),t,p,"Available")); n+=1
    conn.commit()

menu=st.sidebar.radio("MENU",["🏠 Dashboard","🛏️ Đặt phòng","✅ Check-In","🚪 Check-Out","💳 Thanh toán","🏨 Quản lý phòng","📊 Thống kê","🤖 Happy AI Chat"])
st.title("🏨 HAPPY HOTEL")

rooms=pd.read_sql("SELECT * FROM rooms",conn)
books=pd.read_sql("SELECT * FROM bookings",conn)

if menu=="🏠 Dashboard":
    a=(rooms.status=="Available").sum(); o=(rooms.status=="Occupied").sum()
    rev=books.total.sum() if len(books) else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Tổng phòng",len(rooms)); c2.metric("Đang trống",a); c3.metric("Đã thuê",o); c4.metric("Doanh thu",f"{rev:,} đ")
    st.dataframe(rooms,use_container_width=True)

elif menu=="🛏️ Đặt phòng":
    n=st.text_input("Họ tên"); p=st.text_input("SĐT")
    typ=st.selectbox("Hạng",sorted(rooms.type.unique()))
    ci=st.date_input("Check in",date.today()); co=st.date_input("Check out",date.today())
    av=rooms[(rooms.type==typ)&(rooms.status=="Available")]
    if len(av): rm=st.selectbox("Phòng",av.no)
    else: st.warning("Hết phòng"); rm=None
    if rm:
        price=int(av[av.no==rm].price.iloc[0]); nights=max((co-ci).days,1); total=price*nights
        st.info(f"{nights} đêm | {price:,} đ | Tổng {total:,} đ")
        if st.button("Xác nhận đặt phòng"):
            c.execute("INSERT INTO bookings(name,phone,room,cin,cout,nights,total,status) VALUES(?,?,?,?,?,?,?,?)",(n,p,rm,str(ci),str(co),nights,total,"Booked"))
            c.execute("UPDATE rooms SET status='Booked' WHERE no=?",(rm,)); conn.commit(); st.success("Đặt thành công")
            qr=qrcode.make(f"{n}|{rm}|{ci}|{co}")
            buf=BytesIO(); qr.save(buf); st.image(buf.getvalue(),caption="QR xác nhận",width=180)

elif menu=="✅ Check-In":
    b=pd.read_sql("SELECT * FROM bookings WHERE status='Booked'",conn)
    if len(b)==0: st.info("Không có đặt phòng")
    else:
        bid=st.selectbox("Booking",b.id)
        row=b[b.id==bid].iloc[0]
        st.write(row[["name","room","cin","cout"]])
        if st.button("Check In"):
            c.execute("UPDATE bookings SET status='Checked-In' WHERE id=?",(int(bid),))
            c.execute("UPDATE rooms SET status='Occupied' WHERE no=?",(row.room,)); conn.commit(); st.success("Check-in!")

elif menu=="🚪 Check-Out":
    b=pd.read_sql("SELECT * FROM bookings WHERE status='Checked-In'",conn)
    if len(b)==0: st.info("Không có khách")
    else:
        bid=st.selectbox("Khách",b.id); row=b[b.id==bid].iloc[0]
        st.write(f"Khách: {row['name']}"); st.write(f"Tổng: {row['total']:,} đ")
        if st.button("Check Out"):
            c.execute("UPDATE bookings SET status='Completed' WHERE id=?",(int(bid),))
            c.execute("UPDATE rooms SET status='Available' WHERE no=?",(row.room,)); conn.commit(); st.success("Hoàn tất!")

elif menu=="💳 Thanh toán":
    b=pd.read_sql("SELECT * FROM bookings WHERE status='Completed'",conn)
    if len(b)==0: st.info("Chưa có hóa đơn")
    else:
        bid=st.selectbox("Hóa đơn",b.id); row=b[b.id==bid].iloc[0]
        vat=int(row.total*0.08); grand=row.total+vat
        st.subheader("HÓA ĐƠN"); st.write(row[["name","room","nights"]]); st.write(f"Tiền phòng: {row['total']:,} đ"); st.write(f"VAT 8%: {vat:,} đ"); st.success(f"Thanh toán: {grand:,} đ")

elif menu=="🏨 Quản lý phòng":
    ed=st.data_editor(rooms,disabled=["no"],use_container_width=True)
    if st.button("Lưu thay đổi"):
        for _,r in ed.iterrows():
            c.execute("UPDATE rooms SET type=?,price=?,status=? WHERE no=?",(r.type,int(r.price),r.status,r.no))
        conn.commit(); st.success("Đã lưu")

elif menu=="📊 Thống kê":
    if len(books):
        fig=px.bar(books.groupby("room",as_index=False)["total"].sum(),x="room",y="total",title="Doanh thu theo phòng"); st.plotly_chart(fig,use_container_width=True)
        pie=px.pie(rooms,names="status",title="Tình trạng phòng"); st.plotly_chart(pie,use_container_width=True)
    else: st.info("Chưa có dữ liệu")

elif menu=="🤖 Happy AI Chat":
    st.subheader("Happy AI")
    if "chat" not in st.session_state: st.session_state.chat=[]
    for m in st.session_state.chat:
        with st.chat_message(m["r"]): st.markdown(m["t"])
    q=st.chat_input("Hỏi về đặt phòng, giá...")
    if q:
        st.session_state.chat.append({"r":"user","t":q})
        ans="Xin chào! "
        s=q.lower()
        if "giá" in s: ans+="Giá từ 500.000đ đến 2.500.000đ/đêm."
        elif "check" in s: ans+="Check-in 14:00, Check-out 12:00."
        elif "deluxe" in s: ans+="Deluxe có 12 phòng, 850.000đ/đêm."
        else: ans+="Tôi hỗ trợ đặt phòng, giá, tiện ích và thủ tục khách sạn."
        st.session_state.chat.append({"r":"assistant","t":ans})
        st.rerun()
