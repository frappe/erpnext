# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from math import floor

import frappe
from dateutil.relativedelta import relativedelta
from frappe.model.document import Document
from frappe.utils import getdate


class BisectAccountingStatements(Document):
	@frappe.whitelist()
	def bisect(self):
		period_list = [(getdate(self.from_date), getdate(self.to_date))]
		dates = []
		while period_list:
			cur_frm_date, cur_to_date = period_list.pop()
			delta = cur_to_date - cur_frm_date
			if not delta.days > 0:
				continue

			cur_floor = floor(delta.days / 2)
			left = (cur_frm_date, (cur_frm_date + relativedelta(days=+cur_floor)))
			right = ((cur_frm_date + relativedelta(days=+(cur_floor + 1))), cur_to_date)
			period_list.append(left)
			period_list.append(right)
