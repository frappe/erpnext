# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

from frappe.model.document import Document

class Workstation(Document):
	def update_bom_operation(self):
		bom_list = frappe.db.sql("""select DISTINCT parent from `tabBOM Operation` 
			where workstation = %s""", self.name)
		for bom_no in bom_list:
			frappe.db.sql("""update `tabBOM Operation` set hour_rate = %s 
				where parent = %s and workstation = %s""", 
				(self.hour_rate, bom_no[0], self.name))
	
	def on_update(self):
		frappe.db.set(self, 'overhead', flt(self.hour_rate_electricity) + 
		flt(self.hour_rate_consumable) + flt(self.hour_rate_rent))
		frappe.db.set(self, 'hour_rate', flt(self.hour_rate_labour) + flt(self.overhead))
		self.update_bom_operation()