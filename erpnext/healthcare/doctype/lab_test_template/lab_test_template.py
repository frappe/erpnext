# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _

class LabTestTemplate(Document):
	def on_update(self):
		#Item and Price List update --> if (change_in_item)
		if(self.change_in_item and self.is_billable == 1 and self.item):
			updating_item(self)
			if not item_price_exist(self):
				if(self.test_rate != 0.0):
					price_list_name = frappe.db.get_value("Price List", {"selling": 1})
					if(self.test_rate):
						make_item_price(self.test_code, price_list_name, self.test_rate)
					else:
						make_item_price(self.test_code, price_list_name, 0.0)

			frappe.db.set_value(self.doctype,self.name,"change_in_item",0)
		elif(self.is_billable == 0 and self.item):
			frappe.db.set_value("Item",self.item,"disabled",1)
		self.reload()

	def after_insert(self):
		if not self.item:
			create_item_from_template(self)

	#Call before delete the template
	def on_trash(self):
		# remove template refernce from item and disable item
		if(self.item):
			try:
				frappe.delete_doc("Item",self.item)
			except Exception:
				frappe.throw("""Not permitted. Please disable the Test Template""")

def item_price_exist(doc):
	item_price = frappe.db.exists({
	"doctype": "Item Price",
	"item_code": doc.test_code})
	if(item_price):
		return True
	else:
		return False

def updating_item(self):
	frappe.db.sql("""update `tabItem` set item_name=%s, item_group=%s, disabled=0, standard_rate=%s,
		description=%s, modified=NOW() where item_code=%s""",
		(self.test_name, self.test_group , self.test_rate, self.test_description, self.item))

def create_item_from_template(doc):
	if(doc.is_billable == 1):
		disabled = 0
	else:
		disabled = 1
	#insert item
	item =  frappe.get_doc({
	"doctype": "Item",
	"item_code": doc.test_code,
	"item_name":doc.test_name,
	"item_group": doc.test_group,
	"description":doc.test_description,
	"is_sales_item": 1,
	"is_service_item": 1,
	"is_purchase_item": 0,
	"is_stock_item": 0,
	"show_in_website": 0,
	"is_pro_applicable": 0,
	"disabled": disabled,
	"stock_uom": "Unit"
	}).insert(ignore_permissions=True)

	#insert item price
	#get item price list to insert item price
	if(doc.test_rate != 0.0):
		price_list_name = frappe.db.get_value("Price List", {"selling": 1})
		if(doc.test_rate):
			make_item_price(item.name, price_list_name, doc.test_rate)
			item.standard_rate = doc.test_rate
		else:
			make_item_price(item.name, price_list_name, 0.0)
			item.standard_rate = 0.0
	item.save(ignore_permissions = True)
	#Set item to the template
	frappe.db.set_value("Lab Test Template", doc.name, "item", item.name)

	doc.reload() #refresh the doc after insert.

def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		"doctype": "Item Price",
		"price_list": price_list_name,
		"item_code": item,
		"price_list_rate": item_price
	}).insert(ignore_permissions=True)

@frappe.whitelist()
def change_test_code_from_template(test_code, doc):
	args = json.loads(doc)
	doc = frappe._dict(args)

	item_exist = frappe.db.exists({
		"doctype": "Item",
		"item_code": test_code})
	if(item_exist):
		frappe.throw(_("Code {0} already exist").format(test_code))
	else:
		frappe.rename_doc("Item", doc.name, test_code, ignore_permissions = True)
		frappe.db.set_value("Lab Test Template",doc.name,"test_code",test_code)
		frappe.rename_doc("Lab Test Template", doc.name, test_code, ignore_permissions = True)
	return test_code

@frappe.whitelist()
def disable_enable_test_template(status, name,  is_billable):
	frappe.db.set_value("Lab Test Template",name,"disabled",status)
	if(is_billable == 1):
		frappe.db.set_value("Item",name,"disabled",status)
