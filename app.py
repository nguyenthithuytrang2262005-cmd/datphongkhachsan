import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import date
import plotly.express as px
import qrcode
from io import BytesIO

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="HAPPY HOTEL",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# AIVEN MYSQL CONFIG
# =========================================================

DB_CONFIG = {
    "host": "mysql-6ab5bcf-trandinhphuc1702-e8a7.e.aivencloud.com",
    "port": 20874,
    "user": "avnadmin",
    "password": "AVNS_0L4tfzDCvAVBs0WWRXK",
    "database": "defaultdb",

    # Aiven MySQL dùng SSL
    "ssl_disabled": False,
    "ssl_verify_cert": False,
    "ssl_verify_identity": False,

    "connection_timeout": 20
}

# =========================================================
# CONNECT MYSQL
# =========================================================

@st.cache_resource
def get_connection():

    try:

        connection = mysql.connector.connect(
            **DB_CONFIG
        )

        if connection.is_connected():
            return connection

    except Error as e:

        st.error(
            f"❌ Không thể kết nối MySQL Aiven\n\n{e}"
        )

        st.stop()

    return None


conn = get_connection()


# =========================================================
# DATABASE EXECUTE FUNCTION
# =========================================================

def execute_query(
    query,
    params=None,
    fetch=False,
    many=False
):

    cursor = None

    try:

        cursor = conn.cursor(
            dictionary=True
        )

        if many:

            cursor.executemany(
                query,
                params
            )

        else:

            cursor.execute(
                query,
                params
            )

        if fetch:

            result = cursor.fetchall()

            return result

        conn.commit()

        return True

    except Error as e:

        try:
            conn.rollback()
        except:
            pass

        st.error(
            f"❌ MySQL Error: {e}"
        )

        return None

    finally:

        if cursor:
            cursor.close()


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():

    # ---------------- ROOMS ----------------

    rooms_sql = """
    CREATE TABLE IF NOT EXISTS rooms (
        room VARCHAR(20) PRIMARY KEY,
        type VARCHAR(50) NOT NULL,
        price BIGINT NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'Available'
    )
    """

    execute_query(
        rooms_sql
    )

    # ---------------- BOOKINGS ----------------

    bookings_sql = """
    CREATE TABLE IF NOT EXISTS bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guest VARCHAR(150) NOT NULL,
        phone VARCHAR(30),
        idcard VARCHAR(50),
        room VARCHAR(20) NOT NULL,
        checkin DATE NOT NULL,
        checkout DATE NOT NULL,
        guests INT DEFAULT 1,
        status VARCHAR(30) NOT NULL,
        total BIGINT DEFAULT 0,
        minibar BIGINT DEFAULT 0,
        laundry BIGINT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """

    execute_query(
        bookings_sql
    )


create_tables()


# =========================================================
# CREATE DEFAULT 60 ROOMS
# =========================================================

def create_default_rooms():

    result = execute_query(
        """
        SELECT COUNT(*) AS total
        FROM rooms
        """,
        fetch=True
    )

    total = 0

    if result:

        total = int(
            result[0]["total"]
        )

    # Chỉ tạo khi bảng rooms đang trống
    if total == 0:

        rooms = []

        # =================================================
        # STANDARD 101 - 120
        # =================================================

        for i in range(101, 121):

            rooms.append(
                (
                    str(i),
                    "Standard",
                    500000,
                    "Available"
                )
            )

        # =================================================
        # DELUXE 201 - 220
        # =================================================

        for i in range(201, 221):

            rooms.append(
                (
                    str(i),
                    "Deluxe",
                    700000,
                    "Available"
                )
            )

        # =================================================
        # SUITE 301 - 310
        # =================================================

        for i in range(301, 311):

            rooms.append(
                (
                    str(i),
                    "Suite",
                    1200000,
                    "Available"
                )
            )

        # =================================================
        # VIP 401 - 410
        # =================================================

        for i in range(401, 411):

            rooms.append(
                (
                    str(i),
                    "VIP",
                    1800000,
                    "Available"
                )
            )

        insert_sql = """
        INSERT INTO rooms
        (
            room,
            type,
            price,
            status
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """

        execute_query(
            insert_sql,
            rooms,
            many=True
        )


