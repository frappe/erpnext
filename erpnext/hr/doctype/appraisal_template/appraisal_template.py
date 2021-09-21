# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class AppraisalTemplate(Document):
	def validate(self):
		self.check_total_weightage()

	def check_total_weightage(self):
		total_weightage = 0
		for d in self.get('kra_assessment'):
			total_weightage += flt(d.per_weightage)

		if cint(total_weightage) != 100:
			frappe.throw(_('Sum of all percentage should be 100. It is {0}').format(int(total_weightage)))
