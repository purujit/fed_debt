from datetime import datetime

import click

from debt_data_parser import parse_debt_data_file
from debt_projector import build_debt_projection


@click.command()
@click.argument("treasury_debt_data_file", type=click.STRING)
def run(treasury_debt_data_file: str) -> None:
    debts = parse_debt_data_file(treasury_debt_data_file)
    build_debt_projection(
        debts,
        datetime.strptime("2023-10-04", "%Y-%m-%d"),
        datetime.strptime("2033-10-01", "%Y-%m-%d"),
    )


if __name__ == "__main__":
    run()
