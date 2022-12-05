# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.query_builder import DocType
from frappe import qb,_,throw
from frappe.utils import flt, cint,add_days, cstr, flt, getdate, nowdate, rounded, date_diff

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	cols = [
		("Date") + ":date:100",
		("Material Code") + ":Link/Item:110",
		("Material Name")+":data:120",
		("Material Group")+":data:120",
		("Material Sub Group")+":data:150",
		("UoM") + ":data:80",
		("Dispatch Qty")+":data:80",
		("Valuation Rate")+":data:120",
		("Amount")+":Currency:110",
		("Stock Entry")+":Link/Stock Entry:170",
		("Source Warehouse")+":data:170"
	]

	if filters.purpose == "Material Issue":
		cols.append(("Cost Center")+":data:170"),	
		cols.append(("Issued To")+":Data:110"),  
		cols.append(("Issued Employee Name")+":Data:170")
		cols.append(("Issued Equipment")+":Data:170")
		cols.append(("Expense Account")+":Data:170")
	if filters.purpose == "Write Off":
		cols.append(("Cost Center")+":data:170"),
		cols.append(("Expense Account")+":Data:170")

	if filters.purpose == "Material Transfer":
		cols.append(("Target Warehouse")+":data:170")
		cols.append(("Equipment")+":data:120")
		cols.append(("Weight Slip NO")+":data:140")
		cols.append(("POL Slip NO")+":data:120")
		cols.append(("Gross Weight")+":data:120")
		cols.append(("Tare Weight")+":data:120")
		cols.append(("Received Qty")+":data:120")
		cols.append(("Difference Qty")+":data:120")
		cols.append(("Unloading By")+":data:120")
	return cols

def get_data(filters):
	se = qb.DocType('Stock Entry')
	sed = qb.DocType('Stock Entry Detail')
	i = qb.DocType('Item')
	query = (qb.from_(se)
				.inner_join(sed)
				.on(se.name == sed.parent)
				.inner_join(i)
				.on(sed.item_code == i.item_code)
				.select(se.posting_date,sed.item_code,sed.item_name,i.item_group,i.item_sub_group,sed.uom,sed.qty,sed.valuation_rate,sed.amount,se.name,sed.s_warehouse)
				.where(se.docstatus == 1)
				)

	if filters.purpose == 'Material Transfer':
		query = (query
				.select(sed.t_warehouse, sed.equipment, sed.weight_slip_no, sed.pol_slip_no, sed.gross_vehicle_weight,sed.tare_weight, sed.received_qty, sed.difference_qty, sed.unloading_by)
				.where(se.stock_entry_type == 'Material Transfer'))
	elif filters.purpose == 'Material Issue': 
		query = (query
				.select(sed.cost_center, sed.issue_to_employee, sed.issued_employee_name, sed.issue_to_equipment, sed.expense_account)
				.where(se.stock_entry_type == 'Material Issue'))
	elif filters.purpose == 'Write Off':
		query = (query
				.select(sed.cost_center,sed.expense_account)
				.where(se.stock_entry_type == 'Write Off'))

	if filters.get("s_warehouse"):
		query = (query.where(sed.s_warehouse == filters.s_warehouse))
	if filters.get("warehouse"):
		query = (query.where(sed.t_warehouse == filters.warehouse))
	if filters.get("item_code"):
		query = (query.where(sed.item_code == filters.item_code))
	if filters.get("from_date"):
		query = (query.where(filters.from_date <= se.posting_date))
	if filters.get("to_date"):
		query = (query.where(filters.to_date >= se.posting_date))
	return query.run()

