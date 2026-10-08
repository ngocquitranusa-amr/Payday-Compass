import csv
import io
import json
import calendar
import math
import os
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


st.set_page_config(
    page_title="Payday Compass",
    page_icon="🧭",
    layout="centered",
)

st.markdown(
    """
    <style>
    div.st-key-compact_section3 [data-testid="stMetricValue"],
    div.st-key-compact_section4 [data-testid="stMetricValue"],
    div.st-key-compact_section1_totals [data-testid="stMetricValue"] {
        font-size: 1rem !important;
        line-height: 1.25 !important;
        white-space: nowrap;
    }
    div.st-key-compact_section3 [data-testid="stMetricLabel"],
    div.st-key-compact_section4 [data-testid="stMetricLabel"],
    div.st-key-compact_section1_totals [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
    }
    div.st-key-compact_section1_totals [data-testid="stMetric"] {
        background: #f7f9fc;
        border: 1px solid #e5eaf1;
        border-radius: 12px;
        padding: 12px 14px;
        min-height: 92px;
    }
    div.st-key-compact_section3 [data-testid="stMetric"],
    div.st-key-compact_section4 [data-testid="stMetric"],
    div.st-key-living_result [data-testid="stMetric"] {
        background: #f7f9fc;
        border: 1px solid #e5eaf1;
        border-radius: 12px;
        padding: 12px 14px;
        min-height: 92px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


currency = st.selectbox("Đơn vị tiền tệ", ["VND", "USD"], key="currency_choice")
is_vnd = currency == "VND"
unit_label = "VND" if is_vnd else "USD"


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


payment_options = (
    ["Sacombank", "VietinBank", "MB Bank"]
    if is_vnd
    else ["Venmo", "Zelle"]
)
payment_method = st.selectbox("Ngân hàng / phương thức thanh toán", payment_options)


st.title("🧭 Payday Compass")
st.subheader("Biết mình còn bao nhiêu tiền an toàn để tiêu")
st.write(
    "Lập kế hoạch từ hôm nay đến ngày nhận lương tiếp theo: giữ riêng tiền hóa đơn, "
    "tiền tiết kiệm và khoản dự phòng trước khi ước tính ngân sách chi tiêu."
)

feature_columns = st.columns(4)
features = [
    ("💵", "Tiền hiện có", "Nhập số dư hiện tại."),
    ("🧾", "Hóa đơn sắp tới", "Liệt kê khoản chưa thanh toán."),
    ("🎯", "Tiền cần giữ lại", "Đặt tiết kiệm và khoản dự phòng."),
    ("📆", "Mức chi mỗi ngày", "Ước tính đến kỳ lương tới."),
]
for column, (icon, title, detail) in zip(feature_columns, features):
    with column:
        with st.container(border=True):
            st.markdown(f"### {icon}")
            st.markdown(f"**{title}**")
            st.caption(detail)

if is_vnd:
    st.info(
        f"Đang dùng VND và chọn {payment_method}. Đây là lựa chọn để minh họa trong app; "
        "app chưa kết nối tài khoản hoặc tự chuyển tiền. Bạn cần xác nhận giao dịch trong ứng dụng ngân hàng chính thức."
    )
else:
    st.info(
        f"Đang dùng USD và chọn {payment_method}. Đây là lựa chọn để minh họa trong app; "
        "app chưa kết nối tài khoản hoặc tự chuyển tiền. Bạn cần xác nhận giao dịch trong ứng dụng chính thức."
    )

st.subheader("1. Tình hình tiền hiện tại")
now = date.today()
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

st.subheader("2. Hóa đơn và chi tiêu dự kiến")
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
    "Nhập các khoản sinh hoạt dự kiến. Chỉ những khoản được tích chọn mới bị trừ trong kịch bản chi tiêu."
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

st.subheader("3. 🧮 Ngân sách đến kỳ lương")
funds_before_payday = current_balance + other_income
money_after_reserves = funds_before_payday - total_due - savings_reserve - emergency_buffer
shortfall = max(0.0, -money_after_reserves)
safe_to_spend = max(0.0, money_after_reserves)
days_for_daily_budget = max(1, days_until_payday)
daily_limit = safe_to_spend / days_for_daily_budget

with st.container(border=True, key="compact_section3"):
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("🧾 Hóa đơn đến hạn", money(total_due))
    metric2.metric(
        "🔒 Tiền tiết kiệm + dự phòng",
        money(savings_reserve + emergency_buffer),
    )
    metric3.metric("✅ Còn có thể chi", money(safe_to_spend))
    st.caption(
        f"📆 Bình quân khoảng **{money(daily_limit)} mỗi ngày** trong {days_for_daily_budget} ngày đến kỳ lương."
    )

if shortfall > 0:
    st.error(
        f"Theo số liệu đã nhập, đang thiếu {money(shortfall)} để thanh toán hóa đơn, "
        "giữ khoản tiết kiệm và khoản dự phòng như kế hoạch. Hãy kiểm tra số liệu hoặc điều chỉnh kế hoạch."
    )
else:
    st.success(
        f"Sau khi trừ hóa đơn đến hạn, tiền tiết kiệm và khoản dự phòng, "
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
selected_living_total = sum(
    item["amount"] for item in living_expenses if item["include"]
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

st.subheader("4. 💰 Dự kiến còn lại sau khi nhận lương")
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

st.markdown("#### Kết quả nếu chi các khoản đã chọn")
if st.button("🧮 Tính số dư nếu chi các khoản đã chọn", use_container_width=True):
    selected_living_expenses = [item for item in living_expenses if item["include"]]
    living_expense_total = selected_living_total
    remaining_after_living = remaining_after_selected_living

    with st.container(border=True, key="living_result"):
        st.markdown("#### 🧮 Kết quả kịch bản chi tiêu")
        result_col1, result_col2 = st.columns(2)
        result_col1.metric("🛍️ Tổng khoản sinh hoạt đã chọn", money(living_expense_total))
        result_col2.metric("💰 Còn lại sau các khoản đã chọn", money(remaining_after_living))
    if selected_living_expenses:
        st.write("**Đã tính:** " + ", ".join(item["name"] for item in selected_living_expenses))
    else:
        st.info("Bạn chưa chọn khoản sinh hoạt nào nên số dư dự kiến không thay đổi.")
    if remaining_after_living < 0:
        st.error("Các khoản đã chọn vượt quá số dư dự kiến. Hãy thử bỏ chọn hoặc giảm một khoản.")

st.subheader("6. 🎯 Để dành mua món bạn muốn")
st.caption(
    "Nhập sản phẩm, giá, số tiền bạn đã dành dụm và số tiền bạn có thể tiết kiệm mỗi tháng. "
    "App sẽ ước tính thời gian cần để mua được món đó."
)
goal_name_col, goal_price_col = st.columns([2, 1])
with goal_name_col:
    goal_product_name = st.text_input(
        "Bạn muốn mua gì?", placeholder="Ví dụ: Điện thoại, máy tính, xe đạp", key="goal_product_name"
    )
with goal_price_col:
    goal_product_price = amount_input(
        f"Giá sản phẩm ({unit_label})", 20_000_000.0 if is_vnd else 600.0,
        f"goal_product_price_{currency}", is_vnd,
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
    current_date = date.today()
    target_month_index = current_date.month - 1 + months_to_goal
    target_year = current_date.year + target_month_index // 12
    target_month = target_month_index % 12 + 1
    target_day = min(current_date.day, calendar.monthrange(target_year, target_month)[1])
    estimated_purchase_date = date(target_year, target_month, target_day)
    goal_progress = min(1.0, goal_saved_amount / goal_product_price)
    st.progress(goal_progress, text=f"Đã có {goal_progress:.0%} giá sản phẩm")
    st.success(
        f"Còn thiếu {money(goal_remaining)}. Nếu đều đặn để dành {money(goal_monthly_saving)} mỗi tháng, "
        f"bạn cần khoảng **{months_to_goal} tháng** và có thể mua {goal_product_name or 'món đồ này'} "
        f"khoảng ngày {estimated_purchase_date:%d/%m/%Y}."
    )

st.subheader("7. 💬 Hỏi trợ lý chi tiêu")
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
csv_data = ("\ufeff" + csv_buffer.getvalue()).encode("utf-8")

st.download_button(
    "⬇️ Tải kế hoạch ngân sách CSV",
    data=csv_data,
    file_name=f"payday_compass_{date.today():%Y%m%d}.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption(
    "Payday Compass chỉ ước tính từ dữ liệu bạn nhập, không kết nối ngân hàng và không tự động thanh toán. "
    "Mức chi mỗi ngày là gợi ý số học, không phải lời khuyên tài chính. App không lưu lịch sử sau khi tải lại trang."
)

