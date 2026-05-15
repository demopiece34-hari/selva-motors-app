import streamlit as st
import pandas as pd
import gspread
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Selva Motors Attendance", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.main {background-color:#f7f9fc;}
.stButton>button {
    border-radius:10px;
    font-weight:600;
}
.card {
    padding:18px;
    border-radius:15px;
    background:white;
    box-shadow:0 2px 10px rgba(0,0,0,0.08);
    margin-bottom:15px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- GOOGLE SHEET CONNECTION ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

@st.cache_resource
def connect_sheet():
    for _ in range(5):
        try:
            client = gspread.authorize(creds)
            return client.open_by_key(st.secrets["SHEET_ID"])
        except Exception:
            time.sleep(2)
    st.error("⚠️ Google Sheet connection failed. Refresh pannunga.")
    st.stop()

sheet = connect_sheet()

def get_sheet(sheet_name):
    for _ in range(5):
        try:
            return sheet.worksheet(sheet_name)
        except Exception:
            time.sleep(2)
    st.error(f"⚠️ {sheet_name} sheet connection failed")
    st.stop()

def safe_df(ws, columns):
    for _ in range(5):
        try:
            data = ws.get_all_records()
            df = pd.DataFrame(data)

            for col in columns:
                if col not in df.columns:
                    df[col] = ""

            return df

        except Exception:
            time.sleep(2)

    return pd.DataFrame(columns=columns)

attendance_sheet = get_sheet("Attendance")
service_sheet = get_sheet("ServiceReport")
request_sheet = get_sheet("AttendanceRequests")

# ---------------- USERS ----------------
staff_users = {
    "Staff1": {"password": "1234", "name": "Mohan", "role": "Technician"},
    "Staff2": {"password": "1234", "name": "Ajay", "role": "Technician"},
    "Staff3": {"password": "1234", "name": "Prathisha", "role": "System Staff"},
    "Staff4": {"password": "1234", "name": "Vegadesh", "role": "Technician"}
}

admin_user = {"admin": "admin123"}

# ---------------- FUNCTIONS ----------------
def today_date():
    return datetime.now().strftime("%d-%m-%Y")

def now_time():
    return datetime.now().strftime("%H:%M:%S")

def is_absent_today(today, staff_id):
    df = safe_df(attendance_sheet, ["Date", "Staff ID", "Status"])
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Status"].astype(str).str.upper() == "ABSENT")
    ).any()

def is_request_pending(today, staff_id):
    df = safe_df(request_sheet, ["Date", "Staff ID", "Request Status"])
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Request Status"].astype(str).str.upper() == "PENDING")
    ).any()

def is_request_approved(today, staff_id):
    df = safe_df(request_sheet, ["Date", "Staff ID", "Request Status"])
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Request Status"].astype(str).str.upper() == "APPROVED")
    ).any()

def already_present_or_halfday(today, staff_id):
    df = safe_df(attendance_sheet, ["Date", "Staff ID", "Status"])
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Status"].astype(str).str.upper() != "ABSENT")
    ).any()

def service_dataframe():
    df = safe_df(
        service_sheet,
        ["Date", "Staff ID", "Staff Name", "Bike Name", "Service Type", "Labour Amount"]
    )
    df["Labour Amount"] = pd.to_numeric(
        df["Labour Amount"],
        errors="coerce"
    ).fillna(0)
    return df

# ---------------- APP ----------------
st.title("🏍️ SELVA MOTORS STAFF MANAGEMENT ⚙️")

menu = st.sidebar.selectbox(
    "🔐 Select Login",
    ["Staff Login", "Admin Login"]
)

