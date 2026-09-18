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

def save_audit(product_name, tied_capital, days_of_stock, margin_percent, status, recommendation):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_history 
        (product_name, tied_capital, days_of_stock, margin_percent, status, recommendation)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (product_name, tied_capital, days_of_stock, margin_percent, status, recommendation))
    conn.commit()
    conn.close()

def get_audits():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM audit_history ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# Initialize database
init_db()

# --- ENHANCED RISK ENGINE ---
def analyze_inventory_item(purchase_price, selling_price, current_stock, recent_sales, analysis_period):
    tied_capital = current_stock * purchase_price
    daily_sales = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales if daily_sales > 0 else 999
    margin = ((selling_price - purchase_price) / selling_price * 100) if selling_price > 0 else 0

    # Decision Matrix
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

# --- STREAMLIT UI ---
st.set_page_config(page_title="LossGuard v0.2", page_icon="🛡️", layout="wide")
st.title("🛡️ LossGuard Intelligence Engine")

tab1, tab2, tab3 = st.tabs(["🔍 Single Product Audit", "📊 CSV Batch Audit", "📜 Saved Audit Logs"])

# TAB 1: SINGLE PRODUCT AUDIT
with tab1:
    st.subheader("Manual Inventory Risk Assessment")
    
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Product Name", "Engine Oil 5L")
        purchase_price = st.number_input("Purchase Price (₦)", min_value=0.0, value=25000.0)
        selling_price = st.number_input("Selling Price (₦)", min_value=0.0, value=30000.0)
    with col2:
        current_stock = st.number_input("Current Stock (Units)", min_value=0, value=120)
        recent_sales = st.number_input("Recent Sales (Units)", min_value=0, value=15)
        analysis_period = st.number_input("Analysis Period (Days)", min_value=1, value=30)

    if st.button("Run Audit & Log Result"):
        result = analyze_inventory_item(purchase_price, selling_price, current_stock, recent_sales, analysis_period)
        
        save_audit(p_name, result["tied_capital"], result["days_of_stock"], result["margin"], result["status"], result["action"])
        st.success(f"Audit logged to SQLite database!")

        st.metric("Tied Capital", f"₦{result['tied_capital']:,.2f}")
        
        if "🔴" in result["status"]:
            st.error(f"Status: {result['status']}")
        elif "🟡" in result["status"]:
            st.warning(f"Status: {result['status']}")
        else:
            st.success(f"Status: {result['status']}")
            
        st.write(f"**Stock Coverage:** ~{int(result['days_of_stock'])} days remaining")
        st.write(f"**Margin:** {result['margin']:.1f}%")
        st.write(f"**Action Plan:** {result['action']}")

# TAB 2: BATCH CSV AUDIT
with tab2:
    st.subheader("Batch CSV Inventory Audit")
    uploaded_file = st.file_uploader("Upload Store CSV", type=["csv"])

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
                    save_audit(row['Product'], res['tied_capital'], res['days_of_stock'], res['margin'], res['status'], res['action'])
                    results.append(res)
                
                res_df = pd.DataFrame(results)
                df['Status'] = res_df['status']
                df['Tied_Capital'] = res_df['tied_capital']
                df['Days_Of_Stock'] = res_df['days_of_stock']
                df['Margin_%'] = res_df['margin']
                
                st.write("### Batch Analysis Output")
                st.dataframe(df[['Product', 'Status', 'Tied_Capital', 'Days_Of_Stock', 'Margin_%']], use_container_width=True)
                st.success("All items from CSV saved to database.")
            else:
                st.error(f"CSV must contain headers: {', '.join(req_cols)}")
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

# TAB 3: SAVED AUDIT LOGS
with tab3:
    st.subheader("Persistent SQLite Audit Records")
    audits_df = get_audits()
    if not audits_df.empty:
        st.dataframe(audits_df, use_container_width=True)
    else:
        st.info("No audit records found in SQLite database yet.")
                   
