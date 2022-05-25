import frappe
from frappe import qb

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
	make_dimension_in_accounting_doctypes,
)
from erpnext.accounts.utils import create_payment_ledger_entry


def create_accounting_dimension_fields():
	dimensions_and_defaults = get_dimensions()
	if dimensions_and_defaults:
		for dimension in dimensions_and_defaults[0]:
			make_dimension_in_accounting_doctypes(dimension, ["Payment Ledger Entry"])


def execute():
	# create accounting dimension fields in Payment Ledger
	create_accounting_dimension_fields()

	gl = qb.DocType("GL Entry")
	accounts = frappe.db.get_list(
		"Account", "name", filters={"account_type": ["in", ["Receivable", "Payable"]]}, as_list=True
	)
	gl_entries = []
	if accounts:
		# get all gl entries on receivable/payable accounts
		gl_entries = (
			qb.from_(gl)
			.select("*")
			.where(gl.account.isin(accounts))
			.where(gl.is_cancelled == 0)
			.run(as_dict=True)
		)
		if gl_entries:
			# create payment ledger entries for the accounts receivable/payable
			create_payment_ledger_entry(gl_entries, 0)
