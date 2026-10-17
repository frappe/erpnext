import frappe

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
	make_dimension_in_accounting_doctypes,
)

TREASURY_VOUCHERS = ("Investment Transaction", "Investment Interest Accrual", "Investment Revaluation")


def execute():
	"""Treasury vouchers are new, so existing dimensions and closed periods do not cover them yet."""
	dimensions_and_defaults = get_dimensions()
	if dimensions_and_defaults:
		for dimension in dimensions_and_defaults[0]:
			make_dimension_in_accounting_doctypes(dimension, TREASURY_VOUCHERS)

	for period in frappe.get_all("Accounting Period", pluck="name"):
		closed = frappe.get_all(
			"Closed Document",
			filters={"parent": period, "parenttype": "Accounting Period"},
			pluck="document_type",
		)
		for doctype in TREASURY_VOUCHERS:
			if doctype not in closed:
				frappe.get_doc(
					{
						"doctype": "Closed Document",
						"parent": period,
						"parenttype": "Accounting Period",
						"parentfield": "closed_documents",
						"idx": len(closed) + 1,
						"document_type": doctype,
						"closed": 1,
					}
				).db_insert()
				closed.append(doctype)