# ======================================================
# STAFF LOGIN
# ======================================================
if menu == "Staff Login":

    st.subheader("🔑 Staff Login")

    if not st.session_state.get("staff_login"):

        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")

        if st.button("🔓 Login"):

            if user_id in staff_users and staff_users[user_id]["password"] == password:
                st.session_state["staff_login"] = True
                st.session_state["staff_id"] = user_id
                st.session_state["staff_name"] = staff_users[user_id]["name"]
                st.session_state["staff_role"] = staff_users[user_id]["role"]
                st.rerun()
            else:
                st.error("🚫 Invalid Staff Login")

    else:
        staff_id = st.session_state["staff_id"]
        staff_name = st.session_state["staff_name"]
        role = st.session_state["staff_role"]
        today = today_date()

        st.success(f"👋 Hii {staff_name}")
        st.info(f"⚙️ Role: {role}")

        if st.button("🔒 Logout"):
            st.session_state["staff_login"] = False
            st.session_state["staff_id"] = ""
            st.session_state["staff_name"] = ""
            st.session_state["staff_role"] = ""
            st.rerun()

        # ---------------- ATTENDANCE ----------------
        st.header("📥 Staff Attendance")

        absent_block = is_absent_today(today, staff_id)
        approved = is_request_approved(today, staff_id)

        if absent_block and not approved:

            st.error("🚫 Admin absent mark pannirukanga. Attendance block pannirukku.")

            if is_request_pending(today, staff_id):
                st.info("📤 Request already sent. Admin approval pending.")
            else:
                if st.button("📤 Send Attendance Request"):
                    request_sheet.append_row([
                        today,
                        staff_id,
                        staff_name,
                        role,
                        "Pending"
                    ])
                    st.success("✅ Request sent to admin")
                    st.rerun()

        else:

            status = st.selectbox(
                "Attendance Status",
                ["Present", "Half Day Leave"]
            )

            if st.button("📥 Mark Attendance"):

                if already_present_or_halfday(today, staff_id):
                    st.warning("⚠️ Today attendance already marked")
                else:
                    attendance_sheet.append_row([
                        today,
                        now_time(),
                        staff_id,
                        staff_name,
                        role,
                        status
                    ])
                    st.success("✅ Attendance Saved")

        # ---------------- SERVICE ENTRY ----------------
        st.header("🛠️ Daily Service Entry")

        service_df = service_dataframe()

        today_staff_service = service_df[
            (service_df["Date"].astype(str) == today) &
            (service_df["Staff Name"].astype(str) == staff_name)
        ]

        today_bike_count = len(today_staff_service)
        today_labour_total = today_staff_service["Labour Amount"].sum()

        col1, col2 = st.columns(2)
        col1.metric("🏍️ Today Service Bikes", today_bike_count)
        col2.metric("💵 Today Labour Total", f"₹{today_labour_total}")

        if role == "Technician":

            bike = st.selectbox(
                "🏍️ Bike Name",
                [
                    "Passion Plus",
                    "Splendor Plus",
                    "Destiny",
                    "Xoom",
                    "Glamour",
                    "Xtreme",
                    "Super Splendor",
                    "HF Deluxe"
                ]
            )

            service_type = st.selectbox(
                "🛢️ Service Type",
                ["Paid", "FSC", "General"]
            )

            labour = st.number_input(
                "💵 Labour Amount",
                min_value=0
            )

            if "service_lock" not in st.session_state:
                st.session_state["service_lock"] = False

            if st.session_state["service_lock"]:
                st.warning("⏳ Please wait 3 seconds...")
                time.sleep(3)
                st.session_state["service_lock"] = False
                st.rerun()

            if st.button("📤 Save Service Report", disabled=st.session_state["service_lock"]):

                st.session_state["service_lock"] = True

                service_sheet.append_row([
                    today,
                    staff_id,
                    staff_name,
                    bike,
                    service_type,
                    labour
                ])

                st.success("✅ Service Report Saved")
                st.rerun()

        else:
            st.info("💻 System Staff ku service entry illa")

