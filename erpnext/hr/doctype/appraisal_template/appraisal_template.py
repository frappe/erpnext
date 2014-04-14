# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document

class AppraisalTemplate(Document):
	def validate(self):
		self.total_points = 0
		for d in self.get("kra_sheet"):
			self.total_points += int(d.per_weightage or 0)

		if int(self.total_points) != 100:
			frappe.throw(_("Total points for all goals should be 100. It is {0}").format(self.total_points))
