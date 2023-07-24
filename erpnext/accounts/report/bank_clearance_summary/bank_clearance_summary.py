# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import getdate, nowdate


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_entries(filters)

	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Payment Document Type"),
			"fieldname": "payment_document_type",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Dynamic Link",
			"options": "payment_document_type",
			"width": 140,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Cheque/Reference No"), "fieldname": "cheque_no", "width": 120},
		{"label": _("Clearance Date"), "fieldname": "clearance_date", "fieldtype": "Date", "width": 120},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200,
		},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]

	return columns


def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"):
		conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"):
		conditions += " and posting_date<=%(to_date)s"

	return conditions


def get_entries(filters):
	conditions = get_conditions(filters)
	journal_entries = frappe.db.sql(
		"""SELECT
			"Journal Entry", jv.name, jv.posting_date, jv.cheque_no,
			jv.clearance_date, jvd.against_account, jvd.debit - jvd.credit
		FROM
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		WHERE
			jvd.parent = jv.name and jv.docstatus=1 and jvd.account = %(account)s {0}
			order by posting_date DESC, jv.name DESC""".format(
			conditions
		),
		filters,
		as_list=1,
	)

	payment_entries = frappe.db.sql(
		"""SELECT
			"Payment Entry", name, posting_date, reference_no, clearance_date, party,
			if(paid_from=%(account)s, ((paid_amount * -1) - total_taxes_and_charges) , received_amount)
		FROM
			`tabPayment Entry`
		WHERE
			docstatus=1 and (paid_from = %(account)s or paid_to = %(account)s) {0}
			order by posting_date DESC, name DESC""".format(
			conditions
		),
		filters,
		as_list=1,
	)

	# Loan Disbursement
	loan_disbursement = frappe.qb.DocType("Loan Disbursement")

	query = (
		frappe.qb.from_(loan_disbursement)
		.select(
			ConstantColumn("Loan Disbursement").as_("payment_document_type"),
			loan_disbursement.name.as_("payment_entry"),
			loan_disbursement.disbursement_date.as_("posting_date"),
			loan_disbursement.reference_number.as_("cheque_no"),
			loan_disbursement.clearance_date.as_("clearance_date"),
			loan_disbursement.applicant.as_("against"),
			-loan_disbursement.disbursed_amount.as_("amount"),
		)
		.where(loan_disbursement.docstatus == 1)
		.where(loan_disbursement.disbursement_date >= filters["from_date"])
		.where(loan_disbursement.disbursement_date <= filters["to_date"])
		.where(loan_disbursement.disbursement_account == filters["account"])
		.orderby(loan_disbursement.disbursement_date, order=frappe.qb.desc)
		.orderby(loan_disbursement.name, order=frappe.qb.desc)
	)

	if filters.get("from_date"):
		query = query.where(loan_disbursement.disbursement_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(loan_disbursement.disbursement_date <= filters["to_date"])

	loan_disbursements = query.run(as_list=1)

	# Loan Repayment
	loan_repayment = frappe.qb.DocType("Loan Repayment")

	query = (
		frappe.qb.from_(loan_repayment)
		.select(
			ConstantColumn("Loan Repayment").as_("payment_document_type"),
			loan_repayment.name.as_("payment_entry"),
			loan_repayment.posting_date.as_("posting_date"),
			loan_repayment.reference_number.as_("cheque_no"),
			loan_repayment.clearance_date.as_("clearance_date"),
			loan_repayment.applicant.as_("against"),
			loan_repayment.amount_paid.as_("amount"),
		)
		.where(loan_repayment.docstatus == 1)
		.where(loan_repayment.posting_date >= filters["from_date"])
		.where(loan_repayment.posting_date <= filters["to_date"])
		.where(loan_repayment.payment_account == filters["account"])
		.orderby(loan_repayment.posting_date, order=frappe.qb.desc)
		.orderby(loan_repayment.name, order=frappe.qb.desc)
	)

	if filters.get("from_date"):
		query = query.where(loan_repayment.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(loan_repayment.posting_date <= filters["to_date"])

	loan_repayments = query.run(as_list=1)

	return sorted(
		journal_entries + payment_entries + loan_disbursements + loan_repayments,
		key=lambda k: k[2].strftime("%H%M%S") or getdate(nowdate()),
	)
