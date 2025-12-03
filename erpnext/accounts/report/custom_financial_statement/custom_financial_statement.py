# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
	get_export_xlsx_cell_style,
)


def execute(filters: dict | None = None):
	if filters and filters.report_template:
		return FinancialReportEngine().execute(filters)


# ============================================================================
# EXCEL EXPORT CELL STYLING
# ============================================================================


def get_xlsx_cell_style(
	cell_value,
	column: dict,
	row: dict,
	filters: dict,
	is_total_row=False,
) -> dict | None:
	if not filters or not filters.get("report_template"):
		return

	return get_export_xlsx_cell_style(
		cell_value,
		column,
		row,
		filters,
		is_total_row=is_total_row,
	)