create_default_rooms()


# =========================================================
# LOAD ROOMS
# =========================================================

def load_rooms():

    result = execute_query(
        """
        SELECT
            room,
            type,
            price,
            status
        FROM rooms
        ORDER BY CAST(room AS UNSIGNED)
        """,
        fetch=True
    )

    if not result:

        return pd.DataFrame(
            columns=[
                "room",
                "type",
                "price",
                "status"
            ]
        )

    return pd.DataFrame(
        result
    )


# =========================================================
# LOAD BOOKINGS
# =========================================================

def load_bookings():

    result = execute_query(
        """
        SELECT
            id,
            guest,
            phone,
            idcard,
            room,
            checkin,
            checkout,
            guests,
            status,
            total,
            minibar,
            laundry,
            created_at
        FROM bookings
        ORDER BY id DESC
        """,
        fetch=True
    )

    if not result:

        return pd.DataFrame(
            columns=[
                "id",
                "guest",
                "phone",
                "idcard",
                "room",
                "checkin",
                "checkout",
                "guests",
                "status",
                "total",
                "minibar",
                "laundry",
                "created_at"
            ]
        )

    return pd.DataFrame(
        result
    )


# =========================================================
# UPDATE ROOM
# =========================================================

def update_room(
    room,
    status
):

    execute_query(
        """
        UPDATE rooms
        SET status = %s
        WHERE room = %s
        """,
        (
            status,
            room
        )
    )


# =========================================================
# GET ROOM PRICE
# =========================================================

def get_room_price(room):

    result = execute_query(
        """
        SELECT price
        FROM rooms
        WHERE room = %s
        """,
        (room,),
        fetch=True
    )

    if result:

        return int(
            result[0]["price"]
        )

    return 0


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div style="
        background: linear-gradient(
            90deg,
            #0f4c81,
            #1976b8
        );
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 20px;
        color: white;
    ">

        <h1 style="
            margin:0;
            font-size:38px;
        ">
            🏨 HAPPY HOTEL
        </h1>

        <p style="
            margin:5px 0 0 0;
            font-size:18px;
        ">
            Luxury Hotel Management System
        </p>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown(
    """
    <div style="
        text-align:center;
        padding:10px;
    ">

        <h2>
            🏨 HAPPY HOTEL
        </h2>

        <p>
            Hotel Management
        </p>

    </div>
    """,
    unsafe_allow_html=True
)


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


st.sidebar.divider()


st.sidebar.success(
    "🟢 MySQL Aiven Connected"
)


st.sidebar.caption(
    "HAPPY HOTEL\n"
    "60 Rooms Management System"
)


# =========================================================
# LOAD DATA
# =========================================================

rooms = load_rooms()

bookings = load_bookings()


# =========================================================
# DASHBOARD
# =========================================================

