# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import validate_taxes_and_charges, validate_inclusive_tax
from frappe.utils.nestedset import get_root_of

class SalesTaxesandChargesTemplate(Document):
	def validate(self):
		valdiate_taxes_and_charges_template(self)

def valdiate_taxes_and_charges_template(doc):
	if not doc.is_default and not frappe.get_all(doc.doctype, filters={"is_default": 1}):
		doc.is_default = 1

	if doc.is_default == 1:
		frappe.db.sql("""update `tab{0}` set is_default = 0
			where ifnull(is_default,0) = 1 and name != %s and company = %s""".format(doc.doctype),
			(doc.name, doc.company))

	if doc.meta.get_field("territories"):
		if not doc.territories:
			doc.append("territories", {"territory": get_root_of("Territory") })

	for tax in doc.get("taxes"):
		validate_taxes_and_charges(tax)
		validate_inclusive_tax(tax, doc)
