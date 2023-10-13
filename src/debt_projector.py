import heapq
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

import pandas as pd

from debt_data_parser import Debt


@dataclass
class DebtProjection:
    year: datetime
    debt_amount_eoy: float
    spending: float
    revenue: float
    interest_paid: float


@dataclass
class Budget:
    spending: float
    revenue: float
    annual_spending_growth_pct: float
    annual_revenue_growth_pct: float


def build_debt_projection(
    starting_debts: List[Debt],
    starting_budget: Budget,
    start_date: datetime,
    projection_end_date: datetime,
    new_debt_distribution: List[Tuple[int, float, float]],
) -> List[DebtProjection]:
    debts_by_maturity = [
        (d.maturity_date, d.amount, d)
        for d in starting_debts
        if d.maturity_date >= start_date
    ]
    new_debt_issuances: List[datetime] = (
        pd.date_range(start_date, projection_end_date, freq="MS")
        .to_pydatetime()
        .tolist()
    )
    debt_events = debts_by_maturity + [(d, 0, None) for d in new_debt_issuances]
    heapq.heapify(debt_events)
    accrued_interest = 0.0
    accrued_principal = 0.0

    baseline_monthly_spend = starting_budget.spending / 12
    monthly_spending_growth = starting_budget.annual_spending_growth_pct / (12 * 100)

    baseline_monthly_revenue = starting_budget.revenue / 12
    monthly_revenue_growth = starting_budget.annual_revenue_growth_pct / (12 * 100)
    current_year = start_date
    current_year_interest = 0.0
    current_year_spending = 0.0
    current_year_revenue = 0.0
    result = []

    while debt_events:
        event = heapq.heappop(debt_events)
        if event[0] > projection_end_date:
            break
        if event[2] is None:
            # A new month is starting.
            existing_total_debt = 0.0
            for _1, _2, existing_debt in debt_events:
                if existing_debt is not None:
                    accrued_interest += (
                        existing_debt.yield_rate / (12 * 100)
                    ) * existing_debt.amount
                    existing_total_debt += existing_debt.amount
            event_date = event[0]
            months_since_start = (event_date.year - start_date.year) * 12 + (
                event_date.month - start_date.month
            )
            spending = baseline_monthly_spend * (
                1 + monthly_spending_growth * months_since_start
            )
            revenue = baseline_monthly_revenue * (
                1 + monthly_revenue_growth * months_since_start
            )
            new_debt = (spending + accrued_interest + accrued_principal) - revenue
            if new_debt < 0:
                # TODO: Handle surplus
                raise ProjectionException("Unexpected surplus, giving up!")
            for term_in_months, pct, yield_rate in new_debt_distribution:
                new_debt_issue = Debt(
                    new_debt * pct / 100,
                    event_date,
                    event_date + timedelta(days=(int)(term_in_months / 12 * 365)),
                    yield_rate,
                )
                heapq.heappush(
                    debt_events,
                    (
                        new_debt_issue.maturity_date,
                        new_debt_issue.amount,
                        new_debt_issue,
                    ),
                )

            current_year_interest += accrued_interest
            current_year_revenue += revenue
            current_year_spending += spending
            accrued_interest = 0
            accrued_principal = 0
            if event_date.year != current_year.year:
                result.append(
                    DebtProjection(
                        event_date,
                        debt_amount_eoy=existing_total_debt,
                        spending=current_year_spending,
                        revenue=current_year_revenue,
                        interest_paid=current_year_interest,
                    )
                )
                current_year = event_date
                current_year_interest = 0.0
                current_year_revenue = 0.0
                current_year_spending = 0.0
        else:
            maturity_date = event[0]
            debt: Debt = event[2]
            # This is a maturing debt.
            interest_accrual_days = (
                maturity_date - datetime(maturity_date.year, maturity_date.month, 1)
            ).days
            # [ASSUMPTION]: We can apply yield rate equally over 12 30-day months.
            accrued_interest += (debt.yield_rate / (360 * 100)) * interest_accrual_days
            accrued_principal += debt.amount
            # print(f"retiring debt: {debt} on {maturity_date}")
    return result


class ProjectionException(Exception):
    pass
