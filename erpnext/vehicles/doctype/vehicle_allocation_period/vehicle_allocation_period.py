# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day, global_date_format, flt
from frappe.model.document import Document

class VehicleAllocationPeriod(Document):
	_cant_change_fields = ['from_date', 'to_date']

	def before_insert(self):
		self.set_values_based_on_periodicity()

	def validate(self):
		self.set_values_based_on_periodicity()
		self.validate_to_date()
		self.check_date_overlap()
		self.cant_change()

	def set_values_based_on_periodicity(self):
		periodicity = frappe.get_cached_value("Vehicles Settings", None, "vehicle_allocation_periodicity")
		if periodicity == "Monthly":
			self.from_date = get_first_day(self.from_date)
			self.to_date = get_last_day(self.from_date)

			self.period_name = global_date_format(self.from_date, "MMMM Y")

	def validate_to_date(self):
		if not self.to_date:
			frappe.throw(_("To Date is mandatory"))
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date cannot be before From Date"))

	def check_date_overlap(self):
		exclude_condition = ""
		if not self.is_new():
			exclude_condition = "and name != {0}".format(frappe.db.escape(self.name))

		period_list = frappe.db.sql_list("""
			select name
			from `tabVehicle Allocation Period`
			where %s <= ifnull(to_date, '3000-01-01') and %s >= ifnull(from_date, '2000-01-01') {0}
		""".format(exclude_condition), [self.from_date, self.to_date])

		if period_list:
			frappe.throw(_("Date range overlaps with Allocation Period {0}").format(", ".join(period_list)))

	def cant_change(self):
		if not self.get("__islocal") and self.has_transactions():
			before_save_values = frappe.db.get_value("Vehicle Allocation Period", self.name, self._cant_change_fields, as_dict=True)
			if before_save_values:
				for field in self._cant_change_fields:
					if self.get(field) != before_save_values.get(field):
						frappe.throw(_("As there are existing transactions against Vehicle Allocation Period {0}, you can not change the value of {1}")
							.format(self.name, frappe.bold(self.meta.get_label(field))))

	def has_transactions(self):
		if frappe.db.sql("select name from `tabVehicle Allocation` where docstatus = 1 and (allocation_period = %s or delivery_period = %s) limit 1", (self.name, self.name)):
			return True
		elif frappe.db.sql("select name from `tabVehicle Booking Order` where docstatus = 1 and (allocation_period = %s or delivery_period = %s) limit 1", (self.name, self.name)):
			return True
		else:
			return False
