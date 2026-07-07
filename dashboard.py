import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, timedelta
from database import init_database, get_connection
from auth import (
    hash_password, hash_answer, check_password_strength,
    is_valid_username, register_user, login_user,
    change_password, reset_pin_secret_question,
    reset_pin_admin, get_secret_question, get_user_settings,
    save_user_settings, get_budgets, save_budgets,
    add_expense, get_expenses, update_expense, delete_expense,
    add_income, get_income, update_income, delete_income
)

# ── INIT ─────────────────────────────────────────────────
init_database()

ADMIN_PASSWORD = "FinanceAdmin2026"

CURRENCIES = {
    "PKR - Pakistani Rupee": "Rs.",
    "USD - US Dollar": "$",
    "EUR - Euro": "€",
    "GBP - British Pound": "£",
    "AED - UAE Dirham": "AED",
    "SAR - Saudi Riyal": "SAR",
    "INR - Indian Rupee": "₹",
}

CATEGORIES = [
    "Food & Dining", "Groceries", "Travel & Transport",
    "Fuel & Petrol", "Rent & Housing", "Electricity Bill",
    "Gas Bill", "Water Bill", "Internet & Phone",
    "Shopping & Clothes", "Health & Medical", "Medicines",
    "Education & Books", "Entertainment", "Gym & Fitness",
    "Savings & Investment", "Charity & Donations",
    "Personal Care", "Kids & Family", "Pets",
    "Repairs & Maintenance", "Other", "➕ Add Custom Category"
]

DEFAULT_BUDGETS = {
    "Food & Dining": 10000, "Groceries": 8000,
    "Travel & Transport": 5000, "Fuel & Petrol": 5000,
    "Rent & Housing": 20000, "Electricity Bill": 3000,
    "Gas Bill": 2000, "Water Bill": 1000,
    "Internet & Phone": 2000, "Shopping & Clothes": 5000,
    "Health & Medical": 3000, "Medicines": 2000,
    "Education & Books": 5000, "Entertainment": 3000,
    "Gym & Fitness": 2000, "Savings & Investment": 10000,
    "Charity & Donations": 2000, "Personal Care": 2000,
    "Kids & Family": 5000, "Pets": 2000,
    "Repairs & Maintenance": 3000, "Other": 3000,
}

INCOME_SOURCES = [
    "Salary", "Freelance", "Business",
    "Investment", "Gift", "Other",
    "➕ Add Custom Source"
]

SECRET_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was your childhood nickname?",
    "What is your oldest sibling's middle name?",
]

# ── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(page_title="Finance Tracker", layout="wide")
st.title("💰 Personal Finance Tracker")

# ── SESSION STATE ────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()
if "edit_exp_id" not in st.session_state:
    st.session_state.edit_exp_id = None
if "edit_inc_id" not in st.session_state:
    st.session_state.edit_inc_id = None

# ── SESSION TIMEOUT (30 min) ─────────────────────────────
if st.session_state.logged_in:
    inactive = datetime.now() - st.session_state.last_activity
    if inactive > timedelta(minutes=30):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.query_params.clear()
        st.warning(
            "⏱️ Session expired due to inactivity. Please login again.")
    else:
        st.session_state.last_activity = datetime.now()

# ── RESTORE LOGIN FROM URL ───────────────────────────────
params = st.query_params
if not st.session_state.logged_in and "user" in params:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username = ?",
              (params["user"],))
    user = c.fetchone()
    conn.close()
    if user:
        st.session_state.logged_in = True
        st.session_state.current_user = params["user"]
        st.session_state.last_activity = datetime.now()

