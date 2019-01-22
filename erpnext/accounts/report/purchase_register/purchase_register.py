# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = {}

	invoice_list = get_invoices(filters, additional_query_columns)
	columns, expense_accounts, tax_accounts = get_columns(invoice_list, additional_table_columns)

	if not invoice_list:
		msgprint(_("No record found"))
		return columns, invoice_list

	invoice_expense_map = get_invoice_expense_map(invoice_list)
	invoice_expense_map, invoice_tax_map = get_invoice_tax_map(invoice_list,
		invoice_expense_map, expense_accounts)
	invoice_po_pr_map = get_invoice_po_pr_map(invoice_list)
	suppliers = list(set([d.supplier for d in invoice_list]))
	supplier_details = get_supplier_details(suppliers)

	company_currency = frappe.get_cached_value('Company',  filters.company,  "default_currency")

	data = []
	for inv in invoice_list:
		# invoice details
		purchase_order = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_order", [])))
		purchase_receipt = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_receipt", [])))
		project = list(set(invoice_po_pr_map.get(inv.name, {}).get("project", [])))

		row = [inv.name, inv.posting_date, inv.supplier, inv.supplier_name]

		if additional_query_columns:
			for col in additional_query_columns:
				row.append(inv.get(col))

		row += [
			supplier_details.get(inv.supplier), # supplier_group
			inv.tax_id, inv.credit_to, inv.mode_of_payment, ", ".join(project),
			inv.bill_no, inv.bill_date, inv.remarks,
			", ".join(purchase_order), ", ".join(purchase_receipt), company_currency
		]

		# map expense values
		base_net_total = 0
		for expense_acc in expense_accounts:
			expense_amount = flt(invoice_expense_map.get(inv.name, {}).get(expense_acc))
			base_net_total += expense_amount
			row.append(expense_amount)

		# net total
		row.append(base_net_total or inv.base_net_total)

		# tax account
		total_tax = 0
		for tax_acc in tax_accounts:
			if tax_acc not in expense_accounts:
				tax_amount = flt(invoice_tax_map.get(inv.name, {}).get(tax_acc))
				total_tax += tax_amount
				row.append(tax_amount)

		# total tax, grand total, outstanding amount & rounded total
		row += [total_tax, inv.base_grand_total, flt(inv.base_grand_total, 2), inv.outstanding_amount]
		data.append(row)

	return columns, data


def get_columns(invoice_list, additional_table_columns):
	"""return columns based on filters"""
	columns = [
		_("Invoice") + ":Link/Purchase Invoice:120", _("Posting Date") + ":Date:80",
		_("Supplier Id") + "::120", _("Supplier Name") + "::120"]

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		_("Supplier Group") + ":Link/Supplier Group:120", _("Tax Id") + "::80", _("Payable Account") + ":Link/Account:120",
		_("Mode of Payment") + ":Link/Mode of Payment:80", _("Project") + ":Link/Project:80",
		_("Bill No") + "::120", _("Bill Date") + ":Date:80", _("Remarks") + "::150",
		_("Purchase Order") + ":Link/Purchase Order:100",
		_("Purchase Receipt") + ":Link/Purchase Receipt:100",
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Data",
			"width": 80
		}
	]
	expense_accounts = tax_accounts = expense_columns = tax_columns = []

	if invoice_list:
		expense_accounts = frappe.db.sql_list("""select distinct expense_account
			from `tabPurchase Invoice Item` where docstatus = 1
			and (expense_account is not null and expense_account != '')
			and parent in (%s) order by expense_account""" %
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))

		tax_accounts = 	frappe.db.sql_list("""select distinct account_head
			from `tabPurchase Taxes and Charges` where parenttype = 'Purchase Invoice'
			and docstatus = 1 and (account_head is not null and account_head != '')
			and category in ('Total', 'Valuation and Total')
			and parent in (%s) order by account_head""" %
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))


	expense_columns = [(account + ":Currency/currency:120") for account in expense_accounts]
	for account in tax_accounts:
		if account not in expense_accounts:
			tax_columns.append(account + ":Currency/currency:120")

	columns = columns + expense_columns + [_("Net Total") + ":Currency/currency:120"] + tax_columns + \
		[_("Total Tax") + ":Currency/currency:120", _("Grand Total") + ":Currency/currency:120",
			_("Rounded Total") + ":Currency/currency:120", _("Outstanding Amount") + ":Currency/currency:120"]

	return columns, expense_accounts, tax_accounts

