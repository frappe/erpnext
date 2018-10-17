# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, random, erpnext
from datetime import timedelta
from frappe.utils.make_random import how_many
from frappe.desk import query_report
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

def work():
	if random.random() < 0.3: return

	frappe.set_user(frappe.db.get_global('demo_manufacturing_user'))
	if not frappe.get_all('Sales Order'): return

	from erpnext.projects.doctype.timesheet.timesheet import OverlapError

	ppt = frappe.new_doc("Production Plan")
	ppt.company = erpnext.get_default_company()
	# ppt.use_multi_level_bom = 1 #refactored
	ppt.get_items_from = "Sales Order"
	# ppt.purchase_request_for_warehouse = "Stores - WPL" # refactored
	ppt.run_method("get_open_sales_orders")
	if not ppt.get("sales_orders"): return
	ppt.run_method("get_items")
	ppt.run_method("raise_material_requests")
	ppt.save()
	ppt.submit()
	ppt.run_method("raise_work_orders")
	frappe.db.commit()

	# submit work orders
	for pro in frappe.db.get_values("Work Order", {"docstatus": 0}, "name"):
		b = frappe.get_doc("Work Order", pro[0])
		b.wip_warehouse = "Work in Progress - WPL"
		b.submit()
		frappe.db.commit()

	# submit material requests
	for pro in frappe.db.get_values("Material Request", {"docstatus": 0}, "name"):
		b = frappe.get_doc("Material Request", pro[0])
		b.submit()
		frappe.db.commit()

	# stores -> wip
	if random.random() < 0.4:
		for pro in query_report.run("Open Work Orders")["result"][:how_many("Stock Entry for WIP")]:
			make_stock_entry_from_pro(pro[0], "Material Transfer for Manufacture")

	# wip -> fg
	if random.random() < 0.4:
		for pro in query_report.run("Work Orders in Progress")["result"][:how_many("Stock Entry for FG")]:
			make_stock_entry_from_pro(pro[0], "Manufacture")

	for bom in frappe.get_all('BOM', fields=['item'], filters = {'with_operations': 1}):
		pro_order = make_wo_order_test_record(item=bom.item, qty=2,
			source_warehouse="Stores - WPL", wip_warehouse = "Work in Progress - WPL",
			fg_warehouse = "Stores - WPL", company = erpnext.get_default_company(),
			stock_uom = frappe.db.get_value('Item', bom.item, 'stock_uom'),
			planned_start_date = frappe.flags.current_date)

	# submit job card
	if random.random() < 0.4:
		submit_job_cards()

def make_stock_entry_from_pro(pro_id, purpose):
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
	from erpnext.stock.stock_ledger import NegativeStockError
	from erpnext.stock.doctype.stock_entry.stock_entry import IncorrectValuationRateError, \
		DuplicateEntryForWorkOrderError, OperationsNotCompleteError

	try:
		st = frappe.get_doc(make_stock_entry(pro_id, purpose))
		st.posting_date = frappe.flags.current_date
		st.fiscal_year = str(frappe.flags.current_date.year)
		for d in st.get("items"):
			d.cost_center = "Main - " + frappe.get_cached_value('Company',  st.company,  'abbr')
		st.insert()
		frappe.db.commit()
		st.submit()
		frappe.db.commit()
	except (NegativeStockError, IncorrectValuationRateError, DuplicateEntryForWorkOrderError,
		OperationsNotCompleteError):
		frappe.db.rollback()

def submit_job_cards():
	work_orders = frappe.get_all("Work Order", ["name", "creation"], {"docstatus": 1, "status": "Not Started"})
	work_order = random.choice(work_orders)
	# for work_order in work_orders:
	start_date = work_order.creation
	work_order = frappe.get_doc("Work Order", work_order.name)
	job = frappe.get_all("Job Card", ["name", "operation", "work_order"],
		{"docstatus": 0, "work_order": work_order.name})

	if not job: return
	job_map = {}
	for d in job:
		job_map[d.operation] = frappe.get_doc("Job Card", d.name)

	for operation in work_order.operations:
		job = job_map[operation.operation]
		job.actual_start_date = start_date
		minutes = operation.get("time_in_mins")
		random_minutes = random.randint(int(minutes/2), minutes)
		job.actual_end_date = job.actual_start_date + timedelta(minutes=random_minutes)
		start_date = job.actual_end_date
		job.save()
		job.submit()
