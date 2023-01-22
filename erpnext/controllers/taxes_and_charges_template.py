# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class TaxesandChargesTemplate(Document):
	def validate(self):
		if self.is_default and self.disabled:
			frappe.throw(_("Disabled template must not be default template"))

		self.validate_unique_tax_category()

		all_taxes = self.get("taxes")
		for tax in all_taxes:
			tax.validate_taxes_and_charges()
			tax.validate_account_head(self.company)
			tax.validate_cost_center(self.company)
			tax.validate_inclusive_tax(all_taxes)

	def autoname(self):
		if self.company and self.title:
			abbr = frappe.get_cached_value("Company", self.company, "abbr")
			self.name = "{0} - {1}".format(self.title, abbr)

	def on_update(self):
		if self.is_default:
			self.disable_old_default()

	def disable_old_default(self):
		if old_default := frappe.db.get_value(
			self.doctype,
			{"company": self.company, "is_default": 1, "name": ("!=", self.name)},
		):
			frappe.db.set_value(self.doctype, old_default, "is_default", 0)

	def set_missing_values(self):
		for data in self.taxes:
			if data.charge_type == "On Net Total" and flt(data.rate) == 0.0:
				data.rate = frappe.get_cached_value("Account", data.account_head, "tax_rate")

	def validate_unique_tax_category(self):
		if not self.tax_category:
			return

		if frappe.db.exists(
			self.doctype,
			{
				"company": self.company,
				"tax_category": self.tax_category,
				"disabled": 0,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_(
					"A template with tax category {0} already exists. Only one template is allowed with each tax category"
				).format(frappe.bold(self.tax_category))
			)
