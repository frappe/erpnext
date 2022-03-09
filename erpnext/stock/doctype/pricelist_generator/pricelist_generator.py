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
					if self.company==i.company and self.operating_unit==i.selling_cost_center:
						res.brand_list_price=i.item_price
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
				res.list_priceunit = (res.brand_list_price + res.addpkg_cost) * res.weight
				res.list_pricevolume = (res.brand_list_price + res.addpkg_cost)*res.volume

	@frappe.whitelist()
	def get_items_brand(self):
		doc=frappe.db.sql("""select b.name from `tabBrand` b join `tabItem Default` bd on b.name=bd.parent where bd.selling_cost_center='{0}'""".format(self.operating_unit),as_dict=1)
		for i in doc:
			lst=frappe.db.get_all("Item",{"brand":i.name},["name"])
			for j in lst:
				doc=frappe.get_doc("Item",j.name)
				if doc.item_group==self.item_group:
					pack=frappe.get_doc("Product Pack",{"item":doc.name})
					self.append("price_details",{
						"product":doc.name,
						"classifications":doc.description,
						"costunit":doc.valuation_rate,
						"weight":doc.weight_per_unit,
						"addpkg_cost":pack.diff_price

					})
		return True


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
			doc_it.price_list_rate=res.list_priceunit
			doc_it.save()

