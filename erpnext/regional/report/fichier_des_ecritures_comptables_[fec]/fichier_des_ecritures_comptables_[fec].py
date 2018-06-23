# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import format_datetime
from frappe import _

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
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

	if not filters.get('fiscal_year'):
		frappe.throw(_('{0} is mandatory').format(_('Fiscal Year')))


def set_account_currency(filters):

	filters["company_currency"] = frappe.db.get_value("Company", filters.company, "default_currency")

	return filters


def get_columns(filters):
	columns = [
		_("JournalCode") + "::90", _("JournalLib") + "::90",
		_("EcritureNum") + ":Dynamic Link:90", _("EcritureDate") + "::90",
		_("CompteNum") + ":Link/Account:100", _("CompteLib") + ":Link/Account:200",
		_("CompAuxNum") + "::90", _("CompAuxLib") + "::90",
		_("PieceRef") + "::90", _("PieceDate") + "::90",
		_("EcritureLib") + "::90", _("Debit") + "::90", _("Credit") + "::90",
		_("EcritureLet") + "::90", _("DateLet") +
		"::90", _("ValidDate") + "::90",
		_("Montantdevise") + "::90", _("Idevise") + "::90"
	]

	return columns


def get_result(filters):
	gl_entries = get_gl_entries(filters)

	result = get_result_as_list(gl_entries, filters)

	return result


def get_gl_entries(filters):

	group_by_condition = "group by voucher_type, voucher_no, account" \
		if filters.get("group_by_voucher") else "group by gl.name"

	gl_entries = frappe.db.sql("""
		select
			gl.posting_date as GlPostDate, gl.account, gl.transaction_date,
			sum(gl.debit) as debit, sum(gl.credit) as credit,
						sum(gl.debit_in_account_currency) as debitCurr, sum(gl.credit_in_account_currency) as creditCurr,
			gl.voucher_type, gl.voucher_no, gl.against_voucher_type,
						gl.against_voucher, gl.account_currency, gl.against,
						gl.party_type, gl.party, gl.is_opening,
						inv.name as InvName, inv.posting_date as InvPostDate,
						pur.name as PurName, inv.posting_date as PurPostDate,
						jnl.cheque_no as JnlRef, jnl.posting_date as JnlPostDate,
						pay.name as PayName, pay.posting_date as PayPostDate,
						cus.customer_name, cus.name as cusName,
						sup.supplier_name, sup.name as supName

		from `tabGL Entry` gl
					left join `tabSales Invoice` inv on gl.against_voucher = inv.name
					left join `tabPurchase Invoice` pur on gl.against_voucher = pur.name
					left join `tabJournal Entry` jnl on gl.against_voucher = jnl.name
					left join `tabPayment Entry` pay on gl.against_voucher = pay.name
					left join `tabCustomer` cus on gl.party = cus.customer_name
					left join `tabSupplier` sup on gl.party = sup.supplier_name
		where gl.company=%(company)s and gl.fiscal_year=%(fiscal_year)s
		{group_by_condition}
		order by GlPostDate, voucher_no"""
							   .format(group_by_condition=group_by_condition), filters, as_dict=1)

	return gl_entries


def get_result_as_list(data, filters):
	result = []

	company_currency = frappe.db.get_value("Company", filters.company, "default_currency")
	accounts = frappe.get_all("Account", filters={"Company": filters.company}, fields=["name", "account_number"])

	for d in data:

		JournalCode = d.get("voucher_no").split("-")[0]

		EcritureNum = d.get("voucher_no").split("-")[-1]

		EcritureDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		account_number = [account.account_number for account in accounts if account.name == d.get("account")]
		if account_number[0] is not None:
			CompteNum =  account_number[0]
		else:
			frappe.throw(_("Account number for account {0} is not available.<br> Please setup your Chart of Accounts correctly.").format(account.name))

		if d.get("party_type") == "Customer":
			CompAuxNum = d.get("cusName")
			CompAuxLib = d.get("customer_name")

		elif d.get("party_type") == "Supplier":
			CompAuxNum = d.get("supName")
			CompAuxLib = d.get("supplier_name")

		else:
			CompAuxNum = ""
			CompAuxLib = ""

		ValidDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		if d.get("is_opening") == "Yes":
			PieceRef = _("Opening Entry Journal")
			PieceDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		elif d.get("against_voucher_type") == "Sales Invoice":
			PieceRef = _(d.get("InvName"))
			PieceDate = format_datetime(d.get("InvPostDate"), "yyyyMMdd")

		elif d.get("against_voucher_type") == "Purchase Invoice":
			PieceRef = _(d.get("PurName"))
			PieceDate = format_datetime(d.get("PurPostDate"), "yyyyMMdd")

		elif d.get("against_voucher_type") == "Journal Entry":
			PieceRef = _(d.get("JnlRef"))
			PieceDate = format_datetime(d.get("JnlPostDate"), "yyyyMMdd")

		elif d.get("against_voucher_type") == "Payment Entry":
			PieceRef = _(d.get("PayName"))
			PieceDate = format_datetime(d.get("PayPostDate"), "yyyyMMdd")

		elif d.get("voucher_type") == "Period Closing Voucher":
			PieceRef = _("Period Closing Journal")
			PieceDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		else:
			PieceRef = _("No Reference")
			PieceDate = format_datetime(d.get("GlPostDate"), "yyyyMMdd")

		debit = '{:.2f}'.format(d.get("debit")).replace(".", ",")

		credit = '{:.2f}'.format(d.get("credit")).replace(".", ",")

		Idevise = d.get("account_currency")

		if Idevise != company_currency:
			Montantdevise = '{:.2f}'.format(d.get("debitCurr")).replace(".", ",") if d.get("debitCurr") != 0 else '{:.2f}'.format(d.get("creditCurr")).replace(".", ",")
		else:
			Montantdevise = '{:.2f}'.format(d.get("debit")).replace(".", ",") if d.get("debit") != 0 else '{:.2f}'.format(d.get("credit")).replace(".", ",")

		row = [JournalCode, d.get("voucher_type"), EcritureNum, EcritureDate, CompteNum, d.get("account"), CompAuxNum, CompAuxLib,
			   PieceRef, PieceDate, d.get("voucher_no"), debit, credit, "", "", ValidDate, Montantdevise, Idevise]

		result.append(row)

	return result
