# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.sales_register.sales_register import get_mode_of_payments

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = {}
	columns = get_columns(additional_table_columns)
	last_col = len(columns)

	item_list = get_items(filters, additional_query_columns)
	if item_list:
		item_row_tax, tax_accounts = get_tax_accounts(item_list, columns)
	columns.append({
		"fieldname": "currency",
		"label": _("Currency"),
		"fieldtype": "Data",
		"width": 80
	})
	company_currency = frappe.db.get_value("Company", filters.get("company"), "default_currency")
	mode_of_payments = get_mode_of_payments(set([d.parent for d in item_list]))

	data = []
	for d in item_list:
		delivery_note = None
		if d.delivery_note:
			delivery_note = d.delivery_note
		elif d.so_detail:
			delivery_note = ", ".join(frappe.db.sql_list("""select distinct parent
			from `tabDelivery Note Item` where docstatus=1 and so_detail=%s""", d.so_detail))
		if not delivery_note and d.update_stock:
			delivery_note = d.parent

		row = [d.item_code, d.item_name, d.item_group, d.parent, d.posting_date, d.customer, d.customer_name]

		if additional_query_columns:
			for col in additional_query_columns:
				row.append(d.get(col))

		row += [
			d.customer_group, d.debit_to, ", ".join(mode_of_payments.get(d.parent, [])),
			d.territory, d.project, d.company, d.sales_order,
			delivery_note, d.income_account, d.cost_center, d.qty, d.base_net_rate, d.base_net_amount
		]

		for tax in tax_accounts:
			row.append(item_row_tax.get(d.name, {}).get(tax, 0))

		total_tax = sum(row[last_col:])
		row += [total_tax, d.base_net_amount + total_tax, company_currency]

		data.append(row)

	return columns, data

def get_columns(additional_table_columns):
	columns = [
		_("Item Code") + ":Link/Item:120", _("Item Name") + "::120",
		_("Item Group") + ":Link/Item Group:100", _("Invoice") + ":Link/Sales Invoice:120",
		_("Posting Date") + ":Date:80", _("Customer") + ":Link/Customer:120",
		_("Customer Name") + "::120"]

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		_("Customer Group") + ":Link/Customer Group:120",
		_("Receivable Account") + ":Link/Account:120",
		_("Mode of Payment") + "::120", _("Territory") + ":Link/Territory:80",
		_("Project") + ":Link/Project:80", _("Company") + ":Link/Company:100",
		_("Sales Order") + ":Link/Sales Order:100", _("Delivery Note") + ":Link/Delivery Note:100",
		_("Income Account") + ":Link/Account:140", _("Cost Center") + ":Link/Cost Center:140",
		_("Qty") + ":Float:120",
		_("Rate") + ":Currency/currency:120",
		_("Amount") + ":Currency/currency:120"
	]

	return columns

def get_conditions(filters):
	conditions = ""

	for opts in (("company", " and company=%(company)s"),
		("customer", " and si.customer = %(customer)s"),
		("item_code", " and si_item.item_code = %(item_code)s"),
		("from_date", " and si.posting_date>=%(from_date)s"),
		("to_date", " and si.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	if filters.get("mode_of_payment"):
		conditions += """ and exists(select name from `tabSales Invoice Payment`
			 where parent=si.name
			 	and ifnull(`tabSales Invoice Payment`.mode_of_payment, '') = %(mode_of_payment)s)"""

	return conditions

def get_items(filters, additional_query_columns):
	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)

	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select
			si_item.name, si_item.parent, si.posting_date, si.debit_to, si.project,
			si.customer, si.remarks, si.territory, si.company, si.base_net_total,
			si_item.item_code, si_item.item_name, si_item.item_group, si_item.sales_order,
			si_item.delivery_note, si_item.income_account, si_item.cost_center, si_item.qty,
			si_item.base_net_rate, si_item.base_net_amount, si.customer_name,
			si.customer_group, si_item.so_detail, si.update_stock {0}
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si.name = si_item.parent and si.docstatus = 1 %s
		order by si.posting_date desc, si_item.item_code desc
		""".format(additional_query_columns or '') % conditions, filters, as_dict=1)

def get_tax_accounts(item_list, columns):
	import json
	item_row_tax = {}
	tax_accounts = []
	invoice_item_row = {}
	item_row_map = {}
	for d in item_list:
		invoice_item_row.setdefault(d.parent, []).append(d)
		item_row_map.setdefault(d.parent, {}).setdefault(d.item_code, []).append(d)

	tax_details = frappe.db.sql("""
		select
			parent, account_head, item_wise_tax_detail,
			charge_type, base_tax_amount_after_discount_amount
		from `tabSales Taxes and Charges`
		where
			parenttype = 'Sales Invoice' and docstatus = 1
			and (account_head is not null and account_head != '')
			and parent in (%s)
	""" % ', '.join(['%s']*len(invoice_item_row)), tuple(invoice_item_row.keys()))

	for parent, account_head, item_wise_tax_detail, charge_type, tax_amount in tax_details:
		if account_head not in tax_accounts:
			tax_accounts.append(account_head)

		if item_wise_tax_detail:
			try:
				item_wise_tax_detail = json.loads(item_wise_tax_detail)

				for item_code, tax_amount in item_wise_tax_detail.items():
					tax_amount = flt(tax_amount[1]) if isinstance(tax_amount, list) else flt(tax_amount)

					item_net_amount = sum([flt(d.base_net_amount)
						for d in item_row_map.get(parent, {}).get(item_code, [])])

					for d in item_row_map.get(parent, {}).get(item_code, []):
						item_tax_amount = flt((tax_amount * d.base_net_amount) / item_net_amount) if item_net_amount else 0
						item_row_tax.setdefault(d.name, {})[account_head] = item_tax_amount

			except ValueError:
				continue
		elif charge_type == "Actual" and tax_amount:
			for d in invoice_item_row.get(parent, []):
				item_row_tax.setdefault(d.name, {})[account_head] = \
					flt((tax_amount * d.base_net_amount) / d.base_net_total)

	tax_accounts.sort()
	columns += [account_head + ":Currency/currency:80" for account_head in tax_accounts]
	columns += ["Total Tax:Currency/currency:80", "Total:Currency/currency:80"]

	return item_row_tax, tax_accounts