if menu == "📊 Dashboard":

    st.subheader(
        "📊 Hotel Dashboard"
    )

    total_rooms = len(
        rooms
    )

    available = len(
        rooms[
            rooms["status"] == "Available"
        ]
    )

    occupied = len(
        rooms[
            rooms["status"] == "Occupied"
        ]
    )

    reserved = len(
        rooms[
            rooms["status"] == "Reserved"
        ]
    )

    cleaning = len(
        rooms[
            rooms["status"] == "Cleaning"
        ]
    )

    maintenance = len(
        rooms[
            rooms["status"] == "Maintenance"
        ]
    )

    if len(bookings) > 0:

        revenue = bookings[
            bookings["status"] == "Completed"
        ]["total"].sum()

    else:

        revenue = 0

    if total_rooms > 0:

        occupancy = round(
            occupied /
            total_rooms *
            100,
            1
        )

    else:

        occupancy = 0


    # =====================================================
    # METRICS
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "🏨 Total Rooms",
        total_rooms
    )


    c2.metric(
        "🟢 Available",
        available
    )


    c3.metric(
        "🔴 Occupied",
        occupied
    )


    c4.metric(
        "📊 Occupancy",
        f"{occupancy}%"
    )


    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "📅 Reserved",
        reserved
    )


    c2.metric(
        "🧹 Cleaning",
        cleaning
    )


    c3.metric(
        "🔧 Maintenance",
        maintenance
    )


    c4.metric(
        "💰 Revenue",
        f"{int(revenue):,} VND"
    )


    st.divider()


    # =====================================================
    # ROOM CATEGORIES
    # =====================================================

    st.subheader(
        "🏨 Room Categories"
    )


    room_types = (
        rooms
        .groupby("type")
        .agg(
            price=("price", "first"),
            quantity=("room", "count")
        )
        .reset_index()
    )


    if len(room_types) > 0:

        cols = st.columns(
            len(room_types)
        )


        for i, row in room_types.iterrows():

            with cols[i]:

                st.markdown(
                    f"""
                    <div style="
                        padding:20px;
                        border-radius:15px;
                        background:#F5F7FA;
                        text-align:center;
                        border:1px solid #E2E8F0;
                    ">

                        <h3>
                            {row['type']}
                        </h3>

                        <h2>
                            {int(row['price']):,}
                            VND
                        </h2>

                        <p>
                            {int(row['quantity'])}
                            phòng
                        </p>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


    st.divider()


    st.subheader(
        "💰 Revenue Summary"
    )


    st.metric(
        "Total Revenue",
        f"{int(revenue):,} VND"
    )


# =========================================================
# ROOM MANAGEMENT
# =========================================================

elif menu == "🛏 Room Management":

    st.subheader(
        "🛏 Room Management"
    )


    # =====================================================
    # FILTER
    # =====================================================

    c1, c2 = st.columns(2)


    with c1:

        type_filter = st.selectbox(
            "Room Category",
            [
                "All",
                "Standard",
                "Deluxe",
                "Suite",
                "VIP"
            ]
        )


    with c2:

        status_filter = st.selectbox(
            "Status",
            [
                "All",
                "Available",
                "Occupied",
                "Reserved",
                "Cleaning",
                "Maintenance"
            ]
        )


    room_display = rooms.copy()


    if type_filter != "All":

        room_display = room_display[
            room_display["type"]
            == type_filter
        ]


    if status_filter != "All":

        room_display = room_display[
            room_display["status"]
            == status_filter
        ]


    st.dataframe(
        room_display,
        use_container_width=True,
        hide_index=True
    )


    st.divider()


    # =====================================================
    # ADD ROOM
    # =====================================================

    with st.expander(
        "➕ Add Room"
    ):

        c1, c2, c3 = st.columns(3)


        with c1:

            new_room = st.text_input(
                "Room Number"
            )


        with c2:

            new_type = st.selectbox(
                "Type",
                [
                    "Standard",
                    "Deluxe",
                    "Suite",
                    "VIP"
                ]
            )


        price_default = {
            "Standard": 500000,
            "Deluxe": 700000,
            "Suite": 1200000,
            "VIP": 1800000
        }


        with c3:

            new_price = st.number_input(
                "Price / Night",
                min_value=100000,
                max_value=10000000,
                value=price_default[
                    new_type
                ],
                step=50000
            )


        if st.button(
            "➕ Add Room",
            type="primary"
        ):

            if not new_room.strip():

                st.error(
                    "Vui lòng nhập số phòng."
                )

            else:

                exists = execute_query(
                    """
                    SELECT room
                    FROM rooms
                    WHERE room = %s
                    """,
                    (
                        new_room.strip(),
                    ),
                    fetch=True
                )


                if exists:

                    st.error(
                        "❌ Phòng đã tồn tại."
                    )

                else:

                    execute_query(
                        """
                        INSERT INTO rooms
                        (
                            room,
                            type,
                            price,
                            status
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            'Available'
                        )
                        """,
                        (
                            new_room.strip(),
                            new_type,
                            new_price
                        )
                    )


                    st.success(
                        "✅ Thêm phòng thành công."
                    )


                    st.rerun()


    st.divider()


    # =====================================================
    # UPDATE STATUS
    # =====================================================

    st.subheader(
        "🔄 Update Room Status"
    )


    if len(rooms) > 0:

        c1, c2, c3 = st.columns(3)


        with c1:

            room_select = st.selectbox(
                "Select Room",
                rooms["room"].tolist()
            )


        current_status = rooms[
            rooms["room"] == room_select
        ]["status"].iloc[0]


        with c2:

            status_options = [
                "Available",
                "Occupied",
                "Reserved",
                "Cleaning",
                "Maintenance"
            ]


            new_status = st.selectbox(
                "Change Status",
                status_options,
                index=status_options.index(
                    current_status
                )
            )


        with c3:

            st.write("")

            st.write("")


            if st.button(
                "🔄 Update Status",
                type="primary"
            ):

                update_room(
                    room_select,
                    new_status
                )


                st.success(
                    f"Phòng {room_select} "
                    f"→ {new_status}"
                )


                st.rerun()


# =========================================================
# RESERVATION
# =========================================================

elif menu == "📅 Reservation":

    st.subheader(
        "📅 New Reservation"
    )


    available_rooms = rooms[
        rooms["status"] == "Available"
    ]


    if len(available_rooms) == 0:

        st.error(
            "❌ Hiện tại không còn phòng trống."
        )

    else:

        c1, c2, c3 = st.columns(3)


        with c1:

            name = st.text_input(
                "👤 Guest Name"
            )


        with c2:

            phone = st.text_input(
                "📞 Phone"
            )


        with c3:

            idcard = st.text_input(
                "🪪 ID Card"
            )


        c1, c2 = st.columns(2)


        with c1:

            guests = st.slider(
                "👥 Guests",
                1,
                10,
                2
            )


        with c2:

            room = st.selectbox(
                "🛏 Choose Room",
                available_rooms[
                    "room"
                ].tolist()
            )


        c1, c2 = st.columns(2)


        with c1:

            checkin = st.date_input(
                "📅 Check In",
                date.today()
            )


        with c2:

            checkout = st.date_input(
                "📅 Check Out",
                date.today()
            )


        price = get_room_price(
            room
        )


        nights = max(
            (
                checkout -
                checkin
            ).days,
            1
        )


        total = (
            price *
            nights
        )


        st.info(
            f"🌙 {nights} night(s) "
            f"| 💰 Total = "
            f"{total:,} VND"
        )


        # =================================================
        # RECOMMENDATION
        # =================================================

        st.markdown(
            "### 🤖 Smart Recommendation"
        )


        if guests <= 2:

            st.success(
                "Recommended: Standard / Deluxe"
            )

        elif guests <= 4:

            st.success(
                "Recommended: Deluxe / Suite"
            )

        else:

            st.success(
                "Recommended: Suite / VIP"
            )


        # =================================================
        # RESERVE
        # =================================================

        if st.button(
            "📅 Reserve",
            type="primary"
        ):

            if not name.strip():

                st.error(
                    "Vui lòng nhập tên khách."
                )

            elif checkout < checkin:

                st.error(
                    "Ngày Check Out phải sau "
                    "hoặc bằng Check In."
                )

            else:

                execute_query(
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
                        total,
                        minibar,
                        laundry
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        'Reserved',
                        %s,
                        0,
                        0
                    )
                    """,
                    (
                        name,
                        phone,
                        idcard,
                        room,
                        checkin,
                        checkout,
                        guests,
                        total
                    )
                )


                update_room(
                    room,
                    "Reserved"
                )


                st.success(
                    "🎉 Reservation Successful!"
                )


                # =================================================
                # QR CODE
                # =================================================

                qr_data = (
                    f"HAPPY HOTEL\n"
                    f"Guest: {name}\n"
                    f"Room: {room}\n"
                    f"Check In: {checkin}\n"
                    f"Check Out: {checkout}\n"
                    f"Total: {total:,} VND"
                )


                qr = qrcode.make(
                    qr_data
                )


                buf = BytesIO()


                qr.save(
                    buf,
                    format="PNG"
                )


                st.image(
                    buf.getvalue(),
                    caption="Reservation QR Code",
                    width=220
                )


                st.rerun()


