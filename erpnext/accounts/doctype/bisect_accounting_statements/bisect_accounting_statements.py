# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from math import ceil, floor

import frappe
from dateutil.relativedelta import relativedelta
from frappe.model.document import Document
from frappe.utils import getdate


class BisectAccountingStatements(Document):
	@frappe.whitelist()
	def bisect(self):
		cur_frm_date, cur_to_date = getdate(self.from_date), getdate(self.to_date)
		while True:
			delta = cur_to_date - cur_frm_date
			if delta.days == 0:
				return
			cur_floor = floor(delta.days / 2)
			cur_to_date = cur_frm_date + relativedelta(days=+cur_floor)
			print((cur_frm_date, cur_to_date), delta, cur_floor)
