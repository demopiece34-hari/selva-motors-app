import streamlit as st
import pandas as pd
import gspread
import time
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Selva Motors Attendance", layout="wide")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

@st.cache_resource
def connect_sheet():

    for i in range(3):

        try:
            client = gspread.authorize(creds)

            sheet = client.open_by_key(
                st.secrets["SHEET_ID"]
            )

            return sheet

        except Exception as e:

            time.sleep(2)

    st.error("Google Sheet connection failed")
    st.stop()

sheet = connect_sheet()

def get_sheet(sheet_name):
    return sheet.worksheet(sheet_name)

def safe_df(ws, columns):
    data = ws.get_all_records()
    df = pd.DataFrame(data)

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    return df

attendance_sheet = get_sheet("Attendance")

service_sheet = get_sheet("ServiceReport")

request_sheet = get_sheet("AttendanceRequests")

mohan_service_sheet = get_sheet("Mohan_Service")

ajay_service_sheet = get_sheet("Ajay_Service")

vegadesh_service_sheet = get_sheet("Vegadesh_Service")

staff_users = {
    "Staff1": {"password": "1234", "name": "Mohan", "role": "Technician"},
    "Staff2": {"password": "1234", "name": "Ajay", "role": "Technician"},
    "Staff3": {"password": "1234", "name": "Prathisha", "role": "System Staff"},
    "Staff4": {"password": "1234", "name": "Vegadesh", "role": "Technician"}
}

admin_user = {
    "admin": "admin123"
}

technician_sheets = {
    "Mohan": mohan_service_sheet,
    "Ajay": ajay_service_sheet,
    "Vegadesh": vegadesh_service_sheet
}

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
        (df["Request Status"].astype(str) == "Pending")
    ).any()


def is_request_approved(today, staff_id):
    df = safe_df(request_sheet, ["Date", "Staff ID", "Request Status"])

    return (
        (df["Date"].astype(str) == today) &
        (df["Staff ID"].astype(str) == staff_id) &
        (df["Request Status"].astype(str) == "Approved")
    ).any()
    
st.title("SELVA MOTORS STAFF MANAGEMENT")

menu = st.sidebar.selectbox(
    "Select Login",
    ["Staff Login", "Admin Login"]
)

# ======================================================
# STAFF LOGIN
# ======================================================

if menu == "Staff Login":

    st.subheader("Staff Login")

    if not st.session_state.get("staff_login"):

        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")

        if st.button("Login"):

            if user_id in staff_users and staff_users[user_id]["password"] == password:
                st.session_state["staff_login"] = True
                st.session_state["staff_id"] = user_id
                st.session_state["staff_name"] = staff_users[user_id]["name"]
                st.session_state["staff_role"] = staff_users[user_id]["role"]
                st.rerun()
            else:
                st.error("Invalid Login")

    else:
        staff_id = st.session_state["staff_id"]

        staff_name = st.session_state.get(
            "staff_name",
            staff_users.get(staff_id, {}).get("name", "")
        )

        role = st.session_state.get(
            "staff_role",
            staff_users.get(staff_id, {}).get("role", "")
        )

        st.success(f"Hii {staff_name}")
        st.info(f"Role: {role}")

        if st.button("Logout"):
            st.session_state["staff_login"] = False
            st.session_state["staff_id"] = ""
            st.session_state["staff_name"] = ""
            st.session_state["staff_role"] = ""
            st.rerun()

        st.header("Staff Attendance")

        today = datetime.now().strftime("%d-%m-%Y")

        absent_block = is_absent_today(today, staff_id)
        approved = is_request_approved(today, staff_id)

        if absent_block and not approved:

            st.error("You are marked absent today. Send request to admin.")

            if is_request_pending(today, staff_id):
                st.info("Request already sent. Waiting for admin approval.")
            else:
                if st.button("Send Attendance Request"):
                    request_sheet.append_row([
                        today,
                        staff_id,
                        staff_name,
                        role,
                        "Pending"
                    ])
                    st.success("Request sent to admin")
                    st.rerun()

        else:

            status = st.selectbox(
                "Attendance Status",
                ["Present", "Half Day Leave"]
            )

            if st.button("Mark Attendance"):

                now = datetime.now()

                attendance_df = safe_df(
                    attendance_sheet,
                    ["Date", "Staff ID", "Status"]
                )

                already_marked = (
                    (attendance_df["Date"].astype(str) == today) &
                    (attendance_df["Staff ID"].astype(str) == staff_id) &
                    (attendance_df["Status"].astype(str) != "Absent")
                ).any()

                if already_marked:
                    st.warning("Today attendance already marked")
                else:
                    attendance_sheet.append_row([
                        today,
                        now.strftime("%H:%M:%S"),
                        staff_id,
                        staff_name,
                        role,
                        status
                    ])

                    st.success("Attendance Saved")

        st.header("Daily Service Entry")

        if role == "Technician":

            bike = st.selectbox(
                "Bike Name",
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
                "Service Type",
                ["Paid", "FSC", "General"]
            )

            labour = st.number_input(
                "Labour Amount",
                min_value=0
            )

            if "service_lock" not in st.session_state:
                st.session_state["service_lock"] = False

            if st.session_state["service_lock"]:
                st.warning("Please wait 3 seconds...")
                time.sleep(3)
                st.session_state["service_lock"] = False
                st.rerun()

            if st.button("Save Service Report", disabled=st.session_state["service_lock"]):

                st.session_state["service_lock"] = True

                now = datetime.now()
                today = now.strftime("%d-%m-%Y")

                row_data = [
                    today,
                    staff_id,
                    staff_name,
                    bike,
                    service_type,
                    labour
                ]

                service_sheet.append_row(row_data)

                if staff_name in technician_sheets:
                    technician_sheets[staff_name].append_row(row_data)

                st.success("Service Report Saved")
                st.rerun()

        else:
            st.info("System Staff ku service entry illa")

