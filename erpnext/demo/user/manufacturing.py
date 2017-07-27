# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, random, erpnext
from frappe.utils.make_random import how_many
from frappe.desk import query_report
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.manufacturing.doctype.production_order.test_production_order import make_prod_order_test_record

def work():
	frappe.set_user(frappe.db.get_global('demo_manufacturing_user'))

	from erpnext.projects.doctype.timesheet.timesheet import OverlapError

	ppt = frappe.get_doc("Production Planning Tool", "Production Planning Tool")
	ppt.company = erpnext.get_default_company()
	ppt.use_multi_level_bom = 1
	ppt.get_items_from = "Sales Order"
	ppt.purchase_request_for_warehouse = "Stores - WPL"
	ppt.run_method("get_open_sales_orders")
	ppt.run_method("get_items")
	ppt.run_method("raise_production_orders")
	ppt.run_method("raise_material_requests")
	frappe.db.commit()

	# submit production orders
	for pro in frappe.db.get_values("Production Order", {"docstatus": 0}, "name"):
		b = frappe.get_doc("Production Order", pro[0])
		b.wip_warehouse = "Work in Progress - WPL"
		b.submit()
		frappe.db.commit()

	# submit material requests
	for pro in frappe.db.get_values("Material Request", {"docstatus": 0}, "name"):
		b = frappe.get_doc("Material Request", pro[0])
		b.submit()
		frappe.db.commit()

	# stores -> wip
	if random.random() < 0.3:
		for pro in query_report.run("Open Production Orders")["result"][:how_many("Stock Entry for WIP")]:
			make_stock_entry_from_pro(pro[0], "Material Transfer for Manufacture")

	# wip -> fg
	if random.random() < 0.3:
		for pro in query_report.run("Production Orders in Progress")["result"][:how_many("Stock Entry for FG")]:
			make_stock_entry_from_pro(pro[0], "Manufacture")

	for bom in frappe.get_all('BOM', fields=['item'], filters = {'with_operations': 1}):
		pro_order = make_prod_order_test_record(item=bom.item, qty=2,
			source_warehouse="Stores - WPL", wip_warehouse = "Work in Progress - WPL",
			fg_warehouse = "Stores - WPL", company = erpnext.get_default_company(),
			stock_uom = frappe.db.get_value('Item', bom.item, 'stock_uom'),
			planned_start_date = frappe.flags.current_date)

	# submit time logs
	for timesheet in frappe.get_all("Timesheet", ["name"], {"docstatus": 0,
		"production_order": ("!=", ""), "to_time": ("<", frappe.flags.current_date)}):
		timesheet = frappe.get_doc("Timesheet", timesheet.name)
		try:
			timesheet.submit()
			frappe.db.commit()
		except OverlapError:
			pass
		except WorkstationHolidayError:
			pass

def make_stock_entry_from_pro(pro_id, purpose):
	from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry
	from erpnext.stock.stock_ledger import NegativeStockError
	from erpnext.stock.doctype.stock_entry.stock_entry import IncorrectValuationRateError, \
		DuplicateEntryForProductionOrderError, OperationsNotCompleteError

	try:
		st = frappe.get_doc(make_stock_entry(pro_id, purpose))
		st.posting_date = frappe.flags.current_date
		st.fiscal_year = str(frappe.flags.current_date.year)
		for d in st.get("items"):
			d.cost_center = "Main - " + frappe.db.get_value('Company', st.company, 'abbr')
		st.insert()
		frappe.db.commit()
		st.submit()
		frappe.db.commit()
	except (NegativeStockError, IncorrectValuationRateError, DuplicateEntryForProductionOrderError,
		OperationsNotCompleteError):
		frappe.db.rollback()
