import streamlit as st
import pandas as pd
import sqlite3
import hmac
import hashlib
from datetime import datetime

# ==========================================
# 1. DATABASE MANAGEMENT & PERSISTENCE
# ==========================================
DB_NAME = "lossguard.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Audit history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            client_id TEXT,
            product_name TEXT,
            tied_capital REAL,
            days_of_stock REAL,
            margin_percent REAL,
            irvs_score REAL,
            status TEXT,
            recommendation TEXT
        )
    """)
    
    # Moniepoint live transaction ledger
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moniepoint_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            client_id TEXT,
            transaction_ref TEXT,
            product_name TEXT,
            units_sold INTEGER,
            amount_paid REAL
        )
    """)
    conn.commit()
    conn.close()

def record_moniepoint_transaction(client_id, tx_ref, product_name, units_sold, amount_paid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO moniepoint_transactions (client_id, transaction_ref, product_name, units_sold, amount_paid)
        VALUES (?, ?, ?, ?, ?)
    """, (client_id, tx_ref, product_name, units_sold, amount_paid))
    conn.commit()
    conn.close()

def get_moniepoint_sales_summary(client_id, product_name, days_window=30):
    conn = sqlite3.connect(DB_NAME)
    query = """
        SELECT SUM(units_sold) as total_units 
        FROM moniepoint_transactions 
        WHERE client_id = ? AND product_name = ? 
        AND timestamp >= datetime('now', '-' || ? || ' days')
    """
    df = pd.read_sql_query(query, conn, params=(client_id, product_name, days_window))
    conn.close()
    units = df['total_units'].iloc[0]
    return int(units) if units and not pd.isna(units) else 0

def save_audit(client_id, product_name, tied_capital, days_of_stock, margin_percent, irvs_score, status, recommendation):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_history 
        (client_id, product_name, tied_capital, days_of_stock, margin_percent, irvs_score, status, recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (client_id, product_name, tied_capital, days_of_stock, margin_percent, irvs_score, status, recommendation))
    conn.commit()
    conn.close()

def get_client_audits(client_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        "SELECT timestamp, product_name, tied_capital, days_of_stock, margin_percent, irvs_score, status, recommendation FROM audit_history WHERE client_id = ? ORDER BY timestamp DESC", 
        conn, params=(client_id,)
    )
    conn.close()
    return df

init_db()

# ==========================================
# 2. PROPRIETARY RISK & STRATEGY ENGINE
# ==========================================
def compute_institutional_metrics(purchase_price, selling_price, current_stock, recent_sales, analysis_period, capital_cost_apr=0.25):
    tied_capital = current_stock * purchase_price
    daily_sales_velocity = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales_velocity if daily_sales_velocity > 0 else 999
    
    margin_amt = selling_price - purchase_price
    gross_margin_pct = (margin_amt / selling_price * 100) if selling_price > 0 else 0
    
    daily_rate = capital_cost_apr / 365
    carrying_cost_exposure = tied_capital * (((1 + daily_rate)**min(days_of_stock, 365)) - 1)

    velocity_risk = min(100.0, (days_of_stock / 180.0) * 100.0)
    margin_risk = max(0.0, 100.0 - gross_margin_pct) if gross_margin_pct > 0 else 100.0
    irvs_score = round((0.65 * velocity_risk) + (0.35 * margin_risk), 1)

    breakeven_clearance = purchase_price * 1.02
    half_stock_units = int(current_stock / 2)

    if selling_price < purchase_price:
        status = "🔴 CRITICAL: NEGATIVE MARGIN DRAIN"
        impact_analysis = (
            f"Hello! 👋 We detected a major profitability issue here. You are currently losing **₦{abs(margin_amt):,.2f}** on every unit sold. "
            f"Across your full stock of **{current_stock:,} units**, this item will drain **₦{(abs(margin_amt) * current_stock):,.2f}** directly from your store cash flow. "
            f"This requires an immediate pricing review to protect your business."
        )
        opt_conservative = f"**Option 1: Margin Protection Price Increase**\n\n• **Action:** Adjust retail selling price to **₦{(purchase_price * 1.15):,.2f}** minimum.\n• **Why:** Reclaims cost of goods and guarantees a healthy 15% profit margin on each sale."
        opt_aggressive = f"**Option 2: Immediate Supplier Dispute / Exchange**\n\n• **Action:** Freeze active sales immediately and request a credit note or stock replacement from your supplier.\n• **Why:** Stops ongoing capital loss caused by cost price distortions."
        opt_creative = f"**Option 3: Loss-Leader Bundle Strategy**\n\n• **Action:** Pair 1 unit with a fast-moving, high-margin product (>50% margin).\n• **Why:** Disguises the necessary price adjustment within an attractive value bundle while maintaining overall store profitability."

    elif irvs_score >= 70 or days_of_stock > 90:
        status = "🔴 CAPITAL TRAP (SEVERE OVERSTOCK)"
        impact_analysis = (
            f"Welcome to your risk breakdown! 👋 You currently have **₦{tied_capital:,.2f}** in cash locked up in this product line. "
            f"At your current sales rate (**{daily_sales_velocity:.1f} units per day**), it will take about **{int(days_of_stock)} days** to sell out naturally. "
            f"Holding this inventory for so long will cause storage fees, inflation, and opportunity costs to eat away **₦{carrying_cost_exposure:,.2f}** of your capital."
        )
        opt_conservative = f"**Option 1: Controlled Clearance Promotion**\n\n• **Target Price:** **₦{breakeven_clearance:,.2f}** per unit (2% above cost price).\n• **Cash Recovery:** Recovers **₦{(breakeven_clearance * current_stock):,.2f}** in liquid cash within 14 days.\n• **Why:** Safely liquidates slow stock without taking a net loss."
        opt_aggressive = f"**Option 2: Wholesale B2B Cash Offload**\n\n• **Target Volume:** Sell **{half_stock_units:,} units** (50% of stock) at cost price (**₦{purchase_price:,.2f}/unit**).\n• **Cash Recovery:** Unlocks **₦{(half_stock_units * purchase_price):,.2f}** instantly.\n• **Why:** Provides immediate cash to buy faster-moving inventory."
        opt_creative = f"**Option 3: Buy 1, Get 1 at 50% Off Bundle**\n\n• **Target Structure:** Offer a 'Buy 1, Get 1 at Half Price' deal.\n• **Why:** Effectively sells 2 units at **₦{(selling_price * 1.5):,.2f}**, doubling sales speed while preserving positive margins."

    elif irvs_score >= 40:
        status = "🟡 MODERATE RISK (VELOCITY SLOWDOWN)"
        impact_analysis = (
            f"Hi there! 👋 Your inventory velocity is running slightly slower than optimal cycles, with **~{int(days_of_stock)} days of stock** remaining. "
            f"While you are making profit on sales, you have **₦{tied_capital:,.2f}** tied up that could be earning faster returns elsewhere."
        )
        opt_conservative = "**Option 1: Pause Purchase Orders**\n\n• **Action:** Freeze new stock replenishment until remaining coverage drops below 25 days.\n• **Why:** Allows existing stock to clear naturally before committing fresh cash."
        opt_aggressive = "**Option 2: Flash Promotion Boost**\n\n• **Action:** Launch a temporary 10% discount or offer free delivery.\n• **Why:** Re-engages buyers and accelerates daily turnover."
        opt_creative = "**Option 3: Checkout Add-On Feature**\n\n• **Action:** Offer this item as a recommended add-on for customer purchases over ₦50,000.\n• **Why:** Boosts average basket sizes without requiring broad discount campaigns."

    else:
        status = "🟢 HEALTHY CAPITAL EFFICIENCY"
        impact_analysis = (
            f"Great news! 🎉 This product line is performing brilliantly with a solid **{gross_margin_pct:.1f}% profit margin** "
            f"and a healthy inventory buffer of **~{int(days_of_stock)} days of supply**."
        )
        opt_conservative = "**Option 1: Maintain Order Schedules**\n\n• **Action:** Continue standard reorder routines based on steady customer demand."
        opt_aggressive = "**Option 2: Bulk Purchase Discount Negotiation**\n\n• **Action:** Leverage your high sales speed to ask your supplier for a 5% volume discount on the next batch."
        opt_creative = "**Option 3: VIP Loyalty Pre-Access**\n\n• **Action:** Offer early stock access and exclusive bundles to top repeat buyers."

    return {
        "tied_capital": tied_capital,
        "days_of_stock": days_of_stock,
        "margin_pct": gross_margin_pct,
        "irvs_score": irvs_score,
        "carrying_cost": carrying_cost_exposure,
        "status": status,
        "impact_analysis": impact_analysis,
        "opt_conservative": opt_conservative,
        "opt_aggressive": opt_aggressive,
        "opt_creative": opt_creative
    }

# ==========================================
# 3. STREAMLIT USER INTERFACE & CONTROLS
# ==========================================
st.set_page_config(page_title="LossGuard + Moniepoint Core", page_icon="🛡️", layout="wide")

if "client_id" not in st.session_state:
    st.session_state.client_id = None

# LANDING PAGE
if not st.session_state.client_id:
    st.title("🛡️ Welcome to LossGuard")
    st.write("Institutional Financial Risk Engine, Moniepoint POS Integration & Theft Detection Hub.")
    
    user_input = st.text_input("Enter Merchant ID or Store Name:", placeholder="e.g. lagos_auto_hub")
    if st.button("Access Store Workspace"):
        if user_input.strip():
            st.session_state.client_id = user_input.strip().lower()
            st.rerun()
        else:
            st.error("Please enter a valid store identifier to proceed.")
    st.stop()

# SIDEBAR
st.sidebar.title("🛡️ LossGuard Navigation")
st.sidebar.write(f"Active Store Workspace: **{st.session_state.client_id}**")
st.sidebar.success("⚡ Moniepoint POS Bridge: ACTIVE")

if st.sidebar.button("Switch Store / Logout"):
    st.session_state.client_id = None
    st.rerun()

st.title("🛡️ LossGuard Intelligent Business Protection")

tab1, tab2, tab3, tab4 = st.tabs([
    "💳 Live Moniepoint POS Audit", 
    "🕵️ Theft & Logbook Auditor", 
    "🔄 Moniepoint Webhook Terminal", 
    "📜 Historical Audit Stream"
])

# TAB 1: DETAILED & FRIENDLY PRODUCT AUDIT
with tab1:
    st.subheader("🔍 Single Product Financial Risk Audit")
    st.caption("Auto-syncs sales counts with Moniepoint POS transaction logs.")
    
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Product Name", "Engine Oil 5L")
        purchase_price = st.number_input("Unit Cost Price (₦)", min_value=0.0, value=25000.0)
        selling_price = st.number_input("Retail Selling Price (₦)", min_value=0.0, value=30000.0)
    with col2:
        current_stock = st.number_input("Current Warehouse Stock (Units)", min_value=0, value=120)
        analysis_period = st.number_input("Analysis Window (Days)", min_value=1, value=30)

    moniepoint_sales = get_moniepoint_sales_summary(st.session_state.client_id, p_name, days_window=analysis_period)
    
    st.info(f"⚡ **Moniepoint POS Sync:** Recorded **{moniepoint_sales} units sold** via POS over the last {analysis_period} days.")

    if st.button("Run Comprehensive Risk Audit"):
        res = compute_institutional_metrics(purchase_price, selling_price, current_stock, moniepoint_sales, analysis_period)
        save_audit(
            st.session_state.client_id, p_name, res["tied_capital"], res["days_of_stock"], 
            res["margin_pct"], res["irvs_score"], res["status"], res["opt_conservative"]
        )
        
        st.success("✅ Audit Complete! Here is your detailed financial health report:")
        st.write("---")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("💰 Cash Locked in Inventory", f"₦{res['tied_capital']:,.2f}")
        col_b.metric("⚠️ Risk Velocity Score", f"{res['irvs_score']} / 100")
        col_c.metric("💸 Projected Carrying Loss", f"₦{res['carrying_cost']:,.2f}")
        
        st.write("---")
        
        if "🔴" in res["status"]: 
            st.error(f"**Classification Status:** {res['status']}")
        elif "🟡" in res["status"]: 
            st.warning(f"**Classification Status:** {res['status']}")
        else: 
            st.success(f"**Classification Status:** {res['status']}")
            
        st.subheader("📊 Plain-English Financial Breakdown")
        st.write(f"• **Estimated Days of Supply Remaining:** ~{int(res['days_of_stock'])} days (based on active Moniepoint sales velocity).")
        st.write(f"• **Gross Profit Margin:** {res['margin_pct']:.1f}% per unit.")
        st.info(res["impact_analysis"])
        
        st.subheader("💡 Strategic Action Plan & Recovery Options")
        st.write("Explore these custom recovery paths designed to optimize your capital and protect cash flow:")
        
        with st.expander("🛡️ **Option 1: Conservative Strategy (Protect Margin & Unit Profit)**", expanded=True):
            st.markdown(res["opt_conservative"])
            
        with st.expander("⚡ **Option 2: Aggressive Strategy (Rapid Cash Liquidation)**", expanded=True):
            st.markdown(res["opt_aggressive"])
            
        with st.expander("🎨 **Option 3: Creative Strategy (Smart Bundling & Volume)**", expanded=True):
            st.markdown(res["opt_creative"])

# TAB 2: LOGBOOK ANALYSIS & THEFT DETECTION ENGINE
with tab2:
    st.subheader("🕵️ Daily Logbook Audit & Theft Detection Engine")
    st.write(
        "Upload your store's daily sales logbook (CSV or Excel) to compare staff sales logs against expected inventory levels "
        "and payment records. LossGuard will instantly scan for unauthorized discounts, missing stock, and payment discrepancies."
    )
    
    st.caption("Expected file columns: `Date`, `Product`, `Expected_Price`, `Sold_Price`, `Units_Logged`, `POS_Recorded_Units`")
    
    uploaded_logbook = st.file_uploader("Upload Daily Store Logbook", type=["csv", "xlsx"])
    
    if uploaded_logbook is not None:
        try:
            if uploaded_logbook.name.endswith(".csv"):
                log_df = pd.read_csv(uploaded_logbook)
            else:
                log_df = pd.read_excel(uploaded_logbook)
                
            req_log_cols = ['Date', 'Product', 'Expected_Price', 'Sold_Price', 'Units_Logged', 'POS_Recorded_Units']
            
            if all(col in log_df.columns for col in req_log_cols):
                # Calculations for discrepancies
                log_df['Price_Discrepancy'] = log_df['Expected_Price'] - log_df['Sold_Price']
                log_df['Stock_Shrinkage_Units'] = log_df['Units_Logged'] - log_df['POS_Recorded_Units']
                log_df['Estimated_Theft_Loss_NGN'] = (log_df['Price_Discrepancy'] * log_df['Units_Logged']) + (log_df['Stock_Shrinkage_Units'] * log_df['Expected_Price'])
                
                flagged_records = log_df[log_df['Estimated_Theft_Loss_NGN'] > 0]
                total_loss = log_df['Estimated_Theft_Loss_NGN'].sum()
                
                st.write("---")
                st.subheader("🚨 Theft & Discrepancy Findings Summary")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("🚩 Total Flagged Incidents", f"{len(flagged_records)} Days / Transactions")
                c2.metric("💸 Total Estimated Financial Loss", f"₦{total_loss:,.2f}")
                c3.metric("📦 Unaccounted Stock Shrinkage", f"{log_df['Stock_Shrinkage_Units'].sum():,} Units")
                
                st.write("---")
                
                if total_loss > 0:
                    st.error(f"⚠️ **Alert:** LossGuard detected **₦{total_loss:,.2f}** in financial losses across your logbook entries.")
                    st.write("### Flagged Transactions Requiring Investigation")
                    st.dataframe(flagged_records[['Date', 'Product', 'Expected_Price', 'Sold_Price', 'Units_Logged', 'POS_Recorded_Units', 'Estimated_Theft_Loss_NGN']], use_container_width=True)
                else:
                    st.success("🎉 **No Discrepancies Found!** All recorded prices and inventory counts match expected baseline figures.")
                    
                st.write("### Complete Analyzed Logbook Ledger")
                st.dataframe(log_df, use_container_width=True)
                
                csv_report = log_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Discrepancy Report (CSV)", csv_report, "lossguard_theft_audit.csv", "text/csv")
                
            else:
                st.error(f"File formatting error. Please make sure your logbook includes these exact headers: {', '.join(req_log_cols)}")
        except Exception as e:
            st.error(f"Error analyzing logbook file: {e}")
            
    st.write("---")
    st.write("### 📝 Download Sample Logbook Template")
    st.write("Need a template to test? Copy this structure or generate a quick CSV:")
    
    sample_data = pd.DataFrame({
        "Date": ["2026-03-01", "2026-03-02", "2026-03-03"],
        "Product": ["Engine Oil 5L", "Brake Pads", "Car Battery"],
        "Expected_Price": [30000, 15000, 65000],
        "Sold_Price": [30000, 12000, 65000], # Price discrepancy on Brake Pads
        "Units_Logged": [10, 5, 2],
        "POS_Recorded_Units": [10, 5, 1] # Shrinkage discrepancy on Car Battery
    })
    
    st.dataframe(sample_data, use_container_width=True)
    sample_csv = sample_data.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Sample Logbook Template", sample_csv, "sample_store_logbook.csv", "text/csv")

# TAB 3: MONIEPOINT WEBHOOK TESTER
with tab3:
    st.subheader("Moniepoint Transaction Event Bridge")
    st.caption("Simulate real-time POS transaction pushes directly from Moniepoint terminals to LossGuard.")
    
    col1, col2 = st.columns(2)
    with col1:
        tx_ref = st.text_input("Moniepoint Transaction Ref", f"MP-TX-{int(datetime.now().timestamp())}")
        tx_product = st.text_input("Product Item Sold", "Engine Oil 5L")
    with col2:
        tx_units = st.number_input("Units Purchased", min_value=1, value=5)
        tx_price = st.number_input("Total Amount Settlement (₦)", min_value=0.0, value=150000.0)

    if st.button("Simulate Incoming Moniepoint Webhook"):
        record_moniepoint_transaction(st.session_state.client_id, tx_ref, tx_product, tx_units, tx_price)
        st.success(f"Transaction `{tx_ref}` received and stored! LossGuard velocity updated in real time.")

    st.write("### Recorded Moniepoint Transactions")
    conn = sqlite3.connect(DB_NAME)
    tx_df = pd.read_sql_query(
        "SELECT timestamp, transaction_ref, product_name, units_sold, amount_paid FROM moniepoint_transactions WHERE client_id = ? ORDER BY timestamp DESC", 
        conn, params=(st.session_state.client_id,)
    )
    conn.close()
    
    if not tx_df.empty:
        st.dataframe(tx_df, use_container_width=True)
    else:
        st.info("No Moniepoint transactions logged yet.")

# TAB 4: HISTORICAL AUDIT STREAM
with tab4:
    st.subheader(f"Historical Audit Stream for {st.session_state.client_id}")
    history_df = get_client_audits(st.session_state.client_id)
    if not history_df.empty:
        st.dataframe(history_df, use_co
