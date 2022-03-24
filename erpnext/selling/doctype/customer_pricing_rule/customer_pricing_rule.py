# -*- coding: utf-8 -*-
# Copyright (c) 2021, Sangita and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate
import json
class CustomerPricingRule(Document):
	def on_submit(self):
		for i in self.item_details:
			price_list_rate = frappe.db.get_value("Item Price", {"item_code": i.item, 'price_list':self.for_price_list}, "price_list_rate")
			list_price = price_list_rate + i.additional_price
			i.base_price = price_list_rate
			i.list_price = list_price
			doc_title = self.customer+'-'+i.get("item")
			pr_doc = frappe.db.get_value('Pricing Rule', {'title': doc_title}, ['title','customer_pricing_rule_id'], as_dict = True)
			if not pr_doc:
				doc = frappe.new_doc("Pricing Rule")
				doc.title = doc_title
				doc.selling = 1
				doc.applicable_for = "Customer"
				doc.customer = self.customer
				doc.valid_from = self.valid_from
				doc.valid_upto = self.valid_upto
				doc.currency=self.currency
				item_uom = frappe.db.get_value("Item", i.item, "stock_uom")
				doc.append("items", {
				"item_code":i.get("item"),
				"uom": item_uom
				})
				if i.get("type") == "Discount":
					doc.rate_or_discount = "Discount Amount"
					doc.discount_amount = i.get("discount_margin")
				if i.get("type") == "Margin":
					doc.margin_type = "Amount"
					doc.margin_rate_or_amount = i.get("discount_margin")
				doc.min_qty = self.min_qty
				doc.max_qty = self.max_qty
				doc.min_amt = self.min_amt
				doc.max_amt = self.max_amt
				doc.for_price_list = self.for_price_list
				doc.insert()
			if pr_doc:
				if pr_doc.get('title'):
					if i.get("type") == "Discount":
						query = """UPDATE `tabPricing Rule` SET discount_amount = '{0}',rate_or_discount = "Discount Amount",margin_rate_or_amount=0.00 WHERE title = '{1}';""".format(i.get("discount_margin") ,doc_title)	
					if i.get("type") == "Margin":
						query = """UPDATE `tabPricing Rule` SET margin_rate_or_amount = '{0}',margin_type = "Amount",discount_amount=0.00 WHERE title = '{1}';""".format(i.get("discount_margin") ,doc_title)	
					
					frappe.db.sql(query)
					frappe.db.commit()

	def on_cancel(self):
		frappe.db.sql("""delete from `tabPricing Rule` where customer_pricing_rule_id ='{0}' """.format(self.name))


	def before_insert(self):
		is_existing_customer = frappe.db.get_value('Customer Pricing Rule', {'customer': self.customer,"docstatus":1}, 'customer')
		if is_existing_customer == self.customer:
			msg = "Customer Pricing Rule for {0} already exist".format(self.customer)
			frappe.throw(msg)

	@frappe.whitelist()
	def onload_customer_pricing(self):
		print(" inside py onload_customer_pricing ")
		doc=frappe.db.sql("""Select name from `tabCustomer Pricing Rule` where docstatus=1""",as_dict=1)
		for i in doc:
			cprdoc=frappe.get_doc("Customer Pricing Rule",i.get("name"))
			for i in cprdoc.item_details:
				price_list_rate = frappe.db.get_value("Item Price", {"item_code": i.item, 'price_list':cprdoc.for_price_list}, "price_list_rate")
				list_price = price_list_rate + i.additional_price
				i.base_price = price_list_rate
				i.list_price = list_price
				frappe.db.sql("""UPDATE `tabCustomer Pricing Rule Item` SET base_price='{0}',list_price='{1}' where item='{2}' and parent='{3}'""".format(price_list_rate,list_price,i.item,i.parent))
				print(" base", price_list_rate , "laist price", list_price)
				doc_title = cprdoc.customer+'-'+i.get("item")
				pr_doc = frappe.db.get_value('Pricing Rule', {'title': doc_title}, ['title','customer_pricing_rule_id'], as_dict = True)
				if not pr_doc:
					doc = frappe.new_doc("Pricing Rule")
					doc.title = doc_title
					doc.selling = 1
					doc.applicable_for = "Customer"
					doc.customer = cprdoc.customer
					doc.valid_from = cprdoc.valid_from
					doc.valid_upto = cprdoc.valid_upto
					doc.currency=cprdoc.currency
					item_uom = frappe.db.get_value("Item", i.item, "stock_uom")
					doc.append("items", {
					"item_code":i.get("item"),
					"uom": item_uom
					})
					if i.get("type") == "Discount":
						doc.rate_or_discount = "Discount Amount"
						doc.discount_amount = i.get("discount_margin")
					if i.get("type") == "Margin":
						doc.margin_type = "Amount"
						doc.margin_rate_or_amount = i.get("discount_margin")
					doc.min_qty = cprdoc.min_qty
					doc.max_qty = cprdoc.max_qty
					doc.min_amt = cprdoc.min_amt
					doc.max_amt = cprdoc.max_amt
					doc.for_price_list = cprdoc.for_price_list
					doc.insert()
				if pr_doc:
					if pr_doc.get('title'):
						if i.get("type") == "Discount":
							query = """UPDATE `tabPricing Rule` SET discount_amount = '{0}',rate_or_discount = "Discount Amount",margin_rate_or_amount=0.00 WHERE title = '{1}';""".format(i.get("discount_margin") ,doc_title)	
						if i.get("type") == "Margin":
							query = """UPDATE `tabPricing Rule` SET margin_rate_or_amount = '{0}',margin_type = "Amount",discount_amount=0.00 WHERE title = '{1}';""".format(i.get("discount_margin") ,doc_title)	
						
						frappe.db.sql(query)
						frappe.db.commit()	
		return 1	



