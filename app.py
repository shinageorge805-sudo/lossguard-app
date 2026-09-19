    if st.button("Run Financial Audit"):
        res = compute_institutional_metrics(purchase_price, selling_price, current_stock, recent_sales, analysis_period)
        save_audit(
            st.session_state.client_id, p_name, res["tied_capital"], res["days_of_stock"], 
            res["margin_pct"], res["irvs_score"], res["status"], res["opt_conservative"]
        )
        
        st.success("Financial Risk & Liquidation Assessment Complete")
        st.write("---")
        
        # TOP METRIC DASHBOARD
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("💰 Cash Locked in Stock", f"₦{res['tied_capital']:,.2f}")
        col_b.metric("⚠️ Risk Velocity Score", f"{res['irvs_score']} / 100")
        col_c.metric("💸 Projected Holding Loss", f"₦{res['carrying_cost']:,.2f}")
        
        st.write("---")
        
        # STATUS BADGE
        if "🔴" in res["status"]: 
            st.error(f"**Classification:** {res['status']}")
        elif "🟡" in res["status"]: 
            st.warning(f"**Classification:** {res['status']}")
        else: 
            st.success(f"**Classification:** {res['status']}")
            
        # SECTION 1: DETAILED FINANCIAL IMPACT
        st.subheader("📊 Financial & Operational Impact")
        st.write(f"• **Stock Run-out Projection:** ~{int(res['days_of_stock'])} days remaining based on recent velocity.")
        st.write(f"• **Unit Profitability:** {res['margin_pct']:.1f}% gross margin.")
        
        st.info(res["impact_analysis"])
        
        # SECTION 2: MULTI-TIERED ACTION PLAN
        st.subheader("💡 Strategic Capital Recovery Roadmap")
        st.write("Choose the liquidation or optimization strategy that best aligns with your business goals:")
        
        with st.expander("🛡️ **Option 1: Conservative Strategy (Protect Margins)**", expanded=True):
            st.markdown(res["opt_conservative"])
            
        with st.expander("⚡ **Option 2: Aggressive Strategy (Fast Cash Recovery)**", expanded=True):
            st.markdown(res["opt_aggressive"])
            
        with st.expander("🎨 **Option 3: Creative Strategy (Volume & Bundling)**", expanded=True):
            st.markdown(res["opt_creative"])
                                              def compute_institutional_metrics(purchase_price, selling_price, current_stock, recent_sales, analysis_period, capital_cost_apr=0.25):
    # Core calculations
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
    bundle_target_price = (purchase_price * 2) * 1.05  # Bundle 2 units with minor margin

    if selling_price < purchase_price:
        status = "🔴 CRITICAL: NEGATIVE MARGIN DRAIN"
        impact_analysis = (
            f"You are currently losing ₦{abs(margin_amt):,.2f} on every single unit sold. "
            f"Across your remaining stock of {current_stock:,} units, this product will bleed "
            f"₦{(abs(margin_amt) * current_stock):,.2f} directly out of your working capital."
        )
        opt_conservative = f"**Immediate Repricing:** Raise the price to at least ₦{(purchase_price * 1.15):,.2f} to secure a baseline 15% operating margin."
        opt_aggressive = f"**Supplier Return / Exchange:** Halt all sales immediately and request a supplier return or credit exchange based on cost-of-goods distortion."
        opt_creative = f"**Loss-Leader Bundling:** Pair 1 unit of this item with a high-margin (>50%) fast-moving product to mask a re-adjusted bundle price."

    elif irvs_score >= 70 or days_of_stock > 90:
        status = "🔴 CAPITAL TRAP (SEVERE OVERSTOCK)"
        impact_analysis = (
            f"You have **₦{tied_capital:,.2f}** in cash completely frozen in this product line. "
            f"At your current speed of sales ({daily_sales_velocity:.1f} units/day), it will take roughly "
            f"**{int(days_of_stock)} days** to liquidate this inventory naturally. Over that time, storage costs, "
            f"capital inflation, and opportunity cost will erase **₦{carrying_cost_exposure:,.2f}** in store value."
        )
        opt_conservative = f"**Targeted Clearance Sale:** Discount the unit price to **₦{breakeven_clearance:,.2f}** (2% above cost) to recover **₦{(breakeven_clearance * current_stock):,.2f}** in liquid cash within 14 days."
        opt_aggressive = f"**Bulk Liquidation / B2B Offloading:** Offer {half_stock_units:,} units (50% of stock) at wholesale cost (₦{purchase_price:,.2f}/unit) to rival merchants or regional distributors to immediately unlock ₦{(half_stock_units * purchase_price):,.2f}."
        opt_creative = f"**2-for-1 Value Bundles:** Create a 'Buy One, Get One at 50% Off' campaign. This effectively sells 2 units at ₦{(selling_price * 1.5):,.2f}, clearing inventory twice as fast while keeping cash flow positive."

    elif irvs_score >= 40:
        status = "🟡 MODERATE RISK (VELOCITY SLOWDOWN)"
        impact_analysis = (
            f"Your inventory is moving slower than optimal cycles, with roughly **{int(days_of_stock)} days** of stock remaining. "
            f"While not currently losing cash, this stock is tying up **₦{tied_capital:,.2f}** that could be reinvested into faster-moving merchandise."
        )
        opt_conservative = f"**Freeze Purchase Orders:** Do not issue new POs for this item until stock coverage drops below 25 days."
        opt_aggressive = f"**Promotional Push:** Offer a temporary 10% discount or add free delivery to boost daily sales velocity."
        opt_creative = f"**Cross-Selling Incentive:** Recommend this item as a checkout add-on for orders exceeding ₦50,000."

    else:
        status = "🟢 HEALTHY CAPITAL EFFICIENCY"
        impact_analysis = (
            f"This product is operating at optimal parameters with a healthy **{gross_margin_pct:.1f}% profit margin** "
            f"and a manageable **~{int(days_of_stock)} days** of supply."
        )
        opt_conservative = "**Maintain Standard Cycles:** Continue standard reorder intervals based on historical demand."
        opt_aggressive = "**Volume Expansion:** Negotiate a 5% bulk purchase discount from your supplier on the next purchase order."
        opt_creative = "**VIP Early Access:** Feature this product in exclusive promotions for high-value repeat buyers."

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
    # Base calculations
    tied_capital = current_stock * purchase_price
    daily_sales_velocity = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales_velocity if daily_sales_velocity > 0 else 999
    
    margin_amt = selling_price - purchase_price
    gross_margin_pct = (margin_amt / selling_price * 100) if selling_price > 0 else 0
    
    # 1. Capital Carrying Cost Decay Model
    daily_rate = capital_cost_apr / 365
    carrying_cost_exposure = tied_capital * (((1 + daily_rate)**min(days_of_stock, 365)) - 1)

    # 2. Inventory Risk Velocity Score (IRVS) [0 to 100 Multi-Variable Index]
    velocity_risk = min(100.0, (days_of_stock / 180.0) * 100.0)
    margin_risk = max(0.0, 100.0 - gross_margin_pct) if gross_margin_pct > 0 else 100.0
    irvs_score = round((0.65 * velocity_risk) + (0.35 * margin_risk), 1)

    # 3. Dynamic Decision Matrix
    if selling_price < purchase_price:
        status = "🔴 CRITICAL: NEGATIVE MARGIN"
        rec = f"Net unit loss of ₦{abs(margin_amt):,.2f}. Reprice item above baseline cost of ₦{purchase_price:,.2f} immediately."
    elif irvs_score >= 70 or days_of_stock > 90:
        status = "🔴 CAPITAL TRAP"
        breakeven_clearance = purchase_price * 1.02  # 2% recovery margin threshold
        rec = f"Critical risk score ({irvs_score}/100). Holding decay exposure: ₦{carrying_cost_exposure:,.2f}. Target clearance price: ₦{breakeven_clearance:,.2f} to recover capital."
    elif irvs_score >= 40:
        status = "🟡 MODERATE RISK"
        rec = f"Sales velocity decay detected (Score: {irvs_score}/100). Delay pending purchase orders until stock coverage drops below 30 days."
    else:
        status = "🟢 HEALTHY TURNOVER"
        rec = f"Optimal working capital score ({irvs_score}/100). Stock turnover aligns with normal reorder parameters."

    return {
        "tied_capital": tied_capital,
        "days_of_stock": days_of_stock,
        "margin_pct": gross_margin_pct,
        "irvs_score": irvs_score,
        "carrying_cost": carrying_cost_exposure,
        "status": status,
        "recommendation": rec
    }