# ── LOGIN / REGISTER ─────────────────────────────────────
if not st.session_state.logged_in:
    st.subheader("🔐 Login or Create Account")
    tab_login, tab_register, tab_forgot = st.tabs([
        "🔑 Login", "📝 New Account", "🔓 Forgot Password"
    ])

    with tab_login:
        with st.form("login_form"):
            login_user_input = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if login_user_input.strip() == "":
                    st.error("Username cannot be empty!")
                elif not login_user_input.isalnum():
                    st.error(
                        "Username must be letters/numbers only!")
                else:
                    success, msg = login_user(
                        login_user_input, login_pass)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.current_user = \
                            login_user_input
                        st.session_state.last_activity = \
                            datetime.now()
                        st.query_params["user"] = login_user_input
                        st.rerun()
                    elif msg == "user_not_found":
                        st.error(
                            "❌ Username not found. Please create an account.")
                    elif msg == "account_locked":
                        st.error(
                            "🔒 Account locked for 5 minutes due to 4 failed attempts!")
                    elif msg.startswith("locked_"):
                        mins = msg.split("_")[1]
                        st.error(
                            f"🔒 Account locked! Try again in {mins} minute(s).")
                    elif msg.startswith("wrong_password_"):
                        remaining = msg.split("_")[-1]
                        st.error(
                            f"❌ Wrong password! {remaining} attempt(s) remaining before lockout.")

    with tab_register:
        with st.form("register_form"):
            reg_user = st.text_input(
                "Choose Username (letters/numbers, min 3, start with letter)")
            reg_pass = st.text_input(
                "Password (min 8 chars, uppercase, lowercase, number)",
                type="password")
            reg_pass2 = st.text_input("Confirm Password",
                                      type="password")
            st.markdown("---")
            st.caption("🔒 Secret Question (for password recovery)")
            reg_question = st.selectbox(
                "Select a secret question", SECRET_QUESTIONS)
            reg_answer = st.text_input(
                "Your answer (remember this!)")
            if st.form_submit_button("Create Account"):
                if not is_valid_username(reg_user):
                    st.error(
                        "Username: letters/numbers only, min 3 chars, must start with letter.")
                else:
                    strength_errors = check_password_strength(
                        reg_pass)
                    if strength_errors:
                        for e in strength_errors:
                            st.error(f"❌ {e}")
                    elif reg_pass != reg_pass2:
                        st.error("Passwords do not match!")
                    elif reg_answer.strip() == "":
                        st.error(
                            "Secret question answer cannot be empty!")
                    else:
                        success, msg = register_user(
                            reg_user, reg_pass,
                            reg_question, reg_answer)
                        if success:
                            st.success(
                                "✅ Account created! Please login now.")
                        elif msg == "username_taken":
                            st.error(
                                f'❌ Username "{reg_user}" is already taken.')
                            st.warning(
                                "💡 Try one of these instead:")
                            suggestions = [
                                f"{reg_user}123",
                                f"{reg_user}786",
                                f"{reg_user}PK",
                                f"{reg_user}Official",
                                f"{reg_user}2026",
                            ]
                            conn = get_connection()
                            c = conn.cursor()
                            for s in suggestions:
                                c.execute(
                                    "SELECT username FROM users WHERE username = ?",
                                    (s,))
                                if not c.fetchone():
                                    st.code(f"✓ {s}",
                                            language=None)
                            conn.close()

    with tab_forgot:
        st.subheader("🔓 Reset Your Password")
        reset_method = st.radio(
            "Choose reset method:",
            ["🔒 Secret Question", "🔑 Admin Password"],
            horizontal=True)

        if reset_method == "🔒 Secret Question":
            fp_user = st.text_input("Your Username", key="fp_user")
            if fp_user:
                question = get_secret_question(fp_user)
                if question:
                    st.info(f"**Your Question:** {question}")
                    with st.form("sq_reset_form"):
                        sq_answer = st.text_input("Your Answer")
                        new_pass1 = st.text_input(
                            "New Password", type="password")
                        new_pass2 = st.text_input(
                            "Confirm New Password", type="password")
                        if st.form_submit_button("Reset Password"):
                            if new_pass1 != new_pass2:
                                st.error("Passwords do not match!")
                            else:
                                success, msg, _ = \
                                    reset_pin_secret_question(
                                        fp_user, sq_answer,
                                        new_pass1)
                                if success:
                                    st.success(
                                        "✅ Password reset! Please login now.")
                                elif msg == "wrong_answer":
                                    st.error("❌ Wrong answer!")
                                elif isinstance(msg, list):
                                    for e in msg:
                                        st.error(f"❌ {e}")
                else:
                    st.error("Username not found!")
        else:
            with st.form("admin_reset_form"):
                ad_user = st.text_input("Username to Reset")
                ad_pass = st.text_input("Admin Password",
                                        type="password")
                new_pass1 = st.text_input("New Password",
                                          type="password")
                new_pass2 = st.text_input("Confirm New Password",
                                          type="password")
                if st.form_submit_button("Reset Password"):
                    if new_pass1 != new_pass2:
                        st.error("Passwords do not match!")
                    else:
                        success, msg = reset_pin_admin(
                            ad_user, ad_pass,
                            new_pass1, ADMIN_PASSWORD)
                        if success:
                            st.success(
                                f"✅ Password for '{ad_user}' reset!")
                        elif msg == "wrong_admin_password":
                            st.error("❌ Wrong Admin Password!")
                        elif msg == "user_not_found":
                            st.error("❌ Username not found!")
                        elif isinstance(msg, list):
                            for e in msg:
                                st.error(f"❌ {e}")
    st.stop()

