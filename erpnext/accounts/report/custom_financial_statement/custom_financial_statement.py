# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
	get_export_xlsx_cell_format,
)


def execute(filters: dict | None = None):
	if filters and filters.report_template:
		return FinancialReportEngine().execute(filters)


def get_xlsx_cell_formatting(
	cell_value: Any,
	column: dict,
	row: dict,
	filters: dict,
	is_total_row=False,
) -> dict:
	return get_export_xlsx_cell_format(
		cell_value,
		column,
		row,
		filters,
		is_total_row,
	)