# =========================================================
# CHECK IN
# =========================================================

elif menu == "🟢 Check In":

    st.subheader(
        "🟢 Check In"
    )


    reserved = bookings[
        bookings["status"] == "Reserved"
    ]


    if len(reserved) == 0:

        st.info(
            "Không có reservation nào "
            "đang chờ Check In."
        )

    else:

        booking_id = st.selectbox(
            "Booking ID",
            reserved["id"].tolist()
        )


        row = reserved[
            reserved["id"]
            == booking_id
        ].iloc[0]


        c1, c2 = st.columns(2)


        with c1:

            st.write(
                f"**👤 Guest:** "
                f"{row['guest']}"
            )

            st.write(
                f"**📞 Phone:** "
                f"{row['phone']}"
            )

            st.write(
                f"**🪪 ID Card:** "
                f"{row['idcard']}"
            )


        with c2:

            st.write(
                f"**🛏 Room:** "
                f"{row['room']}"
            )

            st.write(
                f"**📅 Check In:** "
                f"{row['checkin']}"
            )

            st.write(
                f"**📅 Check Out:** "
                f"{row['checkout']}"
            )


        st.metric(
            "💰 Total",
            f"{int(row['total']):,} VND"
        )


        if st.button(
            "🟢 Check In",
            type="primary"
        ):

            execute_query(
                """
                UPDATE bookings
                SET status = 'Checked In'
                WHERE id = %s
                """,
                (
                    int(booking_id),
                )
            )


            update_room(
                row["room"],
                "Occupied"
            )


            st.success(
                "✅ Check In thành công!"
            )


            st.rerun()


