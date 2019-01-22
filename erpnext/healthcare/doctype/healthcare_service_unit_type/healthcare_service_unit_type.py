# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class HealthcareServiceUnitType(Document):
	def validate(self):
		if self.is_billable == 1:
			if not self.uom or not self.item_group or not self.description or not self.no_of_hours > 0:
				frappe.throw(_("Configure Item Fields like UOM, Item Group, Description and No of Hours."))

	def after_insert(self):
		if self.inpatient_occupancy and self.is_billable:
			create_item(self)

	def on_trash(self):
		if(self.item):
			try:
				frappe.delete_doc("Item",self.item)
			except Exception:
				frappe.throw(_("""Not permitted. Please disable the Service Unit Type"""))

	def on_update(self):
		if(self.change_in_item and self.is_billable == 1 and self.item):
			updating_item(self)
			item_price = item_price_exist(self)
			if not item_price:
				if(self.rate != 0.0):
					price_list_name = frappe.db.get_value("Price List", {"selling": 1})
					if(self.rate):
						make_item_price(self.item_code, price_list_name, self.rate)
					else:
						make_item_price(self.item_code, price_list_name, 0.0)
			else:
				frappe.db.set_value("Item Price", item_price, "price_list_rate", self.rate)

			frappe.db.set_value(self.doctype,self.name,"change_in_item",0)
		elif(self.is_billable == 0 and self.item):
			frappe.db.set_value("Item",self.item,"disabled",1)
		self.reload()

def item_price_exist(doc):
	item_price = frappe.db.exists({
	"doctype": "Item Price",
	"item_code": doc.item_code})
	if(item_price):
		return item_price[0][0]
	else:
		return False

def updating_item(doc):
	frappe.db.sql("""update `tabItem` set item_name=%s, item_group=%s, disabled=0, standard_rate=%s,
		description=%s, modified=NOW() where item_code=%s""",
		(doc.service_unit_type, doc.item_group , doc.rate, doc.description, doc.item))

def create_item(doc):
	#insert item
	item =  frappe.get_doc({
	"doctype": "Item",
	"item_code": doc.item_code,
	"item_name":doc.service_unit_type,
	"item_group": doc.item_group,
	"description":doc.description,
	"is_sales_item": 1,
	"is_service_item": 1,
	"is_purchase_item": 0,
	"is_stock_item": 0,
	"show_in_website": 0,
	"is_pro_applicable": 0,
	"disabled": 0,
	"stock_uom": doc.uom
	}).insert(ignore_permissions=True)

	#insert item price
	#get item price list to insert item price
	if(doc.rate != 0.0):
		price_list_name = frappe.db.get_value("Price List", {"selling": 1})
		if(doc.rate):
			make_item_price(item.name, price_list_name, doc.rate)
			item.standard_rate = doc.rate
		else:
			make_item_price(item.name, price_list_name, 0.0)
			item.standard_rate = 0.0
	item.save(ignore_permissions = True)
	#Set item to the Doc
	frappe.db.set_value("Healthcare Service Unit Type", doc.name, "item", item.name)

	doc.reload() #refresh the doc after insert.

def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		"doctype": "Item Price",
		"price_list": price_list_name,
		"item_code": item,
		"price_list_rate": item_price
	}).insert(ignore_permissions=True)

@frappe.whitelist()
def change_item_code(item, item_code, doc_name):
	item_exist = frappe.db.exists({
		"doctype": "Item",
		"item_code": item_code})
	if(item_exist):
		frappe.throw(_("Code {0} already exist").format(item_code))
	else:
		frappe.rename_doc("Item", item, item_code, ignore_permissions = True)
		frappe.db.set_value("Healthcare Service Unit Type", doc_name, "item_code", item_code)

@frappe.whitelist()
def disable_enable(status, doc_name, item,  is_billable):
	frappe.db.set_value("Healthcare Service Unit Type", doc_name, "disabled", status)
	if(is_billable == 1):
		frappe.db.set_value("Item", item, "disabled", status)