# ── MAIN APP ─────────────────────────────────────────────
username = st.session_state.current_user
user_settings = get_user_settings(username)
curr_symbol = user_settings.get("currency_symbol", "Rs.")
savings_goal = float(user_settings.get("savings_goal", 30))
budgets = get_budgets(username)
if not budgets:
    budgets = DEFAULT_BUDGETS.copy()

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.current_user = ""
    st.query_params.clear()
    st.rerun()

st.sidebar.success(f"👤 {username}")
st.sidebar.markdown("---")

sidebar_tab = st.sidebar.radio(
    "Menu",
    ["➕ Add Expense", "💵 Add Income",
     "💰 Budget Settings", "🔑 Change Password",
     "⚙️ Settings"],
    label_visibility="collapsed"
)

# ── ADD EXPENSE ───────────────────────────────────────────
if sidebar_tab == "➕ Add Expense":
    st.sidebar.header("➕ Add New Expense")
    exp_cat_select = st.sidebar.selectbox(
        "Category (type to search)", CATEGORIES,
        key="exp_cat_select")
    if exp_cat_select == "➕ Add Custom Category":
        custom_cat = st.sidebar.text_input(
            "✏️ Custom category name",
            placeholder="e.g. Car Insurance...",
            key="custom_cat_input")
        final_cat = custom_cat.strip()
    else:
        final_cat = exp_cat_select

    with st.sidebar.form("expense_form", clear_on_submit=True):
        exp_date = st.date_input("Date", value=datetime.today())
        st.info(
            f"Category: **{final_cat if final_cat else 'Not selected'}**")
        exp_desc = st.text_input("Description (e.g. Lunch)")
        exp_amt = st.number_input(f"Amount ({curr_symbol})",
                                  min_value=1, step=1)
        if st.form_submit_button("Add Expense"):
            if not final_cat:
                st.error("Please enter a category name!")
            elif exp_desc.strip() == "":
                st.error("Description cannot be empty!")
            else:
                add_expense(username, exp_date, final_cat,
                            exp_desc.strip(), exp_amt)
                st.success(
                    f"✅ {final_cat} - {curr_symbol}{exp_amt} added!")
                st.rerun()

# ── ADD INCOME ────────────────────────────────────────────
elif sidebar_tab == "💵 Add Income":
    st.sidebar.header("💵 Add New Income")
    inc_src_select = st.sidebar.selectbox(
        "Income Source", INCOME_SOURCES, key="inc_src_select")
    if inc_src_select == "➕ Add Custom Source":
        custom_src = st.sidebar.text_input(
            "✏️ Custom source name",
            placeholder="e.g. Rental Income...",
            key="custom_src_input")
        final_src = custom_src.strip()
    elif inc_src_select == "Other":
        custom_src = st.sidebar.text_input(
            "✏️ Specify source",
            placeholder="e.g. Bonus, Cashback...",
            key="other_src_input")
        final_src = custom_src.strip() if custom_src.strip() \
            else "Other"
    else:
        final_src = inc_src_select

    with st.sidebar.form("income_form", clear_on_submit=True):
        inc_date = st.date_input("Date", value=datetime.today())
        st.info(
            f"Source: **{final_src if final_src else 'Not selected'}**")
        inc_desc = st.text_input(
            "Description (e.g. Monthly Salary)")
        inc_amt = st.number_input(f"Amount ({curr_symbol})",
                                  min_value=1, step=1)
        if st.form_submit_button("Add Income"):
            if not final_src:
                st.error("Please enter a source name!")
            elif inc_desc.strip() == "":
                st.error("Description cannot be empty!")
            else:
                add_income(username, inc_date, final_src,
                           inc_desc.strip(), inc_amt)
                st.success(
                    f"✅ {final_src} - {curr_symbol}{inc_amt} added!")
                st.rerun()

# ── BUDGET SETTINGS ───────────────────────────────────────
elif sidebar_tab == "💰 Budget Settings":
    st.sidebar.header("💰 Edit Budgets")
    with st.sidebar.form("budget_form"):
        new_budgets = {}
        for cat in CATEGORIES:
            if cat == "➕ Add Custom Category":
                continue
            new_budgets[cat] = st.number_input(
                f"{cat} ({curr_symbol})", min_value=0, step=500,
                value=int(budgets.get(
                    cat, DEFAULT_BUDGETS.get(cat, 3000))))
        if st.form_submit_button("💾 Save Budgets"):
            save_budgets(username, new_budgets)
            st.success("✅ Budgets saved!")
            st.rerun()

