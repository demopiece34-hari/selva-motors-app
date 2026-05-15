import streamlit as st
import pandas as pd
import gspread
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Selva Motors Attendance", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.main {background-color:#f7f9fc;}
.stButton>button {border-radius:10px;font-weight:600;}
.card {
    padding:18px;
    border-radius:15px;
    background:white;
    box-shadow:0 2px 10px rgba(0,0,0,0.08);
    margin-bottom:15px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- GOOGLE SHEET ----------------
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
            df = pd.DataFrame(ws.get_all_records())
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
    "mohan": {"password": "mohan", "name": "Mohan", "role": "Technician"},
    "ajay": {"password": "ajay", "name": "Ajay", "role": "Technician"},
    "prathisha": {"password": "prathisha", "name": "Prathisha", "role": "System Staff"},
    "vengadesh": {"password": "vengadesh", "name": "Vegadesh", "role": "Technician"}
}

admin_user = {
    "manoselva": "manobakiya"
}

# ---------------- FUNCTIONS ----------------

def now_time():
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%I:%M:%S %p")

def today_date():
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y")

def is_late():
    now = datetime.now()
    late_time = now.replace(hour=9, minute=45, second=0)
    return now > late_time

def attendance_df():
    return safe_df(attendance_sheet, ["Date", "Time", "Staff ID", "Staff Name", "Role", "Status"])

def service_df():
    df = safe_df(service_sheet, ["Date", "Staff ID", "Staff Name", "reg_no","Bike Name", "Service Type", "Labour Amount"])
    df["Labour Amount"] = pd.to_numeric(df["Labour Amount"], errors="coerce").fillna(0)
    return df

def request_df():
    return safe_df(request_sheet, ["Date", "Staff ID", "Staff Name", "Role", "Request Status"])

def is_absent_today(today, staff_id):
    df = attendance_df()
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Status"].astype(str).str.upper() == "ABSENT")
    ).any()

def request_pending(today, staff_id):
    df = request_df()
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Request Status"].astype(str).str.upper() == "PENDING")
    ).any()

def request_approved(today, staff_id):
    df = request_df()
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Request Status"].astype(str).str.upper() == "APPROVED")
    ).any()

def already_marked(today, staff_id):
    df = attendance_df()
    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Status"].astype(str).str.upper() != "ABSENT")
    ).any()

def filter_by_month(df, date_col, month_text):
    if df.empty:
        return df
    temp = df.copy()
    temp["Month"] = pd.to_datetime(temp[date_col], format="%d-%m-%Y", errors="coerce").dt.strftime("%m-%Y")
    return temp[temp["Month"] == month_text]

# ---------------- APP ----------------
st.title("🏍️ SELVA MOTORS STAFF MANAGEMENT ⚙️")

