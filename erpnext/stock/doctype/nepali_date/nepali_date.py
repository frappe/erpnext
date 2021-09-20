# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import datetime
# from nepali_date import NepaliDate


class NepaliDate(Document):
	dt = datetime.date(2018, 11, 7)
	# nepali_datetime.date.from_datetime_date(dt)
	pass

	@frappe.whitelist()
	def check_date(self):
		dt = datetime.date(2018, 11, 7)
		# newdate = nepali_datetime.date.from_datetime_date(dt)
		# return newdate
