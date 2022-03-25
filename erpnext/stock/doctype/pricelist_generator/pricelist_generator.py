# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import flt


class PriceListGenerator(Document):


	def validate(self):
		for res in self.price_details:
			if res.brand:
				lst=frappe.get_doc("Brand",res.brand)
				for i in lst.brand_defaults:
					if i.selling_cost_center:
						if self.company==i.company and self.operating_unit==i.selling_cost_center:
							res.brand_list_price=i.item_price
						if not i.item_price:
							frappe.throw("Please set Item Price in brand")
			doc=frappe.get_doc("Item",res.product)
			if not doc.specific_gravity:
				frappe.throw("Please set Specific Gravity On Item")
			if doc.specific_gravity:
				res.volume=flt(res.weight)/flt(doc.specific_gravity)
    


	def before_save(self):
		self.get_cost_weight()
		self.get_cost_volume()

	def get_cost_weight(self):
		for res in self.price_details:
			if res.product:
				res.list_priceweight = (flt(res.brand_list_price) + flt(res.addpkg_cost)) * flt(res.weight)


	def get_cost_volume(self):
		for res in self.price_details:
			if res.product:
				res.list_priceunit = (flt(res.brand_list_price) + flt(res.addpkg_cost)) * flt(res.weight)
				res.list_pricevolume = (flt(res.brand_list_price) + flt(res.addpkg_cost))*flt(res.volume)

	@frappe.whitelist()
	def get_items_brand(self):
		doc=frappe.db.sql("""select b.name from `tabBrand` b join `tabItem Default` bd on b.name=bd.parent where bd.selling_cost_center='{0}'""".format(self.operating_unit),as_dict=1)
		for i in doc:
			lst=frappe.db.get_all("Item",{"brand":i.name},["name"])
			for j in lst:
				doc=frappe.get_doc("Item",j.name)
				if doc.item_group==self.item_group:
					pack_g=frappe.db.value("Product Pack",{"item":doc.name},["name"])
					if pack_g:
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