@frappe.whitelist()
def insert_link_to_doc(name,customer,item_line):
	item_list = json.loads(item_line)
	for i in item_list:
		title = customer+'-'+i.get('item')
		query = """UPDATE `tabPricing Rule` SET customer_pricing_rule_id = '{0}' WHERE title = '{1}';""".format(name, title)
		frappe.db.sql(query)
		frappe.db.commit()



@frappe.whitelist()
def check_duplicate_item(item,doc):
	d = json.loads(doc)
	item_list = []
	for i in d.get('item_details'):
		item_list.append(i.get('item'))
	duplicate_item = set([x for x in item_list if item_list.count(x) > 1])
	
	if duplicate_item:
		for i in duplicate_item:
			if item == i:
				msg = "item <b>{0}</b> is duplicate in table".format(item)
				frappe.throw(msg)

@frappe.whitelist()
def fetch_uom(parent):
	uom_list = []
	all_uom = frappe.db.get_all("Pricing Rule Item Code", {"parent":parent},['uom'])
	for uom in all_uom:
		uom_list.append(uom.get("uom"))
	return uom_list


@frappe.whitelist()
def clear_link(item,customer):
	title = customer+'-'+item
	query = """UPDATE `tabPricing Rule` SET customer_pricing_rule_id = NULL WHERE title = '{0}';""".format(title)
	frappe.db.sql(query)
	frappe.db.commit()

@frappe.whitelist()
def fetch_order_warehouse_num(so_num):
	#so = frappe.get_doc("Sales Order", so_num)
	filters_json = frappe.get_all("Order Warehouse Rule", {"active":'1'},["name1","filters_json", "warehouse", "priority","active"])
	filter_list = []
    # rule_detail = {}
	order_warehouse = None
	order_warehouse_num = None
	copy_list = []
	for filters in filters_json:
		filter={}
		if(filters.get("filters_json")):
			filter_in_json = json.loads(filters.get("filters_json"))
			for lst in filter_in_json:
				filter[lst[1]] = [lst[2],lst[3]]  
			filter['warehouse'] = filters.get("warehouse")
			filter["priority"] = filters.get("priority")
			filter["rule_name"] = filters.get("name1")
			filter_list.append(filter)

	for fil in filter_list:
		copy = fil.copy()
		if fil.get('warehouse'):
			del fil['warehouse']
		if fil.get('rule_name'):
			del fil['rule_name']
		if fil.get('priority'):
			del fil['priority']
		fil['name'] = ['=', so_num]
		
		get_so = frappe.db.get_value('Sales Order', fil, ['name'])
		if(get_so == so_num):
			copy_list.append(copy)
	if(len(copy_list) > 0):
		warehouse_details =  max(copy_list, key=lambda x:x['priority'])
		# return [warehouse_details.get('rule_name'),warehouse_details.get('warehouse')]
		order_warehouse = warehouse_details.get('warehouse')
		order_warehouse_num = warehouse_details.get('rule_name')
	return [order_warehouse_num, order_warehouse]
