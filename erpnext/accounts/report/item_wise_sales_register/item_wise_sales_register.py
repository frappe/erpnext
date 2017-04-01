# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.sales_register.sales_register import get_mode_of_payments

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	last_col = len(columns)
	item_list = get_items(filters)

	data = []
	for d in item_list:
		row = [d.item_name,
			d.item_group,
			d.parent,
			d.posting_date,
			d.customer_name,
			d.customer_group,
			d.qty,
			d.base_net_rate,
			d.base_net_amount,
			d.owner
			]


		data.append(row)

	return columns, data

def get_columns():
	return [
		 _("Item Name") + "::120",
		_("Item Group") + ":Link/Item Group:100",
		_("Invoice") + ":Link/Sales Invoice:120",
		_("Posting Date") + ":Date:80",
		_("Customer Name") + "::120",
		 _("Customer Group") + ":Link/Customer Group:120",
		_("Qty") + ":Float:120",
		_("Rate") + ":Currency/currency:120",
		_("Amount") + ":Currency/currency:120",
		_("Owner") + ":Link/User:120"
	]

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

def get_items(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select
			si_item.name, si_item.parent, si.posting_date, si.debit_to, si.project,
			si.customer, si.remarks, si.territory, si.company, si.base_net_total,
			si_item.item_code, si_item.item_name, si_item.item_group, si_item.sales_order,
			si_item.delivery_note, si_item.income_account, si_item.cost_center, si_item.qty,
			si_item.base_net_rate, si_item.base_net_amount, si.customer_name,
			si.customer_group, si_item.so_detail, si.update_stock,si.owner
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si.name = si_item.parent and si.docstatus = 1 %s
		order by si.posting_date desc, si_item.item_code desc""" % conditions, filters, as_dict=1)

