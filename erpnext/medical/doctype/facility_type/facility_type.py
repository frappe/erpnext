# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _

class FacilityType(Document):
	def on_update(self):
		#Item and Price List update --> if (change_in_item)
		if(self.change_in_item):
			item = frappe.db.get ("Item",{"item_code":self.item_code})
			if(item):
				updating_item(self,item)
				if(self.rate != 0.0):
					updating_rate(self,item)
			else:
				create_item(self)
			frappe.db.set_value(self.doctype,self.name,"change_in_item",0)
			self.reload()

	def after_insert(self):
		create_item(self)

	#Call before delete the facility type
	def on_trash(self):
		# get item
		item = frappe.db.get ("Item",{"item_code":self.item_code})
		if(item):
			try:
				frappe.delete_doc("Item",item.name)
			except Exception, e:
				frappe.throw("""Not permitted. Please disable the Facility Type""")

def updating_item(self,item):
	frappe.db.sql("""update `tabItem` set item_group=%s, disabled=0,
		description=%s, modified=NOW() where item_code=%s""",
		(self.item_group , self.description, self.item_code))
def updating_rate(self,item):
	frappe.db.sql("""update `tabItem Price` set item_name=%s, price_list_rate=%s, modified=NOW() where item_code=%s""",(self.name, self.rate, self.item_code))


def create_item(doc):
	#insert item
	item =  frappe.get_doc({
	"doctype": "Item",
	"item_code": doc.item_code,
	"item_name":doc.room_type,
	"item_group": doc.item_group,
	"description":doc.description,
	"is_sales_item": 1,
	"is_purchase_item": 0,
	"is_stock_item": 0,
	"show_in_website": 0,
	"is_pro_applicable": 0,
	"disabled": 0,
	"stock_uom": "Unit"
	}).insert(ignore_permissions=True)

	frappe.db.set_value(doc.doctype,doc.name,"item",item.name)

	#insert item price
	#get item price list to insert item price
	if(doc.rate != 0.0):
		price_list_name = frappe.db.get_value("Price List", {"selling": 1})
		if(doc.rate):
			make_item_price(item.name, price_list_name, doc.rate)
		else:
			make_item_price(item.name, price_list_name, 0.0)
	doc.reload() #refresh the doc after insert.

def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		"doctype": "Item Price",
		"price_list": price_list_name,
		"item_code": item,
		"price_list_rate": item_price
	}).insert(ignore_permissions=True)

@frappe.whitelist()
def disable_enable_facility_type(status, name):
	frappe.db.set_value("Facility Type",name,"disabled",status)
	frappe.db.set_value("Item",name,"disabled",status)

@frappe.whitelist()
def change_item_code(item_code, doc):
	args = json.loads(doc)
	doc = frappe._dict(args)

	item_exist = frappe.db.exists({
		"doctype": "Item",
		"item_code": item_code})
	if(item_exist):
		frappe.throw(_("Code {0} already exist").format(item_code))
	else:
		frappe.rename_doc("Item", doc.item_code, item_code, ignore_permissions = True)
		frappe.db.set_value("Facility Type",doc.name,"item_code",item_code)
