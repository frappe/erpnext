# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	proj_details = get_project_details()
	pr_item_map = get_purchased_items_cost()
	se_item_map = get_issued_items_cost()
	dn_item_map = get_delivered_items_cost()

	data = []
	for project in proj_details:
		data.append([project.name, pr_item_map.get(project.name, 0),
			se_item_map.get(project.name, 0), dn_item_map.get(project.name, 0),
			project.project_name, project.status, project.company,
			project.customer, project.estimated_costing, project.expected_start_date,
			project.expected_end_date])

	return columns, data

def get_columns():
	return [_("Project Id") + ":Link/Project:140", _("Cost of Purchased Items") + ":Currency:160",
		_("Cost of Issued Items") + ":Currency:160", _("Cost of Delivered Items") + ":Currency:160",
		_("Project Name") + "::120", _("Project Status") + "::120", _("Company") + ":Link/Company:100",
		_("Customer") + ":Link/Customer:140", _("Project Value") + ":Currency:120",
		_("Project Start Date") + ":Date:120", _("Completion Date") + ":Date:120"]

def get_project_details():
	return frappe.db.sql(""" select name, project_name, status, company, customer, estimated_costing,
		expected_start_date, expected_end_date from tabProject where docstatus < 2""", as_dict=1)

def get_purchased_items_cost():
	pr_items = frappe.db.sql("""select project, sum(base_net_amount) as amount
		from `tabPurchase Receipt Item` where ifnull(project, '') != ''
		and docstatus = 1 group by project""", as_dict=1)

	pr_item_map = {}
	for item in pr_items:
		pr_item_map.setdefault(item.project, item.amount)

	return pr_item_map

def get_issued_items_cost():
	se_items = frappe.db.sql("""select se.project, sum(se_item.amount) as amount
		from `tabStock Entry` se, `tabStock Entry Detail` se_item
		where se.name = se_item.parent and se.docstatus = 1 and ifnull(se_item.t_warehouse, '') = ''
		and ifnull(se.project, '') != '' group by se.project""", as_dict=1)

	se_item_map = {}
	for item in se_items:
		se_item_map.setdefault(item.project, item.amount)

	return se_item_map

def get_delivered_items_cost():
	dn_items = frappe.db.sql("""select dn.project, sum(dn_item.base_net_amount) as amount
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where dn.name = dn_item.parent and dn.docstatus = 1 and ifnull(dn.project, '') != ''
		group by dn.project""", as_dict=1)

	si_items = frappe.db.sql("""select si.project, sum(si_item.base_net_amount) as amount
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si.name = si_item.parent and si.docstatus = 1 and si.update_stock = 1
		and si.is_pos = 1 and ifnull(si.project, '') != ''
		group by si.project""", as_dict=1)


	dn_item_map = {}
	for item in dn_items:
		dn_item_map.setdefault(item.project, item.amount)

	for item in si_items:
		dn_item_map.setdefault(item.project, item.amount)

	return dn_item_map
