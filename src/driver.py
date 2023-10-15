from collections import defaultdict
from datetime import datetime
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st

from debt_data_parser import parse_debt_data_file
from debt_projector import Budget, build_debt_projection

DATA_FILE = "data/MSPD_DetailSecty_20230930_20230930.csv"

DATA_FILES = {
    "2023-08-31": "data/MSPD_DetailSecty_20230831_20230831.csv",
    "2023-09-30": "data/MSPD_DetailSecty_20230930_20230930.csv",
}
st.header(
    "Estimated federal debt under different interest rate, revenue and spending assumptions"
)
with st.sidebar:
    data_file_key: str = st.selectbox(
        label="Treasury Data Dump to Use", options=DATA_FILES.keys()
    )
    spending = st.number_input(
        label="2023 Annual Spending (in millions)",
        min_value=5000000,
        max_value=8000000,
        value=6500000,
        step=500000,
    )
    mandatory_spending = st.number_input(
        label="Estimated Federal Mandatory Spending Percent",
        min_value=50,
        max_value=80,
        value=66,
        step=5,
    )
    spending_growth_rate = st.number_input(
        label="Annualized Spending Growth Rate %",
        min_value=-2.0,
        max_value=10.0,
        value=2.0,
        step=0.5,
    )
    revenue = st.number_input(
        label="2023 Annual Revenue (in millions)",
        min_value=4000000,
        max_value=7000000,
        value=5000000,
        step=500000,
    )
    revenue_growth_rate = st.number_input(
        label="Annualized Revenue Growth Rate %",
        min_value=-2.0,
        max_value=10.0,
        value=2.0,
        step=0.5,
    )
    short_term_interest_rate = st.number_input(
        label="Modeled Short-term Interest Rate",
        min_value=-1.0,
        max_value=10.0,
        value=5.5,
        step=0.25,
    )
    long_term_interest_rate = st.number_input(
        label="Modeled Long-term Interest Rate",
        min_value=-1.0,
        max_value=12.0,
        value=5.0,
        step=0.25,
    )
debts = parse_debt_data_file(DATA_FILES[data_file_key])
total = 0.0


STANDARD_TERMS = {
    28: "4 week",
    56: "8 week",
    91: "13 week",
    119: "17 week",
    182: "26 week",
    364: "52 week",
    730: "2 year",
    1825: "5 year",
    3650: "10 year",
    7300: "20 year",
    10950: "30 year",
}


def normalize_term(term: int) -> int:
    standard_term = min([(abs(term - x), x) for x in STANDARD_TERMS])[1]
    return standard_term


debt_total_by_term: Dict[int, float] = defaultdict(float)
for debt in debts:
    total += debt.amount
    term = (debt.maturity_date - debt.issue_date).days
    debt_total_by_term[normalize_term(term)] += debt.amount

debt_distribution = [
    (
        key,
        value * 100 / total,
        short_term_interest_rate if key <= 730 else long_term_interest_rate,
    )
    for (key, value) in debt_total_by_term.items()
]
debt_coarse_distribution = {
    "Short-term (2 years or less)": sum(
        [x for (k, x, i) in debt_distribution if k <= 730]
    ),
    "Long-term (More than 2 years)": sum(
        [x for (k, x, i) in debt_distribution if k > 730]
    ),
}
dist_df = pd.DataFrame(debt_coarse_distribution.items(), columns=["term", "fraction"])
dist_chart = (
    alt.Chart(dist_df)
    .mark_arc()
    .encode(
        theta=alt.Theta("fraction").stack(True),
        color=alt.Color("term"),
    )
    .properties(title="Distribution of Short vs Long Term Debt")
)
st.altair_chart(dist_chart, use_container_width=True)
projection = build_debt_projection(
    debts,
    Budget(
        spending=spending,
        revenue=revenue,
        annual_spending_growth_pct=spending_growth_rate,
        annual_revenue_growth_pct=revenue_growth_rate,
    ),
    datetime.strptime(data_file_key, "%Y-%m-%d"),
    datetime.strptime("2043-12-01", "%Y-%m-%d"),
    new_debt_distribution=debt_distribution,
)
data = pd.DataFrame(filter(lambda p: p.year >= datetime(2025, 1, 1), projection))
data["label"] = data["debt_amount_eoy"].apply(lambda d: f"{int(d//1000000)}T")
data["interest_label"] = data["interest_paid"].apply(lambda d: f"{(int)(d // 1000)}B")
data["average_interest_rate"] = data["interest_paid"] / data["debt_amount_eoy"]
data["discretionary_spending"] = data["spending"].apply(
    lambda s: s * (1 - mandatory_spending / 100)
)
total_debt_line = (
    alt.Chart(data)
    .mark_point()
    .encode(
        x=alt.X("year", title="Year"),
        y=alt.X("debt_amount_eoy", title="Debt (in millions)"),
        size=alt.X("debt_amount_eoy", legend=None),
        tooltip=[
            alt.Tooltip("year", title="Year", timeUnit="year"),
            alt.Tooltip("label", title="amount"),
            alt.Tooltip(
                "average_interest_rate", title="Average Interest Rate", format=".2%"
            ),
        ],
    )
    .properties(title="US Federal Debt Projection")
)

labels = total_debt_line.mark_text(align="left", baseline="middle", dx=16).encode(
    text="label"
)

chart = alt.layer(total_debt_line).resolve_scale(y="independent")
st.altair_chart(chart, use_container_width=True)

combined_line = (
    alt.Chart(data)
    .transform_fold(["interest_paid", "revenue", "spending", "discretionary_spending"])
    .mark_line()
    .encode(
        x=alt.X("year", title="Year"),
        y=alt.X("value:Q", title="Amount (in millions)"),
        color=alt.Color("key:N", legend=None),
    )
    .properties(
        title="US Federal Budget Revenue, Spending and Interest Expense Projection"
    )
)
label = combined_line.encode(
    x=alt.X("year", aggregate="max"),
    y=alt.Y("value:Q", aggregate={"argmax": "year"}),
    text="key:N",
)
text = label.mark_text(align="left", dx=4)
st.altair_chart(combined_line + text, use_container_width=True)
