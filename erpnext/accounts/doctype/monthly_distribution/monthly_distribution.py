# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from frappe.model.document import Document

class MonthlyDistribution(Document):
	def get_months(self):
		month_list = ['January','February','March','April','May','June','July','August','September',
		'October','November','December']
		idx =1
		for m in month_list:
			mnth = self.append('percentages')
			mnth.month = m
			mnth.percentage_allocation = 100.0/12
			mnth.idx = idx
			idx += 1

	def validate(self):
		total = sum([flt(d.percentage_allocation) for d in self.get("percentages")])

		if flt(total, 2) != 100.0:
			frappe.throw(_("Percentage Allocation should be equal to 100%") + \
				" ({0}%)".format(str(flt(total, 2))))
