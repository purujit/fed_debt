import heapq
from dataclasses import dataclass
from datetime import datetime
from typing import List

from debt_data_parser import Debt


@dataclass
class DebtProjection:
    year: int
    debt_amount_eoy: float
    interest_paid: float


# Find the next maturing debt. If it matures beyond the projection, we are done.
# Otherwise, re-issue the debt for the same duration.  To handle new debt,
# whenever handling the next debt, check if any new debt needs to be issued and
# if so, issue it at the same maturity distribution as existing debt.  Find the
# next maturing debt. If it matures beyond the projection, we are done.
# Otherwise, re-issue the debt for the same duration.
# To handle new debt, whenever handling the next debt, check if any new debt
# needs to be issued and if so, issue it at the same maturity distribution as
# existing debt.
def build_debt_projection(
    starting_debts: List[Debt], start_date: datetime, projection_end_date: datetime
) -> List[DebtProjection]:
    debts_by_maturity = [(d.maturity_date, d.amount, d) for d in starting_debts]
    heapq.heapify(
        debts_by_maturity,
    )
    for i in range(100):
        print(heapq.heappop(debts_by_maturity)[0])
    return []