# ── CHANGE PASSWORD ───────────────────────────────────────
elif sidebar_tab == "🔑 Change Password":
    st.sidebar.header("🔑 Change Password")
    with st.sidebar.form("change_pass_form"):
        old_pass = st.text_input("Current Password",
                                 type="password")
        new_pass = st.text_input(
            "New Password (min 8, uppercase, lowercase, number)",
            type="password")
        new_pass2 = st.text_input("Confirm New Password",
                                  type="password")
        if st.form_submit_button("🔄 Change Password"):
            if new_pass != new_pass2:
                st.error("Passwords do not match!")
            else:
                success, msg = change_password(
                    username, old_pass, new_pass)
                if success:
                    st.success("✅ Password changed successfully!")
                elif msg == "wrong_password":
                    st.error("❌ Current password is incorrect!")
                elif isinstance(msg, list):
                    for e in msg:
                        st.error(f"❌ {e}")

# ── SETTINGS ─────────────────────────────────────────────
elif sidebar_tab == "⚙️ Settings":
    st.sidebar.header("⚙️ Settings")
    with st.sidebar.form("settings_form"):
        st.caption("💱 Currency")
        curr_options = list(CURRENCIES.keys())
        current_curr = next(
            (k for k, v in CURRENCIES.items()
             if v == curr_symbol),
            "PKR - Pakistani Rupee")
        selected_curr = st.selectbox(
            "Select Currency", curr_options,
            index=curr_options.index(current_curr))
        st.caption("🎯 Savings Goal")
        new_goal = st.slider(
            "Monthly Savings Target (%)",
            min_value=5, max_value=80,
            value=int(savings_goal), step=5,
            help="What % of your income do you want to save?")
        if st.form_submit_button("💾 Save Settings"):
            new_symbol = CURRENCIES[selected_curr]
            save_user_settings(username, new_symbol, new_goal)
            st.success("✅ Settings saved!")
            st.rerun()

# ── FILTERS ──────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.header("📅 Filters")

df_exp = get_expenses(username)
df_inc = get_income(username)

if not df_exp.empty:
    df_exp["Month"] = df_exp["Date"].dt.to_period("M").astype(str)
    all_months = ["All Months"] + sorted(
        df_exp["Month"].unique().tolist(), reverse=True)
    sel_month = st.sidebar.selectbox("Select Month", all_months)
    df_exp_f = df_exp[df_exp["Month"] == sel_month] \
        if sel_month != "All Months" else df_exp.copy()
else:
    df_exp_f = df_exp.copy()
    sel_month = "All Months"

if not df_inc.empty:
    df_inc["Month"] = df_inc["Date"].dt.to_period("M").astype(str)
    df_inc_f = df_inc[df_inc["Month"] == sel_month] \
        if sel_month != "All Months" else df_inc.copy()
else:
    df_inc_f = df_inc.copy()

# ── HELPER: SMART ADVISOR ────────────────────────────────
def get_smart_advice(total_inc, total_exp, savings_goal,
                     curr_symbol, cat_totals, budgets):
    tips = []
    if total_inc == 0:
        return tips

    savings = total_inc - total_exp
    savings_rate = (savings / total_inc) * 100

    # Savings goal check
    if savings_rate >= savings_goal + 20:
        tips.append(("success",
                     f"🌟 Excellent! You are saving {savings_rate:.1f}% — "
                     f"{savings_rate - savings_goal:.1f}% above your {savings_goal}% goal. "
                     f"Consider investing the extra savings!"))
    elif savings_rate >= savings_goal:
        tips.append(("success",
                     f"✅ Great job! Savings rate {savings_rate:.1f}% is meeting "
                     f"your {savings_goal}% goal."))
    else:
        shortfall = (savings_goal / 100 * total_inc) - savings
        tips.append(("error",
                     f"❌ Savings rate is {savings_rate:.1f}% — below your "
                     f"{savings_goal}% goal. You need to save "
                     f"{curr_symbol}{shortfall:,.0f} more this month."))

    # Over budget categories
    for cat, spent in cat_totals.items():
        budget = budgets.get(cat,
                             DEFAULT_BUDGETS.get(cat, 3000))
        if budget > 0 and spent > budget:
            tips.append(("warning",
                         f"⚠️ {cat} is over budget by "
                         f"{curr_symbol}{spent - budget:,.0f}. "
                         f"Try to cut down next month."))

    # High food spending
    food_spent = cat_totals.get("Food & Dining", 0) + \
                 cat_totals.get("Groceries", 0)
    food_budget = budgets.get("Food & Dining", 10000) + \
                  budgets.get("Groceries", 8000)
    if food_budget > 0 and food_spent > food_budget * 0.8:
        tips.append(("warning",
                     f"🍽️ Food spending is high ({curr_symbol}{food_spent:,.0f}). "
                     f"Try cooking at home more often."))

    # Entertainment check
    ent_spent = cat_totals.get("Entertainment", 0)
    ent_budget = budgets.get("Entertainment", 3000)
    if ent_budget > 0 and ent_spent > ent_budget * 0.9:
        tips.append(("warning",
                     f"🎬 Entertainment spending at "
                     f"{curr_symbol}{ent_spent:,.0f} — close to limit."))

    # Positive: if expenses very low
    if total_exp < total_inc * 0.3:
        tips.append(("success",
                     f"💪 Impressive! Your expenses are only "
                     f"{(total_exp/total_inc)*100:.1f}% of income. "
                     f"You are doing great financially!"))

    return tips

