# coding: utf-8
from __future__ import unicode_literals
import frappe
from frappe.utils import format_datetime
from frappe import DoesNotExistError
from frappe import _


def execute(filters=None):
	validate_filters(filters)
	filters = set_account_currency(filters)

	columns = get_columns()
	result = get_result(filters)

	return columns, result


def validate_filters(filters):
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

	if not filters.get('fiscal_year'):
		frappe.throw(_('{0} is mandatory').format(_('Fiscal Year')))


def set_account_currency(filters):
	filters["company_currency"] = frappe.get_cached_value(
		'Company',  filters.company,  "default_currency")
	return filters


def get_columns():
	columns = [
		{
			"label": "Umsatz (ohne Soll/Haben-Kz)",
			"fieldname": "umsatz",
			"fieldtype": "Data",
		},
		{
			"label": "Soll/Haben-Kennzeichen",
			"fieldname": "soll_haben_kennzeichen",
			"fieldtype": "Data",
		},
		{
			"label": "Kontonummer",
			"fieldname": "kontonummer",
			"fieldtype": "Data",
		},
		{
			"label": "Gegenkonto (ohne BU-Schlüssel)",
			"fieldname": "gegenkonto_nummer",
			"fieldtype": "Data",
		},
		{
			"label": "Belegdatum",
			"fieldname": "belegdatum",
			"fieldtype": "Data",
		}
	]

	return columns


def get_result(filters):
	gl_entries = get_gl_entries(filters)
	result = get_result_as_list(gl_entries)
	return result


def get_gl_entries(filters):
	gl_entries = frappe.db.sql("""
		select
			gl.posting_date as GlPostDate, 
			gl.name as GlName, 
			gl.account, 
			gl.transaction_date, 
			sum(gl.debit) as debit, 
			sum(gl.credit) as credit,
			sum(gl.debit_in_account_currency) as debitCurr, 
			sum(gl.credit_in_account_currency) as creditCurr,
			gl.voucher_type, 
			gl.voucher_no, 
			gl.against_voucher_type, 
			gl.against_voucher, 
			gl.account_currency, 
			gl.against, 
			gl.party_type, 
			gl.party,
			inv.name as InvName, 
			inv.title as InvTitle, 
			inv.posting_date as InvPostDate, 
			pur.name as PurName, 
			pur.title as PurTitle, 
			pur.posting_date as PurPostDate,
			jnl.cheque_no as JnlRef, 
			jnl.posting_date as JnlPostDate, 
			jnl.title as JnlTitle,
			pay.name as PayName, 
			pay.posting_date as PayPostDate, 
			pay.title as PayTitle,
			cus.customer_name, 
			cus.name as cusName,
			sup.supplier_name, 
			sup.name as supName
 
		from `tabGL Entry` gl
			left join `tabSales Invoice` inv 
			on gl.voucher_no = inv.name

			left join `tabPurchase Invoice` pur 
			on gl.voucher_no = pur.name

			left join `tabJournal Entry` jnl 
			on gl.voucher_no = jnl.name

			left join `tabPayment Entry` pay 
			on gl.voucher_no = pay.name

			left join `tabCustomer` cus 
			on gl.party = cus.name

			left join `tabSupplier` sup 
			on gl.party = sup.name
		where gl.company=%(company)s and gl.fiscal_year=%(fiscal_year)s
		group by voucher_type, voucher_no, account
		order by GlPostDate, voucher_no""", filters, as_dict=1)

	return gl_entries


def get_result_as_list(data):
	result = []

	for d in data:
		if d.get("debit"):
			amount = d.get("debit")
			kennzeichen = 'S'
		elif d.get("credit"):
			amount = d.get('credit')
			kennzeichen = 'H'
		else:
			amount = 0.0
			kennzeichen = ''

		umsatz = '{:.2f}'.format(amount).replace(".", ",")

		konto = d.get('account')
		gegenkonto = d.get('against')
		kontonummer = get_account_number(konto)
		gegenkonto_nummer = get_account_number(gegenkonto)
		
		belegdatum = format_datetime(d.get("GlPostDate"), "ddMMyyyy")
		
		row = [umsatz, kennzeichen, kontonummer, gegenkonto_nummer, belegdatum]
		result.append(row)

	return result


def get_account_number(name):
	try:
		acc = frappe.get_doc("Account", name)
		return acc.account_number
	except DoesNotExistError:
		return ''
