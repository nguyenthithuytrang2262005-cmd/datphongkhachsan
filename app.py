import streamlit as st
import sqlite3, pandas as pd
from datetime import date
import plotly.express as px

st.set_page_config(page_title="HAPPY HOTEL",page_icon="🏨",layout="wide")
conn=sqlite3.connect("hotel.db",check_same_thread=False);cur=conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS rooms(no TEXT PRIMARY KEY,typ TEXT,price INT,status TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,phone TEXT,room TEXT,ci TEXT,co TEXT,total INT,status TEXT)")
if cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]==0:
 data=[];spec=[("Standard",12,600000),("Superior",12,850000),("Deluxe",12,1200000),("Executive",8,1600000),("Family",8,2000000),("Suite",8,2800000)]
 n=101
 for t,c,p in spec:
  for i in range(c):
   data.append((str(n),t,p,"Available"));n+=1
 cur.executemany("INSERT INTO rooms VALUES(?,?,?,?)",data);conn.commit()
st.sidebar.title("🏨 HAPPY HOTEL")
page=st.sidebar.radio("Menu",["Dashboard","Đặt phòng","Lễ tân","Quản lý","💬 ChatBox"])
rooms=pd.read_sql("SELECT * FROM rooms",conn);books=pd.read_sql("SELECT * FROM bookings",conn)
if page=="Dashboard":
 st.title("HAPPY HOTEL Dashboard")
 c1,c2,c3,c4=st.columns(4)
 c1.metric("Tổng phòng",60)
 c2.metric("Trống",(rooms.status=="Available").sum())
 c3.metric("Đã đặt",(rooms.status=="Booked").sum())
 c4.metric("Đang ở",(rooms.status=="Occupied").sum())
 occ=((rooms.status!="Available").sum()/60)*100
 st.metric("Occupancy",f"{occ:.1f}%")
 if len(books):
  df=books.groupby("status").size().reset_index(name="count")
  st.plotly_chart(px.pie(df,names="status",values="count"),use_container_width=True)
 st.subheader("Sơ đồ phòng")
 colors={"Available":"🟩","Booked":"🟨","Occupied":"🟥"}
 cols=st.columns(6)
 for i,r in rooms.iterrows():
  cols[i%6].markdown(f"**{colors[r.status]} {r.no}**\n\n{r.typ}")
elif page=="Đặt phòng":
 st.title("Đặt phòng")
 name=st.text_input("Họ tên");phone=st.text_input("SĐT")
 ci=st.date_input("Check-in",date.today());co=st.date_input("Check-out",date.today())
 typ=st.selectbox("Hạng",rooms.typ.unique())
 av=rooms[(rooms.typ==typ)&(rooms.status=="Available")]
 if len(av):
  room=st.selectbox("Phòng",av.no)
  price=int(av[av.no==room].price.iloc[0]);days=max((co-ci).days,1);total=days*price
  st.info(f"{days} đêm | {price:,}đ | Tổng {total:,}đ")
  if st.button("Xác nhận đặt"):
   cur.execute("INSERT INTO bookings(name,phone,room,ci,co,total,status) VALUES(?,?,?,?,?,?,?)",(name,phone,room,str(ci),str(co),total,"Booked"))
   cur.execute("UPDATE rooms SET status='Booked' WHERE no=?",(room,));conn.commit();st.success("Đặt thành công")
 else: st.warning("Hết phòng")
elif page=="Lễ tân":
 st.title("Check-in / Check-out")
 b=pd.read_sql("SELECT * FROM bookings",conn)
 st.subheader("Check-in")
 bk=b[b.status=="Booked"]
 if len(bk):
  bid=st.selectbox("Booking",bk.id)
  if st.button("Check-in"):
   rm=bk[bk.id==bid].room.iloc[0]
   cur.execute("UPDATE bookings SET status='Checked-in' WHERE id=?",(int(bid),))
   cur.execute("UPDATE rooms SET status='Occupied' WHERE no=?",(rm,));conn.commit();st.success("OK")
 st.subheader("Check-out")
 ck=b[b.status=="Checked-in"]
 if len(ck):
  cid=st.selectbox("Khách",ck.id)
  if st.button("Check-out"):
   rm=ck[ck.id==cid].room.iloc[0]
   cur.execute("UPDATE bookings SET status='Completed' WHERE id=?",(int(cid),))
   cur.execute("UPDATE rooms SET status='Available' WHERE no=?",(rm,));conn.commit();st.success("Hoàn tất")
elif page=="Quản lý":
 st.title("Quản lý")
 st.dataframe(rooms,use_container_width=True)
 st.dataframe(books,use_container_width=True)
 st.download_button("Xuất Excel",books.to_csv(index=False),"bookings.csv")
else:
 st.title("💬 HAPPY AI")
 if "msg" not in st.session_state: st.session_state.msg=[]
 for m in st.session_state.msg:
  with st.chat_message(m["r"]): st.write(m["t"])
 q=st.chat_input("Hỏi về khách sạn...")
 if q:
  st.session_state.msg.append({"r":"user","t":q})
  ans="Xin chào! "
  s=q.lower()
  if "4" in s or "gia đình" in s: ans+="Family phù hợp 4 khách (2.000.000đ)."
  elif "suite" in s: ans+="Suite cao cấp 2.800.000đ/đêm."
  elif "check" in s: ans+="Check-in 14:00, Check-out 12:00."
  else: ans+="Chúng tôi có 60 phòng: Standard, Superior, Deluxe, Executive, Family, Suite."
  st.session_state.msg.append({"r":"assistant","t":ans});st.rerun()
