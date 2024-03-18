from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	create_accounting_dimensions_for_doctype,
)


def execute():
	create_accounting_dimensions_for_doctype(doctype="Payment Reconciliation")
	create_accounting_dimensions_for_doctype(doctype="Payment Reconciliation Allocation")
