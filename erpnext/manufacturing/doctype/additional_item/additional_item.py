# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate

class AdditionalItem(Document):
	def after_save(self):
		self.date= nowdate()
		self.user = frappe.session.user
	@frappe.whitelist()
	def bom_wise_item(self):
		q = """select bom_no from `tabWork Order` where name ='{0}';""".format(self.work_order)
		bom = frappe.db.sql(q, as_dict = True)
		if bom:
			doc = frappe.get_doc("BOM",bom[0].get('bom_no') )
			item_list = []
			wo_doc = frappe.get_doc("Work Order", self.work_order)
			bom_doc = frappe.get_doc("BOM", wo_doc.bom_no)
			
			if doc.get('allow_adding_items') == 1:
				items = frappe.db.sql("select distinct item_code from `tabItem` where is_stock_item = 1 and disabled = 0",as_dict = True)
				for i in items:
					item_list.append(i.get('item_code'))
			else:
				query = """select item_code from `tabBOM Item` where parent="{0}";""".format(bom[0].get('bom_no'))
				items = frappe.db.sql(query, as_dict = True)
				for i in items:
					item_list.append(i.get('item_code'))
			
			for i in bom_doc.items:
				print(i.get("allowed_to_change_qty_in_wo"), i.get('item_code'))
				if i.get("allowed_to_change_qty_in_wo") == 0:
					item_list.remove(i.get('item_code'))
			return item_list
	
	@frappe.whitelist()
	def get_job_card(self):
		all_job_card = frappe.db.get_all("Job Card", {"work_order": self.work_order}, ['name'])
		job_card = []
		for job in all_job_card:
			job_card.append(job.get('name'))
		return job_card

	def before_submit(self):
		work_order = frappe.get_doc("Work Order", {'name':self.work_order})
		wo_item = []
		wo_item_qty = []
		for item in work_order.required_items:
			wo_item.append(item.get("item_code"))
			wo_item_qty.append(item.get('required_qty'))

		for item in self.items:
			if item.get("item") in wo_item:
				q = """select rate from `tabWork Order Item` where parent = "{0}" and item_code="{1}";""".format(self.work_order,item.get("item"))
				item_rate = frappe.db.sql(q,as_dict = True)
				item_index = wo_item.index(item.get('item'))
				old_qty = wo_item_qty[item_index]
				item_qty = item.get('qty')
				total_qty = float(old_qty) + float(item_qty)
				amount = total_qty * int(item_rate[0].get("rate"))
				query = """UPDATE `tabWork Order Item` SET required_qty = {0}, amount = {1}  WHERE parent='{2}' and item_code='{3}';""".format(total_qty,amount,self.work_order,item.get("item"))
				frappe.db.sql(query)
				frappe.db.commit()
				
			else:
				item_master = frappe.db.get_value('Item', {'item_code':item.get('item')},['item_name','include_item_in_manufacturing','description'], as_dict = 1)
				
				
				doc = frappe.get_doc("Work Order", self.work_order)
				rate = 0
				rate_with_warehouse = frappe.db.get_value("Bin", {"item_code":item.get("item"),"warehouse":doc.source_warehouse},['valuation_rate'])
				if rate_with_warehouse:
					rate = rate_with_warehouse
				rate_without_warehouse = frappe.db.get_value("Bin", {"item_code":item.get("item")},['valuation_rate'])
				if not rate_with_warehouse and rate_without_warehouse:
					rate = rate_without_warehouse
				amt = float(item.get("qty")) * float(rate)
				
				doc.append("required_items", {
					"item_name": item_master.get("item_name"),
					"item_code": item.get("item"),
					"required_qty": item.get("qty"),
					"source_warehouse": doc.source_warehouse,
					"include_item_in_manufacturing": item_master.get('include_item_in_manufacturing'),
					"additional_material":1,
					"wip_warehouse": doc.wip_warehouse,
					"type": "RM",
					'available_qty_at_source_warehouse': item.get("current_stock"),
					"weight_per_unit": item.get("weight_per_unit"),
					"description" : item_master.get("description"),
					'rate': rate,
					'amount': amt

				})
				doc.flags.ignore_validate_update_after_submit = True
				doc.save(ignore_permissions= True)

@frappe.whitelist()
def get_item_data(item,wo):
	wo_source_warehouse = frappe.db.get_value("Work Order", {'name':wo}, ['source_warehouse'])
	item_stock = frappe.db.get_value("Bin", {"warehouse": wo_source_warehouse,"item_code":item},['actual_qty'])
	q = """select item_name,weight_uom,weight_per_unit from `tabItem` where item_code='{0}'""".format(item)

	item_detail = frappe.db.sql(q, as_dict = True)
	data = []
	for i in item_detail:
		i['qty'] = item_stock
		data.append(i)
	return data

@frappe.whitelist()
def set_qty(table):
	table = json.loads(table)
	total = 0
	for row in table:
		item_weight_per_unit = frappe.db.get_value("Item", {"item_code": row.get("item_code")},['weight_per_unit'])
		if (item_weight_per_unit and row.get("transfer_qty")):
			weight = item_weight_per_unit * row.get("transfer_qty")
			total += weight
	return total