# =========================================================
# CHECK OUT
# =========================================================

elif menu == "🔴 Check Out":

    st.subheader(
        "🔴 Check Out"
    )


    staying = bookings[
        bookings["status"]
        == "Checked In"
    ]


    if len(staying) == 0:

        st.info(
            "Không có khách đang lưu trú."
        )

    else:

        booking_id = st.selectbox(
            "Booking",
            staying["id"].tolist()
        )


        row = staying[
            staying["id"]
            == booking_id
        ].iloc[0]


        st.write(
            f"**👤 Guest:** "
            f"{row['guest']}"
        )


        st.write(
            f"**🛏 Room:** "
            f"{row['room']}"
        )


        st.write(
            f"**📅 Check In:** "
            f"{row['checkin']}"
        )


        st.write(
            f"**📅 Check Out:** "
            f"{row['checkout']}"
        )


        st.divider()


        c1, c2 = st.columns(2)


        with c1:

            minibar = st.number_input(
                "🍫 MiniBar",
                min_value=0,
                max_value=5000000,
                value=0,
                step=10000
            )


        with c2:

            laundry = st.number_input(
                "👕 Laundry",
                min_value=0,
                max_value=5000000,
                value=0,
                step=10000
            )


        room_total = int(
            row["total"]
        )


        final_total = (
            room_total
            + minibar
            + laundry
        )


        st.metric(
            "🏨 Room Charge",
            f"{room_total:,} VND"
        )


        st.metric(
            "💰 Grand Total",
            f"{final_total:,} VND"
        )


        if st.button(
            "🔴 Complete Check Out",
            type="primary"
        ):

            execute_query(
                """
                UPDATE bookings
                SET
                    status = 'Completed',
                    total = %s,
                    minibar = %s,
                    laundry = %s
                WHERE id = %s
                """,
                (
                    final_total,
                    minibar,
                    laundry,
                    int(booking_id)
                )
            )


            update_room(
                row["room"],
                "Cleaning"
            )


            st.success(
                "✅ Check Out Completed!"
            )


            st.rerun()


