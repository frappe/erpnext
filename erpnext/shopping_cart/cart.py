# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.selling.doctype.quotation.quotation import Quotation
from erpnext.utilities.doctype.contact.contact import get_contact_details
from erpnext.utilities.doctype.address.address import get_address_display
from erpnext.crm.doctype.lead.lead import _make_customer
from erpnext.selling.doctype.quotation.quotation import _make_sales_order

@frappe.whitelist()
def get_cart(quotation=None):
	return ShoppingCart(quotation).render()

@frappe.whitelist()
def set_qty(quotation, item_code, qty):
	cart = ShoppingCart(quotation)
	cart.set_qty(item_code, qty)
	return cart.render()

@frappe.whitelist()
def set_address(quotation, address_fieldname, address_name):
	cart = ShoppingCart(quotation)
	cart.set_address(address_fieldname, address_name)
	return cart.render()

@frappe.whitelist()
def select_shipping_rule(quotation, shipping_rule):
	cart = ShoppingCart(quotation)
	cart.select_shipping_rule(shipping_rule)
	return cart.render()

@frappe.whitelist()
def place_order(quotation):
	return ShoppingCart(quotation).place_order()

class ShoppingCart:
	"""Wrapper around Quotation for Shopping Cart feature"""
	def __init__(self, quotation=None):
		self.email_id = frappe.session.user
		self.doc = self.get_quotation(quotation)
		if quotation:
			self.check_permission()

	def save(self):
		self.apply_cart_settings()
		self.doc.save(ignore_permissions=True)

	def get_quotation(self, quotation=None):
		if quotation:
			doc = frappe.get_doc("Quotation", quotation)
			if (doc.docstatus == 0 and doc.status in ("Draft", "Open")):
				# additional validation to make sure this is a valid quotation
				return doc

		return self.get_open_cart_quotation() or self.create_new_cart_quotation()

	def check_permission(self):
		if not ((self.doc.contact_email == self.email_id)
			and (self.doc.customer == self.get_customer_and_contact()["customer"])):
			frappe.throw(_("You are not permitted to access this shopping cart"),
				frappe.PermissionError)

	def render(self):
		pass

	def set_qty(self, item_code, qty):
		qty = flt(qty)
		item = self.doc.get("items", {"item_code": item_code})

		if qty:
			if item:
				item[0].qty = qty
			else:
				self.doc.append("items", {
					"doctype": "Quotation Item",
					"item_code": item_code,
					"qty": qty
				})

		elif item:
			self.doc.items.remove(item[0])

		self.save()

	def set_address(self, address_fieldname, address_name):
		address_display = get_address_display(frappe.get_doc("Address", address_name).as_dict())
		if address_fieldname == "shipping_address_name":
			self.doc.shipping_address_name = address_name
			self.doc.shipping_address = address_display

			if not self.doc.customer_address:
				address_fieldname = "customer_address"

		if address_fieldname == "customer_address":
			self.doc.customer_address = address_name
			self.doc.address_display = address_display

		self.save()

	def select_shipping_rule(self, shipping_rule):
		self.doc.shipping_rule = shipping_rule
		self.save()

	def place_order(self):
		for fieldname in ("customer_address", "shipping_address_name"):
			if not self.doc.get(fieldname):
				frappe.throw(_("{0} is required to place order").format(self.doc.meta.get_label(fieldname)))

		self.doc.flags.ignore_permissions = True
		self.save()
		self.doc.submit()

		sales_order = frappe.get_doc(_make_sales_order(self.doc.name, ignore_permissions=True))
		for item in sales_order.get("items"):
			# TODO should be a better place to set this
			# possible solution: normalize Item table into Website Item
			item.reserved_warehouse = frappe.db.get_value("Item", item.item_code, "website_warehouse") or None

		sales_order.flags.ignore_permissions = True
		sales_order.insert()
		sales_order.submit()

		return sales_order.name

	def apply_cart_settings(self):
		# TODO
		# apply shipping rule and set shipping charge
		# was part of apply cart settings
		shopping_cart_settings = frappe.get_doc("Shopping Cart Settings")

		# reset values and price list
		price_lists = [d.price_list for d in shopping_cart_settings.get("price_lists")]
		self.doc._subset_of_price_lists = price_lists

		# taxes
		cart_tax_templates = [d.sales_taxes_and_charges_master for d in
			shopping_cart_settings.get("sales_taxes_and_charges_masters")]
		self.doc._subset_of_tax_templates = cart_tax_templates

		# shipping rule
		cart_shipping_rules = [d.shipping_rule for d in shopping_cart_settings.get("shipping_rules")]
		self.doc._subset_of_shipping_rules = cart_shipping_rules

		self.doc.auto_price_list = True
		self.doc.auto_tax_and_shipping_rule = True

	def get_open_cart_quotation(self):
		try:
			return frappe.get_doc("Quotation", {"contact_email": self.email_id,
				"status": ("in", ("Open", "Draft")), "docstatus": 0})

		except frappe.DoesNotExistError:
			pass

	def create_new_cart_quotation(self):
		doc = frappe.new_doc("Quotation")
		doc.update(self.get_customer_and_contact())
		doc.run_method("validate")
		return doc

	def get_customer_and_contact(self):
		contact = self.get_contact()
		out = get_contact_details(contact)
		out["customer"] = frappe.db.get_value("Contact", contact, "customer")
		return out

	def get_contact(self):
		contact = frappe.db.get_value("Contact", {"email_id": self.email_id}, "name")
		if not contact:
			contact = self.make_contact_from_lead()

		return contact

	def make_contact_from_lead(self):
		lead = frappe.db.get_value("Lead", {"email_id": self.email_id}, "name")
		if not lead:
			# create new lead
			lead_doc = frappe.new_doc("Lead")
			lead_doc.email_id = self.email_id
			lead_doc.lead_name = self.email_id.split("@")[0].title()
			lead_doc.territory = self.guess_territory()
			lead_doc.insert(ignore_permissions=True)
			lead = lead_doc.name

		# convert lead to customer and contact
		customer = _make_customer(lead, ignore_permissions=True)
		customer.insert(ignore_permissions=True)

		return frappe.db.get_value("Contact", {"email_id": self.email_id}, "name")

	def guess_territory(self):
		territory = None
		geoip_country = frappe.session.get("session_country")
		if geoip_country:
			territory = frappe.db.get_value("Territory", geoip_country)

		return territory or frappe.db.get_single_value("Shopping Cart Settings", "default_territory")

