# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import throw, _
from frappe.utils import cstr

from frappe.model.document import Document
from jinja2 import TemplateSyntaxError
from frappe.utils.user import is_website_user
from frappe.model.naming import make_autoname

class Address(Document):
	def __setup__(self):
		self.flags.linked = False

	def autoname(self):
		if not self.address_title:
			self.address_title = self.customer \
				or self.supplier or self.sales_partner or self.lead

		if self.address_title:
			self.name = (cstr(self.address_title).strip() + "-" + cstr(self.address_type).strip())
			if frappe.db.exists("Address", self.name):
				self.name = make_autoname(cstr(self.address_title).strip() + "-" + 
					cstr(self.address_type).strip() + "-.#")
		else:
			throw(_("Address Title is mandatory."))

	def validate(self):
		self.link_fields = ("customer", "supplier", "sales_partner", "lead")
		self.link_address()
		self.validate_primary_address()
		self.validate_shipping_address()
		self.validate_reference()

	def validate_primary_address(self):
		"""Validate that there can only be one primary address for particular customer, supplier"""
		if self.is_primary_address == 1:
			self._unset_other("is_primary_address")

		elif self.is_shipping_address != 1:
			for fieldname in self.link_fields:
				if self.get(fieldname):
					if not frappe.db.sql("""select name from `tabAddress` where is_primary_address=1
						and `%s`=%s and name!=%s""" % (frappe.db.escape(fieldname), "%s", "%s"),
						(self.get(fieldname), self.name)):
							self.is_primary_address = 1
					break

	def link_address(self):
		"""Link address based on owner"""
		if not self.flags.linked:
			self.check_if_linked()

		if not self.flags.linked and not self.is_your_company_address:
			contact = frappe.db.get_value("Contact", {"email_id": self.owner},
				("name", "customer", "supplier"), as_dict = True)
			if contact:
				self.customer = contact.customer
				self.supplier = contact.supplier

			self.lead = frappe.db.get_value("Lead", {"email_id": self.owner})

	def check_if_linked(self):
		for fieldname in self.link_fields:
			if self.get(fieldname):
				self.flags.linked = True
				break

	def validate_shipping_address(self):
		"""Validate that there can only be one shipping address for particular customer, supplier"""
		if self.is_shipping_address == 1:
			self._unset_other("is_shipping_address")
			
	def validate_reference(self):
		if self.is_your_company_address:
			if not self.company:
				frappe.throw(_("Company is mandatory, as it is your company address"))
			if self.customer or self.supplier or self.sales_partner or self.lead:
				frappe.throw(_("Remove reference of customer, supplier, sales partner and lead, as it is your company address"))

	def _unset_other(self, is_address_type):
		for fieldname in ["customer", "supplier", "sales_partner", "lead"]:
			if self.get(fieldname):
				frappe.db.sql("""update `tabAddress` set `%s`=0 where `%s`=%s and name!=%s""" %
					(is_address_type, fieldname, "%s", "%s"), (self.get(fieldname), self.name))
				break

	def get_display(self):
		return get_address_display(self.as_dict())

@frappe.whitelist()
def get_address_display(address_dict):
	if not address_dict:
		return
		
	if not isinstance(address_dict, dict):
		address_dict = frappe.db.get_value("Address", address_dict, "*", as_dict=True) or {}

	name, template = get_address_templates(address_dict)
	
	try:
		return frappe.render_template(template, address_dict)
	except TemplateSyntaxError:
		frappe.throw(_("There is an error in your Address Template {0}").format(name))


def get_territory_from_address(address):
	"""Tries to match city, state and country of address to existing territory"""
	if not address:
		return

	if isinstance(address, basestring):
		address = frappe.get_doc("Address", address)

	territory = None
	for fieldname in ("city", "state", "country"):
		territory = frappe.db.get_value("Territory", address.get(fieldname))
		if territory:
			break

	return territory

def get_list_context(context=None):
	from erpnext.shopping_cart.cart import get_address_docs
	return {
		"title": _("Addresses"),
		"get_list": get_address_list,
		"row_template": "templates/includes/address_row.html",
		'no_breadcrumbs': True,
	}
	
def get_address_list(doctype, txt, filters, limit_start, limit_page_length=20):
	from frappe.www.list import get_list
	user = frappe.session.user
	ignore_permissions = False
	if is_website_user():
		if not filters: filters = []
		filters.append(("Address", "owner", "=", user))
		ignore_permissions = True

	return get_list(doctype, txt, filters, limit_start, limit_page_length, ignore_permissions=ignore_permissions)
	
def has_website_permission(doc, ptype, user, verbose=False):
	"""Returns true if customer or lead matches with user"""
	customer = frappe.db.get_value("Contact", {"email_id": frappe.session.user}, "customer")
	if customer:
		return doc.customer == customer
	else:
		lead = frappe.db.get_value("Lead", {"email_id": frappe.session.user})
		if lead:
			return doc.lead == lead

	return False

def get_address_templates(address):
	result = frappe.db.get_value("Address Template", \
		{"country": address.get("country")}, ["name", "template"])
		
	if not result:
		result = frappe.db.get_value("Address Template", \
			{"is_default": 1}, ["name", "template"])

	if not result:
		frappe.throw(_("No default Address Template found. Please create a new one from Setup > Printing and Branding > Address Template."))
	else:
		return result

@frappe.whitelist()
def get_shipping_address(company):
	filters = {"company": company, "is_your_company_address":1}
	fieldname = ["name", "address_line1", "address_line2", "city", "state", "country"]

	address_as_dict = frappe.db.get_value("Address", filters=filters, fieldname=fieldname, as_dict=True)

	if address_as_dict:
		name, address_template = get_address_templates(address_as_dict)
		return address_as_dict.get("name"), frappe.render_template(address_template, address_as_dict)