# ── TABS ─────────────────────────────────────────────────
page = st.tabs(["📊 Dashboard", "📈 Monthly Report",
                "📋 All Expenses", "💵 All Income"])

# ── TAB 1: DASHBOARD ─────────────────────────────────────
with page[0]:
    st.subheader(f"👤 {username}'s Dashboard")

    total_exp = df_exp_f["Amount"].sum() \
        if not df_exp_f.empty else 0
    total_inc = df_inc_f["Amount"].sum() \
        if not df_inc_f.empty else 0
    savings = total_inc - total_exp
    savings_rate = (savings / total_inc * 100) \
        if total_inc > 0 else 0

    # ── SUMMARY CARDS ────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💸 Total Expenses",
              f"{curr_symbol} {total_exp:,.0f}")
    c2.metric("💵 Total Income",
              f"{curr_symbol} {total_inc:,.0f}")
    c3.metric("🏦 Savings",
              f"{curr_symbol} {savings:,.0f}",
              delta="Saved" if savings >= 0 else "Deficit")
    if not df_exp_f.empty:
        top_cat = df_exp_f.groupby(
            "Category")["Amount"].sum().idxmax()
        c4.metric("🏆 Top Expense", top_cat)

    st.markdown("---")

    # ── SAVINGS GOAL CARD ─────────────────────────────────
    if total_inc > 0:
        st.subheader("🎯 Monthly Saving Goal")
        g1, g2, g3 = st.columns(3)

        with g1:
            st.metric("🎯 Your Goal", f"{savings_goal:.0f}%")
        with g2:
            st.metric("📊 Current Rate", f"{savings_rate:.1f}%")
        with g3:
            if savings_rate >= savings_goal:
                st.metric("✅ Status", "Goal Achieved! 🎉")
            else:
                shortfall = (savings_goal/100*total_inc) - savings
                st.metric("❌ Status",
                          f"Need {curr_symbol}{shortfall:,.0f} more")

        # Progress bar
        goal_progress = min(savings_rate / savings_goal, 1.0) \
            if savings_goal > 0 else 0
        st.progress(goal_progress,
                    text=f"Savings Progress: {savings_rate:.1f}% / {savings_goal:.0f}% goal")

        st.markdown("---")

    # ── SMART FINANCE ADVISOR ─────────────────────────────
    if total_inc > 0:
        st.subheader("🧠 Smart Finance Advisor")
        cat_totals = df_exp_f.groupby(
            "Category")["Amount"].sum() \
            if not df_exp_f.empty else pd.Series(dtype=float)

        tips = get_smart_advice(
            total_inc, total_exp, savings_goal,
            curr_symbol, cat_totals, budgets)

        if tips:
            for tip_type, tip_msg in tips:
                if tip_type == "success":
                    st.success(tip_msg)
                elif tip_type == "warning":
                    st.warning(tip_msg)
                elif tip_type == "error":
                    st.error(tip_msg)
        else:
            st.info(
                "💡 Add more expenses to get personalized advice!")

        st.markdown("---")

    # ── BUDGET STATUS WITH PROGRESS BARS ─────────────────
    # ── BUDGET STATUS WITH PROGRESS BARS ─────────────────
    if not df_exp_f.empty:
        st.subheader("⚠️ Budget Status")
        cat_totals = df_exp_f.groupby("Category")["Amount"].sum()
        budget_cats = [c for c in CATEGORIES
                       if c != "➕ Add Custom Category"]

        # Sirf woh categories jo spent > 0 hain
        active_cats = [
            cat for cat in budget_cats
            if cat_totals.get(cat, 0) > 0
        ]

        if active_cats:
            bcols = st.columns(4)
            for i, cat in enumerate(active_cats):
                spent = cat_totals.get(cat, 0)
                budget = budgets.get(
                    cat, DEFAULT_BUDGETS.get(cat, 3000))
                if budget == 0 and spent == 0:
                    continue
                pct = (spent / budget * 100) \
                    if budget > 0 else 100
                progress_val = min(pct / 100, 1.0)

                with bcols[i % 4]:
                    if spent > budget:
                        st.error(
                            f"**{cat}**\n"
                            f"{curr_symbol}{spent:,.0f} / "
                            f"{curr_symbol}{budget:,.0f}")
                        st.progress(
                            1.0, text=f"🚨 {pct:.0f}% — Over!")
                    elif pct > 75:
                        st.warning(
                            f"**{cat}**\n"
                            f"{curr_symbol}{spent:,.0f} / "
                            f"{curr_symbol}{budget:,.0f}")
                        st.progress(
                            progress_val,
                            text=f"⚠️ {pct:.0f}%")
                    else:
                        st.success(
                            f"**{cat}**\n"
                            f"{curr_symbol}{spent:,.0f} / "
                            f"{curr_symbol}{budget:,.0f}")
                        st.progress(
                            progress_val,
                            text=f"✅ {pct:.0f}%")

        st.markdown("---")

        # ── CHARTS ───────────────────────────────────────
        cl, cr = st.columns(2)
        cat_df = df_exp_f.groupby(
            "Category")["Amount"].sum().reset_index()
        with cl:
            fig = px.pie(
                cat_df, names="Category", values="Amount",
                title="Expense Distribution by Category")
            st.plotly_chart(fig, use_container_width=True)
        with cr:
            fig2 = px.bar(
                cat_df, x="Category", y="Amount",
                title="Category-wise Total",
                text_auto=True, color="Category")
            st.plotly_chart(fig2, use_container_width=True)

        date_df = df_exp_f.groupby(
            df_exp_f["Date"].dt.date)[
            "Amount"].sum().reset_index()
        date_df.columns = ["Date", "Amount"]
        fig3 = px.line(
            date_df, x="Date", y="Amount",
            markers=True, title="Daily Expense Trend")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info(
            "No expenses yet. Add your first expense from the sidebar!")

