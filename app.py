import csv
import io
import json
import calendar
import hashlib
import math
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


st.set_page_config(
    page_title="Payday Compass",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #fbfbfa;
        color: #252b33;
    }
    .block-container {
        max-width: 1080px;
        padding-top: 1.35rem;
        padding-bottom: 2.5rem;
    }
    section[data-testid="stSidebar"] {
        background: #f7f7f5;
        border-right: 1px solid #e8e8e5;
    }
    h1 {
        color: #202923 !important;
        letter-spacing: -0.04em;
        font-weight: 700 !important;
    }
    h2, h3, h4 {
        color: #29352f !important;
        letter-spacing: -0.025em;
    }
    h1 {
        font-size: 2rem !important;
    }
    h2, h3 {
        font-size: 1.25rem !important;
        font-weight: 650 !important;
    }
    div[data-testid="stWidgetLabel"] p {
        color: #515a54;
        font-weight: 500;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #e7e8e4 !important;
        border-radius: 12px !important;
        background-color: #ffffff;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        border-radius: 8px;
    }
    div.stButton > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 8px;
        min-height: 2.45rem;
        font-weight: 550;
        transition: all 120ms ease-in-out;
    }
    div.stButton > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        border-color: #8b9b8f;
        color: #344d3c;
    }
    div[data-testid="stAlert"] {
        border-radius: 9px;
    }
    div[data-testid="stExpander"] {
        border-color: #e7e8e4;
        border-radius: 10px;
    }
    div.st-key-compact_section3 [data-testid="stMetricValue"],
    div.st-key-compact_section4 [data-testid="stMetricValue"],
    div.st-key-compact_section1_totals [data-testid="stMetricValue"],
    div.st-key-living_budget_card [data-testid="stMetricValue"],
    div.st-key-purchase_check [data-testid="stMetricValue"] {
        font-size: 1rem !important;
        line-height: 1.25 !important;
        white-space: nowrap;
    }
    div.st-key-compact_section3 [data-testid="stMetricLabel"],
    div.st-key-compact_section4 [data-testid="stMetricLabel"],
    div.st-key-compact_section1_totals [data-testid="stMetricLabel"],
    div.st-key-living_budget_card [data-testid="stMetricLabel"],
    div.st-key-purchase_check [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
    }
    div.st-key-compact_section1_totals [data-testid="stMetric"] {
        background: #fafbf9;
        border: 1px solid #e9ebe7;
        border-radius: 10px;
        padding: 10px 12px;
        min-height: 84px;
    }
    div.st-key-compact_section3 [data-testid="stMetric"],
    div.st-key-compact_section4 [data-testid="stMetric"],
    div.st-key-living_budget_card [data-testid="stMetric"],
    div.st-key-purchase_check [data-testid="stMetric"],
    div.st-key-living_result [data-testid="stMetric"] {
        background: #fafbf9;
        border: 1px solid #e9ebe7;
        border-radius: 10px;
        padding: 10px 12px;
        min-height: 84px;
    }
    div.st-key-compact_section3 [data-testid="stMetric"]:last-child,
    div.st-key-compact_section4 [data-testid="stMetric"]:last-child {
        background: #f1f6f1;
        border-color: #dce8dc;
    }
    div.st-key-compact_section3 [data-testid="stMetric"]:last-child [data-testid="stMetricValue"],
    div.st-key-compact_section4 [data-testid="stMetric"]:last-child [data-testid="stMetricValue"] {
        color: #315d3c;
    }
    div[data-testid="stMarkdownContainer"] p {
        color: #4f5952;
    }
    .quick-start {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0.4rem 0 1.4rem;
    }
    .quick-start a {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.55rem 0.8rem;
        border: 1px solid #e6e9e4;
        border-radius: 999px;
        background: #fff;
        color: #3c5141 !important;
        font-size: 0.88rem;
        text-decoration: none !important;
    }
    .quick-start a:hover {
        border-color: #aab9aa;
        background: #f4f7f3;
    }
    .step-anchor {
        display: block;
        height: 0;
        scroll-margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(amount):
    if is_vnd:
        return f"{amount:,.0f}".replace(",", ".") + " VND"
    return f"${amount:,.2f}"


def parse_amount(raw, use_vnd):
    text = str(raw).strip().lower().replace("₫", "").replace("vnd", "").replace("$", "").replace("usd", "").replace(" ", "")
    if not text:
        return 0.0
    if use_vnd and "tr" in text:
        return max(0.0, float(text.replace("tr", "").replace(",", ".")) * 1_000_000)
    if use_vnd and "," in text and "." not in text:
        return max(0.0, float(text.replace(",", ".")) * 1_000_000)
    if use_vnd:
        return max(0.0, float(text.replace(".", "").replace(",", "")))
    return max(0.0, float(text.replace(",", "")))


def format_amount_input(amount, use_vnd):
    return f"{amount:,.0f}".replace(",", ".") if use_vnd else f"{amount:,.2f}"


def normalize_amount_input(key, use_vnd):
    try:
        st.session_state[key] = format_amount_input(
            parse_amount(st.session_state[key], use_vnd), use_vnd
        )
    except ValueError:
        pass


def amount_input(label, initial_value, key, use_vnd, help_text=None):
    input_key = f"{key}_formatted"
    if input_key not in st.session_state:
        st.session_state[input_key] = format_amount_input(initial_value, use_vnd)
    raw_value = st.text_input(
        label,
        key=input_key,
        on_change=normalize_amount_input,
        args=(input_key, use_vnd),
        help=help_text or (
            "Nhập số đầy đủ hoặc dạng triệu, ví dụ 1,5 hay 1,5tr = 1.500.000 VND."
            if use_vnd else "Dùng dấu phẩy ngăn cách hàng nghìn và dấu chấm cho phần lẻ, ví dụ 1,500.00."
        ),
    )
    try:
        return parse_amount(raw_value, use_vnd)
    except ValueError:
        st.warning(f"{label}: vui lòng nhập số tiền hợp lệ.")
        return 0.0


DB_PATH = Path(__file__).resolve().with_name("payday_compass.db")
VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def vietnam_now():
    return datetime.now(VIETNAM_TIMEZONE)


def format_history_timestamp(value):
    saved_time = datetime.fromisoformat(str(value))
    if saved_time.tzinfo is None:
        # Older SQLite rows used CURRENT_TIMESTAMP, which is UTC.
        saved_time = saved_time.replace(tzinfo=ZoneInfo("UTC"))
    return saved_time.astimezone(VIETNAM_TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")


def get_db_connection():
    """Open the local SQLite file and create its history table if needed."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_hash TEXT NOT NULL,
            month_key TEXT NOT NULL,
            currency TEXT NOT NULL,
            current_balance REAL NOT NULL DEFAULT 0,
            payday TEXT NOT NULL,
            projected_remaining REAL NOT NULL DEFAULT 0,
            after_living REAL NOT NULL DEFAULT 0,
            snapshot_json TEXT NOT NULL,
            saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_owner_saved "
        "ON monthly_history (owner_hash, saved_at)"
    )
    connection.commit()
    return connection


def save_monthly_history(owner_hash, month_key, currency_code, snapshot):
    connection = get_db_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO monthly_history
                (owner_hash, month_key, currency, current_balance, payday,
                 projected_remaining, after_living, snapshot_json, saved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_hash,
                month_key,
                currency_code,
                snapshot["current_balance"],
                snapshot["payday"],
                snapshot["projected_remaining"],
                snapshot["after_living"],
                json.dumps(snapshot, ensure_ascii=False),
                vietnam_now().isoformat(timespec="seconds"),
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def load_monthly_history(owner_hash):
    connection = get_db_connection()
    try:
        cursor = connection.execute(
            """
            SELECT id, month_key, currency, current_balance, payday,
                   projected_remaining, after_living, saved_at
            FROM monthly_history
            WHERE owner_hash = ?
            ORDER BY saved_at DESC
            LIMIT 24
            """,
            (owner_hash,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def delete_monthly_history_record(owner_hash, record_id):
    connection = get_db_connection()
    try:
        connection.execute(
            "DELETE FROM monthly_history WHERE owner_hash = ? AND id = ?",
            (owner_hash, record_id),
        )
        connection.commit()
    finally:
        connection.close()


def delete_all_monthly_history(owner_hash):
    connection = get_db_connection()
    try:
        connection.execute(
            "DELETE FROM monthly_history WHERE owner_hash = ?",
            (owner_hash,),
        )
        connection.commit()
    finally:
        connection.close()


@st.fragment(run_every=30)
def show_vietnam_clock():
    current_time = vietnam_now()
    st.markdown(
        f"""
        <div style="text-align:left; border:1px solid #e5eaf1; background:#f7f9fc;
                    border-radius:12px; padding:8px 12px; line-height:1.35;">
          <div style="font-size:0.72rem; color:#6b7280;">🕒 GIỜ VIỆT NAM</div>
          <div style="font-size:1rem; font-weight:650; color:#243247;">
            {current_time:%H:%M:%S}
          </div>
          <div style="font-size:0.75rem; color:#6b7280;">
            {current_time:%d/%m/%Y}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.title("Payday Compass")
st.caption("Lập kế hoạch đến kỳ lương tiếp theo trong 3 bước đơn giản.")
st.markdown(
    """
    <nav class="quick-start" aria-label="Đi đến các bước">
      <a href="#step-money"><strong>1</strong> Tiền & ngày lương</a>
      <a href="#step-expenses"><strong>2</strong> Hóa đơn & sinh hoạt</a>
      <a href="#step-results"><strong>3</strong> Xem kết quả</a>
      <a href="#step-tools">Mục tiêu & công cụ</a>
    </nav>
    """,
    unsafe_allow_html=True,
)

currency_col, payment_col = st.columns([1, 2])
with currency_col:
    currency = st.selectbox("Đơn vị tiền", ["VND", "USD"], key="currency_choice")
is_vnd = currency == "VND"
unit_label = "VND" if is_vnd else "USD"
payment_options = (
    ["Sacombank", "VietinBank", "MB Bank"] if is_vnd else ["Venmo", "Zelle"]
)
with payment_col:
    payment_method = st.selectbox(
        "Ngân hàng / phương thức minh họa", payment_options
    )

st.caption(
    f"{currency} · {payment_method} · Chỉ dùng để minh họa, chưa kết nối ngân hàng hoặc tự chuyển tiền."
)

st.markdown('<span id="step-money" class="step-anchor"></span>', unsafe_allow_html=True)
st.subheader("1. Tiền hiện tại và ngày nhận lương")
now = vietnam_now().date()
col_balance, col_payday, col_paycheck = st.columns(3)
with col_balance:
    current_balance = amount_input(
        f"Số dư hiện có ({unit_label})", 36_000_000.0 if is_vnd else 1800.0,
        f"balance_{currency}", is_vnd
    )
with col_payday:
    payday = st.date_input("Ngày nhận lương tiếp theo", value=now + timedelta(days=14))
with col_paycheck:
    paycheck_amount = amount_input(
        f"Lương dự kiến nhận ({unit_label})", 34_000_000.0 if is_vnd else 1700.0,
        f"paycheck_{currency}", is_vnd
    )

col_income, col_savings, col_buffer = st.columns(3)
with col_income:
    other_income = amount_input(
        f"Thu nhập khác trước ngày lương ({unit_label})", 0.0,
        f"other_income_{currency}", is_vnd,
        help_text="Chỉ tính khoản bạn dự kiến chắc chắn nhận trước ngày lương tiếp theo.",
    )
with col_savings:
    savings_reserve = amount_input(
        f"Muốn dành riêng để tiết kiệm ({unit_label})", 3_000_000.0 if is_vnd else 150.0,
        f"savings_{currency}", is_vnd,
    )
with col_buffer:
    emergency_buffer = amount_input(
        f"Khoản dự phòng không muốn tiêu ({unit_label})", 4_000_000.0 if is_vnd else 200.0,
        f"buffer_{currency}", is_vnd,
    )

section1_total = st.empty()

if payday < now:
    st.error("Ngày nhận lương tiếp theo không thể ở trong quá khứ.")
    st.stop()

days_until_payday = (payday - now).days

st.markdown('<span id="step-expenses" class="step-anchor"></span>', unsafe_allow_html=True)
st.subheader("2. Hóa đơn và chi phí sinh hoạt")
st.markdown("#### Hóa đơn chưa thanh toán")
bill_count = st.number_input(
    "Số hóa đơn muốn thêm", min_value=1, max_value=12, value=1, step=1
)
st.caption("Chỉ hóa đơn chưa đánh dấu đã trả và đến hạn trước hoặc vào ngày nhận lương mới được trừ khỏi ngân sách kỳ này.")

bills = []
for index in range(int(bill_count)):
    st.markdown(f"**Hóa đơn {index + 1}**")
    name_col, amount_col, due_col, paid_col = st.columns([2, 1.2, 1.5, 1])
    with name_col:
        bill_name = st.text_input(
            "Tên khoản",
            value=["Tiền nhà", "Điện nước", "Điện thoại / internet"][index]
            if index < 3 else f"Hóa đơn {index + 1}",
            key=f"bill_name_{index}",
            label_visibility="collapsed",
            placeholder="Tên hóa đơn",
        )
    with amount_col:
        bill_amount = amount_input(
            f"Số tiền ({unit_label})",
            ([20_000_000.0, 1_500_000.0, 600_000.0][index] if is_vnd else [950.0, 140.0, 70.0][index]) if index < 3 else 0.0,
            f"bill_amount_{currency}_{index}", is_vnd,
        )
    with due_col:
        due_date = st.date_input(
            "Ngày đến hạn",
            value=now + timedelta(days=[5, 8, 10][index] if index < 3 else 7),
            key=f"bill_due_{index}",
            label_visibility="collapsed",
        )
    with paid_col:
        is_paid = st.checkbox(
            "Đã trả",
            value=False,
            key=f"bill_paid_{index}",
        )
    bills.append(
        {
            "name": bill_name.strip() or f"Hóa đơn {index + 1}",
            "amount": float(bill_amount),
            "due_date": due_date,
            "paid": is_paid,
        }
    )

bills_due_before_payday = [
    bill for bill in bills if not bill["paid"] and bill["due_date"] <= payday
]
bills_due_later = [
    bill for bill in bills if not bill["paid"] and bill["due_date"] > payday
]
unpaid_bills = [bill for bill in bills if not bill["paid"]]
total_due = sum(bill["amount"] for bill in bills_due_before_payday)
total_all_unpaid = sum(bill["amount"] for bill in unpaid_bills)

st.markdown("#### Chi phí sinh hoạt")
st.caption(
    "Nhập các khoản sinh hoạt dự kiến. Khoản được tích chọn sẽ được tính vào kế hoạch chi tiêu và số tiền còn lại."
)
living_expense_count = st.number_input(
    "Số khoản chi sinh hoạt", min_value=1, max_value=12, value=1, step=1
)
living_expense_defaults = (
    [3_000_000.0, 1_500_000.0, 1_000_000.0]
    if is_vnd
    else [300.0, 150.0, 80.0]
)
living_expense_labels = ["Tiền ăn / đi chợ", "Mua sắm", "Đi lại"]
living_expenses = []
for index in range(int(living_expense_count)):
    expense_label = (
        living_expense_labels[index]
        if index < len(living_expense_labels)
        else f"Khoản sinh hoạt {index + 1}"
    )
    default_amount = (
        living_expense_defaults[index]
        if index < len(living_expense_defaults)
        else 0.0
    )
    st.markdown(f"**Khoản sinh hoạt {index + 1}**")
    expense_name_col, expense_col, include_col = st.columns([2, 1.5, 1])
    with expense_name_col:
        expense_name = st.text_input(
            "Tên khoản chi",
            value=expense_label,
            key=f"living_expense_name_{index}",
            label_visibility="collapsed",
            placeholder="Tên khoản chi",
        )
    with expense_col:
        expense_amount = amount_input(
            f"Số tiền ({unit_label})",
            default_amount,
            f"living_expense_{currency}_{index}",
            is_vnd,
        )
    with include_col:
        st.write("")
        include_expense = st.checkbox(
            "Tính khoản này",
            value=False,
            key=f"include_living_expense_{currency}_{index}",
        )
    living_expenses.append(
        {
            "name": expense_name.strip() or f"Khoản sinh hoạt {index + 1}",
            "amount": expense_amount,
            "include": include_expense,
        }
    )

selected_living_total = sum(
    item["amount"] for item in living_expenses if item["include"]
)
with st.container(border=True, key="living_budget_card"):
    st.markdown("#### 🎯 Giới hạn chi sinh hoạt")
    st.caption("Đặt mức tối đa muốn chi để theo dõi các khoản sinh hoạt đã chọn.")
    budget_input_col, budget_used_col = st.columns(2)
    with budget_input_col:
        living_budget_limit = amount_input(
            f"Mức chi tối đa ({unit_label})",
            0.0,
            f"living_budget_limit_{currency}",
            is_vnd,
        )
    with budget_used_col:
        st.metric("🧾 Tổng khoản đã chọn", money(selected_living_total))
    if living_budget_limit > 0:
        budget_ratio = selected_living_total / living_budget_limit
        st.progress(
            min(budget_ratio, 1.0),
            text=f"Đã dùng {budget_ratio:.0%} · giới hạn {money(living_budget_limit)}",
        )
        if budget_ratio > 1:
            st.error(
                f"⚠️ Đã vượt giới hạn {money(selected_living_total - living_budget_limit)}. "
                "Hãy cân nhắc giảm hoặc bỏ chọn một khoản."
            )
        elif budget_ratio >= 0.8:
            st.warning(
                f"Sắp chạm giới hạn · còn {money(living_budget_limit - selected_living_total)}."
            )
        else:
            st.success(
                f"Trong giới hạn · còn có thể chi {money(living_budget_limit - selected_living_total)}."
            )
    else:
        st.caption("Nhập mức chi tối đa lớn hơn 0 để bật cảnh báo.")

st.markdown('<span id="step-results" class="step-anchor"></span>', unsafe_allow_html=True)
st.subheader("3. Còn bao nhiêu để chi đến kỳ lương?")
funds_before_payday = current_balance + other_income
money_after_fixed_reserves = (
    funds_before_payday - total_due - savings_reserve - emergency_buffer
)
money_after_planned_living = money_after_fixed_reserves - selected_living_total
shortfall = max(0.0, -money_after_planned_living)
safe_to_spend = max(0.0, money_after_planned_living)
days_for_daily_budget = max(1, days_until_payday)
daily_limit = safe_to_spend / days_for_daily_budget

with st.container(border=True, key="compact_section3"):
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("🧾 Hóa đơn đến hạn", money(total_due))
    metric2.metric("🛒 Sinh hoạt đã chọn", money(selected_living_total))
    metric3.metric("🔒 Tiết kiệm + dự phòng", money(savings_reserve + emergency_buffer))
    metric4.metric("Còn có thể chi", money(safe_to_spend))
    st.caption(
        f"Bình quân còn khoảng **{money(daily_limit)}/ngày** trong {days_for_daily_budget} ngày đến kỳ lương, "
        "sau khi đã giữ tiền cho các khoản ở trên."
    )

if shortfall > 0:
    st.error(
        f"Theo số liệu đã nhập, đang thiếu {money(shortfall)} để chi trả các khoản đã chọn "
        "và giữ tiết kiệm/dự phòng như kế hoạch. Hãy kiểm tra số liệu hoặc điều chỉnh kế hoạch."
    )
else:
    st.success(
        f"Sau khi trừ hóa đơn đến hạn, chi phí sinh hoạt đã chọn, tiết kiệm và dự phòng, "
        f"bạn còn {money(safe_to_spend)} có thể phân bổ đến kỳ lương tiếp theo."
    )

if days_until_payday == 0:
    st.caption("Ngày nhận lương là hôm nay; mức chi mỗi ngày được tính trên 1 ngày để tránh chia cho 0.")
else:
    st.caption(f"Còn {days_until_payday} ngày đến ngày nhận lương tiếp theo ({payday:%b %d, %Y}).")

if bills_due_before_payday:
    st.markdown("#### Các hóa đơn được tính vào ngân sách kỳ này")
    for bill in bills_due_before_payday:
        late_label = " · đã quá hạn" if bill["due_date"] < now else ""
        st.write(f"- {bill['name']} — {money(bill['amount'])}, đến hạn {bill['due_date']:%d/%m/%Y}{late_label}")
else:
    st.write("Chưa có hóa đơn chưa thanh toán đến hạn trước kỳ lương tiếp theo.")

if bills_due_later:
    with st.expander("Hóa đơn chưa đến hạn trong kỳ này"):
        for bill in bills_due_later:
            st.write(f"- {bill['name']} — {money(bill['amount'])}, đến hạn {bill['due_date']:%d/%m/%Y}")

projected_after_payday = (
    current_balance
    + other_income
    + paycheck_amount
    - total_all_unpaid
    - savings_reserve
    - emergency_buffer
)
remaining_after_selected_living = projected_after_payday - selected_living_total
with section1_total.container():
    with st.container(key="compact_section1_totals"):
        st.markdown("#### 💰 Tổng tiền còn lại sau khi tính các khoản đã nhập")
        total_col1, total_col2 = st.columns(2)
        total_col1.metric(
            "🧾 Sau lương, hóa đơn, tiết kiệm và dự phòng",
            money(projected_after_payday),
        )
        total_col2.metric(
            "🛍️ Nếu chi các khoản sinh hoạt đã chọn",
            money(remaining_after_selected_living),
        )
        st.caption(
            "Tổng này tự cập nhật khi bạn thay đổi số liệu. Chi phí sinh hoạt chỉ bị trừ khi bạn tích chọn ở mục 2."
        )

st.subheader("Dự kiến số dư sau khi nhận lương")
st.caption(
    "Tính cả hóa đơn chưa trả (kể cả hóa đơn đến hạn sau ngày lương), tiền tiết kiệm và khoản dự phòng."
)
projected_income = current_balance + other_income + paycheck_amount
projected_deductions = total_all_unpaid + savings_reserve + emergency_buffer
with st.container(border=True, key="compact_section4"):
    projection_cols = st.columns(3)
    projection_cols[0].metric("💵 Tổng tiền + thu nhập", money(projected_income))
    projection_cols[1].metric("🧾 Tổng khoản cần trừ", money(projected_deductions))
    projection_cols[2].metric("🏦 Số dư dự kiến", money(projected_after_payday))
    with st.expander("Xem chi tiết phép tính"):
        st.write(f"**Tiền hiện có:** {money(current_balance)}")
        st.write(f"**Thu nhập khác trước kỳ lương:** + {money(other_income)}")
        st.write(f"**Lương sắp nhận:** + {money(paycheck_amount)}")
        st.write(f"**Hóa đơn chưa trả:** − {money(total_all_unpaid)}")
        st.write(f"**Tiết kiệm:** − {money(savings_reserve)}")
        st.write(f"**Khoản dự phòng:** − {money(emergency_buffer)}")
        st.markdown(
            f"**Phép tính:** {money(projected_income)} − {money(projected_deductions)} "
            f"= **{money(projected_after_payday)}**"
        )
if projected_after_payday < 0:
    st.error(f"Sau các khoản đã nhập, dự kiến còn thiếu {money(abs(projected_after_payday))}.")
else:
    st.success(f"Dự kiến còn lại: **{money(projected_after_payday)}**.")

with st.sidebar:
    with st.container(border=True, key="history_sidebar_card"):
        show_vietnam_clock()
        st.markdown("### Lịch sử kế hoạch")
        st.caption("Lưu và xem lại các kế hoạch đã lưu.")
        history_access_code = st.text_input(
            "Mã riêng tư",
            type="password",
            help="Dùng lại đúng mã này để xem lịch sử. Không chia sẻ mã.",
            key="history_access_code",
        )
        if history_access_code:
            history_owner_hash = hashlib.sha256(
                history_access_code.encode("utf-8")
            ).hexdigest()
            save_history_clicked = st.button(
                "💾 Lưu kế hoạch tháng này", use_container_width=True
            )
            if save_history_clicked:
                history_snapshot = {
                    "currency": currency,
                    "current_balance": current_balance,
                    "payday": payday.isoformat(),
                    "paycheck_amount": paycheck_amount,
                    "other_income": other_income,
                    "savings_reserve": savings_reserve,
                    "emergency_buffer": emergency_buffer,
                    "living_budget_limit": living_budget_limit,
                    "bills": [
                        {
                            "name": bill["name"],
                            "amount": bill["amount"],
                            "due_date": bill["due_date"].isoformat(),
                            "paid": bill["paid"],
                        }
                        for bill in bills
                    ],
                    "living_expenses": living_expenses,
                    "selected_living_total": selected_living_total,
                    "projected_remaining": projected_after_payday,
                    "after_living": remaining_after_selected_living,
                }
                try:
                    save_monthly_history(
                        history_owner_hash,
                        vietnam_now().strftime("%Y-%m"),
                        currency,
                        history_snapshot,
                    )
                    st.success("Đã lưu kế hoạch.")
                except Exception as exc:
                    st.error(f"Chưa lưu được: {exc}")
            try:
                saved_history = load_monthly_history(history_owner_hash)
                if saved_history:
                    st.markdown("**Các lần lưu gần đây**")
                    for row in saved_history:
                        saved_time_label = format_history_timestamp(row["saved_at"])
                        with st.expander(
                            f"{row['month_key']} · {row['currency']} · {saved_time_label}"
                        ):
                            payday_label = date.fromisoformat(
                                str(row["payday"])
                            ).strftime("%d/%m/%Y")
                            if row["currency"] == "VND":
                                projected_label = f"{row['projected_remaining']:,.0f} VND"
                                living_label = f"{row['after_living']:,.0f} VND"
                            else:
                                projected_label = f"${row['projected_remaining']:,.2f}"
                                living_label = f"${row['after_living']:,.2f}"
                            st.caption(f"Ngày nhận lương: {payday_label}")
                            st.write(f"**Số dư dự kiến:** {projected_label}")
                            st.write(f"**Còn lại sau sinh hoạt:** {living_label}")
                            confirm_delete = st.checkbox(
                                "Xác nhận xóa lần lưu này",
                                key=f"confirm_delete_history_{row['id']}",
                            )
                            if st.button(
                                "🗑️ Xóa lần lưu này",
                                key=f"delete_history_{row['id']}",
                                use_container_width=True,
                                disabled=not confirm_delete,
                            ):
                                delete_monthly_history_record(
                                    history_owner_hash, row["id"]
                                )
                                st.rerun()
                    with st.expander("🧹 Xóa toàn bộ lịch sử"):
                        confirm_delete_all = st.checkbox(
                            "Xác nhận xóa tất cả lịch sử của mã này",
                            key="confirm_delete_all_history",
                        )
                        if st.button(
                            "Xóa tất cả",
                            key="delete_all_history",
                            use_container_width=True,
                            disabled=not confirm_delete_all,
                        ):
                            delete_all_monthly_history(history_owner_hash)
                            st.rerun()
                else:
                    st.caption("Chưa có lịch sử. Bấm lưu để tạo bản ghi đầu tiên.")
            except Exception as exc:
                st.error(f"Không đọc được lịch sử: {exc}")
        else:
            st.info("Nhập mã riêng tư để lưu và xem lịch sử.")

st.markdown('<span id="step-tools" class="step-anchor"></span>', unsafe_allow_html=True)
st.subheader("4. Thử xem có nên mua món đồ này")
st.caption(
    "Ước tính số dư sau khi mua món đồ, sau khi đã tính hóa đơn, tiền giữ lại và chi phí sinh hoạt bạn chọn."
)
with st.container(border=True, key="purchase_check"):
    purchase_name_col, purchase_price_col = st.columns([2, 1])
    with purchase_name_col:
        purchase_name = st.text_input(
            "Bạn định mua gì?",
            placeholder="Ví dụ: tai nghe, giày, điện thoại",
            key="purchase_check_name",
        )
    with purchase_price_col:
        purchase_price = amount_input(
            f"Giá món đồ ({unit_label})",
            0.0,
            f"purchase_check_price_{currency}",
            is_vnd,
        )
    if purchase_price > 0:
        after_purchase = remaining_after_selected_living - purchase_price
        st.metric("💰 Còn lại nếu mua", money(after_purchase))
        if after_purchase < 0:
            st.warning(
                f"Món {purchase_name or 'đồ này'} vượt quá ngân sách có thể chi "
                f"{money(abs(after_purchase))}. Có thể cân nhắc đợi hoặc giảm khoản chi khác."
            )
        else:
            st.success(
                f"Dự kiến vẫn còn {money(after_purchase)} sau khi mua {purchase_name or 'món đồ này'}, "
                "không cần lấy vào khoản hóa đơn, tiết kiệm và dự phòng đã giữ lại."
            )
    else:
        st.caption("Nhập giá món đồ để xem thử tác động đến số dư.")

st.subheader("5. Lập mục tiêu tiết kiệm")
st.caption(
    "Nhập sản phẩm, giá, số tiền bạn đã dành dụm và số tiền bạn có thể tiết kiệm mỗi tháng. "
    "App sẽ ước tính thời gian cần để mua được món đó; chưa tính lãi hoặc thay đổi giá sản phẩm."
)
goal_name_col, goal_price_col, goal_date_col = st.columns([2, 1, 1])
with goal_name_col:
    goal_product_name = st.text_input(
        "Bạn muốn mua gì?", placeholder="Ví dụ: Điện thoại, máy tính, xe đạp", key="goal_product_name"
    )
with goal_price_col:
    goal_product_price = amount_input(
        f"Giá sản phẩm ({unit_label})", 20_000_000.0 if is_vnd else 600.0,
        f"goal_product_price_{currency}", is_vnd,
    )
with goal_date_col:
    today_for_goal = vietnam_now().date()
    target_month_index = today_for_goal.month - 1 + 6
    default_target_year = today_for_goal.year + target_month_index // 12
    default_target_month = target_month_index % 12 + 1
    default_target_day = min(
        today_for_goal.day,
        calendar.monthrange(default_target_year, default_target_month)[1],
    )
    goal_target_date = st.date_input(
        "Ngày muốn mua",
        value=date(default_target_year, default_target_month, default_target_day),
        key="goal_target_date",
    )

goal_saved_col, goal_monthly_col = st.columns(2)
with goal_saved_col:
    goal_saved_amount = amount_input(
        f"Đã tiết kiệm cho món này ({unit_label})", 0.0,
        f"goal_saved_amount_{currency}", is_vnd,
    )
with goal_monthly_col:
    goal_monthly_saving = amount_input(
        f"Có thể để dành mỗi tháng ({unit_label})", 3_000_000.0 if is_vnd else 150.0,
        f"goal_monthly_saving_{currency}", is_vnd,
    )

goal_remaining = max(0.0, goal_product_price - goal_saved_amount)
if goal_product_price <= 0:
    st.info("Nhập giá sản phẩm lớn hơn 0 để xem thời gian dự kiến.")
elif goal_remaining == 0:
    st.success(f"Bạn đã dành đủ tiền cho {goal_product_name or 'món đồ này'}.")
elif goal_monthly_saving <= 0:
    st.warning("Nhập số tiền có thể để dành mỗi tháng lớn hơn 0 để app tính thời gian.")
else:
    months_to_goal = math.ceil(goal_remaining / goal_monthly_saving)
    current_date = today_for_goal
    target_month_index = current_date.month - 1 + months_to_goal
    target_year = current_date.year + target_month_index // 12
    target_month = target_month_index % 12 + 1
    target_day = min(current_date.day, calendar.monthrange(target_year, target_month)[1])
    estimated_purchase_date = date(target_year, target_month, target_day)
    goal_progress = min(1.0, goal_saved_amount / goal_product_price)
    st.progress(goal_progress, text=f"Đã có {goal_progress:.0%} giá sản phẩm")
    if goal_target_date < current_date:
        st.warning("Ngày muốn mua đang ở trong quá khứ. Hãy chọn ngày hôm nay hoặc một ngày sau đó.")
    else:
        months_available = (
            (goal_target_date.year - current_date.year) * 12
            + goal_target_date.month - current_date.month
        )
        if goal_target_date.day < current_date.day:
            months_available -= 1
        if months_available <= 0:
            st.warning(
                f"Hạn mua đến trước kỳ tiết kiệm tháng kế tiếp. Bạn còn thiếu "
                f"{money(goal_remaining)}; hãy tăng số tiền đã có hoặc lùi ngày mua. "
                f"Nếu tiếp tục để dành {money(goal_monthly_saving)}/tháng, "
                f"ước tính cần khoảng {months_to_goal} tháng để đủ tiền."
            )
        else:
            required_monthly_saving = math.ceil(goal_remaining / months_available)
            if goal_monthly_saving >= required_monthly_saving:
                st.success(
                    f"Kế hoạch đang đủ để kịp ngày {goal_target_date:%d/%m/%Y}. "
                    f"Bạn cần dành ít nhất {money(required_monthly_saving)}/tháng; "
                    f"với mức hiện tại, dự kiến đủ tiền sau khoảng {months_to_goal} tháng "
                    f"({estimated_purchase_date:%d/%m/%Y})."
                )
            else:
                st.warning(
                    f"Để kịp ngày {goal_target_date:%d/%m/%Y}, cần dành khoảng "
                    f"{money(required_monthly_saving)}/tháng — nhiều hơn mức hiện tại "
                    f"{money(required_monthly_saving - goal_monthly_saving)}/tháng. "
                    f"Với mức hiện tại, dự kiến đủ tiền sau khoảng {months_to_goal} tháng "
                    f"({estimated_purchase_date:%d/%m/%Y})."
                )

st.subheader("6. Hỏi trợ lý chi tiêu")
st.caption(
    "Bạn có thể hỏi về một món đồ đang định mua, cách chia ngân sách hoặc nên mua ngay hay để dành lần sau. "
    "Trợ lý sẽ tham khảo số liệu bạn vừa nhập để gợi ý."
)


def get_openrouter_api_key():
    try:
        key = st.secrets.get("OPENROUTER_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("OPENROUTER_API_KEY", "")


if "spending_chat_history" not in st.session_state:
    st.session_state.spending_chat_history = []

for message in st.session_state.spending_chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("Ví dụ: Mình có nên mua đôi giày này tháng này không?")
if user_question:
    st.session_state.spending_chat_history.append(
        {"role": "user", "content": user_question}
    )
    with st.chat_message("user"):
        st.markdown(user_question)

    api_key = get_openrouter_api_key()
    if not api_key:
        answer = (
            "Chưa cấu hình API key nên trợ lý chưa thể trả lời. "
            "Hãy thêm `OPENROUTER_API_KEY` trong mục Secrets của Streamlit Cloud "
            "hoặc trong file `.streamlit/secrets.toml` khi chạy trên máy."
        )
        with st.chat_message("assistant"):
            st.info(answer)
    else:
        system_prompt = (
            "Bạn là trợ lý hướng dẫn lập ngân sách cá nhân, trả lời bằng tiếng Việt đơn giản, thân thiện. "
            "Giúp người dùng cân nhắc mua sắm dựa trên nhu cầu, khoản thiết yếu, số dư và ngân sách họ cung cấp. "
            "Khi phù hợp, hỏi giá món đồ và thời điểm cần dùng; có thể gợi ý quy tắc chờ 24 giờ, so sánh giá, "
            "hoặc đặt mục tiêu tiết kiệm. Không gây áp lực mua hàng, không bịa dữ liệu và không yêu cầu thông tin "
            "đăng nhập ngân hàng, mật khẩu hay mã OTP. Nêu rõ đây là gợi ý tham khảo, không phải tư vấn tài chính chuyên nghiệp.\n\n"
            f"Thông tin kế hoạch hiện tại: đơn vị {currency}; số dư hiện có {money(current_balance)}; "
            f"thu nhập khác trước kỳ lương {money(other_income)}; lương dự kiến {money(paycheck_amount)}; "
            f"hóa đơn chưa trả {money(total_all_unpaid)}; tiền tiết kiệm dự kiến {money(savings_reserve)}; "
            f"khoản dự phòng {money(emergency_buffer)}; còn lại sau lương và các hóa đơn là "
            f"{money(projected_after_payday)}; còn lại nếu chi các khoản sinh hoạt đã chọn là "
            f"{money(remaining_after_selected_living)}. Đây chỉ là dữ liệu người dùng tự nhập, "
            "chưa xác minh với ngân hàng."
        )
        request_messages = [
            {"role": "system", "content": system_prompt},
            *st.session_state.spending_chat_history[-12:],
        ]
        request_body = json.dumps(
            {
                "model": "openai/gpt-4o-mini",
                "messages": request_messages,
                "temperature": 0.4,
                "max_tokens": 500,
            }
        ).encode("utf-8")
        request = Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with st.chat_message("assistant"):
            with st.spinner("Đang xem câu hỏi và ngân sách của bạn..."):
                try:
                    with urlopen(request, timeout=45) as response:
                        result = json.loads(response.read().decode("utf-8"))
                    answer = result["choices"][0]["message"]["content"].strip()
                    if not answer:
                        answer = "Mình chưa nhận được câu trả lời. Bạn thử hỏi lại nhé."
                    st.markdown(answer)
                except HTTPError as error:
                    if error.code in (401, 403):
                        answer = "API key không hợp lệ hoặc chưa được cấp quyền. Hãy kiểm tra lại Secrets trên Streamlit."
                    elif error.code == 429:
                        answer = "Dịch vụ đang giới hạn yêu cầu hoặc tài khoản API đã hết hạn mức. Bạn thử lại sau nhé."
                    else:
                        answer = f"Dịch vụ chat đang báo lỗi (mã {error.code}). Bạn thử lại sau nhé."
                    st.error(answer)
                except (URLError, TimeoutError):
                    answer = "Không kết nối được dịch vụ chat. Hãy kiểm tra mạng rồi thử lại."
                    st.error(answer)
                except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                    answer = "Dịch vụ chat trả về dữ liệu chưa đúng định dạng. Bạn thử lại sau nhé."
                    st.error(answer)
        st.session_state.spending_chat_history.append(
            {"role": "assistant", "content": answer}
        )

# Tải lịch kế hoạch để lưu hoặc chia sẻ.
csv_buffer = io.StringIO()
writer = csv.writer(csv_buffer)
writer.writerow(["Payday Compass - kế hoạch ngân sách"])
writer.writerow(["Ngày nhận lương", payday.isoformat()])
writer.writerow([f"Đơn vị tiền tệ", currency])
writer.writerow([f"Ngân hàng / phương thức", payment_method])
writer.writerow([f"Số dư hiện có ({currency})", f"{current_balance:.0f}" if is_vnd else f"{current_balance:.2f}"])
writer.writerow([f"Thu nhập khác trước ngày lương ({currency})", f"{other_income:.0f}" if is_vnd else f"{other_income:.2f}"])
writer.writerow([f"Tiết kiệm dự kiến ({currency})", f"{savings_reserve:.0f}" if is_vnd else f"{savings_reserve:.2f}"])
writer.writerow([f"Khoản dự phòng ({currency})", f"{emergency_buffer:.0f}" if is_vnd else f"{emergency_buffer:.2f}"])
writer.writerow([f"Tổng hóa đơn chưa thanh toán ({currency})", f"{total_all_unpaid:.0f}" if is_vnd else f"{total_all_unpaid:.2f}"])
writer.writerow([f"Dự kiến còn lại sau lương và hóa đơn đã nhập ({currency})", f"{projected_after_payday:.0f}" if is_vnd else f"{projected_after_payday:.2f}"])
writer.writerow([])
writer.writerow(["Tên hóa đơn", f"Số tiền {currency}", "Ngày đến hạn", "Đã thanh toán", "Được tính kỳ này"])
for bill in bills:
    include_now = (not bill["paid"]) and bill["due_date"] <= payday
    writer.writerow([
        bill["name"],
        f"{bill['amount']:.0f}" if is_vnd else f"{bill['amount']:.2f}",
        bill["due_date"].isoformat(),
        "Có" if bill["paid"] else "Không",
        "Có" if include_now else "Không",
    ])
writer.writerow([])
writer.writerow(["Tên chi phí sinh hoạt", f"Số tiền {currency}", "Tính vào kế hoạch"])
for expense in living_expenses:
    writer.writerow([
        expense["name"],
        f"{expense['amount']:.0f}" if is_vnd else f"{expense['amount']:.2f}",
        "Có" if expense["include"] else "Không",
    ])
writer.writerow([
    "Tổng chi phí sinh hoạt đã chọn",
    f"{selected_living_total:.0f}" if is_vnd else f"{selected_living_total:.2f}",
    "",
])
writer.writerow([
    "Còn lại sau chi phí sinh hoạt đã chọn",
    f"{remaining_after_selected_living:.0f}" if is_vnd else f"{remaining_after_selected_living:.2f}",
    "",
])
csv_data = ("\ufeff" + csv_buffer.getvalue()).encode("utf-8")

st.download_button(
    "⬇️ Tải kế hoạch ngân sách CSV",
    data=csv_data,
    file_name=f"payday_compass_{vietnam_now():%Y%m%d}.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption(
    "Payday Compass chỉ ước tính từ dữ liệu bạn nhập, không kết nối ngân hàng và không tự động thanh toán. "
    "Lịch sử được lưu trong SQLite của môi trường đang chạy; trên Streamlit Cloud, dữ liệu có thể mất nếu máy chủ được dựng lại. "
    "Mức chi mỗi ngày là gợi ý số học, không phải lời khuyên tài chính."
)

