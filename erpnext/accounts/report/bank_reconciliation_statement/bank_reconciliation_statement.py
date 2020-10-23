# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, add_to_date, nowdate
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()

	if not filters.get("account"): return columns, []

	account_currency = frappe.db.get_value("Account", filters.account, "account_currency")

	if "report_date" in filters:
		filters["later_date"] = add_to_date(filters["report_date"], years=1)
	data = get_entries(filters)

	from erpnext.accounts.utils import get_balance_on
	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	bank_bal = flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) \
		+ amounts_not_reflected_in_system

	data += [
		get_balance_row(_("Bank Statement balance as per General Ledger"), balance_as_per_system, account_currency),
		{},
		{
			"from_document": _("Outstanding Cheques and Deposits to clear"),
			"debit": total_debit,
			"credit": total_credit,
			"account_currency": account_currency
		},
		get_balance_row(_("Cheques and Deposits incorrectly cleared"), amounts_not_reflected_in_system,
			account_currency),
		{},
		get_balance_row(_("Calculated Bank Statement balance"), bank_bal, account_currency)
	]

	return columns, data

def get_columns():
	return [
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 90
		},
		{
			"fieldname": "payment_document",
			"label": _("Payment Document Type"),
			"fieldtype": "Data",
			"width": 220
		},
		{
			"fieldname": "from_document",
			"label": _("From Document"),
			"fieldtype": "Dynamic Link",
			"options": "from_document_type",
			"width": 220
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},
		{
			"fieldname": "against_account",
			"label": _("Against Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"fieldname": "reference_no",
			"label": _("Reference"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "ref_date",
			"label": _("Ref Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "clearance_date",
			"label": _("Clearance Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "account_currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Document"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 150
		},
		{
			"fieldname": "from_document_type",
			"label": _("From Type of Document"),
			"fieldtype": "Data",
			"width": 150
		},
	]

def get_entries(filters):
	jea_payments = frappe.db.sql("""
		select "Journal Entry Account" as payment_document, jv.posting_date,
			jvd.name as payment_entry, jvd.debit_in_account_currency as debit,
			jvd.credit_in_account_currency as credit, jvd.against_account,
			jv.cheque_no as reference_no, jv.cheque_date as ref_date, jvd.clearance_date,
			jvd.account_currency, jv.name as from_document, "Journal Entry" as from_document_type
		from
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s
			and ifnull(jvd.clearance_date, %(later_date)s) > %(report_date)s
			and ifnull(jv.is_opening, 'No') = 'No'""", filters, as_dict=1)

	pe_payments = frappe.db.sql("""
		select
			"Payment Entry" as payment_document, name as payment_entry,
			reference_no, reference_date as ref_date,
			if(paid_to=%(account)s, received_amount, 0) as debit,
			if(paid_from=%(account)s, paid_amount, 0) as credit,
			posting_date, ifnull(party,if(paid_from=%(account)s,paid_to,paid_from)) as against_account, clearance_date,
			if(paid_to=%(account)s, paid_to_account_currency, paid_from_account_currency) as account_currency,
			name as from_document, "Payment Entry" as from_document_type
		from `tabPayment Entry`
		where
			(paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
			and posting_date <= %(report_date)s
			and ifnull(clearance_date, %(later_date)s) > %(report_date)s
	""", filters, as_dict=1)

	sip_payments = []
	pi_payments = []
	if filters.include_pos_transactions:
		sip_payments = frappe.db.sql("""
			select
				"Sales Invoice Payment" as payment_document, sip.name as payment_entry, sip.amount as debit,
				si.posting_date, si.debit_to as against_account, sip.clearance_date, si.remarks as reference_no,
				account.account_currency, 0 as credit, sip.name as from_document,
				"Sales Invoice Payment" as from_document_type
			from `tabSales Invoice Payment` sip, `tabSales Invoice` si, `tabAccount` account
			where
				sip.account=%(account)s and si.docstatus=1 and sip.parent = si.name
				and account.name = sip.account and si.posting_date <= %(report_date)s and
				ifnull(sip.clearance_date, %(later_date)s) > %(report_date)s
			order by si.name DESC
		""", filters, as_dict=1)


		pi_query = """
			SELECT
				"Purchase Invoice" as payment_document, name as payment_entry, paid_amount as credit, 0 as debit,
				posting_date, supplier_name as against_account, clearance_date, bill_no as reference_no,
				currency as account_currency, name as from_document, "Purchase Invoice" as from_document_type
			FROM `tabPurchase Invoice`
			WHERE
				cash_bank_account=%(account)s and docstatus=1
				and posting_date <= %(report_date)s
				and ifnull(clearance_date, %(later_date)s) > %(report_date)s
			ORDER BY name
		"""
		pi_payments = frappe.db.sql(pi_query, filters, as_dict=1)

	return sorted(jea_payments + pe_payments + sip_payments + pi_payments,
		key=lambda k: k['posting_date'] or getdate(nowdate()))

def get_amounts_not_reflected_in_system(filters):
	je_amount = frappe.db.sql("""
		select sum(jvd.debit_in_account_currency - jvd.credit_in_account_currency)
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account=%(account)s
		and jv.posting_date > %(report_date)s and jvd.clearance_date <= %(report_date)s
		and ifnull(jv.is_opening, 'No') = 'No' """, filters)

	je_amount = flt(je_amount[0][0]) if je_amount else 0.0

	pe_amount = frappe.db.sql("""
		select sum(if(paid_from=%(account)s, paid_amount, received_amount))
		from `tabPayment Entry`
		where (paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
		and posting_date > %(report_date)s and clearance_date <= %(report_date)s""", filters)

	pe_amount = flt(pe_amount[0][0]) if pe_amount else 0.0

	sip_amount = 0.0
	pi_amount = 0.0
	if filters.include_pos_transactions:
		sip_amount = frappe.db.sql("""
			SELECT sum(sip.amount)
			FROM `tabSales Invoice Payment` sip, `tabSales Invoice` si
			WHERE sip.parent = si.name and si.docstatus=1
			and sip.account=%(account)s
			and si.posting_date > %(report_date)s
			and sip.clearance_date <= %(report_date)s
		""", filters)
		if sip_amount:
			sip_amount = flt(sip_amount[0][0])

		pi_amount = frappe.db.sql("""
			SELECT sum(paid_amount)
			FROM `tabPurchase Invoice`
			WHERE docstatus=1 and cash_bank_account=%(account)s
			and posting_date > %(report_date)s
			and clearance_date <=  %(report_date)s
		""", filters)
		if pi_amount:
			pi_amount = -flt(pi_amount[0][0])

	return je_amount + pe_amount + sip_amount + pi_amount

def get_balance_row(label, amount, account_currency):
	if amount > 0:
		return {
			"from_document": label,
			"debit": amount,
			"credit": 0,
			"account_currency": account_currency
		}
	else:
		return {
			"from_document": label,
			"debit": 0,
			"credit": abs(amount),
			"account_currency": account_currency
		}