# ── TAB 2: MONTHLY REPORT ────────────────────────────────
with page[1]:
    st.subheader("📈 Monthly Report")
    if df_exp.empty and df_inc.empty:
        st.info("No data available yet.")
    else:
        if not df_exp.empty:
            df_exp["Month"] = df_exp["Date"].dt.to_period(
                "M").astype(str)
            monthly_exp = df_exp.groupby(
                "Month")["Amount"].sum().reset_index()
            monthly_exp.columns = ["Month", "Expenses"]
        else:
            monthly_exp = pd.DataFrame(
                columns=["Month", "Expenses"])

        if not df_inc.empty:
            df_inc["Month"] = df_inc["Date"].dt.to_period(
                "M").astype(str)
            monthly_inc = df_inc.groupby(
                "Month")["Amount"].sum().reset_index()
            monthly_inc.columns = ["Month", "Income"]
        else:
            monthly_inc = pd.DataFrame(
                columns=["Month", "Income"])

        if not monthly_exp.empty and not monthly_inc.empty:
            monthly = pd.merge(
                monthly_exp, monthly_inc,
                on="Month", how="outer").fillna(0)
        elif not monthly_exp.empty:
            monthly = monthly_exp.copy()
            monthly["Income"] = 0
        else:
            monthly = monthly_inc.copy()
            monthly["Expenses"] = 0

        monthly["Savings"] = \
            monthly["Income"] - monthly["Expenses"]
        monthly["Savings Rate %"] = monthly.apply(
            lambda r: round(r["Savings"] / r["Income"] * 100, 1)
            if r["Income"] > 0 else 0, axis=1)
        monthly["Goal Met"] = monthly["Savings Rate %"].apply(
            lambda x: "✅ Yes" if x >= savings_goal else "❌ No")
        monthly = monthly.sort_values("Month")

        st.dataframe(monthly.style.format({
            "Expenses": f"{curr_symbol} {{:,.0f}}",
            "Income": f"{curr_symbol} {{:,.0f}}",
            "Savings": f"{curr_symbol} {{:,.0f}}",
            "Savings Rate %": "{:.1f}%"
        }), use_container_width=True)

        fig_m = px.bar(
            monthly, x="Month",
            y=["Income", "Expenses"],
            title="Monthly Income vs Expenses",
            barmode="group",
            color_discrete_map={
                "Income": "#2ecc71",
                "Expenses": "#e74c3c"})
        st.plotly_chart(fig_m, use_container_width=True)

        fig_s = px.line(
            monthly, x="Month", y="Savings",
            markers=True, title="Monthly Savings Trend",
            color_discrete_sequence=["#3498db"])
        fig_s.add_hline(
            y=0, line_dash="dash", line_color="red",
            annotation_text="Break Even")
        st.plotly_chart(fig_s, use_container_width=True)

        if len(monthly) > 0:
            best = monthly.loc[monthly["Savings"].idxmax()]
            worst = monthly.loc[monthly["Savings"].idxmin()]
            col1, col2 = st.columns(2)
            col1.success(
                f"🏆 **Best Month:** {best['Month']}\n\n"
                f"Savings: {curr_symbol} {best['Savings']:,.0f} "
                f"({best['Savings Rate %']:.1f}%)")
            col2.error(
                f"📉 **Worst Month:** {worst['Month']}\n\n"
                f"Savings: {curr_symbol} {worst['Savings']:,.0f} "
                f"({worst['Savings Rate %']:.1f}%)")

