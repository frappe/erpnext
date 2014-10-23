# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import throw, _
from frappe.utils import cstr

from frappe.model.document import Document

class Address(Document):
	def autoname(self):
		if not self.address_title:
			self.address_title = self.customer \
				or self.supplier or self.sales_partner or self.lead

		if self.address_title:
			self.name = cstr(self.address_title).strip() + "-" + cstr(self.address_type).strip()
		else:
			throw(_("Address Title is mandatory."))

	def validate(self):
		self.validate_primary_address()
		self.validate_shipping_address()

	def validate_primary_address(self):
		"""Validate that there can only be one primary address for particular customer, supplier"""
		if self.is_primary_address == 1:
			self._unset_other("is_primary_address")

		elif self.is_shipping_address != 1:
			for fieldname in ["customer", "supplier", "sales_partner", "lead"]:
				if self.get(fieldname):
					if not frappe.db.sql("""select name from `tabAddress` where is_primary_address=1
						and `%s`=%s and name!=%s""" % (fieldname, "%s", "%s"),
						(self.get(fieldname), self.name)):
							self.is_primary_address = 1
					break

	def validate_shipping_address(self):
		"""Validate that there can only be one shipping address for particular customer, supplier"""
		if self.is_shipping_address == 1:
			self._unset_other("is_shipping_address")

	def _unset_other(self, is_address_type):
		for fieldname in ["customer", "supplier", "sales_partner", "lead"]:
			if self.get(fieldname):
				frappe.db.sql("""update `tabAddress` set `%s`=0 where `%s`=%s and name!=%s""" %
					(is_address_type, fieldname, "%s", "%s"), (self.get(fieldname), self.name))
				break

@frappe.whitelist()
def get_address_display(address_dict):
	if not address_dict:
		return
	if not isinstance(address_dict, dict):
		address_dict = frappe.db.get_value("Address", address_dict, "*", as_dict=True) or {}

	template = frappe.db.get_value("Address Template", \
		{"country": address_dict.get("country")}, "template")
	if not template:
		template = frappe.db.get_value("Address Template", \
			{"is_default": 1}, "template")

	if not template:
		frappe.throw(_("No default Address Template found. Please create a new one from Setup > Printing and Branding > Address Template."))

	return frappe.render_template(template, address_dict)

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



