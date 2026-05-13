import streamlit as st
import pandas as pd
import gspread
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

sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1lD_M0LUTzXceUV_kc9Q8mEkEt6rs9oXYO-I0Cni0Kfk/edit?usp=drivesdk"
)

try:
    attendance_sheet = sheet.worksheet("Attendance")
except:
    attendance_sheet = sheet.add_worksheet("Attendance", rows="1000", cols="10")

try:
    service_sheet = sheet.worksheet("ServiceReport")
except:
    service_sheet = sheet.add_worksheet("ServiceReport", rows="1000", cols="10")

if attendance_sheet.row_values(1) == []:
    attendance_sheet.append_row([
        "Date", "Time", "Staff ID", "Staff Name", "Role", "Status"
    ])

if service_sheet.row_values(1) == []:
    service_sheet.append_row([
        "Date", "Staff ID", "Staff Name",
        "Bike Name", "Service Type", "Labour Amount"
    ])

staff_users = {
    "Staff1": {"password": "1234", "name": "Mohan"},
    "Staff2": {"password": "1234", "name": "Ajay"},
    "Staff3": {"password": "1234", "name": "Prathisha"},
    "Staff4": {"password": "1234", "name": "Vegadesh"}
}

admin_user = {
    "admin": "admin123"
}

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
                st.rerun()
            else:
                st.error("Invalid Login")

    else:
        staff_id = st.session_state["staff_id"]
        staff_name = st.session_state.get(
            "staff_name",
            staff_users.get(staff_id, {}).get("name", "")
        )

        st.success(f"Hii {staff_name}")

        if st.button("Logout"):
            st.session_state["staff_login"] = False
            st.session_state["staff_id"] = ""
            st.session_state["staff_name"] = ""
            st.rerun()

        st.header("Staff Attendance")

        role = st.selectbox(
            "Role",
            ["Technician", "System Staff"]
        )

        status = st.selectbox(
            "Attendance Status",
            ["Present", "Half Day Leave"]
        )

        if st.button("Mark Attendance"):

            now = datetime.now()

            attendance_sheet.append_row([
                now.strftime("%d-%m-%Y"),
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

            if st.button("Save Service Report"):

                now = datetime.now()

                service_sheet.append_row([
                    now.strftime("%d-%m-%Y"),
                    staff_id,
                    staff_name,
                    bike,
                    service_type,
                    labour
                ])

                st.success("Service Report Saved")

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

        if st.button("Add Today Absent Staff"):

            attendance_data = attendance_sheet.get_all_records()
            attendance_df = pd.DataFrame(attendance_data)

            today_present_ids = []

            if not attendance_df.empty:
                today_df = attendance_df[attendance_df["Date"] == today]
                today_present_ids = today_df["Staff ID"].tolist()

            for sid, info in staff_users.items():
                if sid not in today_present_ids:
                    attendance_sheet.append_row([
                        today,
                        "-",
                        sid,
                        info["name"],
                        "-",
                        "Absent"
                    ])

            st.success("Absent Staff Added Successfully")

        st.header("Overall Attendance Report")

        attendance_data = attendance_sheet.get_all_records()
        attendance_df = pd.DataFrame(attendance_data)

        st.dataframe(attendance_df, use_container_width=True)

        st.header("Service Report")

        service_data = service_sheet.get_all_records()
        service_df = pd.DataFrame(service_data)

        st.dataframe(service_df, use_container_width=True)

        st.header("Staff Wise Total Labour Amount")

        if not service_df.empty:
            if "Labour Amount" not in service_df.columns:
                st.error("ServiceReport sheet-la 'Labour Amount' column missing. First row header correct pannunga.")
                st.stop()
                
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