# --- APPLICATION USER INTERFACE ---
st.set_page_config(page_title="LossGuard Intelligence", page_icon="🛡️", layout="wide")

if "client_id" not in st.session_state:
    st.session_state.client_id = None

# CLIENT LOGIN SCREEN
if not st.session_state.client_id:
    st.title("🛡️ Welcome to LossGuard")
    st.write("Institutional Inventory Risk Analytics & Capital Recovery Engine.")
    
    user_input = st.text_input("Enter Store Name or Business Email:", placeholder="e.g. Lagos Auto Hub or store@domain.com")
    if st.button("Launch Analytics Workspace"):
        if user_input.strip():
            st.session_state.client_id = user_input.strip().lower()
            st.rerun()
        else:
            st.error("Please enter a business identifier to access your workspace.")
    st.stop()

# WORKSPACE SIDEBAR
st.sidebar.title("🛡️ LossGuard Control")
st.sidebar.write(f"Active Workspace: **{st.session_state.client_id}**")
if st.sidebar.button("Switch Store / Log Out"):
    st.session_state.client_id = None
    st.rerun()

st.title("🛡️ LossGuard Inventory Risk Engine")

tab1, tab2, tab3 = st.tabs(["🔍 Single Product Audit", "📊 CSV Batch Audit", "📜 Executive Audit History"])

