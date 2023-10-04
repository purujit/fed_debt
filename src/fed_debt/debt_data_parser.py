from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd
from pandas import DataFrame


@dataclass
class Debt:
    amount: int
    issue_date: datetime
    maturity_date: datetime
    yield_rate: float


def parse_debt_data_file(filename: str) -> List[Debt]:
    """Given a CSV data dump from the Treasury:
    (https://fiscaldata.treasury.gov/datasets/monthly-statement-public-debt/
     detail-of-treasury-securities-outstanding),
    parses out the relevant information in the form of a list of Debt.
    """
    data: DataFrame = pd.read_csv(filename, keep_default_na=False)
    marketable_debts: DataFrame = data.query(
        """
            `Security Type Description` == 'Marketable' &
            `Issue Date` != 'null' & `Maturity Date` != 'null'
        """
    )
    return list(
        marketable_debts.apply(
            lambda row: Debt(
                amount=row["Issued Amount (in Millions)"],
                yield_rate=row["Yield"],
                # issue_date=row["Issue Date"],
                # maturity_date=row["Maturity Date"],
                issue_date=datetime.strptime(row["Issue Date"], "%Y-%m-%d"),
                maturity_date=datetime.strptime(row["Maturity Date"], "%Y-%m-%d"),
            ),
            axis=1,
        )
    )
