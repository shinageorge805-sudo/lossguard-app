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
    