# TAB 1: SINGLE PRODUCT AUDIT
with tab1:
    st.subheader("Single Item Risk Model")
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
            res["margin_pct"], res["irvs_score"], res["status"], res["recommendation"]
        )
        
        st.success("Financial assessment complete and recorded.")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Tied Capital Exposure", f"₦{res['tied_capital']:,.2f}")
        col_b.metric("Inventory Risk Score (IRVS)", f"{res['irvs_score']} / 100")
        col_c.metric("Carrying Cost Erosion", f"₦{res['carrying_cost']:,.2f}")
        
        if "🔴" in res["status"]: st.error(f"Status: {res['status']}")
        elif "🟡" in res["status"]: st.warning(f"Status: {res['status']}")
        else: st.success(f"Status: {res['status']}")
            
        st.write(f"**Stock Coverage:** ~{int(res['days_of_stock'])} days remaining")
        st.write(f"**Gross Margin:** {res['margin_pct']:.1f}%")
        st.write(f"**Recommended Action:** {res['recommendation']}")

# TAB 2: BATCH CSV AUDIT
with tab2:
    st.subheader("Batch Inventory CSV Audit")
    st.caption("Required headers: Product, Purchase_Price, Selling_Price, Current_Stock, Recent_Sales, Analysis_Period")
    uploaded_file = st.file_uploader("Upload Store Inventory CSV", type=["csv"])

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
                        res['margin_pct'], res['irvs_score'], res['status'], res['recommendation']
                    )
                    results.append(res)
                
                res_df = pd.DataFrame(results)
                df['Status'] = res_df['status']
                df['IRVS_Score'] = res_df['irvs_score']
                df['Tied_Capital_NGN'] = res_df['tied_capital']
                df['Holding_Decay_NGN'] = res_df['carrying_cost']
                df['Action_Plan'] = res_df['recommendation']
                
                st.write("### Institutional Audit Output")
                st.dataframe(df[['Product', 'Status', 'IRVS_Score', 'Tied_Capital_NGN', 'Holding_Decay_NGN', 'Action_Plan']], use_container_width=True)
                
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Audit Report (CSV)", csv_data, "lossguard_executive_audit.csv", "text/csv")
            else:
                st.error(f"CSV format mismatch. Required headers: {', '.join(req_cols)}")
        except Exception as e:
            st.error(f"Processing error: {e}")

# TAB 3: AUDIT HISTORY
with tab3:
    st.subheader(f"Historical Audit Stream for {st.session_state.client_id}")
    history_df = get_client_audits(st.session_state.client_id)
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
        csv_history = history_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download History (CSV)", csv_history, "audit_history.csv", "text/csv")
    else:
        st.info("No recorded logs in this workspace yet. Run a single or CSV audit to populate history.")
    import streamlit as st
import pandas as pd
import numpy as np

# --- INSTITUTIONAL RISK ENGINE ---
def compute_institutional_metrics(purchase_price, selling_price, current_stock, recent_sales, analysis_period, capital_cost_apr=0.25):
    # 1. Base Variables
    tied_capital = current_stock * purchase_price
    daily_sales_velocity = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales_velocity if daily_sales_velocity > 0 else 999
    
    margin_amt = selling_price - purchase_price
    gross_margin_pct = (margin_amt / selling_price * 100) if selling_price > 0 else 0
    
    # 2. Capital Decay (Compound Carrying Cost Risk)
    daily_rate = capital_cost_apr / 365
    carrying_cost_exposure = tied_capital * ((1 + daily_rate)**days_of_stock - 1)
    net_realizable_capital = tied_capital - carrying_cost_exposure

    # 3. Dynamic Risk Score (0 - 100 Scale)
    velocity_risk = min(100, (days_of_stock / 180.0) * 100)
    margin_risk = max(0, 100 - gross_margin_pct) if gross_margin_pct > 0 else 100
    irvs_score = round((0.65 * velocity_risk) + (0.35 * margin_risk), 1)

    # 4. Status Matrix & Strategic Liquidation Recommendation
    if selling_price < purchase_price:
        status = "🔴 CRITICAL: NEGATIVE MARGIN"
        rec = f"Selling at a net loss of ₦{abs(margin_amt):,.2f}/unit. Reprice item above ₦{purchase_price:,.2f} immediately."
    elif irvs_score >= 70 or days_of_stock > 90:
        breakeven_clearance = purchase_price * 1.02  # 2% recovery margin
        rec = f"Capital Trap (Score: {irvs_score}/100). Projected carrying cost erosion: ₦{carrying_cost_exposure:,.2f}. Execute liquidation bundle at target price: ₦{breakeven_clearance:,.2f} to recover liquidity."
    elif irvs_score >= 40:
        rec = f"Moderate Velocity Decay (Score: {irvs_score}/100). Freeze pending purchase orders. Monitor sales velocity over next 14 days."
    else:
        rec = f"Optimal Capital Efficiency (Score: {irvs_score}/100). Stock turnover aligns with healthy working capital cycles."

    return {
        "tied_capital": tied_capital,
        "days_of_stock": days_of_stock,
        "margin_pct": gross_margin_pct,
        "irvs_score": irvs_score,
        "carrying_cost": carrying_cost_exposure,
        "net_realizable": net_realizable_capital,
        "recommendation": rec
    }
    
