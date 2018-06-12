# -*- coding: utf-8 -*-
# Copyright (c) 2017, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

class ClinicalProcedureTemplate(Document):
	def on_update(self):
		#Item and Price List update --> if (change_in_item)
		if(self.change_in_item and self.is_billable == 1 and self.item):
			updating_item(self)
			if(self.rate != 0.0):
				updating_rate(self)
		elif(self.is_billable == 0 and self.item):
			frappe.db.set_value("Item",self.item,"disabled",1)

		frappe.db.set_value(self.doctype,self.name,"change_in_item",0)
		self.reload()

	def after_insert(self):
		create_item_from_template(self)

	#Call before delete the template
	def on_trash(self):
		if(self.item):
			try:
				frappe.delete_doc("Item",self.item)
			except Exception:
				frappe.throw("""Not permitted. Please disable the Procedure Template""")

	def get_item_details(self, args=None):
		item = frappe.db.sql("""select stock_uom, item_name
			from `tabItem`
			where name = %s
				and disabled=0
				and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %s)""",
			(args.get('item_code'), nowdate()), as_dict = 1)
		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get('item_code')))

		item = item[0]

		ret = {
			'uom'			      	: item.stock_uom,
			'stock_uom'			  	: item.stock_uom,
			'item_name' 		  	: item.item_name,
			'quantity'				: 0,
			'transfer_qty'			: 0,
			'conversion_factor'		: 1
		}
		return ret

def updating_item(self):
	frappe.db.sql("""update `tabItem` set item_name=%s, item_group=%s, disabled=0,
		description=%s, modified=NOW() where item_code=%s""",
		(self.template, self.item_group , self.description, self.item))
def updating_rate(self):
	frappe.db.sql("""update `tabItem Price` set item_name=%s, price_list_rate=%s, modified=NOW() where
	 item_code=%s""",(self.template, self.rate, self.item))

def create_item_from_template(doc):
	if(doc.is_billable == 1):
		disabled = 0
	else:
		disabled = 1
	#insert item
	item =  frappe.get_doc({
	"doctype": "Item",
	"item_code": doc.template,
	"item_name":doc.template,
	"item_group": doc.item_group,
	"description":doc.description,
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
	if(doc.rate != 0.0):
		price_list_name = frappe.db.get_value("Price List", {"selling": 1})
		if(doc.rate):
			make_item_price(item.name, price_list_name, doc.rate)
		else:
			make_item_price(item.name, price_list_name, 0.0)
	#Set item to the template
	frappe.db.set_value("Clinical Procedure Template", doc.name, "item", item.name)

	doc.reload() #refresh the doc after insert.

def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		"doctype": "Item Price",
		"price_list": price_list_name,
		"item_code": item,
		"price_list_rate": item_price
	}).insert(ignore_permissions=True)

@frappe.whitelist()
def change_item_code_from_template(item_code, doc):
	args = json.loads(doc)
	doc = frappe._dict(args)

	if(frappe.db.exists({
		"doctype": "Item",
		"item_code": item_code})):
		frappe.throw(_("Code {0} already exist").format(item_code))
	else:
		frappe.rename_doc("Item", doc.item_code, item_code, ignore_permissions = True)
		frappe.db.set_value("Clinical Procedure Template", doc.name, "item_code", item_code)
	return

@frappe.whitelist()
def disable_enable_template(status, name, item_code):
	frappe.db.set_value("Clinical Procedure Template", name, "disabled", status)
	if (frappe.db.exists({ #set Item's disabled field to status
		"doctype": "Item",
		"item_code": item_code})):
			frappe.db.set_value("Item", item_code, "disabled", status)

	return
