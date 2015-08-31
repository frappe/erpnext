# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from erpnext.accounts.doctype.sales_taxes_and_charges_template.sales_taxes_and_charges_template \
	import valdiate_taxes_and_charges_template

class PurchaseTaxesandChargesTemplate(Document):
	def validate(self):
		valdiate_taxes_and_charges_template(self)
