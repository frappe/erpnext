# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils.data import flt, getdate


class PriceListGenerator(Document):

	def validate(self):
		if getdate(self.start_date)>getdate(self.end_date):
			frappe.throw("End date Cannot be Less than Start date")
		for res in self.price_details:
			pack_g=frappe.db.get_value("Product Pack",{"item":res.item},["diff_price"])
			if res.brand:
				lst=frappe.get_doc("Brand",res.brand)
				for i in lst.brand_defaults:
					if i.selling_cost_center:
						if self.company==i.company and self.cost_center==i.selling_cost_center:
							res.brand_list_price=i.item_price
						if not i.item_price:
							frappe.throw("Please set Item Price in brand")

	def before_save(self):
		self.get_cost_volume()


	def get_cost_volume(self):
		for res in self.price_details:
			if res.item:
				res.list_priceunit = (flt(res.brand_list_price) + flt(res.addpkg_cost)) * flt(res.weight)
			
	@frappe.whitelist()
	def get_items_brand(self,filters=None):
		lst=frappe.db.get_all("Item",filters=filters)
		for j in lst:
			doc=frappe.get_doc("Item",j.name)
			doc1 = frappe.db.get_all("Brand Price",{"cost_center":self.cost_center},["brand","price"])
			for d in doc1:
				if doc.brand==d.get("brand"):
					pack_g=frappe.db.get_value("Product Pack",{"item":doc.name},["diff_price"])
					self.append("price_details",{
						"item":doc.name,
						"item_name":doc.item_name,
						"item_group":doc.item_group,
						"uom":doc.stock_uom,
						"costunit":doc.valuation_rate,
						"weight":doc.weight_per_unit,
						"weight_uom":doc.weight_uom,
						"brand":doc.brand,
						"min_qty":1,
						"addpkg_cost":pack_g,
						"brand_list_price":d.get("price")
					})

			self.save()
		return True


	def on_submit(self):
		doc=frappe.new_doc("Price List")
		doc.price_list_name=self.pricelist_name
		doc.selling=self.selling
		doc.buying=self.buying
		doc.append("countries", {
			"Country":"India"
		})
		doc.save()
		for res in self.price_details: 
			doc_it=frappe.new_doc("Item Price")
			doc_it.item_code=res.item
			doc_it.brand=res.brand
			doc_it.price_list=doc.name
			doc_it.price_list_rate=res.list_priceunit
			doc_it.valid_from=self.start_date
			doc_it.valid_upto=self.end_date
			doc_it.save(ignore_permissions=True)