# ── TAB 3: ALL EXPENSES ───────────────────────────────────
with page[2]:
    st.subheader("📋 All Expenses")
    if df_exp_f.empty:
        st.info("No expenses found.")
    else:
        col_s, col_d1, col_d2 = st.columns(3)
        with col_s:
            search_exp = st.text_input(
                "🔍 Search",
                placeholder="Search description or category...")
        with col_d1:
            date_from = st.date_input(
                "From Date",
                value=df_exp_f["Date"].min().date())
        with col_d2:
            date_to = st.date_input(
                "To Date",
                value=df_exp_f["Date"].max().date())

        disp = df_exp_f.copy()
        disp = disp[(disp["Date"].dt.date >= date_from) &
                    (disp["Date"].dt.date <= date_to)]
        if search_exp:
            mask = (
                disp["Description"].str.contains(
                    search_exp, case=False, na=False) |
                disp["Category"].str.contains(
                    search_exp, case=False, na=False))
            disp = disp[mask]

        st.caption(
            f"Showing {len(disp)} records | "
            f"Total: {curr_symbol} {disp['Amount'].sum():,.0f}")

        csv_out = disp.copy()
        csv_out["Date"] = csv_out["Date"].dt.strftime("%Y-%m-%d")
        st.download_button(
            "📥 Download CSV",
            csv_out.to_csv(index=False).encode("utf-8"),
            f"{username}_expenses.csv", "text/csv")

        disp_show = disp.copy()
        disp_show["Date"] = disp_show["Date"].dt.strftime(
            "%Y-%m-%d")
        disp_show = disp_show.drop(
            columns=["Month"], errors="ignore")
        disp_show = disp_show.sort_values("Date", ascending=False)

        for _, row in disp_show.iterrows():
            exp_id = row["id"]
            if st.session_state.edit_exp_id == exp_id:
                with st.form(key=f"edit_exp_{exp_id}"):
                    st.markdown("**✏️ Editing Expense**")
                    e1, e2 = st.columns(2)
                    new_date = e1.date_input(
                        "Date", value=datetime.strptime(
                            row["Date"], "%Y-%m-%d"))
                    new_cat = e2.selectbox(
                        "Category", CATEGORIES,
                        index=CATEGORIES.index(row["Category"])
                        if row["Category"] in CATEGORIES else 0)
                    new_desc = st.text_input(
                        "Description",
                        value=row["Description"])
                    new_amt = st.number_input(
                        f"Amount ({curr_symbol})",
                        value=float(row["Amount"]),
                        min_value=1.0)
                    s1, s2 = st.columns(2)
                    if s1.form_submit_button("💾 Save"):
                        update_expense(
                            exp_id, new_date,
                            new_cat, new_desc, new_amt)
                        st.session_state.edit_exp_id = None
                        st.success("✅ Updated!")
                        st.rerun()
                    if s2.form_submit_button("❌ Cancel"):
                        st.session_state.edit_exp_id = None
                        st.rerun()
            else:
                c1, c2, c3, c4, c5, c6 = st.columns(
                    [2, 2, 3, 2, 1, 1])
                c1.write(row["Date"])
                c2.write(row["Category"])
                c3.write(row["Description"])
                c4.write(f"{curr_symbol} {row['Amount']:,.0f}")
                if c5.button("✏️", key=f"edit_exp_{exp_id}"):
                    st.session_state.edit_exp_id = exp_id
                    st.rerun()
                if c6.button("🗑️", key=f"del_exp_{exp_id}"):
                    delete_expense(exp_id)
                    st.rerun()