# ======================================================
# ADMIN LOGIN
# ======================================================
if menu == "Admin Login":

    st.subheader("🔐 Admin Login")

    if not st.session_state.get("admin_login"):

        admin_id = st.text_input("Admin User ID")
        admin_pass = st.text_input("Admin Password", type="password")

        if st.button("🔓 Admin Login"):

            if admin_id in admin_user and admin_user[admin_id] == admin_pass:
                st.session_state["admin_login"] = True
                st.rerun()
            else:
                st.error("🚫 Invalid Admin Login")

    else:

        st.success("🔓 Admin Logged In")

        if st.button("🔒 Admin Logout"):
            st.session_state["admin_login"] = False
            st.rerun()

        today = today_date()

        st.header("📊 Admin Dashboard")

        # ---------------- MARK ABSENT ----------------
        st.subheader("🚫 Mark Particular Staff Absent")

        staff_map = {
            "Mohan": "Staff1",
            "Ajay": "Staff2",
            "Prathisha": "Staff3",
            "Vegadesh": "Staff4"
        }

        selected_absent_staff = st.selectbox(
            "Select Staff",
            ["Mohan", "Ajay", "Prathisha", "Vegadesh"]
        )

        if st.button("🚫 Mark Selected Staff Absent"):

            sid = staff_map[selected_absent_staff]
            info = staff_users[sid]

            if already_present_or_halfday(today, sid) or is_absent_today(today, sid):
                st.warning("⚠️ Today attendance already exists")
            else:
                attendance_sheet.append_row([
                    today,
                    "-",
                    sid,
                    info["name"],
                    info["role"],
                    "ABSENT"
                ])
                st.success(f"✅ {selected_absent_staff} marked ABSENT")
                st.rerun()

        # ---------------- REQUEST APPROVAL ----------------
        st.subheader("📤 Attendance Requests")

        request_df = safe_df(
            request_sheet,
            ["Date", "Staff ID", "Staff Name", "Role", "Request Status"]
        )

        pending_df = request_df[
            (request_df["Date"].astype(str) == today) &
            (request_df["Request Status"].astype(str).str.upper() == "PENDING")
        ]

        if pending_df.empty:
            st.info("No pending requests")
        else:
            for i, row in pending_df.iterrows():

                st.write(
                    f"🔗 {row['Staff Name']} ({row['Staff ID']}) attendance open request"
                )

                if st.button(f"✅ Approve {row['Staff Name']}", key=f"approve_{i}"):
                    request_sheet.update_cell(i + 2, 5, "Approved")
                    st.success("✅ Request Approved")
                    st.rerun()

        # ---------------- SERVICE COUNT ----------------
        st.subheader("📈 Today Technician Service Count")

        service_df = service_dataframe()

        today_service_df = service_df[
            service_df["Date"].astype(str) == today
        ]

        tech_names = ["Mohan", "Ajay", "Vegadesh"]

        count_rows = []
        for name in tech_names:
            staff_df = today_service_df[
                today_service_df["Staff Name"].astype(str) == name
            ]

            count_rows.append({
                "Technician": name,
                "Today Bikes": len(staff_df),
                "Today Labour Amount": staff_df["Labour Amount"].sum()
            })

        count_df = pd.DataFrame(count_rows)

        st.dataframe(count_df, use_container_width=True)

        total_bikes = count_df["Today Bikes"].sum()
        total_labour = count_df["Today Labour Amount"].sum()

        col1, col2 = st.columns(2)
        col1.metric("🏍️ Total Bikes Today", total_bikes)
        col2.metric("💸 Total Labour Today", f"₹{total_labour}")

        # ---------------- REPORTS ----------------
        st.subheader("📥 Overall Attendance Report")

        attendance_df = safe_df(
            attendance_sheet,
            ["Date", "Time", "Staff ID", "Staff Name", "Role", "Status"]
        )

        st.dataframe(attendance_df, use_container_width=True)

        st.subheader("🛠️ Overall Service Report")

        st.dataframe(service_df, use_container_width=True)

        csv_service = service_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download Service Report CSV",
            data=csv_service,
            file_name="service_report.csv",
            mime="text/csv"
            )
