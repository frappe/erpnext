# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, cint, format_time, format_datetime

date_format = "d/MM/Y"
time_format = "hh:mm a"
datetime_format = "{0}, {1}".format(date_format, time_format)


class AppointmentSheetReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		self.is_vehicle_service = cint('Vehicles' in frappe.get_active_domains())

	def run(self):
		self.get_data()
		self.process_data()
		columns = self.get_columns()
		return columns, self.data

	def get_data(self):
		conditions = self.get_conditions()

		extra_rows = ""
		if self.is_vehicle_service:
			extra_rows = ", a.vehicle_license_plate, a.vehicle_unregistered, a.vehicle_chassis_no, a.vehicle_engine_no"

		self.data = frappe.db.sql("""
			select a.name as appointment, a.appointment_type, a.voice_of_customer, a.remarks,
				a.scheduled_dt, a.scheduled_date, a.scheduled_time, a.appointment_duration, a.end_dt,
				a.appointment_for, a.party_name, a.customer_name,
				a.contact_display, a.contact_mobile, a.contact_phone, a.contact_email,
				a.applies_to_variant_of, a.applies_to_variant_of_name, a.applies_to_item, a.applies_to_item_name {0}
			from `tabAppointment` a
			where a.docstatus = 1 and a.status != 'Rescheduled' {1}
			order by a.scheduled_dt, a.creation
		""".format(extra_rows, conditions), self.filters, as_dict=1)

	def process_data(self):
		for d in self.data:
			d.contact_number = d.contact_mobile or d.contact_phone

			# Model Name if not a variant
			if not d.applies_to_variant_of_name:
				d.applies_to_variant_of_name = d.applies_to_item_name

			# Date/Time Formatting
			self.set_formatted_datetime(d)

	def set_formatted_datetime(self, d):
		d.scheduled_dt_fmt = format_datetime(d.scheduled_dt, datetime_format)
		d.scheduled_time_fmt = format_time(d.scheduled_time, time_format)

	def get_conditions(self):
		conditions = []

		if self.filters.get("company"):
			conditions.append("a.company = %(company)s")

		if self.filters.get("from_date"):
			conditions.append("a.scheduled_date >= %(from_date)s")

		if self.filters.get("to_date"):
			conditions.append("a.scheduled_date <= %(to_date)s")

		if self.filters.get("appointment_type"):
			conditions.append("a.appointment_type = %(appointment_type)s")

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		columns = [
			{'label': _("Appointment"), 'fieldname': 'appointment', 'fieldtype': 'Link', 'options': 'Appointment', 'width': 100},
			{'label': _("Date"), 'fieldname': 'scheduled_date', 'fieldtype': 'Date', 'width': 80},
			{'label': _("Time"), 'fieldname': 'scheduled_time_fmt', 'fieldtype': 'Data', 'width': 70},
			{'label': _("Party"), 'fieldname': 'party_name', 'fieldtype': 'Dynamic Link', 'options': 'appointment_for', 'width': 100},
			{'label': _("Customer Name"), 'fieldname': 'customer_name', 'fieldtype': 'Data', 'width': 150},
			{'label': _("Contact #"), 'fieldname': 'contact_number', 'fieldtype': 'Data', 'width': 100},
			{"label": _("Model") if self.is_vehicle_service else _("Item"),
				"fieldname": "applies_to_variant_of_name", "fieldtype": "Data", "width": 120},
			{"label": _("Variant Code") if self.is_vehicle_service else _("Item Code"),
				"fieldname": "applies_to_item", "fieldtype": "Link", "options": "Item", "width": 120},
		]

		if self.is_vehicle_service:
			columns += [
				{"label": _("Reg No"), "fieldname": "vehicle_license_plate", "fieldtype": "Data", "width": 80},
				{"label": _("Chassis No"), "fieldname": "vehicle_chassis_no", "fieldtype": "Data", "width": 150},
			]

		columns += [
			{"label": _("Voice of Customer"), "fieldname": "voice_of_customer", "fieldtype": "Data", "width": 200},
			{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 200, "editable": 1},
		]

		return columns


def execute(filters=None):
	return AppointmentSheetReport(filters).run()
