# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document

class AppraisalTemplate(Document):
		
	def validate(self):
		self.total_points = 0
		for d in self.doclist.get({"doctype":"Appraisal Template Goal"}):
			self.total_points += int(d.per_weightage or 0)
		
		if int(self.total_points) != 100:
			frappe.msgprint(_("Total (sum of) points distribution for all goals should be 100.") \
				+ " " + _("Not") + " " + str(self.total_points),
				raise_exception=True)