def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " and company=%(company)s"
	if filters.get("supplier"): conditions += " and supplier = %(supplier)s"

	if filters.get("from_date"): conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date<=%(to_date)s"

	if filters.get("mode_of_payment"): conditions += " and ifnull(mode_of_payment, '') = %(mode_of_payment)s"

	return conditions

def get_invoices(filters, additional_query_columns):
	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)

	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select
			name, posting_date, credit_to, supplier, supplier_name, tax_id, bill_no, bill_date,
			remarks, base_net_total, base_grand_total, outstanding_amount,
			mode_of_payment {0}
		from `tabPurchase Invoice`
		where docstatus = 1 %s
		order by posting_date desc, name desc""".format(additional_query_columns or '') % conditions, filters, as_dict=1)


def get_invoice_expense_map(invoice_list):
	expense_details = frappe.db.sql("""
		select parent, expense_account, sum(base_net_amount) as amount
		from `tabPurchase Invoice Item`
		where parent in (%s)
		group by parent, expense_account
	""" % ', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)

	invoice_expense_map = {}
	for d in expense_details:
		invoice_expense_map.setdefault(d.parent, frappe._dict()).setdefault(d.expense_account, [])
		invoice_expense_map[d.parent][d.expense_account] = flt(d.amount)

	return invoice_expense_map

def get_invoice_tax_map(invoice_list, invoice_expense_map, expense_accounts):
	tax_details = frappe.db.sql("""
		select parent, account_head, case add_deduct_tax when "Add" then sum(base_tax_amount_after_discount_amount)
		else sum(base_tax_amount_after_discount_amount) * -1 end as tax_amount
		from `tabPurchase Taxes and Charges`
		where parent in (%s) and category in ('Total', 'Valuation and Total')
			and base_tax_amount_after_discount_amount != 0
		group by parent, account_head, add_deduct_tax
	""" % ', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)

	invoice_tax_map = {}
	for d in tax_details:
		if d.account_head in expense_accounts:
			if d.account_head in invoice_expense_map[d.parent]:
				invoice_expense_map[d.parent][d.account_head] += flt(d.tax_amount)
			else:
				invoice_expense_map[d.parent][d.account_head] = flt(d.tax_amount)
		else:
			invoice_tax_map.setdefault(d.parent, frappe._dict()).setdefault(d.account_head, [])
			invoice_tax_map[d.parent][d.account_head] = flt(d.tax_amount)

	return invoice_expense_map, invoice_tax_map

def get_invoice_po_pr_map(invoice_list):
	pi_items = frappe.db.sql("""
		select parent, purchase_order, purchase_receipt, po_detail, project
		from `tabPurchase Invoice Item`
		where parent in (%s) and (ifnull(purchase_order, '') != '' or ifnull(purchase_receipt, '') != '')
	""" % ', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)

	invoice_po_pr_map = {}
	for d in pi_items:
		if d.purchase_order:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault(
				"purchase_order", []).append(d.purchase_order)

		pr_list = None
		if d.purchase_receipt:
			pr_list = [d.purchase_receipt]
		elif d.po_detail:
			pr_list = frappe.db.sql_list("""select distinct parent from `tabPurchase Receipt Item`
				where docstatus=1 and purchase_order_item=%s""", d.po_detail)

		if pr_list:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault("purchase_receipt", pr_list)

		if d.project:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault(
				"project", []).append(d.project)

	return invoice_po_pr_map

def get_account_details(invoice_list):
	account_map = {}
	accounts = list(set([inv.credit_to for inv in invoice_list]))
	for acc in frappe.db.sql("""select name, parent_account from tabAccount
		where name in (%s)""" % ", ".join(["%s"]*len(accounts)), tuple(accounts), as_dict=1):
			account_map[acc.name] = acc.parent_account

	return account_map

def get_supplier_details(suppliers):
	supplier_details = {}
	for supp in frappe.db.sql("""select name, supplier_group from `tabSupplier`
		where name in (%s)""" % ", ".join(["%s"]*len(suppliers)), tuple(suppliers), as_dict=1):
			supplier_details.setdefault(supp.name, supp.supplier_group)

	return supplier_details
