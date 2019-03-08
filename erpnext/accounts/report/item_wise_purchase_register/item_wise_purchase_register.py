# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import get_tax_accounts

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = {}
	filters.update({"from_date": filters.get("date_range")[0], "to_date": filters.get("date_range")[1]})
	columns = get_columns(additional_table_columns)

	company_currency = erpnext.get_company_currency(filters.company)

	item_list = get_items(filters, additional_query_columns)
	aii_account_map = get_aii_accounts()
	if item_list:
		itemised_tax, tax_columns = get_tax_accounts(item_list, columns, company_currency,
			doctype="Purchase Invoice", tax_doctype="Purchase Taxes and Charges")

	columns.append({
		"fieldname": "currency",
		"label": _("Currency"),
		"fieldtype": "Data",
		"width": 80
	})

	po_pr_map = get_purchase_receipts_against_purchase_order(item_list)

	data = []
	for d in item_list:
		if not d.stock_qty:
			continue

		purchase_receipt = None
		if d.purchase_receipt:
			purchase_receipt = d.purchase_receipt
		elif d.po_detail:
			purchase_receipt = ", ".join(po_pr_map.get(d.po_detail, []))

		expense_account = d.expense_account or aii_account_map.get(d.company)
		row = [d.item_code, d.item_name, d.item_group, d.description, d.parent, d.posting_date, d.supplier,
			d.supplier_name]

		if additional_query_columns:
			for col in additional_query_columns:
				row.append(d.get(col))

		row += [
			d.credit_to, d.mode_of_payment, d.project, d.company, d.purchase_order,
			purchase_receipt, expense_account, d.stock_qty, d.stock_uom, d.base_net_amount / d.stock_qty, d.base_net_amount
		]

		total_tax = 0
		for tax in tax_columns:
			item_tax = itemised_tax.get(d.name, {}).get(tax, {})
			row += [item_tax.get("tax_rate", 0), item_tax.get("tax_amount", 0)]
			total_tax += flt(item_tax.get("tax_amount"))

		row += [total_tax, d.base_net_amount + total_tax, company_currency]

		data.append(row)

	return columns, data


def get_columns(additional_table_columns):
	columns = [
		_("Item Code") + ":Link/Item:120", _("Item Name") + "::120",
		_("Item Group") + ":Link/Item Group:100", "Description::150", _("Invoice") + ":Link/Purchase Invoice:120",
		_("Posting Date") + ":Date:80", _("Supplier") + ":Link/Supplier:120",
		"Supplier Name::120"
	]

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		 "Payable Account:Link/Account:120",
		_("Mode of Payment") + ":Link/Mode of Payment:80", _("Project") + ":Link/Project:80",
		_("Company") + ":Link/Company:100", _("Purchase Order") + ":Link/Purchase Order:100",
		_("Purchase Receipt") + ":Link/Purchase Receipt:100", _("Expense Account") + ":Link/Account:140",
		_("Stock Qty") + ":Float:120", _("Stock UOM") + "::100",
		_("Rate") + ":Currency/currency:120", _("Amount") + ":Currency/currency:120"
	]

	return columns

def get_conditions(filters):
	conditions = ""

	for opts in (("company", " and company=%(company)s"),
		("supplier", " and `tabPurchase Invoice`.supplier = %(supplier)s"),
		("item_code", " and `tabPurchase Invoice Item`.item_code = %(item_code)s"),
		("from_date", " and `tabPurchase Invoice`.posting_date>=%(from_date)s"),
		("to_date", " and `tabPurchase Invoice`.posting_date<=%(to_date)s"),
		("mode_of_payment", " and ifnull(mode_of_payment, '') = %(mode_of_payment)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	return conditions

def get_items(filters, additional_query_columns):
	conditions = get_conditions(filters)
	match_conditions = frappe.build_match_conditions("Purchase Invoice")

	if match_conditions:
		match_conditions = " and {0} ".format(match_conditions)

	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)

	return frappe.db.sql("""
		select
			`tabPurchase Invoice Item`.`name`, `tabPurchase Invoice Item`.`parent`,
			`tabPurchase Invoice`.posting_date, `tabPurchase Invoice`.credit_to, `tabPurchase Invoice`.company,
			`tabPurchase Invoice`.supplier, `tabPurchase Invoice`.remarks, `tabPurchase Invoice`.base_net_total, `tabPurchase Invoice Item`.`item_code`,
			`tabPurchase Invoice Item`.`item_name`, `tabPurchase Invoice Item`.`item_group`, `tabPurchase Invoice Item`.description,
			`tabPurchase Invoice Item`.`project`, `tabPurchase Invoice Item`.`purchase_order`,
			`tabPurchase Invoice Item`.`purchase_receipt`, `tabPurchase Invoice Item`.`po_detail`,
			`tabPurchase Invoice Item`.`expense_account`, `tabPurchase Invoice Item`.`stock_qty`,
			`tabPurchase Invoice Item`.`stock_uom`, `tabPurchase Invoice Item`.`base_net_amount`,
			`tabPurchase Invoice`.supplier_name, `tabPurchase Invoice`.mode_of_payment {0}
		from `tabPurchase Invoice`, `tabPurchase Invoice Item`
		where `tabPurchase Invoice`.name = `tabPurchase Invoice Item`.`parent` and
		`tabPurchase Invoice`.docstatus = 1 %s %s
		order by `tabPurchase Invoice`.posting_date desc, `tabPurchase Invoice Item`.item_code desc
	""".format(additional_query_columns) % (conditions, match_conditions), filters, as_dict=1)

def get_aii_accounts():
	return dict(frappe.db.sql("select name, stock_received_but_not_billed from tabCompany"))

def get_purchase_receipts_against_purchase_order(item_list):
	po_pr_map = frappe._dict()
	po_item_rows = list(set([d.po_detail for d in item_list]))

	if po_item_rows:
		purchase_receipts = frappe.db.sql("""
			select parent, purchase_order_item
			from `tabPurchase Receipt Item`
			where docstatus=1 and purchase_order_item in (%s)
			group by purchase_order_item, parent
		""" % (', '.join(['%s']*len(po_item_rows))), tuple(po_item_rows), as_dict=1)

		for pr in purchase_receipts:
			po_pr_map.setdefault(pr.po_detail, []).append(pr.parent)

	return po_pr_map
