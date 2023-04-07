# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re

import frappe
from frappe import _
from frappe.utils import format_datetime


def execute(filters=None):
	account_details = {}
	for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
		account_details.setdefault(acc.name, acc)

	validate_filters(filters, account_details)

	filters = set_account_currency(filters)

	columns = get_columns(filters)

	res = get_result(filters)

	return columns, res


def validate_filters(filters, account_details):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if not filters.get("fiscal_year"):
		frappe.throw(_("{0} is mandatory").format(_("Fiscal Year")))


def set_account_currency(filters):

	filters["company_currency"] = frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	return filters


def get_columns(filters):
	columns = [
		"JournalCode" + "::90",
		"JournalLib" + "::90",
		"EcritureNum" + ":Dynamic Link:90",
		"EcritureDate" + "::90",
		"CompteNum" + ":Link/Account:100",
		"CompteLib" + ":Link/Account:200",
		"CompAuxNum" + "::90",
		"CompAuxLib" + "::90",
		"PieceRef" + "::90",
		"PieceDate" + "::90",
		"EcritureLib" + "::90",
		"Debit" + "::90",
		"Credit" + "::90",
		"EcritureLet" + "::90",
		"DateLet" + "::90",
		"ValidDate" + "::90",
		"Montantdevise" + "::90",
		"Idevise" + "::90",
	]

	return columns


def get_result(filters):
	gl_entries = get_gl_entries(filters)

	result = get_result_as_list(gl_entries, filters)

	return result


def get_gl_entries(filters):

	gle = frappe.qb.DocType("GL Entry")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	journal_entry = frappe.qb.DocType("Journal Entry")
	payment_entry = frappe.qb.DocType("Payment Entry")
	customer = frappe.qb.DocType("Customer")
	supplier = frappe.qb.DocType("Supplier")
	employee = frappe.qb.DocType("Employee")

	debit = frappe.query_builder.functions.Sum(gle.debit).as_("debit")
	credit = frappe.query_builder.functions.Sum(gle.credit).as_("credit")
	debit_currency = frappe.query_builder.functions.Sum(gle.debit_in_account_currency).as_("debitCurr")
	credit_currency = frappe.query_builder.functions.Sum(gle.credit_in_account_currency).as_("creditCurr")

	query = (
		frappe.qb.from_(gle)
		.left_join(sales_invoice)
		.on(gle.voucher_no == sales_invoice.name)
		.left_join(purchase_invoice)
		.on(gle.voucher_no == purchase_invoice.name)
		.left_join(journal_entry)
		.on(gle.voucher_no == journal_entry.name)
		.left_join(payment_entry)
		.on(gle.voucher_no == payment_entry.name)
		.left_join(customer)
		.on(gle.party == customer.name)
		.left_join(supplier)
		.on(gle.party == supplier.name)
		.left_join(employee)
		.on(gle.party == employee.name)
		.select(
			gle.posting_date.as_("GlPostDate"),
			gle.name.as_("GlName"),
			gle.account,
			gle.transaction_date,
			debit,
			credit,
			debit_currency,
			credit_currency,
			gle.voucher_type,
			gle.voucher_no,
			gle.against_voucher_type,
			gle.against_voucher,
			gle.account_currency,
			gle.against,
			gle.party_type,
			gle.party,
			sales_invoice.name.as_("InvName"),
			sales_invoice.title.as_("InvTitle"),
			sales_invoice.posting_date.as_("InvPostDate"),
			purchase_invoice.name.as_("PurName"),
			purchase_invoice.title.as_("PurTitle"),
			purchase_invoice.posting_date.as_("PurPostDate"),
			journal_entry.cheque_no.as_("JnlRef"),
			journal_entry.posting_date.as_("JnlPostDate"),
			journal_entry.title.as_("JnlTitle"),
			payment_entry.name.as_("PayName"),
			payment_entry.posting_date.as_("PayPostDate"),
			payment_entry.title.as_("PayTitle"),
			customer.customer_name,
			customer.name.as_("cusName"),
			supplier.supplier_name,
			supplier.name.as_("supName"),
			employee.employee_name,
			employee.name.as_("empName")
		)
		.where(
			(gle.company == filters.get("company"))
			& (gle.fiscal_year == filters.get("fiscal_year"))
		)
		.groupby(gle.voucher_type, gle.voucher_no, gle.account)
		.orderby(gle.posting_date, gle.voucher_no)
	)
	gl_entries = query.run(as_dict=True)

	return gl_entries


