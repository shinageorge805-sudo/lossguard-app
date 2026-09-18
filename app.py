import streamlit as st
import pandas as pd
import sqlite3

# --- DATABASE SETUP ---
DB_NAME = "lossguard.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            client_id TEXT,
            product_name TEXT,
            tied_capital REAL,
            days_of_stock REAL,
            margin_percent REAL,
            status TEXT,
            recommendation TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_audit(client_id, product_name, tied_capital, days_of_stock, margin_percent, status, recommendation):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_history 
        (client_id, product_name, tied_capital, days_of_stock, margin_percent, status, recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (client_id, product_name, tied_capital, days_of_stock, margin_percent, status, recommendation))
    conn.commit()
    conn.close()

def get_client_audits(client_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT timestamp, product_name, tied_capital, days_of_stock, margin_percent, status, recommendation FROM audit_history WHERE client_id = ? ORDER BY timestamp DESC", 
        conn, params=(client_id,)
    )
    conn.close()
    return df

init_db()

# --- ANALYSIS ENGINE ---
def analyze_inventory_item(purchase_price, selling_price, current_stock, recent_sales, analysis_period):
    tied_capital = current_stock * purchase_price
    daily_sales = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales if daily_sales > 0 else 999
    margin = ((selling_price - purchase_price) / selling_price * 100) if selling_price > 0 else 0

    if selling_price < purchase_price:
        status = "🔴 SEVERE LOSS"
        action = "Stop sales immediately. Item is priced below cost."
    elif days_of_stock > 60:
        status = "🔴 CAPITAL TRAP"
        action = "Freeze reorders. Liquidate excess stock with bundle discounts."
    elif days_of_stock > 30 or margin < 15:
        status = "🟡 WATCH"
        action = "Monitor velocity. Delay planned POs until stock drops."
    else:
        status = "🟢 NORMAL"
        action = "Healthy inventory performance. Maintain standard reorder cycle."

    return {
        "tied_capital": tied_capital,
        "days_of_stock": days_of_stock,
        "margin": margin,
        "status": status,
        "action": action
    }

# --- PAGE CONFIG & SESSION ---
st.set_page_config(page_title="LossGuard Public Beta", page_icon="🛡️", layout="wide")

if "client_id" not in st.session_state:
    st.session_state.client_id = None

# --- CLIENT PORTAL LANDING SCREEN ---
if not st.session_state.client_id:
    st.title("🛡️ Welcome to LossGuard")
    st.write("Free Inventory Intelligence & Capital Trap Detector for Retailers & E-commerce Stores.")
    
    st.subheader("Start Your Audit Session")
    user_input = st.text_input("Enter your Store Name or Business Email to start:", placeholder="e.g. Lagos Auto Parts or store@domain.com")
    
    if st.button("Launch Inventory Workspace"):
        if user_input.strip():
            st.session_state.client_id = user_input.strip().lower()
            st.rerun()
        else:
            st.error("Please enter a valid store name or email to continue.")
    st.stop()

# --- MAIN CLIENT WORKSPACE ---
st.sidebar.title("🛡️ LossGuard Workspace")
st.sidebar.write(f"Logged in as: **{st.session_state.client_id}**")
if st.sidebar.button("Switch Store / Exit"):
    st.session_state.client_id = None
    st.rerun()

st.title("🛡️ LossGuard Inventory Engine")

tab1, tab2, tab3 = st.tabs(["🔍 Single Product Audit", "📊 CSV Batch Audit", "📜 My Audit History"])

# TAB 1: SINGLE ITEM
with tab1:
    st.subheader("Manual Item Assessment")
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Product Name", "Engine Oil 5L")
        purchase_price = st.number_input("Purchase Price (₦)", min_value=0.0, value=25000.0)
        selling_price = st.number_input("Selling Price (₦)", min_value=0.0, value=30000.0)
    with col2:
        current_stock = st.number_input("Current Stock (Units)", min_value=0, value=120)
        recent_sales = st.number_input("Recent Sales (Units)", min_value=0, value=15)
        analysis_period = st.number_input("Analysis Period (Days)", min_value=1, value=30)

    if st.button("Run Audit"):
        res = analyze_inventory_item(purchase_price, selling_price, current_stock, recent_sales, analysis_period)
        save_audit(st.session_state.client_id, p_name, res["tied_capital"], res["days_of_stock"], res["margin"], res["status"], res["action"])
        
        st.success("Audit complete and saved to your history!")
        st.metric("Tied Capital", f"₦{res['tied_capital']:,.2f}")
        
        if "🔴" in res["status"]: st.error(f"Status: {res['status']}")
        elif "🟡" in res["status"]: st.warning(f"Status: {res['status']}")
        else: st.success(f"Status: {res['status']}")
            
        st.write(f"**Stock Coverage:** ~{int(res['days_of_stock'])} days remaining")
        st.write(f"**Margin:** {res['margin']:.1f}%")
        st.write(f"**Recommended Action:** {res['action']}")

# TAB 2: BATCH CSV
with tab2:
    st.subheader("Upload Store Inventory CSV")
    st.caption("Required CSV columns: Product, Purchase_Price, Selling_Price, Current_Stock, Recent_Sales, Analysis_Period")
    uploaded_file = st.file_uploader("Choose CSV File", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            req_cols = ['Product', 'Purchase_Price', 'Selling_Price', 'Current_Stock', 'Recent_Sales', 'Analysis_Period']
            
            if all(c in df.columns for c in req_cols):
                results = []
                for _, row in df.iterrows():
                    res = analyze_inventory_item(
                        row['Purchase_Price'], row['Selling_Price'], 
                        row['Current_Stock'], row['Recent_Sales'], row['Analysis_Period']
                    )
                    save_audit(st.session_state.client_id, row['Product'], res['tied_capital'], res['days_of_stock'], res['margin'], res['status'], res['action'])
                    results.append(res)
                
                res_df = pd.DataFrame(results)
                df['Status'] = res_df['status']
                df['Tied_Capital (₦)'] = res_df['tied_capital']
                df['Days_Of_Stock'] = res_df['days_of_stock']
                df['Action_Plan'] = res_df['action']
                
                st.write("### Batch Analysis Results")
                st.dataframe(df[['Product', 'Status', 'Tied_Capital (₦)', 'Days_Of_Stock', 'Action_Plan']], use_container_width=True)
                
                # Allow CSV Export
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Audit Report (CSV)", csv_data, "lossguard_audit_report.csv", "text/csv")
            else:
                st.error(f"CSV format invalid. Please ensure columns match: {', '.join(req_cols)}")
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

# TAB 3: CLIENT HISTORY
with tab3:
    st.subheader(f"Audit History for {st.session_state.client_id}")
    history_df = get_client_audits(st.session_state.client_id)
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
        csv_history = history_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export History to CSV", csv_history, "audit_history.csv", "text/csv")
    else:
        st.info("No saved audits found for your workspace. Run a single product or CSV batch audit to get started.")
