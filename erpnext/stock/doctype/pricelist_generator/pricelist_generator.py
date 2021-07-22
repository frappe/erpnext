# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PriceListGenerator(Document):


	def validate(self):
		for res in self.price_details:
			if res.brand:
				lst=frappe.get_doc("Brand",res.brand)
				for i in lst.brand_defaults:
					if i.company:
						if self.company==i.company:
							res.brand_list_price==i.item_price
			doc=frappe.get_doc("Item",res.product)
			if doc.specific_gravity:
				res.volume=res.weight/doc.specific_gravity


	def before_save(self):
		self.get_cost_weight()
		self.get_cost_volume()

	def get_cost_weight(self):
		for res in self.price_details:
			if res.product:
				res.list_priceweight = (res.brand_list_price + res.addpkg_cost) * res.weight


	def get_cost_volume(self):
		for res in self.price_details:
			if res.product:
				res.list_priceunit = res.brand_list_price + res.addpkg_cost
				res.list_pricevolume = (res.brand_list_price + res.addpkg_cost)*res.volume




	def on_submit(self):
		doc=frappe.new_doc("Price List")
		doc.price_list_name=self.pricelist_name
		doc.selling=1
		doc.buying=1
		doc.append("countries", {
			"Country":"India"
		})
		doc.save()
		for res in self.price_details: 
			doc_it=frappe.new_doc("Item Price")
			doc_it.item_code=res.product
			doc_it.uom=res.uom
			doc_it.brand=res.brand
			doc_it.price_list=doc.name
			doc_it.price_list_rate=res.brand_list_price
			doc_it.save()

