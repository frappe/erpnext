# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document

class SalesTaxesandChargesMaster(Document):
	def validate(self):
		if self.is_default == 1:
			frappe.db.sql("""update `tabSales Taxes and Charges Master` set is_default = 0
				where ifnull(is_default,0) = 1 and name != %s and company = %s""",
				(self.name, self.company))

		# at least one territory
		self.validate_table_has_rows("valid_for_territories")
