import frappe
from frappe import qb
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import IfNull

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
	make_dimension_in_accounting_doctypes,
)


def create_accounting_dimension_fields():
	dimensions_and_defaults = get_dimensions()
	if dimensions_and_defaults:
		for dimension in dimensions_and_defaults[0]:
			make_dimension_in_accounting_doctypes(dimension, ["Payment Ledger Entry"])


def generate_name_for_payment_ledger_entries(gl_entries):
	for index, entry in enumerate(gl_entries, 1):
		entry.name = index


def get_columns():
	columns = [
		"name",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"docstatus",
		"posting_date",
		"account_type",
		"account",
		"party_type",
		"party",
		"voucher_type",
		"voucher_no",
		"against_voucher_type",
		"against_voucher_no",
		"amount",
		"amount_in_account_currency",
		"account_currency",
		"company",
		"cost_center",
		"due_date",
		"finance_book",
	]

	dimensions_and_defaults = get_dimensions()
	if dimensions_and_defaults:
		for dimension in dimensions_and_defaults[0]:
			columns.append(dimension.fieldname)

	return columns


def build_insert_query():
	ple = qb.DocType("Payment Ledger Entry")
	columns = get_columns()
	insert_query = qb.into(ple)

	# build 'insert' columns in query
	insert_query = insert_query.columns(tuple(columns))

	return insert_query


def insert_chunk_into_payment_ledger(insert_query, gl_entries):
	if gl_entries:
		columns = get_columns()

		# build tuple of data with same column order
		for entry in gl_entries:
			data = ()
			for column in columns:
				data += (entry[column],)
			insert_query = insert_query.insert(data)
		insert_query.run()


def execute():
	if frappe.reload_doc("accounts", "doctype", "payment_ledger_entry"):
		# create accounting dimension fields in Payment Ledger
		create_accounting_dimension_fields()

		gl = qb.DocType("GL Entry")
		account = qb.DocType("Account")
		ifelse = CustomFunction("IF", ["condition", "then", "else"])

		gl_entries = (
			qb.from_(gl)
			.inner_join(account)
			.on((gl.account == account.name) & (account.account_type.isin(["Receivable", "Payable"])))
			.select(
				gl.star,
				ConstantColumn(1).as_("docstatus"),
				account.account_type.as_("account_type"),
				IfNull(
					ifelse(gl.against_voucher_type == "", None, gl.against_voucher_type), gl.voucher_type
				).as_("against_voucher_type"),
				IfNull(ifelse(gl.against_voucher == "", None, gl.against_voucher), gl.voucher_no).as_(
					"against_voucher_no"
				),
				# convert debit/credit to amount
				Case()
				.when(account.account_type == "Receivable", gl.debit - gl.credit)
				.else_(gl.credit - gl.debit)
				.as_("amount"),
				# convert debit/credit in account currency to amount in account currency
				Case()
				.when(
					account.account_type == "Receivable",
					gl.debit_in_account_currency - gl.credit_in_account_currency,
				)
				.else_(gl.credit_in_account_currency - gl.debit_in_account_currency)
				.as_("amount_in_account_currency"),
			)
			.where(gl.is_cancelled == 0)
			.orderby(gl.creation)
			.run(as_dict=True)
		)

		# primary key(name) for payment ledger records
		generate_name_for_payment_ledger_entries(gl_entries)

		# split data into chunks
		chunk_size = 1000
		try:
			for i in range(0, len(gl_entries), chunk_size):
				insert_query = build_insert_query()
				insert_chunk_into_payment_ledger(insert_query, gl_entries[i : i + chunk_size])
				frappe.db.commit()
		except Exception as err:
			frappe.db.rollback()
			ple = qb.DocType("Payment Ledger Entry")
			qb.from_(ple).delete().where(ple.docstatus >= 0).run()
			frappe.db.commit()
			raise err
