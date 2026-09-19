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
            irvs_score REAL,
            status TEXT,
            recommendation TEXT
        )
    """)
    conn.commit()
    conn.close()

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

# --- PROPRIETARY INSTITUTIONAL RISK ENGINE ---
def compute_institutional_metrics(purchase_price, selling_price, current_stock, recent_sales, analysis_period, capital_cost_apr=0.25):
    # Base variables
    tied_capital = current_stock * purchase_price
    daily_sales_velocity = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales_velocity if daily_sales_velocity > 0 else 999
    
    margin_amt = selling_price - purchase_price
    gross_margin_pct = (margin_amt / selling_price * 100) if selling_price > 0 else 0
    
    # Capital Carrying Cost Decay Model (Compounded APR)
    daily_rate = capital_cost_apr / 365
    carrying_cost_exposure = tied_capital * (((1 + daily_rate)**min(days_of_stock, 365)) - 1)

    # Multi-variable Inventory Risk Velocity Score (0-100)
    velocity_risk = min(100.0, (days_of_stock / 180.0) * 100.0)
    margin_risk = max(0.0, 100.0 - gross_margin_pct) if gross_margin_pct > 0 else 100.0
    irvs_score = round((0.65 * velocity_risk) + (0.35 * margin_risk), 1)

    # Strategy Formulations
    breakeven_clearance = purchase_price * 1.02  # 2% recovery buffer
    half_stock_units = int(current_stock / 2)

    if selling_price < purchase_price:
        status = "🔴 CRITICAL: NEGATIVE MARGIN DRAIN"
        impact_analysis = (
            f"You are currently losing ₦{abs(margin_amt):,.2f} on every single unit sold. "
            f"Across your remaining stock of {current_stock:,} units, this product will bleed "
            f"₦{(abs(margin_amt) * current_stock):,.2f} directly out of your working capital."
        )
        opt_conservative = f"Immediate Repricing: Increase retail price to at least ₦{(purchase_price * 1.15):,.2f} to cover unit cost and secure a 15% baseline operating margin."
        opt_aggressive = f"Supplier Dispute / Return: Halt all active sales immediately and request a supplier credit exchange due to cost-of-goods distortion."
        opt_creative = f"Loss-Leader Bundling: Pair 1 unit of this item with a high-margin (>50%) fast-moving product to mask a re-adjusted bundle price."

    elif irvs_score >= 70 or days_of_stock > 90:
        status = "🔴 CAPITAL TRAP (SEVERE OVERSTOCK)"
        impact_analysis = (
            f"You have ₦{tied_capital:,.2f} in cash completely frozen in this product line. "
            f"At your current sales velocity ({daily_sales_velocity:.1f} units/day), it will take roughly "
            f"{int(days_of_stock)} days to sell out naturally. Over that time, storage fees, degradation, "
            f"and inflation will erase an estimated ₦{carrying_cost_exposure:,.2f} in business capital."
        )
        opt_conservative = f"Targeted Clearance Sale: Discount the unit price to ₦{breakeven_clearance:,.2f} (2% above cost) to recover ₦{(breakeven_clearance * current_stock):,.2f} in liquid cash within 14 days."
        opt_aggressive = f"Bulk Offloading (B2B): Sell {half_stock_units:,} units (50% of stock) at wholesale cost (₦{purchase_price:,.2f}/unit) to regional distributors to immediately recover ₦{(half_stock_units * purchase_price):,.2f}."
        opt_creative = f"2-for-1 Value Bundling: Launch a 'Buy 1, Get 1 at 50% Off' campaign. This clears inventory twice as fast while preserving positive net transaction margins."

    elif irvs_score >= 40:
        status = "🟡 MODERATE RISK (VELOCITY SLOWDOWN)"
        impact_analysis = (
            f"Your inventory is moving slower than optimal cycles, with roughly {int(days_of_stock)} days of stock remaining. "
            f"While not currently losing cash, this stock is locking up ₦{tied_capital:,.2f} that could be reinvested into faster-moving merchandise."
        )
        opt_conservative = "Freeze Purchase Orders: Do not issue new POs for this item until stock coverage drops below 25 days."
        opt_aggressive = "Promotional Incentive: Offer a temporary 10% flash discount or free delivery to accelerate daily sales velocity."
        opt_creative = "Checkout Cross-Selling: Feature this item as a recommended checkout add-on for online orders exceeding ₦50,000."

    else:
        status = "🟢 HEALTHY CAPITAL EFFICIENCY"
        impact_analysis = (
            f"This product is operating at optimal parameters with a healthy {gross_margin_pct:.1f}% profit margin "
            f"and a manageable ~{int(days_of_stock)} days of supply on hand."
        )
        opt_conservative = "Maintain Standard Cycles: Continue standard reorder intervals based on historical demand."
        opt_aggressive = "Volume Negotiation: Request a 5% bulk purchase discount from your supplier on the next order batch."
        opt_creative = "VIP Early Access: Feature this item in exclusive pre-launch promotions for high-value repeat customers."

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

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="LossGuard Intelligence", page_icon="🛡️", layout="wide")

if "client_id" not in st.session_state:
    st.session_state.client_id = None

# LANDING & WORKSPACE SELECTION
if not st.session_state.client_id:
    st.title("🛡️ Welcome to LossGuard")
    st.write("Institutional Inventory Risk Engine & Capital Recovery Portal.")
    
    user_input = st.text_input("Enter Store Name or Business Email:", placeholder="e.g. Lagos Auto Hub or merchant@domain.com")
    if st.button("Access Workspace"):
        if user_input.strip():
            st.session_state.client_id = user_input.strip().lower()
            st.rerun()
        else:
            st.error("Please enter a valid store identifier to proceed.")
    st.stop()

# SIDEBAR NAVIGATION
st.sidebar.title("🛡️ LossGuard Control")
st.sidebar.write(f"Active Workspace: **{st.session_state.client_id}**")
if st.sidebar.button("Switch Store / Exit"):
    st.session_state.client_id = None
    st.rerun()

st.title("🛡️ LossGuard Risk & Liquidation Engine")

tab1, tab2, tab3 = st.tabs(["🔍 Single Product Audit", "📊 CSV Batch Audit", "📜 Historical Audit Stream"])

# TAB 1: SINGLE ITEM AUDIT
with tab1:
    st.subheader("Single Item Financial Risk Assessment")
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Product Name", "Engine Oil 5L")
        purchase_price = st.number_input("Purchase Price (₦)", min_value=0.0, value=25000.0)
        selling_price = st.number_input("Selling Price (₦)", min_value=0.0, value=30000.0)
    with col2:
        current_stock = st.number_input("Current Stock (Units)", min_value=0, value=120)
        recent_sales = st.number_input("Recent Sales (Units)", min_value=0, value=15)
        analysis_period = st.number_input("Analysis Period (Days)", min_value=1, value=30)

    if st.button("Run Financial Audit"):
        res = compute_institutional_metrics(purchase_price, selling_price, current_stock, recent_sales, analysis_period)
        save_audit(
            st.session_state.client_id, p_name, res["tied_capital"], res["days_of_stock"], 
            res["margin_pct"], res["irvs_score"], res["status"], res["opt_conservative"]
        )
        
        st.success("Financial Risk & Liquidation Assessment Complete")
        st.write("---")
        
        # KEY METRICS DASHBOARD
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("💰 Cash Locked in Stock", f"₦{res['tied_capital']:,.2f}")
        col_b.metric("⚠️ Risk Velocity Score", f"{res['irvs_score']} / 100")
        col_c.metric("💸 Projected Holding Loss", f"₦{res['carrying_cost']:,.2f}")
        
        st.write("---")
        
        # STATUS CLASSIFICATION BADGE
        if "🔴" in res["status"]: 
            st.error(f"**Classification:** {res['status']}")
        elif "🟡" in res["status"]: 
            st.warning(f"**Classification:** {res['status']}")
        else: 
            st.success(f"**Classification:** {res['status']}")
            
        # DETAILED FINANCIAL IMPACT
        st.subheader("📊 Financial & Operational Impact")
        st.write(f"• **Stock Run-out Projection:** ~{int(res['days_of_stock'])} days remaining based on recent sales speed.")
        st.write(f"• **Gross Margin:** {res['margin_pct']:.1f}% per unit.")
        st.info(res["impact_analysis"])
        
        # MULTI-OPTION STRATEGIC ROADMAP
        st.subheader("💡 Strategic Capital Recovery Roadmap")
        st.write("Select the liquidation or optimization strategy that best suits your store's operational goals:")
        
        with st.expander("🛡️ **Option 1: Conservative Strategy (Protect Unit Margins)**", expanded=True):
            st.write(res["opt_conservative"])
            
        with st.expander("⚡ **Option 2: Aggressive Strategy (Fast Cash Recovery)**", expanded=True):
            st.write(res["opt_aggressive"])
            
        with st.expander("🎨 **Option 3: Creative Strategy (Volume & Bundling)**", expanded=True):
            st.write(res["opt_creative"])

# TAB 2: BATCH CSV AUDIT
with tab2:
    st.subheader("Batch Inventory CSV Audit")
    st.caption("Required headers: Product, Purchase_Price, Selling_Price, Current_Stock, Recent_Sales, Analysis_Period")
    uploaded_file = st.file_uploader("Upload Store Inventory CSV File", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            req_cols = ['Product', 'Purchase_Price', 'Selling_Price', 'Current_Stock', 'Recent_Sales', 'Analysis_Period']
            
            if all(c in df.columns for c in req_cols):
                results = []
                for _, row in df.iterrows():
                    res = compute_institutional_metrics(
                        row['Purchase_Price'], row['Selling_Price'], 
                        row['Current_Stock'], row['Recent_Sales'], row['Analysis_Period']
                    )
                    save_audit(
                        st.session_state.client_id, row['Product'], res['tied_capital'], res['days_of_stock'], 
                        res['margin_pct'], res['irvs_score'], res['status'], res['opt_conservative']
                    )
                    results.append(res)
                
                res_df = pd.DataFrame(results)
                df['Status'] = res_df['status']
                df['IRVS_Score'] = res_df['irvs_score']
                df['Tied_Capital_NGN'] = res_df['tied_capital']
                df['Holding_Decay_NGN'] = res_df['carrying_cost']
                df['Action_Plan'] = res_df['opt_conservative']
                
                st.write("### Executive Audit Summary")
                st.dataframe(df[['Product', 'Status', 'IRVS_Score', 'Tied_Capital_NGN', 'Holding_Decay_NGN', 'Action_Plan']], use_container_width=True)
                
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Audit Report (CSV)", csv_data, "lossguard_executive_audit.csv", "text/csv")
            else:
                st.error(f"CSV column mismatch. Required headers are: {', '.join(req_cols)}")
        except Exception as e:
            st.error(f"Processing error: {e}")

# TAB 3: AUDIT LOGS
with tab3:
    st.subheader(f"Historical Audit Stream for {st.session_state.client_id}")
    history_df = get_client_audits(st.session_state.client_id)
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
        csv_history = history_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Audit Stream (CSV)", csv_history, "audit_history.csv", "text/csv")
    else:
        st.info("No recorded logs found in this workspace. Run a single product or CSV audit to populate history.")
    
