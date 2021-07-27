# -*- coding: utf-8 -*-
# Copyright (c) 2020, Sangita and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, cint, nowdate, flt
from frappe.model.mapper import get_mapped_doc
from itertools import groupby
class BulkPickListCreationTool(Document):
	@frappe.whitelist()
	def get_options(self, arg=None):
		if frappe.get_meta("Pick List").get_field("naming_series"):
			return frappe.get_meta("Pick List").get_field("naming_series").options

	@frappe.whitelist()
	def get_item(self):
		if self.purpose == "Delivery":
			return self.get_so()
		if self.purpose == "Material Transfer for Manufacture":
			return self.get_items_for_manufacturing()
	def get_items_for_manufacturing(self):
		condition = {}
		if self.from_date and self.to_date:
			condition['planned_start_date'] = ["between",[self.from_date,self.to_date]]
		if self.item_to_manufacture:
			condition['production_item'] = self.item_to_manufacture
		if self.work_order:
			condition['name'] = self.work_order
		
		all_wo = frappe.db.get_all('Work Order', filters = condition, fields = ['name','material_transferred_for_manufacturing','qty','status','skip_transfer','transfer_material_against'])
		data = []
		
		for wo in all_wo:
			show_pick_list = False
			if wo.get('transfer_material_against') or wo.get('skip_transfer'):
				show_pick_list = True
			remaining_qty = wo.get("material_transferred_for_manufacturing") - wo.get("qty")
		
			if remaining_qty < 0 and wo.get('status') != "Stopped" and show_pick_list:
				all_wo_items = frappe.db.get_all("Work Order Item", {"parent": wo.get("name")}, ['item_code','parent','required_qty','transferred_qty'])
				for item in all_wo_items:
					data.append(item)
		for d in data:
			qty = d.get("required_qty") - d.get("transferred_qty")
			bom = frappe.db.get_value("Work Order", {"name":d.get('parent')}, 'bom_no')
			self.append("item", {
				"item_code": d.get("item_code"),
				"work_order": d.get('parent'),
				"qty": qty,
				'bom': bom,
			})
		return True

	def get_so(self):
		conditions = ""
		if self.company:
			conditions +="AND so.company = %s" % frappe.db.escape(self.company)

		if self.delivery_date_from:
			conditions += "AND soi.delivery_date >= '%s'" % self.delivery_date_from

		if self.delivery_date_to:
			conditions += "AND soi.delivery_date <= '%s'" % self.delivery_date_to

		if self.warehouse:
			conditions += "AND soi.warehouse = %s " % frappe.db.escape(self.warehouse)

		if self.item_name:
			conditions += "AND soi.item_code = %s " % frappe.db.escape(self.item_name)

		if self.customer:
			conditions +="AND so.customer = %s" % frappe.db.escape(self.customer)

		if self.customer_group:
			conditions +="AND c.customer_group = %s "% frappe.db.escape(self.customer_group)

		if self.customer_name:
			conditions +="AND c.customer_name = %s"% frappe.db.escape(self.customer_name)

		query = frappe.db.sql(""" select 
			so.customer,
			c.customer_name,
			soi.item_code,
			soi.item_name,
			soi.description,
			soi.item_group,
			soi.warehouse,
			soi.qty,
			soi.stock_qty,
			soi.uom,
			soi.conversion_factor,
			soi.stock_uom,
			so.name,
			soi.name as soi_item,
			soi.delivered_qty

			from `tabSales Order Item` soi 
			join `tabSales Order` so ON soi.parent = so.name
			join `tabCustomer` c on so.customer = c.name
			where so.docstatus = 1
			{conditions} """.format(conditions=conditions), as_dict=1)
		
		for data in query:
			data["qty"] = data["qty"] - data["delivered_qty"]
			data["stock_qty"] = (data["qty"] - data["delivered_qty"]) * data["conversion_factor"]
		return query

	@frappe.whitelist()
	def make_pick_list(self):
		if self.purpose == "Delivery":
			self.make_pick_list_for_so()
		if self.purpose == "Material Transfer for Manufacture":
			self.make_pick_list_for_wo()
	#@frappe.whitelist()
	def make_pick_list_for_wo(self):
		item_table = []
		for i in self.item:
			item_table.append(i.as_dict())

		def key_func(k):
			return k['work_order']
		item_table = sorted(item_table, key=key_func)
		wo_wise_data = []
		for key, value in groupby(item_table, key_func):
			#print(list(value))
			wo_wise_data.append(list(value))
		#print(wo_wise_data)
		for data in wo_wise_data:
			doc = frappe.new_doc("Pick List")
			doc.naming_series = self.series
			#doc.customer = customer
			doc.company = self.company
			doc.purpose = "Material Transfer for Manufacture"
			doc.work_order = data[0].get("work_order")
			for d in data:
				item_data = frappe.db.get_value("Item", {"item_code":d.get("item_code")},['stock_uom',"name"], as_dict = True)
				con_factor = frappe.db.get_value("UOM Conversion Detail",{"parent": item_data.get("name"),"uom":item_data.get("stock_uom")},'conversion_factor')
				doc.append("locations", {
					'item_code': d.get("item_code"),
					"qty": d.get("qty"),
					"stock_qty": d.get("qty"),
					'uom': item_data.get("stock_uom"),
					"conversion_factor": con_factor
				})
			doc.insert()
			doc.save()
	#@frappe.whitelist()
	def make_pick_list_for_so(self):
		lst = []
		for itm in self.items:
			lst.append(itm.customer)
		for customer in set(lst):
			doc = frappe.new_doc("Pick List")
			doc.naming_series = self.series
			doc.customer = customer
			doc.company = self.company
			doc.purpose = "Delivery"
			doc.parent_warehouse = self.parent_warehouse
			for itm in self.items:
				if customer == itm.customer:
					doc.append("locations", {
						"item_name": itm.item_name,
						"item_code": itm.item_code,
						"description": itm.description,
						"warehouse": itm.warehouse,
						"qty": itm.qty,
						"uom": itm.uom,
						"stock_qty": itm.stock_qty,
						"stock_uom": itm.stock_uom,
						"conversion_factor": itm.conversion_factor,
						"sales_order": itm.sales_order,
						"sales_order_item": itm.sales_order_item,
					})
			doc.set_item_locations()
			doc.insert()
			doc.save()
			#doc.submit()
			#print('line: ', doc.get('locations'))


# @frappe.whitelist()
# def create_pick_list(source_name, target_doc=None):
# 	def update_item_quantity(source, target, source_parent):
# 		target.qty = flt(source.qty) - flt(source.delivered_qty)
# 		target.stock_qty = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.conversion_factor)
# 		if source_parent.customer:
# 			target.customer = source_parent.customer

# 	doc = get_mapped_doc('Sales Order', source_name, {
# 		'Sales Order': {
# 			'doctype': 'Bulk Pick List Creation Tool',
# 			'validation': {
# 				'docstatus': ['=', 1]
# 			}
# 		},
# 		'Sales Order Item': {
# 			'doctype': 'Bulk Pick List Item',
# 			'field_map': {
# 				'parent': 'sales_order',
# 				'name': 'sales_order_item'
# 			},
# 			'postprocess': update_item_quantity,
# 			'condition': lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
# 		},
# 	}, target_doc)
# 	return doc