# =========================================================
# GUESTS
# =========================================================

elif menu == "👥 Guests":

    st.subheader(
        "👥 Guest List"
    )


    keyword = st.text_input(
        "🔎 Search Guest / Phone / Room"
    )


    df = bookings.copy()


    if keyword.strip():

        keyword = keyword.lower()


        df = df[
            df.apply(
                lambda row:
                keyword in
                " ".join(
                    row.astype(str)
                ).lower(),
                axis=1
            )
        ]


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    csv = df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )


    st.download_button(
        "⬇ Export CSV",
        csv,
        "happy_hotel_guests.csv",
        "text/csv"
    )


# =========================================================
# REVENUE
# =========================================================

elif menu == "📈 Revenue":

    st.subheader(
        "📈 Revenue Analytics"
    )


    df = bookings[
        bookings["status"]
        == "Completed"
    ].copy()


    if len(df) == 0:

        st.info(
            "Chưa có doanh thu."
        )

    else:

        df["checkin"] = pd.to_datetime(
            df["checkin"]
        )


        daily = (
            df
            .groupby(
                df["checkin"].dt.date
            )["total"]
            .sum()
            .reset_index()
        )


        daily.columns = [
            "date",
            "revenue"
        ]


        fig = px.line(
            daily,
            x="date",
            y="revenue",
            markers=True,
            title="💰 Daily Revenue"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


        total_revenue = int(
            df["total"].sum()
        )


        c1, c2, c3 = st.columns(3)


        c1.metric(
            "💰 Total Revenue",
            f"{total_revenue:,} VND"
        )


        c2.metric(
            "🧾 Completed Bills",
            len(df)
        )


        c3.metric(
            "💵 Average Bill",
            f"{int(df['total'].mean()):,} VND"
        )


        st.divider()


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# AI CHATBOX
# =========================================================

elif menu == "💬 AI ChatBox":

    st.subheader(
        "💬 HAPPY HOTEL AI Assistant"
    )


    st.caption(
        "Trợ lý ảo hỗ trợ khách hàng "
        "và lễ tân 24/7"
    )


    # =====================================================
    # CHAT HISTORY
    # =====================================================

    if "messages" not in st.session_state:

        st.session_state.messages = [
            {
                "role": "assistant",
                "content":
                """
👋 Xin chào!

Tôi là trợ lý của **HAPPY HOTEL**.

Tôi có thể hỗ trợ:

💵 Giá phòng

🛏 Phòng còn trống

📅 Thông tin đặt phòng

🟢 Giờ Check-in

🔴 Giờ Check-out

📶 Wifi

📍 Địa chỉ

☎ Hotline

💰 Doanh thu
                """
            }
        ]


    # =====================================================
    # SHOW CHAT
    # =====================================================

    for msg in st.session_state.messages:

        with st.chat_message(
            msg["role"]
        ):

            st.markdown(
                msg["content"]
            )


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


        with st.chat_message(
            "user"
        ):

            st.write(
                prompt
            )


        text = prompt.lower()


        # =================================================
        # PRICE
        # =================================================

        if (
            "giá" in text
            or "price" in text
            or "bao nhiêu tiền" in text
        ):

            price_list = (
                rooms
                .groupby("type")["price"]
                .first()
            )


            reply = (
                "### 💵 Bảng giá phòng\n\n"
            )


            for room_type, price in price_list.items():

                reply += (
                    f"- **{room_type}**: "
                    f"{int(price):,} "
                    f"VND/đêm\n"
                )


        # =================================================
        # AVAILABLE
        # =================================================

        elif (
            "phòng trống" in text
            or "phòng còn" in text
            or "available" in text
        ):

            available = rooms[
                rooms["status"]
                == "Available"
            ]


            if len(available) == 0:

                reply = (
                    "❌ Hiện tại không còn "
                    "phòng trống."
                )

            else:

                reply = (
                    "### 🟢 Phòng đang trống\n\n"
                )


                for _, room_row in available.iterrows():

                    reply += (
                        f"- Phòng "
                        f"**{room_row['room']}** "
                        f"({room_row['type']}) - "
                        f"{int(room_row['price']):,} "
                        f"VND/đêm\n"
                    )


        # =================================================
        # CHECK IN
        # =================================================

        elif (
            "check in" in text
            or "check-in" in text
            or "nhận phòng" in text
        ):

            reply = (
                "🟢 Giờ Check-in: **14:00**"
            )


        # =================================================
        # CHECK OUT
        # =================================================

        elif (
            "check out" in text
            or "check-out" in text
            or "trả phòng" in text
        ):

            reply = (
                "🔴 Giờ Check-out: **12:00**"
            )


        # =================================================
        # WIFI
        # =================================================

        elif "wifi" in text:

            reply = (
                "📶 Wifi: "
                "**HAPPYHOTEL_FREE**\n\n"
                "Mật khẩu: **happy123**"
            )


        # =================================================
        # ADDRESS
        # =================================================

        elif (
            "địa chỉ" in text
            or "ở đâu" in text
        ):

            reply = (
                "📍 HAPPY HOTEL\n\n"
                "123 Đường Biển, Vũng Tàu"
            )


        # =================================================
        # HOTLINE
        # =================================================

        elif (
            "liên hệ" in text
            or "sdt" in text
            or "số điện thoại" in text
            or "hotline" in text
        ):

            reply = (
                "☎ Hotline: "
                "**0909 888 999**"
            )


        # =================================================
        # REVENUE
        # =================================================

        elif (
            "doanh thu" in text
            or "revenue" in text
        ):

            revenue = bookings[
                bookings["status"]
                == "Completed"
            ]["total"].sum()


            reply = (
                f"💰 Tổng doanh thu hiện tại: "
                f"**{int(revenue):,} VND**"
            )


        # =================================================
        # ROOM STATUS
        # =================================================

        elif (
            "tình trạng phòng" in text
            or "room status" in text
        ):

            status_count = (
                rooms["status"]
                .value_counts()
                .to_dict()
            )


            reply = (
                "### 🛏 Room Status\n\n"
            )


            for status, count in status_count.items():

                reply += (
                    f"- **{status}**: "
                    f"{count} phòng\n"
                )


        # =================================================
        # TOTAL ROOMS
        # =================================================

        elif (
            "bao nhiêu phòng" in text
            or "tổng số phòng" in text
        ):

            reply = (
                f"🏨 HAPPY HOTEL hiện có "
                f"**{len(rooms)} phòng**."
            )


        # =================================================
        # DEFAULT
        # =================================================

        else:

            reply = """
Tôi có thể hỗ trợ:

💵 **Giá phòng**

🛏 **Phòng còn trống**

📅 **Đặt phòng**

🟢 **Giờ Check-in**

🔴 **Giờ Check-out**

📶 **Wifi**

📍 **Địa chỉ**

☎ **Hotline**

💰 **Doanh thu**

🛏 **Tình trạng phòng**
"""


        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply
            }
        )


        with st.chat_message(
            "assistant"
        ):

            st.markdown(
                reply
            )
