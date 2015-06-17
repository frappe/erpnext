# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import validate_taxes_and_charges, validate_inclusive_tax
from erpnext.utilities.match_address import validate_address_params
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import onload_for_shopping_cart_settings

class SalesTaxesandChargesTemplate(Document):
	def onload(self):
		onload_for_shopping_cart_settings(self)

	def validate(self):
		if self.is_default == 1:
			frappe.db.sql("""update `tabSales Taxes and Charges Template`
				set is_default = 0
				where ifnull(is_default,0) = 1
				and name != %s and company = %s""",
				(self.name, self.company))

		for tax in self.get("taxes"):
			validate_taxes_and_charges(tax)
			validate_inclusive_tax(tax, self)

		validate_address_params(self)

