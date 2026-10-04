import csv
import io
from datetime import date, timedelta

import streamlit as st


st.set_page_config(
    page_title="Payday Compass",
    page_icon="🧭",
    layout="centered",
)


currency = st.selectbox("Đơn vị tiền tệ", ["VND", "USD"], key="currency_choice")
is_vnd = currency == "VND"
unit_label = "VND" if is_vnd else "USD"
step = 100_000.0 if is_vnd else 10.0
number_format = "%.0f" if is_vnd else "%.2f"


def money(amount):
    if is_vnd:
        return f"{amount:,.0f}".replace(",", ".") + " VND"
    return f"${amount:,.2f}"


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
    current_balance = st.number_input(
        f"Số dư hiện có ({unit_label})", min_value=0.0,
        value=36_000_000.0 if is_vnd else 1800.0,
        step=step if is_vnd else 50.0, format=number_format, key=f"balance_{currency}"
    )
with col_payday:
    payday = st.date_input("Ngày nhận lương tiếp theo", value=now + timedelta(days=14))
with col_paycheck:
    paycheck_amount = st.number_input(
        f"Lương dự kiến nhận ({unit_label})", min_value=0.0,
        value=34_000_000.0 if is_vnd else 1700.0,
        step=step if is_vnd else 50.0, format=number_format, key=f"paycheck_{currency}"
    )

col_income, col_savings, col_buffer = st.columns(3)
with col_income:
    other_income = st.number_input(
        f"Thu nhập khác trước ngày lương ({unit_label})",
        min_value=0.0,
        value=0.0,
        step=step if is_vnd else 25.0,
        format=number_format,
        key=f"other_income_{currency}",
        help="Chỉ tính khoản bạn dự kiến chắc chắn nhận trước ngày lương tiếp theo.",
    )
with col_savings:
    savings_reserve = st.number_input(
        f"Muốn dành riêng để tiết kiệm ({unit_label})",
        min_value=0.0,
        value=3_000_000.0 if is_vnd else 150.0,
        step=step if is_vnd else 25.0,
        format=number_format,
        key=f"savings_{currency}",
    )
with col_buffer:
    emergency_buffer = st.number_input(
        f"Khoản dự phòng không muốn tiêu ({unit_label})",
        min_value=0.0,
        value=4_000_000.0 if is_vnd else 200.0,
        step=step if is_vnd else 25.0,
        format=number_format,
        key=f"buffer_{currency}",
    )

if payday < now:
    st.error("Ngày nhận lương tiếp theo không thể ở trong quá khứ.")
    st.stop()

days_until_payday = (payday - now).days

st.subheader("2. Hóa đơn chưa thanh toán")
bill_count = st.number_input(
    "Số hóa đơn muốn thêm", min_value=1, max_value=12, value=3, step=1
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
        bill_amount = st.number_input(
            f"Số tiền ({unit_label})",
            min_value=0.0,
            value=([20_000_000.0, 1_500_000.0, 600_000.0][index] if is_vnd else [950.0, 140.0, 70.0][index]) if index < 3 else 0.0,
            step=step,
            format=number_format,
            key=f"bill_amount_{currency}_{index}",
            label_visibility="collapsed",
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

st.subheader("3. Ngân sách từ hôm nay đến ngày nhận lương")
funds_before_payday = current_balance + other_income
money_after_reserves = funds_before_payday - total_due - savings_reserve - emergency_buffer
shortfall = max(0.0, -money_after_reserves)
safe_to_spend = max(0.0, money_after_reserves)
days_for_daily_budget = max(1, days_until_payday)
daily_limit = safe_to_spend / days_for_daily_budget

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Hóa đơn cần trả trước kỳ lương", money(total_due))
metric2.metric("Còn có thể phân bổ", money(safe_to_spend))
metric3.metric("Mức chi trung bình mỗi ngày", money(daily_limit))

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
st.subheader("4. Còn bao nhiêu sau khi nhận lương và trả hết chi phí đã nhập?")
st.caption(
    "Ước tính này trừ toàn bộ hóa đơn chưa đánh dấu đã trả, kể cả khoản đến hạn sau ngày lương, "
    "rồi trừ tiền tiết kiệm và khoản dự phòng đã đặt."
)
projection_cols = st.columns(4)
projection_cols[0].metric("Số dư hiện tại", money(current_balance))
projection_cols[1].metric("Thu nhập trước ngày lương", money(other_income))
projection_cols[2].metric("Lương sắp nhận", money(paycheck_amount))
projection_cols[3].metric("Tổng hóa đơn chưa trả", money(total_all_unpaid))
st.write(
    f"**Phép tính:** {money(current_balance)} + {money(other_income)} + "
    f"{money(paycheck_amount)} − {money(total_all_unpaid)} − "
    f"{money(savings_reserve)} tiết kiệm − {money(emergency_buffer)} dự phòng"
)
if projected_after_payday < 0:
    st.error(f"Sau các khoản đã nhập, dự kiến còn thiếu {money(abs(projected_after_payday))}.")
else:
    st.success(f"Dự kiến còn lại: **{money(projected_after_payday)}**.")

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

