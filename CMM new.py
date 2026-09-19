import sqlite3
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="BIW Quality & Tooling Intelligence Portal",
    page_icon="⚙️",
    layout="wide",
)

DB_FILE = "biw_quality.db"


# ==============================================================================
# DATABASE SETUP & INITIALIZATION
# ==============================================================================
def get_db_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database tables and seed data if not present."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Jig Correction Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jig_logs (
            Log_ID TEXT PRIMARY KEY,
            Timestamp TEXT,
            Station TEXT,
            Jig_ID TEXT,
            Locator TEXT,
            Axis TEXT,
            Action_Taken TEXT,
            Dimension_mm REAL,
            Engineer_ID TEXT,
            Trial_Number INTEGER,
            Remarks TEXT
        );
    """)

    # 2. Supplier Defect Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_logs (
            Defect_ID TEXT PRIMARY KEY,
            Timestamp TEXT,
            Supplier_Code TEXT,
            Part_Name TEXT,
            Batch_Lot TEXT,
            Deviated_Dimension_mm REAL,
            Tolerance_Limit_mm REAL,
            Defect_Type TEXT,
            Action_Required TEXT,
            Inspector_ID TEXT
        );
    """)

    # 3. Master Mapping Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_mapping (
            CMM_Point TEXT PRIMARY KEY,
            BIW_Area TEXT,
            Station TEXT,
            Jig_ID TEXT,
            Locator TEXT,
            Axis TEXT,
            Tolerance_mm REAL,
            Source_Type TEXT,
            Supplier_Code TEXT,
            Part_Name TEXT
        );
    """)

    # Seed Master Mapping if empty
    cursor.execute("SELECT COUNT(*) FROM master_mapping")
    if cursor.fetchone()[0] == 0:
        seed_mapping = [
            (
                "PMP_UB_01",
                "Underbody",
                "ST-010",
                "JIG-UB-01",
                "MCP-101",
                "X",
                0.5,
                "Supplier Part",
                "SUP-IND-88",
                "Floor Pan Assembly",
            ),
            (
                "PMP_UB_02",
                "Underbody",
                "ST-010",
                "JIG-UB-01",
                "MCS-102",
                "Z",
                0.5,
                "In-House Press",
                "IN-HOUSE",
                "Cross Member",
            ),
            (
                "FD_SIDE_01",
                "Side Structure",
                "ST-030",
                "JIG-SS-02",
                "MCP-301",
                "Y",
                0.7,
                "Supplier Part",
                "SUP-AUTO-12",
                "B-Pillar Reinforcement",
            ),
            (
                "FD_SIDE_02",
                "Side Structure",
                "ST-030",
                "JIG-SS-02",
                "MCS-302",
                "Z",
                0.7,
                "Supplier Part",
                "SUP-AUTO-12",
                "Side Outer Panel",
            ),
        ]
        cursor.executemany(
            "INSERT INTO master_mapping VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            seed_mapping,
        )

    # Seed initial sample Jig Log if empty
    cursor.execute("SELECT COUNT(*) FROM jig_logs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO jig_logs VALUES (
                'JIG-LOG-1001', '2026-09-18 10:30', 'ST-010', 'JIG-UB-01', 'MCS-102', 'Z',
                'Shim Added', 0.5, 'ENG-402', 1, 'Corrected Z-axis sag after CMM PMP score drop.'
            )
        """)

    # Seed initial sample Supplier Log if empty
    cursor.execute("SELECT COUNT(*) FROM supplier_logs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO supplier_logs VALUES (
                'SUP-LOG-5001', '2026-09-18 14:15', 'SUP-IND-88', 'Floor Pan Assembly', 'LOT-202609-A9',
                0.85, 0.35, 'Stamping Spring-back', 'Lot Quarantined / SCAR Issued', 'QC-108'
            )
        """)

    conn.commit()
    conn.close()


# Initialize DB
init_db()


# Helper Functions for Data Read/Write
def load_data(table_name):
    """Loads a full table from SQLite into a Pandas DataFrame."""
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df


def insert_jig_log(log_dict):
    """Inserts a new record into the jig_logs table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO jig_logs (
            Log_ID, Timestamp, Station, Jig_ID, Locator, Axis,
            Action_Taken, Dimension_mm, Engineer_ID, Trial_Number, Remarks
        ) VALUES (:Log_ID, :Timestamp, :Station, :Jig_ID, :Locator, :Axis,
                  :Action_Taken, :Dimension_mm, :Engineer_ID, :Trial_Number, :Remarks)
    """,
        log_dict,
    )
    conn.commit()
    conn.close()


def insert_supplier_log(log_dict):
    """Inserts a new record into the supplier_logs table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO supplier_logs (
            Defect_ID, Timestamp, Supplier_Code, Part_Name, Batch_Lot,
            Deviated_Dimension_mm, Tolerance_Limit_mm, Defect_Type, Action_Required, Inspector_ID
        ) VALUES (:Defect_ID, :Timestamp, :Supplier_Code, :Part_Name, :Batch_Lot,
                  :Deviated_Dimension_mm, :Tolerance_Limit_mm, :Defect_Type, :Action_Required, :Inspector_ID)
    """,
        log_dict,
    )
    conn.commit()
    conn.close()


# Sidebar Navigation
st.sidebar.title("⚙️ BIW Quality System")
st.sidebar.caption("Connected to: `biw_quality.db` (SQLite)")
st.sidebar.markdown("**Target Metrics:** PMP ≥ 97% | FD ≥ 95%")
st.sidebar.divider()

page = st.sidebar.radio(
    "Select Portal Module:",
    [
        "📊 CMM Analytics & Diagnostic Engine",
        "🛠️ Shop-Floor Jig Correction Form",
        "🏭 Supplier Defect Logging Portal",
        "📁 Historical Database Records",
    ],
)

# ==============================================================================
# MODULE 1: CMM ANALYTICS & DIAGNOSTIC ENGINE
# ==============================================================================
if page == "📊 CMM Analytics & Diagnostic Engine":
    st.title("📊 Real-Time CMM Analytics & Diagnostic Engine")
    st.caption(
        "Upload CMM Excel reports to analyze out-of-tolerance points and correlate them with tooling locators and incoming part non-conformances."
    )

    # --- Section A: Live CMM Inspection Report Analyzer ---
    st.subheader("📥 CMM Inspection Report Analyzer")
    uploaded_file = st.file_uploader(
        "Upload CMM Excel File (.xlsx, .xls)", type=["xlsx", "xls"]
    )

    if uploaded_file is not None:
        # Reset file pointer to prevent buffer errors
        uploaded_file.seek(0)

        try:
            # Determine engine based on extension
            if uploaded_file.name.endswith(".xls"):
                df_cmm = pd.read_excel(uploaded_file, engine="xlrd")
            else:
                df_cmm = pd.read_excel(uploaded_file, engine="openpyxl")

            st.success(f"Successfully loaded `{uploaded_file.name}`")

            with st.expander("🔍 Raw CMM Data Preview", expanded=False):
                st.dataframe(df_cmm.head())

            # Standardize column header strings
            df_cmm.columns = [str(col).strip() for col in df_cmm.columns]
            required_cols = ["Feature", "Nominal", "Actual", "USL", "LSL"]

            if all(col in df_cmm.columns for col in required_cols):
                # Coerce numerical columns
                for col in ["Nominal", "Actual", "USL", "LSL"]:
                    df_cmm[col] = pd.to_numeric(df_cmm[col], errors="coerce")

                # Calculate Deviations & Out-of-Tolerance Status
                df_cmm["Dev"] = df_cmm["Actual"] - df_cmm["Nominal"]
                df_cmm["Status"] = np.where(
                    (df_cmm["Actual"] > df_cmm["USL"])
                    | (df_cmm["Actual"] < df_cmm["LSL"]),
                    "OUT OF TOLERANCE",
                    "OK",
                )

                # Performance Metrics
                total_points = len(df_cmm)
                out_of_spec = len(
                    df_cmm[df_cmm["Status"] == "OUT OF TOLERANCE"]
                )
                pass_rate = (
                    ((total_points - out_of_spec) / total_points) * 100
                    if total_points > 0
                    else 0
                )

                m1, m2, m3 = st.columns(3)
                m1.metric("Total Inspection Points", total_points)
                m2.metric(
                    "Out of Tolerance Points",
                    out_of_spec,
                    delta_color="inverse",
                )
                m3.metric("Pass Rate (FD/PMP Score)", f"{pass_rate:.1f}%")

                if out_of_spec > 0:
                    st.warning(
                        f"⚠️ Found {out_of_spec} out-of-tolerance inspection point(s) in uploaded file:"
                    )
                    out_df = df_cmm[df_cmm["Status"] == "OUT OF TOLERANCE"][
                        ["Feature", "Nominal", "Actual", "LSL", "USL", "Dev"]
                    ]
                    st.dataframe(
                        out_df.style.format({
                            "Nominal": "{:.2f}",
                            "Actual": "{:.2f}",
                            "LSL": "{:.2f}",
                            "USL": "{:.2f}",
                            "Dev": "{:+.2f}",
                        }),
                        use_container_width=True,
                    )
                else:
                    st.success(
                        "✅ All uploaded inspection points are within specified tolerances!"
                    )

            else:
                st.info(
                    "💡 **Column Notice:** Standard headers (`Feature`, `Nominal`, `Actual`, `USL`, `LSL`) were not all detected. Preview shown above."
                )

        except Exception as e:
            st.error(f"Error reading Excel file: {e}")

    st.divider()

    # --- Section B: Line Dashboard & Diagnostics ---
    col1, col2, col3 = st.columns(3)
    pmp_score = 94.20
    fd_score = 96.10

    col1.metric(
        "PMP Target Status (Target 97%)",
        f"{pmp_score}%",
        delta="-2.80% (BELOW TARGET)",
        delta_color="inverse",
    )
    col2.metric(
        "FD Target Status (Target 95%)", f"{fd_score}%", delta="+1.10% (PASS)"
    )
    col3.metric(
        "Total Open Deviations",
        "2 Points",
        delta="Requires Action",
        delta_color="off",
    )

    st.subheader(
        "⚠️ Active Out-of-Tolerance CMM Deviations & Diagnostic Actions"
    )

    active_deviations = pd.DataFrame([
        {
            "CMM_Point": "PMP_UB_01",
            "Station": "ST-010",
            "Jig_ID": "JIG-UB-01",
            "Locator": "MCP-101",
            "Axis": "X",
            "Measured_Dev_mm": +0.82,
            "Tolerance_mm": 0.50,
            "Source_Type": "Supplier Part",
            "Supplier_Code": "SUP-IND-88",
            "Part_Name": "Floor Pan Assembly",
            "Diagnostic_Root_Cause": (
                "🔴 SUPPLIER NON-CONFORMANCE: Incoming part stamping spring-back"
                " exceeds receiving limits (+0.70mm)."
            ),
            "Recommended_Action": (
                "Do NOT shim in-house jig. Quarantine lot 'LOT-202609-A9' and"
                " issue SCAR to SUP-IND-88."
            ),
        },
        {
            "CMM_Point": "PMP_UB_02",
            "Station": "ST-010",
            "Jig_ID": "JIG-UB-01",
            "Locator": "MCS-102",
            "Axis": "Z",
            "Measured_Dev_mm": -0.65,
            "Tolerance_mm": 0.50,
            "Source_Type": "In-House Press",
            "Supplier_Code": "IN-HOUSE",
            "Part_Name": "Cross Member",
            "Diagnostic_Root_Cause": (
                "🟡 IN-PROCESS JIG DRIFT: Incoming part is on-spec. Wear or"
                " loose bolts detected on MCS-102 locator surface."
            ),
            "Recommended_Action": (
                "Add 0.65mm shim at MCS-102 locator on JIG-UB-01 (Station"
                " ST-010) in Z-axis."
            ),
        },
    ])

    for idx, row in active_deviations.iterrows():
        with st.expander(
            f"🔴 Point: {row['CMM_Point']} | Station: {row['Station']} | Jig:"
            f" {row['Jig_ID']} | Dev: {row['Measured_Dev_mm']:+.2f} mm"
            f" ({row['Axis']}-Axis)",
            expanded=True,
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Part Name:** {row['Part_Name']}")
                st.write(
                    f"**Source Type:** {row['Source_Type']}"
                    f" ({row['Supplier_Code']})"
                )
                st.write(f"**Target Locator:** {row['Locator']}")
            with c2:
                st.write(
                    f"**Root-Cause Diagnosis:** {row['Diagnostic_Root_Cause']}"
                )
                st.info(f"**Action Plan:** {row['Recommended_Action']}")

# ==============================================================================
# MODULE 2: SHOP-FLOOR JIG CORRECTION FORM
# ==============================================================================
elif page == "🛠️ Shop-Floor Jig Correction Form":
    st.title("🛠️ Shop-Floor Jig & Tooling Correction Form")
    st.caption(
        "Digitize shim adjustments, pin shifts, and locator modifications"
        " performed on the line."
    )

    with st.form("jig_correction_form", clear_on_submit=True):
        st.subheader("Locator & Jig Identification")
        c1, c2, c3 = st.columns(3)

        station = c1.selectbox("Station ID", [
            "ST-010 (Underbody Framing)",
            "ST-020 (Underbody Main)",
            "ST-030 (Side Structure)",
            "ST-040 (Closure/Doors)",
        ])
        jig_id = c2.selectbox(
            "Jig / Fixture ID",
            ["JIG-UB-01", "JIG-UB-02", "JIG-SS-01", "JIG-SS-02", "JIG-CL-01"],
        )
        locator_id = c3.selectbox("Locator / Pin ID", [
            "MCP-101 (Pin)",
            "MCS-102 (Surface)",
            "MCP-301 (Pin)",
            "MCS-302 (Surface)",
            "MCS-501 (Surface)",
        ])

        st.subheader("Correction Details")
        c4, c5, c6 = st.columns(3)

        axis = c4.selectbox(
            "Adjustment Axis",
            ["X-Axis (Fore/Aft)", "Y-Axis (In/Out)", "Z-Axis (Height)"],
        )
        action = c5.selectbox("Correction Action", [
            "Shim Added",
            "Shim Removed",
            "Pin Shifted / Re-aligned",
            "Locator Surface Ground",
            "Bolt Tightened/Torqued",
        ])
        dimension = c6.number_input(
            "Adjustment Value (mm)",
            min_value=-5.0,
            max_value=5.0,
            value=0.5,
            step=0.05,
        )

        c7, c8 = st.columns(2)
        engineer_id = c7.text_input(
            "Maintenance Engineer / Technician ID", value="ENG-"
        )
        trial_num = c8.number_input(
            "Trial Number for this Issue", min_value=1, max_value=10, value=1
        )

        remarks = st.text_area(
            "Correction Remarks / Reason for Adjustment",
            placeholder=(
                "e.g., Added shim to compensate for Z-axis drop following CMM"
                " PMP alert."
            ),
        )

        submitted = st.form_submit_button("💾 Save Jig Correction Log")

        if submitted:
            current_jig_logs = load_data("jig_logs")
            new_log_id = f"JIG-LOG-{1000 + len(current_jig_logs) + 1}"

            new_log = {
                "Log_ID": new_log_id,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Station": station.split()[0],
                "Jig_ID": jig_id,
                "Locator": locator_id.split()[0],
                "Axis": axis[0],
                "Action_Taken": action,
                "Dimension_mm": float(dimension),
                "Engineer_ID": engineer_id,
                "Trial_Number": int(trial_num),
                "Remarks": remarks,
            }

            insert_jig_log(new_log)
            st.success(
                "✅ Saved to SQLite (`biw_quality.db`)! Assigned Log ID:"
                f" {new_log_id}"
            )

# ==============================================================================
# MODULE 3: SUPPLIER DEFECT LOGGING PORTAL
# ==============================================================================
elif page == "🏭 Supplier Defect Logging Portal":
    st.title("🏭 Supplier Part Defect Logging Portal")
    st.caption(
        "Escalate incoming component non-conformances before executing"
        " unnecessary in-house tooling shimming."
    )

    with st.form("supplier_defect_form", clear_on_submit=True):
        st.subheader("Supplier & Part Information")
        c1, c2, c3 = st.columns(3)

        supplier_code = c1.selectbox("Supplier Code & Name", [
            "SUP-IND-88 (Press Parts Ltd)",
            "SUP-AUTO-12 (AutoBody Stampings)",
            "SUP-COMP-05 (Precision Components)",
        ])
        part_name = c2.selectbox("Component / Assembly Name", [
            "Floor Pan Assembly",
            "B-Pillar Reinforcement",
            "Side Outer Panel",
            "Front Wheelhouse",
        ])
        batch_lot = c3.text_input("Batch / Lot Number", value="LOT-202609-")

        st.subheader("Dimensional Non-Conformance Metrics")
        c4, c5, c6 = st.columns(3)

        dev_val = c4.number_input(
            "Measured Deviation from Nominal (mm)",
            min_value=-10.0,
            max_value=10.0,
            value=0.75,
            step=0.05,
        )
        tol_limit = c5.number_input(
            "Supplier Receiving Tolerance Limit (mm)",
            min_value=0.1,
            max_value=2.0,
            value=0.35,
            step=0.05,
        )
        defect_type = c6.selectbox("Defect Category", [
            "Stamping Spring-back",
            "Panel Contour Distortion",
            "Pierced Hole Shift",
            "Burr / Weld Flange Issue",
            "Material Thickness Variation",
        ])

        c7, c8 = st.columns(2)
        action_req = c7.selectbox("Escalation Action Required", [
            "Quarantine Batch & Issue SCAR",
            "Supplier Quality Warning Sent",
            "100% Sorting at Line",
            "Deviated Concession Approval",
        ])
        inspector_id = c8.text_input("Quality Inspector ID", value="QC-")

        submitted_sup = st.form_submit_button("🚨 Submit Supplier Defect Alert")

        if submitted_sup:
            current_sup_logs = load_data("supplier_logs")
            new_defect_id = f"SUP-LOG-{5000 + len(current_sup_logs) + 1}"

            new_sup_log = {
                "Defect_ID": new_defect_id,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Supplier_Code": supplier_code.split()[0],
                "Part_Name": part_name,
                "Batch_Lot": batch_lot,
                "Deviated_Dimension_mm": float(dev_val),
                "Tolerance_Limit_mm": float(tol_limit),
                "Defect_Type": defect_type,
                "Action_Required": action_req,
                "Inspector_ID": inspector_id,
            }

            insert_supplier_log(new_sup_log)
            st.warning(
                "🚨 Saved to SQLite (`biw_quality.db`)! Generated Defect ID:"
                f" {new_defect_id}"
            )

# ==============================================================================
# MODULE 4: HISTORICAL DATABASE RECORDS
# ==============================================================================
elif page == "📁 Historical Database Records":
    st.title("📁 Centralized Historical Quality & Correction Database")
    st.caption(
        "Live query output directly from `biw_quality.db` SQLite database file."
    )

    tab1, tab2, tab3 = st.tabs([
        "🛠️ Jig Correction History",
        "🏭 Supplier Defect Logs",
        "📍 CMM Points Master Mapping",
    ])

    with tab1:
        st.subheader("Shop-Floor Jig Correction History")
        df_jig = load_data("jig_logs")
        st.dataframe(df_jig, use_container_width=True)
        st.caption(f"Total Records: {len(df_jig)}")

    with tab2:
        st.subheader("Supplier Non-Conformance Escalation History")
        df_sup = load_data("supplier_logs")
        st.dataframe(df_sup, use_container_width=True)
        st.caption(f"Total Records: {len(df_sup)}")

    with tab3:
        st.subheader("Master CMM Points to Station/Locator Mapping")
        df_map = load_data("master_mapping")
        st.dataframe(df_map, use_container_width=True)
        if uploaded_file is not None:
            if uploaded_file.seek(0)
    
    try:
        # Check if file is .xls or .xlsx
        if uploaded_file.name.endswith('.xls'):
            df_cmm = pd.read_excel(uploaded_file, engine='xlrd')
        else:
            try:
                df_cmm = pd.read_excel(uploaded_file, engine='openpyxl')
            except ModuleNotFoundError:
                st.error("⚠️ `openpyxl` is missing. Please add `openpyxl` to your requirements.txt file and reboot the app.")
                st.stop()
