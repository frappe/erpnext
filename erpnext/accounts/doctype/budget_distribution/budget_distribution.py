# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from frappe.model.document import Document

class BudgetDistribution(Document):
	def get_months(self):
		month_list = ['January','February','March','April','May','June','July','August','September',
		'October','November','December']
		idx =1
		for m in month_list:
			mnth = self.append('budget_distribution_details')
			mnth.month = m
			mnth.idx = idx
			idx += 1

	def validate(self):
		total = sum([flt(d.percentage_allocation) for d in self.get("budget_distribution_details")])

		if total != 100.0:
			frappe.throw(_("Percentage Allocation should be equal to 100%"))
