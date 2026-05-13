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
    attendance_sheet = sheet.add_worksheet(
        title="Attendance",
        rows="1000",
        cols="10"
    )
    attendance_sheet.append_row([
        "Date", "Time", "Staff ID",
        "Staff Name", "Role", "Phone"
    ])

try:
    service_sheet = sheet.worksheet("ServiceReport")
except:
    service_sheet = sheet.add_worksheet(
        title="ServiceReport",
        rows="1000",
        cols="10"
    )
    service_sheet.append_row([
        "Date", "Staff ID", "Staff Name",
        "Bike Name", "Service Type", "Labour Amount"
    ])

# ---------------- LOGIN DATA ----------------

staff_users = {
    "staff1": "1234",
    "staff2": "1234",
    "staff3": "1234",
    "staff4": "1234"
}

admin_user = {
    "admin": "admin123"
}

# ---------------- TITLE ----------------

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

    user_id = st.text_input("User ID")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if user_id in staff_users and staff_users[user_id] == password:

            st.success("Login Successful")

            st.session_state["staff_login"] = True
            st.session_state["staff_id"] = user_id

        else:
            st.error("Invalid Login")

    # ---------------- STAFF PANEL ----------------

    if st.session_state.get("staff_login"):

        st.header("Staff Attendance")

        name = st.text_input("Staff Name")

        role = st.selectbox(
            "Role",
            ["Technician", "System Staff"]
        )

        phone = st.text_input("Phone Number")

        if st.button("Mark Attendance"):

            now = datetime.now()

            attendance_sheet.append_row([
                now.strftime("%d-%m-%Y"),
                now.strftime("%H:%M:%S"),
                st.session_state["staff_id"],
                name,
                role,
                phone
            ])

            st.success("Attendance Saved")

        # ======================================================
        # SERVICE ENTRY
        # ======================================================

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
                    "Super Splendor"
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
                    st.session_state["staff_id"],
                    name,
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
    admin_pass = st.text_input(
        "Admin Password",
        type="password"
    )

    if st.button("Admin Login"):

        if admin_id in admin_user and admin_user[admin_id] == admin_pass:

            st.session_state["admin_login"] = True

            st.success("Admin Login Successful")

        else:
            st.error("Invalid Admin Login")

    # ---------------- ADMIN PANEL ----------------

    if st.session_state.get("admin_login"):

        st.header("Overall Attendance Report")

        attendance_data = attendance_sheet.get_all_records()
        attendance_df = pd.DataFrame(attendance_data)

        st.dataframe(attendance_df, use_container_width=True)

        st.header("Monthly Service Report")

        service_data = service_sheet.get_all_records()
        service_df = pd.DataFrame(service_data)

        st.dataframe(service_df, use_container_width=True)
