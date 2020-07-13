# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class Vehicle(Document):
	def validate(self):
		if self.get("__islocal"):
			self.last_odometer_value = self.initial_odometer_value
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Insurance Start date should be less than Insurance End date"))
		if getdate(self.carbon_check_date) > getdate():
			frappe.throw(_("Last carbon check date cannot be a future date"))

	def on_submit(self):
		#Create Initial vehicle Record
		vehicle_log = frappe.new_doc("Vehicle Log")
		vehicle_log.license_plate = self.name
		vehicle_log.is_opening = 1
		vehicle_log.model = self.model
		vehicle_log.make = self.make
		vehicle_log.date = getdate()
		vehicle_log.odometer = self.initial_odometer_value

		vehicle_log.save()
		vehicle_log.submit()

def get_timeline_data(doctype, name):
	'''Return timeline for vehicle log'''
	return dict(frappe.db.sql('''select unix_timestamp(date), count(*)
	from `tabVehicle Log` where license_plate=%s
	and date > date_sub(curdate(), interval 1 year)
	group by date''', name))
