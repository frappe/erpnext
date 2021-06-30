# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AddAlternateItem(Document):
	def on_submit(self):
		self.alter_original_item_qty()
		self.add_alternate_item()
	@frappe.whitelist()
	def get_aditional_item_data(self):
		all_item = frappe.get_all("Additional Items Detail",{'parent': self.add_additional_item},['item','item_name','qty','parent'])
		alternate_item_list = []
		item_list = []
		for i in all_item:
			item = frappe.get_doc('Item',i.get('item'))
			if(item.get('allow_alternative_item') ==1 ):
				alt_item = frappe.db.get_all("Item Alternative", {'item_code':i.get('item')}, ['alternative_item_code'])
				for itm in alt_item:
					alternate_item_list.append(itm.get('alternative_item_code'))
				wo = frappe.get_doc('Additional Item',self.add_additional_item).get('work_order')
				warehouse = frappe.get_value("Work Order Item", {'parent':wo,'item_code':i.get('item')},'source_warehouse')
				self.append('item',{
					'item_code': i.get('item'),
					'item_name': i.get('item_name'),
					'qty': i.get('qty'),
					'warehouse': warehouse
				})
		return alternate_item_list

	@frappe.whitelist()
	def get_wo_item_data(self):
		all_item = frappe.get_all("Work Order Item",{'parent': self.work_order},['item_code','item_name','required_qty'])
		alternate_item_list = []
		item_list = []
		for i in all_item:
			item = frappe.get_doc('Item',i.get('item_code'))
			if(item.get('allow_alternative_item') ==1 ):
				alt_item = frappe.db.get_all("Item Alternative", {'item_code':i.get('item_code')}, ['alternative_item_code'])
				for itm in alt_item:
					alternate_item_list.append(itm.get('alternative_item_code'))
				#wo = frappe.get_doc('Work Order',self.work_order).get('work_order')
				warehouse = frappe.get_value("Work Order Item", {'parent':self.work_order,'item_code':i.get('item_code')},'source_warehouse')
				self.append('item',{
					'item_code': i.get('item_code'),
					'item_name': i.get('item_name'),
					'qty': i.get('required_qty'),
					'warehouse': warehouse
				})
		return alternate_item_list

	def alter_original_item_qty(self):
		if self.add_additional_item and not self.work_order:
			for item in self.item:
				get_qty_from_additional_item = frappe.get_value("Additional Items Detail", {'parent':self.add_additional_item, 'item':item.get('item_code')},'qty')
				alternate_item_qty = float(get_qty_from_additional_item) - float(item.get('qty'))
				if item.get('item_code') != item.get('alternate_item_code') and item.get('alternate_item_code'):
					q = """
						UPDATE `tabAdditional Items Detail`
						SET qty = {0}
						WHERE parent = '{1}' and item = '{2}';
						""".format(alternate_item_qty,self.add_additional_item,item.get('item_code'))
					frappe.db.sql(q)
			frappe.db.commit()

		if not self.add_additional_item and self.work_order:
			for item in self.item:
				get_qty_from_work_order = frappe.get_value("Work Order Item", {'parent':self.work_order, 'item_code':item.get('item_code')},'required_qty')
				alternate_item_qty = float(get_qty_from_work_order) - float(item.get('qty'))
				if item.get('item_code') != item.get('alternate_item_code') and item.get('alternate_item_code'):
					q = """
						UPDATE `tabWork Order Item`
						SET required_qty = {0}
						WHERE parent = '{1}' and item_code = '{2}';
						""".format(alternate_item_qty,self.work_order,item.get('item_code'))
					frappe.db.sql(q)
			frappe.db.commit()




	def add_alternate_item(self):
		if self.add_additional_item and not self.work_order:
			doc = frappe.get_doc("Additional Item",self.add_additional_item)
			for item in self.item:
				if item.get('item_code') != item.get('alternate_item_code') and item.get('alternate_item_code'):
					doc.append('items',{
						'item': item.get('alternate_item_code'),
						'item_name': item.get('item_name'),
						'qty': item.get('qty')
					})
			doc.save()
		
		if not self.add_additional_item and self.work_order:
			doc = frappe.get_doc("Work Order",self.work_order)
			for item in self.item:
				if item.get('item_code') != item.get('alternate_item_code') and item.get('alternate_item_code'):
					doc.append('required_items',{
						'item_code': item.get('alternate_item_code'),
						'item_name': item.get('alternate_item_name'),
						'required_qty': item.get('qty'),
						'source_warehouse': item.get('warehouse')
					})
			doc.save()
			
	
			

