# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.jinja import validate_template
from frappe import _

class AddressTemplate(Document):
	def validate(self):
		if not self.template:
			self.template = get_default_address_template()

		self.defaults = frappe.db.get_values("Address Template", {"is_default":1, "name":("!=", self.name)})
		if not self.is_default:
			if not self.defaults:
				self.is_default = 1
				frappe.msgprint(_("Setting this Address Template as default as there is no other default"))

		validate_template(self.template)

	def on_update(self):
		if self.is_default and self.defaults:
			for d in self.defaults:
				frappe.db.set_value("Address Template", d[0], "is_default", 0)

	def on_trash(self):
		if self.is_default:
			frappe.throw(_("Default Address Template cannot be deleted"))

@frappe.whitelist()
def get_default_address_template():
	'''Get default address template (translated)'''
	return '''{{ address_line1 }}<br>{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}\
{{ city }}<br>
{% if state %}{{ state }}<br>{% endif -%}
{% if pincode %}{{ pincode }}<br>{% endif -%}
{{ country }}<br>
{% if phone %}'''+_('Phone')+''': {{ phone }}<br>{% endif -%}
{% if fax %}'''+_('Fax')+''': {{ fax }}<br>{% endif -%}
{% if email_id %}'''+_('Email')+''': {{ email_id }}<br>{% endif -%}'''