# ── TAB 4: ALL INCOME ────────────────────────────────────
with page[3]:
    st.subheader("💵 All Income")
    if df_inc_f.empty:
        st.info("No income added yet.")
    else:
        col_s, col_d1, col_d2 = st.columns(3)
        with col_s:
            search_inc = st.text_input(
                "🔍 Search",
                placeholder="Search description or source...",
                key="inc_search")
        with col_d1:
            inc_from = st.date_input(
                "From Date",
                value=df_inc_f["Date"].min().date(),
                key="inc_from")
        with col_d2:
            inc_to = st.date_input(
                "To Date",
                value=df_inc_f["Date"].max().date(),
                key="inc_to")

        disp_inc = df_inc_f.copy()
        disp_inc = disp_inc[
            (disp_inc["Date"].dt.date >= inc_from) &
            (disp_inc["Date"].dt.date <= inc_to)]
        if search_inc:
            mask = (
                disp_inc["Description"].str.contains(
                    search_inc, case=False, na=False) |
                disp_inc["Source"].str.contains(
                    search_inc, case=False, na=False))
            disp_inc = disp_inc[mask]

        st.caption(
            f"Showing {len(disp_inc)} records | "
            f"Total: {curr_symbol} {disp_inc['Amount'].sum():,.0f}")

        csv_inc = disp_inc.copy()
        csv_inc["Date"] = csv_inc["Date"].dt.strftime("%Y-%m-%d")
        st.download_button(
            "📥 Download CSV",
            csv_inc.to_csv(index=False).encode("utf-8"),
            f"{username}_income.csv", "text/csv",
            key="inc_download")

        disp_inc_show = disp_inc.copy()
        disp_inc_show["Date"] = \
            disp_inc_show["Date"].dt.strftime("%Y-%m-%d")
        disp_inc_show = disp_inc_show.drop(
            columns=["Month"], errors="ignore")
        disp_inc_show = disp_inc_show.sort_values(
            "Date", ascending=False)

        for _, row in disp_inc_show.iterrows():
            inc_id = row["id"]
            if st.session_state.edit_inc_id == inc_id:
                with st.form(key=f"edit_inc_{inc_id}"):
                    st.markdown("**✏️ Editing Income**")
                    e1, e2 = st.columns(2)
                    new_date = e1.date_input(
                        "Date", value=datetime.strptime(
                            row["Date"], "%Y-%m-%d"))
                    new_src = e2.selectbox(
                        "Source", INCOME_SOURCES,
                        index=INCOME_SOURCES.index(row["Source"])
                        if row["Source"] in INCOME_SOURCES else 0)
                    new_desc = st.text_input(
                        "Description",
                        value=row["Description"])
                    new_amt = st.number_input(
                        f"Amount ({curr_symbol})",
                        value=float(row["Amount"]),
                        min_value=1.0)
                    s1, s2 = st.columns(2)
                    if s1.form_submit_button("💾 Save"):
                        update_income(
                            inc_id, new_date,
                            new_src, new_desc, new_amt)
                        st.session_state.edit_inc_id = None
                        st.success("✅ Updated!")
                        st.rerun()
                    if s2.form_submit_button("❌ Cancel"):
                        st.session_state.edit_inc_id = None
                        st.rerun()
            else:
                c1, c2, c3, c4, c5, c6 = st.columns(
                    [2, 2, 3, 2, 1, 1])
                c1.write(row["Date"])
                c2.write(row["Source"])
                c3.write(row["Description"])
                c4.write(f"{curr_symbol} {row['Amount']:,.0f}")
                if c5.button("✏️", key=f"edit_inc_{inc_id}"):
                    st.session_state.edit_inc_id = inc_id
                    st.rerun()
                if c6.button("🗑️", key=f"del_inc_{inc_id}"):
                    delete_income(inc_id)
                    st.rerun()