menu = st.sidebar.selectbox("🔐 Select Login", ["Staff Login", "Admin Login"])

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
            st.session_state.clear()
            st.rerun()

        # Attendance
        st.header("📥 Staff Attendance")

        absent = is_absent_today(today, staff_id)
        approved = request_approved(today, staff_id)

        if absent and not approved:
            st.error("🚫 Admin absent mark pannirukanga. Attendance block.")
            if request_pending(today, staff_id):
                st.info("📤 Request already sent. Admin approval pending.")
            else:
                if st.button("📤 Send Attendance Request"):
                    request_sheet.append_row([today, staff_id, staff_name, role, "Pending"])
                    st.success("✅ Request sent to admin")
                    st.rerun()
        else:
            status = st.selectbox("Attendance Status", ["Present", "Half Day Leave"])
            selfie = st.camera_input("📸 Optional Selfie Attendance")

            if st.button("📥 Mark Attendance"):
                if already_marked(today, staff_id):
                    st.warning("⚠️ Today attendance already marked")
                else:
                    final_status = status
                    if status == "Present" and is_late():
                        final_status = "Late Present"

                    attendance_sheet.append_row([
                        today, now_time(), staff_id, staff_name, role, final_status
                    ])
                    st.success("✅ Attendance Saved")

        # Service Entry
        st.header("🛠️ Daily Service Entry")

        sdf = service_df()
        today_staff_service = sdf[
            (sdf["Date"].astype(str) == today) &
            (sdf["Staff Name"].astype(str) == staff_name)
        ]

        col1, col2 = st.columns(2)
        col1.metric("🏍️ Today Service Bikes", len(today_staff_service))
        col2.metric("💵 Today Labour Total", f"₹{today_staff_service['Labour Amount'].sum()}")

        if role == "Technician":
            reg_no = st.text_input(
                "🔗 Vehicle Reg Number",
                placeholder="TN 82 AB 1234"
            )
            bike = st.selectbox("🏍️ Bike Name", [
                "Passion Plus", "Splendor Plus", "Destiny", "Xoom",
                "Glamour", "Xtreme", "Super Splendor", "HF Deluxe"
            ])

            service_type = st.selectbox("🛢️ Service Type", ["Paid", "FSC", "General"])
            labour = st.number_input("💵 Labour Amount", min_value=0)

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
                    today, staff_id, staff_name, reg_no, bike, service_type, labour
                ])
                st.success("✅ Service Report Saved")
                st.rerun()

            st.subheader("📜 Today Service History")

            if st.button("📋 Show Today History"):

                history_data = service_df()

                history_df = history_data[
                    (service_df["Date"].astype(str) == today) &
                    (service_df["Staff Name"].astype(str) == staff_name)
                ]

                if history_df.empty:

                    st.warning("No today service entries")

                else:

                    show_df = history_df[
                        [
                            "Reg No",
                            "Bike Name",
                            "Service Type",
                            "Labour Amount"
                        ]
                    ]

                    st.dataframe(
                        show_df,
                        use_container_width=True
                    )
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
            st.session_state.clear()
            st.rerun()

        today = today_date()

        st.header("📊 Admin Dashboard")

        # Mark Absent
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

            if already_marked(today, sid) or is_absent_today(today, sid):
                st.warning("⚠️ Today attendance already exists")
            else:
                attendance_sheet.append_row([
                    today, "-", sid, info["name"], info["role"], "ABSENT"
                ])
                st.success(f"✅ {selected_absent_staff} marked ABSENT")
                st.rerun()

        # Approval
        st.subheader("📤 Attendance Requests")

        rdf = request_df()
        pending_df = rdf[
            (rdf["Date"].astype(str) == today) &
            (rdf["Request Status"].astype(str).str.upper() == "PENDING")
        ]

        if pending_df.empty:
            st.info("No pending requests")
        else:
            for i, row in pending_df.iterrows():
                st.write(f"🔗 {row['Staff Name']} ({row['Staff ID']}) attendance open request")
                if st.button(f"✅ Approve {row['Staff Name']}", key=f"approve_{i}"):
                    request_sheet.update_cell(i + 2, 5, "Approved")
                    st.success("✅ Request Approved")
                    st.rerun()

        # Reports
        adf = attendance_df()
        sdf = service_df()

        st.subheader("📈 Today Technician Service Count & Labour")

        today_service = sdf[sdf["Date"].astype(str) == today]
        tech_names = ["Mohan", "Ajay", "Vegadesh"]

        rows = []
        for name in tech_names:
            temp = today_service[today_service["Staff Name"].astype(str) == name]
            rows.append({
                "Technician": name,
                "Today Bikes": len(temp),
                "Today Labour Amount": temp["Labour Amount"].sum()
            })

        count_df = pd.DataFrame(rows)
        st.dataframe(count_df, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("🏍️ Total Bikes Today", count_df["Today Bikes"].sum())
        c2.metric("💸 Total Labour Today", f"₹{count_df['Today Labour Amount'].sum()}")

        # Monthly Salary
        st.subheader("💵 Monthly Salary Report")

        month_text = st.text_input("Enter Month MM-YYYY", datetime.now().strftime("%m-%Y"))

        monthly_att = filter_by_month(adf, "Date", month_text)

        salary_rows = []
        per_day_salary = 500

        for sid, info in staff_users.items():
            temp = monthly_att[monthly_att["Staff ID"].astype(str) == sid]
            present = len(temp[temp["Status"].astype(str).str.upper().isin(["PRESENT", "LATE PRESENT"])])
            halfday = len(temp[temp["Status"].astype(str).str.upper() == "HALF DAY LEAVE"])
            absent_count = len(temp[temp["Status"].astype(str).str.upper() == "ABSENT"])

            salary = (present * per_day_salary) + (halfday * per_day_salary * 0.5)

            salary_rows.append({
                "Staff Name": info["name"],
                "Present": present,
                "Half Day": halfday,
                "Absent": absent_count,
                "Salary": salary
            })

        st.dataframe(pd.DataFrame(salary_rows), use_container_width=True)

        # Filters
        st.subheader("🔍 Filter Reports")

        filter_staff = st.selectbox("Filter Staff", ["All", "Mohan", "Ajay", "Prathisha", "Vegadesh"])
        filter_date = st.text_input("Filter Date DD-MM-YYYY", "")

        filtered_att = adf.copy()
        filtered_ser = sdf.copy()

        if filter_staff != "All":
            filtered_att = filtered_att[filtered_att["Staff Name"].astype(str) == filter_staff]
            filtered_ser = filtered_ser[filtered_ser["Staff Name"].astype(str) == filter_staff]

        if filter_date.strip():
            filtered_att = filtered_att[filtered_att["Date"].astype(str) == filter_date.strip()]
            filtered_ser = filtered_ser[filtered_ser["Date"].astype(str) == filter_date.strip()]

        st.subheader("📥 Attendance Report")
        st.dataframe(filtered_att, use_container_width=True)

        st.subheader("🛠️ Service Report")
        st.dataframe(filtered_ser, use_container_width=True)

        # Download
        st.download_button(
            "📥 Download Attendance CSV",
            data=filtered_att.to_csv(index=False).encode("utf-8"),
            file_name="attendance_report.csv",
            mime="text/csv"
        )

        st.download_button(
            "📥 Download Service CSV",
            data=filtered_ser.to_csv(index=False).encode("utf-8"),
            file_name="service_report.csv",
            mime="text/csv"
        )

        # WhatsApp format
        st.subheader("📤 WhatsApp Daily Report Format")

        whatsapp_text = f"""
SELVA MOTORS DAILY REPORT
Date: {today}

Total Bikes: {count_df["Today Bikes"].sum()}
Total Labour: ₹{count_df["Today Labour Amount"].sum()}

Mohan: {rows[0]["Today Bikes"]} bikes | ₹{rows[0]["Today Labour Amount"]}
Ajay: {rows[1]["Today Bikes"]} bikes | ₹{rows[1]["Today Labour Amount"]}
Vegadesh: {rows[2]["Today Bikes"]} bikes | ₹{rows[2]["Today Labour Amount"]}
"""

        st.text_area("Copy WhatsApp Report", whatsapp_text, height=180)
