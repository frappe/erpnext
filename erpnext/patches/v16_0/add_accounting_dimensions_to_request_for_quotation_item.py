from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
	make_dimension_in_accounting_doctypes,
)


def execute():
	dimensions, _ = get_dimensions()
	for dimension in dimensions:
		make_dimension_in_accounting_doctypes(dimension, ["Request for Quotation Item"])
