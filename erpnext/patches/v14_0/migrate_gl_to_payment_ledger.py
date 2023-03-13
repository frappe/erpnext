import frappe
from frappe import qb
from frappe.query_builder import CustomFunction
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Count, IfNull
from frappe.utils import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
	make_dimension_in_accounting_doctypes,
)


def create_accounting_dimension_fields():
	dimensions_and_defaults = get_dimensions()
	if dimensions_and_defaults:
		for dimension in dimensions_and_defaults[0]:
			make_dimension_in_accounting_doctypes(dimension, ["Payment Ledger Entry"])


def generate_name_and_calculate_amount(gl_entries, start, receivable_accounts):
	for index, entry in enumerate(gl_entries, 0):
		entry.name = start + index
		if entry.account in receivable_accounts:
			entry.account_type = "Receivable"
			entry.amount = entry.debit - entry.credit
			entry.amount_in_account_currency = (
				entry.debit_in_account_currency - entry.credit_in_account_currency
			)
		else:
			entry.account_type = "Payable"
			entry.amount = entry.credit - entry.debit
			entry.amount_in_account_currency = (
				entry.credit_in_account_currency - entry.debit_in_account_currency
			)


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

	if frappe.db.has_column("Payment Ledger Entry", "remarks"):
		columns.append("remarks")

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
	"""
	Description:
	Migrate records from `tabGL Entry` to `tabPayment Ledger Entry`.
	Patch is non-resumable. if patch failed or is terminatted abnormally, clear 'tabPayment Ledger Entry' table manually before re-running. Re-running is safe only during V13->V14 update.

	Note: Post successful migration to V14, re-running is NOT-SAFE and SHOULD NOT be attempted.
	"""

	if frappe.reload_doc("accounts", "doctype", "payment_ledger_entry"):
		# create accounting dimension fields in Payment Ledger
		create_accounting_dimension_fields()

		gl = qb.DocType("GL Entry")
		account = qb.DocType("Account")
		ifelse = CustomFunction("IF", ["condition", "then", "else"])

		# Get Records Count
		relavant_accounts = (
			qb.from_(account)
			.select(account.name, account.account_type)
			.where((account.account_type == "Receivable") | (account.account_type == "Payable"))
			.orderby(account.name)
			.run(as_dict=True)
		)

		receivable_accounts = [x.name for x in relavant_accounts if x.account_type == "Receivable"]
		accounts = [x.name for x in relavant_accounts]

		un_processed = (
			qb.from_(gl)
			.select(Count(gl.name))
			.where((gl.is_cancelled == 0) & (gl.account.isin(accounts)))
			.run()
		)[0][0]

		if un_processed:
			print(f"Migrating {un_processed} GL Entries to Payment Ledger")

			processed = 0
			last_update_percent = 0
			batch_size = 5000
			last_name = None

			while True:
				if last_name:
					where_clause = gl.name.gt(last_name) & gl.account.isin(accounts) & gl.is_cancelled == 0
				else:
					where_clause = gl.account.isin(accounts) & gl.is_cancelled == 0

				gl_entries = (
					qb.from_(gl)
					.select(
						gl.star,
						ConstantColumn(1).as_("docstatus"),
						IfNull(
							ifelse(gl.against_voucher_type == "", None, gl.against_voucher_type), gl.voucher_type
						).as_("against_voucher_type"),
						IfNull(ifelse(gl.against_voucher == "", None, gl.against_voucher), gl.voucher_no).as_(
							"against_voucher_no"
						),
					)
					.where(where_clause)
					.orderby(gl.name)
					.limit(batch_size)
					.run(as_dict=True)
				)

				if gl_entries:
					last_name = gl_entries[-1].name

					# add primary key(name) and calculate based on debit and credit
					generate_name_and_calculate_amount(gl_entries, processed, receivable_accounts)

					try:
						insert_query = build_insert_query()
						insert_chunk_into_payment_ledger(insert_query, gl_entries)
						frappe.db.commit()

						processed += len(gl_entries)

						# Progress message
						percent = flt((processed / un_processed) * 100, 2)
						if percent - last_update_percent > 1:
							print(f"{percent}% ({processed}) records processed")
							last_update_percent = percent

					except Exception as err:
						print("Migration Failed. Clear `tabPayment Ledger Entry` table before re-running")
						raise err
				else:
					break
			print(f"{processed} records have been sucessfully migrated")
