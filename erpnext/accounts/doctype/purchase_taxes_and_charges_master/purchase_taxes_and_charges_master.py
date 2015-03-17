# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import validate_taxes_and_charges, validate_inclusive_tax

class PurchaseTaxesandChargesMaster(Document):
	def validate(self):
		for tax in self.get("taxes"):
			validate_taxes_and_charges(tax)
			validate_inclusive_tax(tax, self)