def get_result_as_list(data, filters):
	result = []

	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	accounts = frappe.get_all(
		"Account", filters={"Company": filters.company}, fields=["name", "account_number"]
	)

	for d in data:

		JournalCode = re.split("-|/|[0-9]", d.get("voucher_no"))[0]

		if d.get("voucher_no").startswith("{0}-".format(JournalCode)) or d.get("voucher_no").startswith(
			"{0}/".format(JournalCode)
		):
			EcritureNum = re.split("-|/", d.get("voucher_no"))[1]
		else:
			EcritureNum = re.search(
				r"{0}(\d+)".format(JournalCode), d.get("voucher_no"), re.IGNORECASE
			).group(1)

		EcritureDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		account_number = [
			account.account_number for account in accounts if account.name == d.get("account")
		]
		if account_number[0] is not None:
			CompteNum = account_number[0]
		else:
			frappe.throw(
				_(
					"Account number for account {0} is not available.<br> Please setup your Chart of Accounts correctly."
				).format(d.get("account"))
			)

		if d.get("party_type") == "Customer":
			CompAuxNum = d.get("cusName")
			CompAuxLib = d.get("customer_name")

		elif d.get("party_type") == "Supplier":
			CompAuxNum = d.get("supName")
			CompAuxLib = d.get("supplier_name")

		elif d.get("party_type") == "Employee":
			CompAuxNum = d.get("empName")
			CompAuxLib = d.get("employee_name")

		elif d.get("party_type") == "Student":
			CompAuxNum = d.get("stuName")
			CompAuxLib = d.get("student_name")

		elif d.get("party_type") == "Member":
			CompAuxNum = d.get("memName")
			CompAuxLib = d.get("member_name")

		else:
			CompAuxNum = ""
			CompAuxLib = ""

		ValidDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		PieceRef = d.get("voucher_no") if d.get("voucher_no") else "Sans Reference"

		# EcritureLib is the reference title unless it is an opening entry
		if d.get("is_opening") == "Yes":
			EcritureLib = _("Opening Entry Journal")
		if d.get("voucher_type") == "Sales Invoice":
			EcritureLib = d.get("InvTitle")
		elif d.get("voucher_type") == "Purchase Invoice":
			EcritureLib = d.get("PurTitle")
		elif d.get("voucher_type") == "Journal Entry":
			EcritureLib = d.get("JnlTitle")
		elif d.get("voucher_type") == "Payment Entry":
			EcritureLib = d.get("PayTitle")
		else:
			EcritureLib = d.get("voucher_type")

		PieceDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		debit = "{:.2f}".format(d.get("debit")).replace(".", ",")

		credit = "{:.2f}".format(d.get("credit")).replace(".", ",")

		Idevise = d.get("account_currency")

		if Idevise != company_currency:
			Montantdevise = (
				"{:.2f}".format(d.get("debitCurr")).replace(".", ",")
				if d.get("debitCurr") != 0
				else "{:.2f}".format(d.get("creditCurr")).replace(".", ",")
			)
		else:
			Montantdevise = (
				"{:.2f}".format(d.get("debit")).replace(".", ",")
				if d.get("debit") != 0
				else "{:.2f}".format(d.get("credit")).replace(".", ",")
			)

		row = [
			JournalCode,
			d.get("voucher_type"),
			EcritureNum,
			EcritureDate,
			CompteNum,
			d.get("account"),
			CompAuxNum,
			CompAuxLib,
			PieceRef,
			PieceDate,
			EcritureLib,
			debit,
			credit,
			"",
			"",
			ValidDate,
			Montantdevise,
			Idevise,
		]

		result.append(row)

	return result
