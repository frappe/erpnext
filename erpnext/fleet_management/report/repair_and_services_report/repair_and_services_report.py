# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.query_builder import DocType
from frappe import qb,_


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	cols = [
		("Branch") + ":Link/Branch:200",
		("Cost Center") + ":Link/Cost Center:200",
		("Posting Date") + ":date:100",
		("Equipment/Vehicle") + ":Link/Equipment:100",
		("Equipment Type")+":Link/Equipment Type:120",
		("Equipment Model")+":data:60",
		("Current KM")+":data:70",
		("KM Difference") + ":data:50",
		("Supplier")+":data:50",
		("Item")+":Link/Item:60",
		("Item Name")+":data:80",
		("Item Group")+":data:80",
		("Rate")+":Currency:60",
		("Qty") +":data:20",
		("Charge Amount") +"Currency:60",
		("Total Amount") +"data:60",
		("Company") +"Link/Company:120",
		("Last Service Date") +"date:50"
	]
	return cols

def get_data(filters):
	rs = qb.DocType('Repair And Services')
	rsi = qb.DocType('Repair And Services Item')
	query = (qb.from_(rs)
				.inner_join(rsi)
				.on(rs.name == rsi.parent)
				.select(rs.branch,rs.cost_center,rs.posting_date,rs.equipment,rs.equipment_type,rs.equipment_model,rs.current_km,rs.km_difference,rs.supplier)
				.select(rsi.item_code,rsi.item_name,rsi.item_group,rsi.rate,rsi.qty,rsi.charge_amount)
				.select(rs.total_amount,rs.company,rs.last_service_date)
				.where(rs.docstatus == 1)
				)

	if filters.get("branch"):
		query = (query.where(rs.branch == filters.branch))
	if filters.get("equipment"):
		query = (query.where(rs.equipment == filters.equipment))
	if filters.get("equipment_type"):
		query = (query.where(rs.equipment_type == filters.equipment_type))
	if filters.get("equipment_model"):
		query = (query.where(rs.equipment_model == filters.equipment_model))
	return query.run()
