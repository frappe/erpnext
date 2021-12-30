# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ItemPriceDuplicateItem(frappe.ValidationError):
	pass


class ItemPrice(Document):

	def validate(self):
		self.validate_item()
		self.validate_dates()
		self.update_price_list_details()
		self.update_item_details()
		self.check_duplicates()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item_code):
			frappe.throw(_("Item {0} not found.").format(self.item_code))

	def validate_dates(self):
		if self.valid_from and self.valid_upto:
			if getdate(self.valid_from) > getdate(self.valid_upto):
				frappe.throw(_("Valid From Date must be lesser than Valid Upto Date."))

	def update_price_list_details(self):
		if self.price_list:
			price_list_details = frappe.db.get_value("Price List",
				{"name": self.price_list, "enabled": 1},
				["buying", "selling", "currency"])

			if not price_list_details:
				link = frappe.utils.get_link_to_form('Price List', self.price_list)
				frappe.throw("The price list {0} does not exist or is disabled".format(link))

			self.buying, self.selling, self.currency = price_list_details

	def update_item_details(self):
		if self.item_code:
			self.item_name, self.item_description = frappe.db.get_value("Item", self.item_code,["item_name", "description"])

	def check_duplicates(self):
		conditions = """where item_code = %(item_code)s and price_list = %(price_list)s and name != %(name)s"""

		for field in [
			"uom",
			"valid_from",
			"valid_upto",
			"packing_unit",
			"customer",
			"supplier",
			"batch_no"]:
			if self.get(field):
				conditions += " and {0} = %({0})s ".format(field)
			else:
				conditions += "and (isnull({0}) or {0} = '')".format(field)

		price_list_rate = frappe.db.sql("""
				select price_list_rate
				from `tabItem Price`
				{conditions}
			""".format(conditions=conditions),
			self.as_dict(),)

		if price_list_rate:
			frappe.throw(_("Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, Batch, UOM, Qty, and Dates."), ItemPriceDuplicateItem,)

	def before_save(self):
		if self.selling:
			self.reference = self.customer
		if self.buying:
			self.reference = self.supplier

		if self.selling and not self.buying:
			# if only selling then remove supplier
			self.supplier = None
		if self.buying and not self.selling:
			# if only buying then remove customer
			self.customer = None
		
	@frappe.whitelist()
	def update_customer_pricing_rule_item(self):
		old_rate = frappe.get_value('Item Price',{'name':self.name},'price_list_rate')
		if(self.price_list_rate != old_rate):
			all_items = frappe.db.get_all("Customer Pricing Rule Item",{'Item':self.item_code},['name','additional_price','parent'])

			for item in all_items:
				doc = frappe.get_doc('Customer Pricing Rule', item.get('parent'))
				if doc.get('for_price_list' == self.price_list):
					list_price = self.price_list_rate + item.get('additional_price') 
					q = """
						UPDATE `tabCustomer Pricing Rule Item`
						SET base_price = '{0}', list_price = '{1}'
						WHERE name = '{2}';
						""".format(self.price_list_rate,list_price,item.get('name'))
					frappe.db.sql(q)
					frappe.db.commit()
