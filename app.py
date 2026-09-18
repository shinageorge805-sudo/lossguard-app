import streamlit as st
import pandas as pd

st.set_page_config(page_title="LossGuard v0.1", page_icon="🛡️", layout="wide")

st.title("🛡️ LossGuard v0.1 Engine")
st.subheader("Inventory Capital Trap & Profit Leakage Detector")

tab1, tab2 = st.tabs(["📊 CSV Inventory Batch Audit", "🔍 Single Product Audit"])

# --- TAB 1: CSV FILE AUDIT ---
with tab1:
    st.write("Upload a store inventory CSV file to audit all items instantly.")
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = ['Product', 'Purchase_Price', 'Selling_Price', 'Current_Stock', 'Recent_Sales', 'Analysis_Period']
            
            if all(col in df.columns for col in required_cols):
                df['Tied_Capital'] = df['Current_Stock'] * df['Purchase_Price']
                df['Daily_Sales'] = df['Recent_Sales'] / df['Analysis_Period']
                df['Days_Of_Stock'] = df['Current_Stock'] / df['Daily_Sales']
                df['Gross_Margin_%'] = ((df['Selling_Price'] - df['Purchase_Price']) / df['Selling_Price']) * 100

                def evaluate_status(row):
                    if row['Days_Of_Stock'] > 60 or row['Selling_Price'] < row['Purchase_Price']:
                        return "🔴 POTENTIAL LOSS"
                    elif row['Days_Of_Stock'] > 30 or row['Gross_Margin_%'] < 15:
                        return "🟡 WATCH"
                    else:
                        return "🟢 NORMAL"

                df['Status'] = df.apply(evaluate_status, axis=1)

                trapped_df = df[df['Status'] == "🔴 POTENTIAL LOSS"]
                total_trapped_cash = trapped_df['Tied_Capital'].sum()
                total_inventory_value = df['Tied_Capital'].sum()

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Inventory Value", f"₦{total_inventory_value:,.2f}")
                col2.metric("Trapped Capital at Risk", f"₦{total_trapped_cash:,.2f}")
                col3.metric("High Risk Items Count", f"{len(trapped_df)} items")

                st.divider()
                st.write("### Full Inventory Risk Audit Table")
                st.dataframe(df[['Product', 'Status', 'Tied_Capital', 'Days_Of_Stock', 'Gross_Margin_%']], use_container_width=True)
            else:
                st.error(f"Invalid CSV structure. Required columns: {', '.join(required_cols)}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

# --- TAB 2: SINGLE PRODUCT MANUAL AUDIT ---
with tab2:
    st.sidebar.header("Manual Inputs")
    p_name = st.text_input("Product Name", "Sample Product")
    purchase_price = st.sidebar.number_input("Purchase Price (₦)", min_value=0.0, value=2000.0)
    selling_price = st.sidebar.number_input("Selling Price (₦)", min_value=0.0, value=3000.0)
    current_stock = st.sidebar.number_input("Current Stock (Units)", min_value=0, value=150)
    recent_sales = st.sidebar.number_input("Recent Sales (Units)", min_value=0, value=20)
    analysis_period = st.sidebar.number_input("Analysis Period (Days)", min_value=1, value=30)

    tied_capital = current_stock * purchase_price
    daily_sales = recent_sales / analysis_period if analysis_period > 0 else 0
    days_of_stock = current_stock / daily_sales if daily_sales > 0 else 999
    margin = ((selling_price - purchase_price) / selling_price * 100) if selling_price > 0 else 0

    if days_of_stock > 60 or selling_price < purchase_price:
        st.error(f"🔴 STATUS: POTENTIAL LOSS ({p_name})")
        st.metric("Money at Risk", f"₦{tied_capital:,.2f}")
        st.write(f"**Why:** ~{int(days_of_stock)} days of stock remaining. Capital is trapped in slow-moving inventory.")
        st.write("**Recommended Action:** Pause reorders. Run a discount campaign to liquidate stock.")
    elif days_of_stock > 30 or margin < 15:
        st.warning(f"🟡 STATUS: WATCH ({p_name})")
        st.metric("Money Tied Up", f"₦{tied_capital:,.2f}")
        st.write(f"**Why:** ~{int(days_of_stock)} days left or low margin ({margin:.1f}%).")
        st.write("**Recommended Action:** Monitor sales velocity before reordering.")
    else:
        st.success(f"🟢 STATUS: NORMAL ({p_name})")
        st.metric("Capital Invested", f"₦{tied_capital:,.2f}")
        st.write(f"**Why:** Healthy turnover (~{int(days_of_stock)} days stock) and strong margin ({margin:.1f}%).")
              