# ======================================================
# ADMIN LOGIN
# ======================================================

if menu == "Admin Login":

    st.subheader("Admin Login")

    admin_id = st.text_input("Admin User ID")
    admin_pass = st.text_input("Admin Password", type="password")

    if st.button("Admin Login"):

        if admin_id in admin_user and admin_user[admin_id] == admin_pass:
            st.session_state["admin_login"] = True
            st.success("Admin Login Successful")
        else:
            st.error("Invalid Admin Login")

    if st.session_state.get("admin_login"):

        st.header("Admin Dashboard")

        today = datetime.now().strftime("%d-%m-%Y")

        st.header("Mark Particular Staff Absent")

        selected_absent_staff = st.selectbox(
            "Select Staff",
            [
                "Mohan",
                "Ajay",
                "Prathisha",
                "Vegadesh"
            ]
        )

        staff_map = {
            "Mohan": "Staff1",
            "Ajay": "Staff2",
            "Prathisha": "Staff3",
            "Vegadesh": "Staff4"
        }

        if st.button("Mark Selected Staff Absent"):

            sid = staff_map[selected_absent_staff]

            info = staff_users[sid]

            attendance_data = attendance_sheet.get_all_records()
            attendance_df = pd.DataFrame(attendance_data)

            already_exists = False

            if not attendance_df.empty:

                if "Date" in attendance_df.columns and "Staff ID" in attendance_df.columns:

                    already_exists = (
                        (attendance_df["Date"].astype(str) == today) &
                        (attendance_df["Staff ID"].astype(str) == sid)
                    ).any()

            if already_exists:

                st.warning("Attendance already marked for today")

            else:

                attendance_sheet.append_row([
                    today,
                    "-",
                    sid,
                    info["name"],
                    info["role"],
                    "Absent"
                ])
  
                st.success(f"{selected_absent_staff} marked absent")

        st.header("Attendance Requests")

        request_data = request_sheet.get_all_records()
        request_df = pd.DataFrame(request_data)

        if not request_df.empty:

            for i, row in request_df.iterrows():

                if row.get("Date") == today and row.get("Request Status") == "Pending":

                    st.write(
                        f"{row.get('Staff Name')} attendance request"
                    )

                    if st.button(
                        f"Approve {row.get('Staff Name')}",
                        key=f"approve_{i}"
                    ):

                        request_sheet.update_cell(i + 2, 5, "Approved")

                        st.success("Attendance Approved")

                        st.rerun()

        st.header("Overall Service Report")

        service_data = service_sheet.get_all_records()
        service_df = pd.DataFrame(service_data)

        st.dataframe(service_df, use_container_width=True)

        st.header("Technician Wise Service Report")

        selected_technician = st.selectbox(
            "Select Technician",
            ["Mohan", "Ajay", "Vegadesh"]
        )

        tech_sheet = technician_sheets[selected_technician]
        tech_data = tech_sheet.get_all_records()
        tech_df = pd.DataFrame(tech_data)

        st.subheader(f"{selected_technician} Service Entries")
        st.dataframe(tech_df, use_container_width=True)

        if not tech_df.empty and "Labour Amount" in tech_df.columns:
            tech_df["Labour Amount"] = pd.to_numeric(
                tech_df["Labour Amount"],
                errors="coerce"
            ).fillna(0)

            tech_total = tech_df["Labour Amount"].sum()
            st.success(f"{selected_technician} Total Labour Amount: ₹{tech_total}")

        st.header("Staff Wise Total Labour Amount")

        if not service_df.empty and "Labour Amount" in service_df.columns:

            service_df["Labour Amount"] = pd.to_numeric(
                service_df["Labour Amount"],
                errors="coerce"
            ).fillna(0)

            total_df = service_df.groupby(
                ["Staff ID", "Staff Name"],
                as_index=False
            )["Labour Amount"].sum()

            st.dataframe(total_df, use_container_width=True)

            grand_total = service_df["Labour Amount"].sum()
            st.subheader(f"Overall Total Labour Amount: ₹{grand_total}")

        else:
            st.info("No service data available")
