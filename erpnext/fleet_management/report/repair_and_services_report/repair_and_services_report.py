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
		("Posting Date") + ":Date:120",
		("Equipment/Vehicle") + ":Link/Equipment:120",
		("Equipment Type")+":Link/Equipment Type:130",
		("Current KM")+":Data:100",
		("KM Difference") + ":Data:100",
		("Item")+":Link/Item:100",
		("Item Name")+":Data:100",
		("Rate")+":Currency:100",
		("Qty") +":Data:80",
		("Amount") +":Currency:100",
		("Last Service Date") +":Date:100",
		("Repair & Services Type") + ":Data:130"
	]
	return cols

def get_data(filters):
	rs = qb.DocType('Repair And Services')
	rsi = qb.DocType('Repair And Services Item')
	query = (qb.from_(rs)
				.inner_join(rsi)
				.on(rs.name == rsi.parent)
				.select(rs.branch,rs.posting_date,rs.equipment,rs.equipment_type,rs.current_km,rs.km_difference)
				.select(rsi.item_code,rsi.item_name,rsi.rate,rsi.qty,rsi.charge_amount)
				.select(rsi.last_service_date,rs.repair_and_services_type)
				.where(rs.docstatus == 1)
				)

	if filters.get("branch"):
		query = (query.where(rs.branch == filters.branch))
	if filters.get("equipment"):
		query = (query.where(rs.equipment == filters.equipment))
	if filters.get("equipment_type"):
		query = (query.where(rs.equipment_type == filters.equipment_type))
	# if filters.get("equipment_model"):
	# 	query = (query.where(rs.equipment_model == filters.equipment_model))
	if filters.from_date > filters.to_date:
		frappe.throw("From Date cannot be greater than To Date")
	if filters.from_date and filters.to_date:
		query = (query.where((rs.posting_date >= filters.from_date) & ( rs.posting_date <= filters.to_date)))
	if filters.repair_and_services_type:
		query = (query.where(rs.repair_and_services_type == filters.repair_and_services_type))
	return query.run()
