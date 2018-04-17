# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate
from frappe.model.document import Document

class LeavePeriod(Document):
	def validate(self):
		self.validate_dates()
		self.validate_overlap()

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To date can not be equal or less than from date"))

	def validate_overlap(self):
		if not self.name:
			# hack! if name is null, it could cause problems with !=
			self.name = "New Leave Period"

		leave_period = frappe.db.sql("""
			select name
			from `tabLeave Period`
			where company = %(company)s
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
			and name != %(name)s""", {
				"company": self.company,
				"from_date": self.from_date,
				"to_date": self.to_date,
				"name": self.name
			}, as_dict = 1)

		if leave_period:
			self.throw_overlap_error(leave_period[0].name)

	def throw_overlap_error(self, leave_period):
		msg = _("Company {0} already have Leave Period between {1} and {2} : ").format(self.company,
			formatdate(self.from_date), formatdate(self.to_date)) \
			+ """ <b><a href="#Form/Compensatory Leave Request/{0}">{0}</a></b>""".format(leave_period)
		frappe.throw(msg)
