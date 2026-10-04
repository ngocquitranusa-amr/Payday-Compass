import csv
import io
from datetime import date, timedelta

import streamlit as st


st.set_page_config(
    page_title="Payday Compass",
    page_icon="🧭",
    layout="centered",
)


def dollars(amount):
    return f"${amount:,.2f}"


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

st.info(
    "Bản demo dùng USD và dữ liệu do bạn nhập. Không kết nối ngân hàng, "
    "không tự động đọc giao dịch và không chuyển tiền."
)

st.subheader("1. Tình hình tiền hiện tại")
now = date.today()
col_balance, col_payday, col_paycheck = st.columns(3)
with col_balance:
    current_balance = st.number_input(
        "Số dư hiện có (USD)", min_value=0.0, value=1800.0, step=50.0, format="%.2f"
    )
with col_payday:
    payday = st.date_input("Ngày nhận lương tiếp theo", value=now + timedelta(days=14))
with col_paycheck:
    paycheck_amount = st.number_input(
        "Lương dự kiến nhận (USD)", min_value=0.0, value=1700.0, step=50.0, format="%.2f"
    )

col_income, col_savings, col_buffer = st.columns(3)
with col_income:
    other_income = st.number_input(
        "Thu nhập khác trước ngày lương (USD)",
        min_value=0.0,
        value=0.0,
        step=25.0,
        format="%.2f",
        help="Chỉ tính khoản bạn dự kiến chắc chắn nhận trước ngày lương tiếp theo.",
    )
with col_savings:
    savings_reserve = st.number_input(
        "Muốn dành riêng để tiết kiệm (USD)",
        min_value=0.0,
        value=150.0,
        step=25.0,
        format="%.2f",
    )
with col_buffer:
    emergency_buffer = st.number_input(
        "Khoản dự phòng không muốn tiêu (USD)",
        min_value=0.0,
        value=200.0,
        step=25.0,
        format="%.2f",
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
            "Số tiền (USD)",
            min_value=0.0,
            value=[950.0, 140.0, 70.0][index] if index < 3 else 0.0,
            step=10.0,
            format="%.2f",
            key=f"bill_amount_{index}",
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
total_due = sum(bill["amount"] for bill in bills_due_before_payday)

st.subheader("3. Ngân sách từ hôm nay đến ngày nhận lương")
funds_before_payday = current_balance + other_income
money_after_reserves = funds_before_payday - total_due - savings_reserve - emergency_buffer
shortfall = max(0.0, -money_after_reserves)
safe_to_spend = max(0.0, money_after_reserves)
days_for_daily_budget = max(1, days_until_payday)
daily_limit = safe_to_spend / days_for_daily_budget

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Hóa đơn cần trả trước kỳ lương", dollars(total_due))
metric2.metric("Còn có thể phân bổ", dollars(safe_to_spend))
metric3.metric("Mức chi trung bình mỗi ngày", dollars(daily_limit))

if shortfall > 0:
    st.error(
        f"Theo số liệu đã nhập, đang thiếu {dollars(shortfall)} để thanh toán hóa đơn, "
        "giữ khoản tiết kiệm và khoản dự phòng như kế hoạch. Hãy kiểm tra số liệu hoặc điều chỉnh kế hoạch."
    )
else:
    st.success(
        f"Sau khi trừ hóa đơn đến hạn, tiền tiết kiệm và khoản dự phòng, "
        f"bạn còn {dollars(safe_to_spend)} có thể phân bổ đến kỳ lương tiếp theo."
    )

if days_until_payday == 0:
    st.caption("Ngày nhận lương là hôm nay; mức chi mỗi ngày được tính trên 1 ngày để tránh chia cho 0.")
else:
    st.caption(f"Còn {days_until_payday} ngày đến ngày nhận lương tiếp theo ({payday:%b %d, %Y}).")

if bills_due_before_payday:
    st.markdown("#### Các hóa đơn được tính vào ngân sách kỳ này")
    for bill in bills_due_before_payday:
        late_label = " · đã quá hạn" if bill["due_date"] < now else ""
        st.write(f"- {bill['name']} — {dollars(bill['amount'])}, đến hạn {bill['due_date']:%b %d}{late_label}")
else:
    st.write("Chưa có hóa đơn chưa thanh toán đến hạn trước kỳ lương tiếp theo.")

if bills_due_later:
    with st.expander("Hóa đơn chưa đến hạn trong kỳ này"):
        for bill in bills_due_later:
            st.write(f"- {bill['name']} — {dollars(bill['amount'])}, đến hạn {bill['due_date']:%b %d}")

projected_after_payday = money_after_reserves + paycheck_amount
st.metric(
    "Số dư dự kiến sau kỳ lương (nếu không phát sinh khoản khác)",
    dollars(projected_after_payday),
    help="Ước tính số tiền còn lại sau các khoản đã nhập và cộng lương dự kiến; chi tiêu khác chưa được trừ.",
)

# Tải lịch kế hoạch để lưu hoặc chia sẻ.
csv_buffer = io.StringIO()
writer = csv.writer(csv_buffer)
writer.writerow(["Payday Compass - kế hoạch ngân sách"])
writer.writerow(["Ngày nhận lương", payday.isoformat()])
writer.writerow(["Số dư hiện có (USD)", f"{current_balance:.2f}"])
writer.writerow(["Thu nhập khác trước ngày lương (USD)", f"{other_income:.2f}"])
writer.writerow(["Tiết kiệm dự kiến (USD)", f"{savings_reserve:.2f}"])
writer.writerow(["Khoản dự phòng (USD)", f"{emergency_buffer:.2f}"])
writer.writerow([])
writer.writerow(["Tên hóa đơn", "Số tiền USD", "Ngày đến hạn", "Đã thanh toán", "Được tính kỳ này"])
for bill in bills:
    include_now = (not bill["paid"]) and bill["due_date"] <= payday
    writer.writerow([
        bill["name"],
        f"{bill['amount']:.2f}",
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

