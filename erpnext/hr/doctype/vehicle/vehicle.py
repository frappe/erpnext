# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class Vehicle(Document):
	def validate(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Insurance Start date should be less than Insurance End date"))
		if getdate(self.carbon_check_date) > getdate():
			frappe.throw(_("Last carbon check date cannot be a future date"))

def get_timeline_data(doctype, name):
	'''Return timeline for vehicle log'''
	return dict(frappe.db.sql('''select unix_timestamp(date), count(*)
	from `tabVehicle Log` where license_plate=%s
	and date > date_sub(curdate(), interval 1 year)
	group by date''', name))
