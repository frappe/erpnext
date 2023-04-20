# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.utils import format_datetime

COLUMNS = [
	{
		"label": "JournalCode",
		"fieldname": "JournalCode",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "JournalLib",
		"fieldname": "JournalLib",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "EcritureNum",
		"fieldname": "EcritureNum",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "EcritureDate",
		"fieldname": "EcritureDate",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "CompteNum",
		"fieldname": "CompteNum",
		"fieldtype": "Link",
		"options": "Account",
		"width": 100,
	},
	{
		"label": "CompteLib",
		"fieldname": "CompteLib",
		"fieldtype": "Link",
		"options": "Account",
		"width": 200,
	},
	{
		"label": "CompAuxNum",
		"fieldname": "CompAuxNum",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "CompAuxLib",
		"fieldname": "CompAuxLib",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "PieceRef",
		"fieldname": "PieceRef",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "PieceDate",
		"fieldname": "PieceDate",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "EcritureLib",
		"fieldname": "EcritureLib",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "Debit",
		"fieldname": "Debit",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "Credit",
		"fieldname": "Credit",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "EcritureLet",
		"fieldname": "EcritureLet",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "DateLet",
		"fieldname": "DateLet",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "ValidDate",
		"fieldname": "ValidDate",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "Montantdevise",
		"fieldname": "Montantdevise",
		"fieldtype": "Data",
		"width": 90,
	},
	{
		"label": "Idevise",
		"fieldname": "Idevise",
		"fieldtype": "Data",
		"width": 90,
	},
]


def execute(filters=None):
	validate_filters(filters)
	return COLUMNS, get_result(
		company=filters["company"],
		fiscal_year=filters["fiscal_year"],
	)


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if not filters.get("fiscal_year"):
		frappe.throw(_("{0} is mandatory").format(_("Fiscal Year")))


def get_gl_entries(company, fiscal_year):
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
	debit_currency = frappe.query_builder.functions.Sum(gle.debit_in_account_currency).as_(
		"debitCurr"
	)
	credit_currency = frappe.query_builder.functions.Sum(gle.credit_in_account_currency).as_(
		"creditCurr"
	)

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
			employee.name.as_("empName"),
		)
		.where((gle.company == company) & (gle.fiscal_year == fiscal_year))
		.groupby(gle.voucher_type, gle.voucher_no, gle.account)
		.orderby(gle.posting_date, gle.voucher_no)
	)

	return query.run(as_dict=True)


def get_result(company, fiscal_year):
	data = get_gl_entries(company, fiscal_year)

	result = []

	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	accounts = frappe.get_all(
		"Account", filters={"Company": company}, fields=["name", "account_number"]
	)

	for d in data:
		JournalCode = re.split("-|/|[0-9]", d.get("voucher_no"))[0]

		if d.get("voucher_no").startswith("{0}-".format(JournalCode)) or d.get("voucher_no").startswith(
			"{0}/".format(JournalCode)
		):
			EcritureNum = re.split("-|/", d.get("voucher_no"))[1]
		else:
			EcritureNum = re.search(r"{0}(\d+)".format(JournalCode), d.get("voucher_no"), re.IGNORECASE)[1]

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

		PieceRef = d.get("voucher_no") or "Sans Reference"

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
