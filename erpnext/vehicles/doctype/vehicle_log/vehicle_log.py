# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, formatdate
from frappe.model.document import Document
from erpnext.vehicles.doctype.vehicle.vehicle import get_vehicle_odometer, get_last_odometer_log

class VehicleLog(Document):
	def validate(self):
		self.validate_negative_odometer()
		self.validate_last_odometer()
		self.validate_future_date()

	def on_submit(self):
		self.update_vehicle_odometer()
		self.update_project_odometer()

	def on_cancel(self):
		self.update_vehicle_odometer()
		self.update_project_odometer()

	def validate_future_date(self):
		if getdate(self.date) > getdate():
			frappe.throw(_("Vehicle Log Date cannot be in the future"))

	def validate_negative_odometer(self):
		if cint(self.odometer) < 0:
			frappe.throw(_("Odometer Reading cannot be negative"))

	def validate_last_odometer(self):
		previous_odometer_log = get_last_odometer_log(self.vehicle, self.date)
		self.last_odometer = cint(previous_odometer_log.odometer) if previous_odometer_log else 0

		# if current odometer reading is less than previous odometer, allow if previous odometer is on same date
		if cint(self.odometer) < cint(self.last_odometer):
			if previous_odometer_log and previous_odometer_log.date == getdate(self.date):
				previous_odometer_log = get_last_odometer_log(self.vehicle, self.date, date_operator='<')
				self.last_odometer = cint(previous_odometer_log.odometer) if previous_odometer_log else 0

		if cint(self.odometer) < cint(self.last_odometer):
			frappe.throw(_("Current Odometer Reading {0} km on {1} cannot be less than Previous Odometer Reading {2} km{3}")
				.format(frappe.bold(self.get_formatted('odometer')),
				formatdate(self.date),
				frappe.bold(self.get_formatted('last_odometer')),
				" on {0}".format(formatdate(previous_odometer_log.date)) if previous_odometer_log else ""))

	def update_vehicle_odometer(self):
		odometer = get_vehicle_odometer(self.vehicle)
		frappe.db.set_value("Vehicle", self.vehicle, "last_odometer", odometer, notify=True)

	def update_project_odometer(self):
		from erpnext.vehicles.doctype.vehicle.vehicle import get_project_odometer

		if self.project and frappe.get_meta("Project").has_field("applies_to_vehicle") and 'Vehicles' in frappe.get_active_domains():
			vehicle = frappe.db.get_value("Project", self.project, "applies_to_vehicle")
			if vehicle:
				update_modified = not self.flags.from_project_update

				odo = get_project_odometer(self.project, vehicle)
				frappe.db.set_value("Project", self.project, {
					"vehicle_first_odometer": odo.vehicle_first_odometer,
					"vehicle_last_odometer": odo.vehicle_last_odometer
				}, None, update_modified=update_modified, notify=update_modified)

@frappe.whitelist()
def make_expense_claim(docname):
	expense_claim = frappe.db.exists("Expense Claim", {"vehicle_log": docname})
	if expense_claim:
		frappe.throw(_("Expense Claim {0} already exists for the Vehicle Log").format(expense_claim))

	vehicle_log = frappe.get_doc("Vehicle Log", docname)
	service_expense = sum([flt(d.expense_amount) for d in vehicle_log.service_detail])

	claim_amount = service_expense + flt(vehicle_log.price)
	if not claim_amount:
		frappe.throw(_("No additional expenses has been added"))

	exp_claim = frappe.new_doc("Expense Claim")
	exp_claim.employee = vehicle_log.employee
	exp_claim.vehicle_log = vehicle_log.name
	exp_claim.remark = _("Expense Claim for Vehicle Log {0}").format(vehicle_log.name)
	exp_claim.append("expenses", {
		"expense_date": vehicle_log.date,
		"description": _("Vehicle Expenses"),
		"amount": claim_amount
	})
	return exp_claim.as_dict()


@frappe.whitelist()
def make_odometer_log_api(vehicle, odometer, date=None, project=None):
	make_odometer_log(vehicle, odometer, date, project, ignore_permissions=False)


def make_odometer_log(vehicle, odometer, date=None, project=None, ignore_permissions=True, from_project_update=False):
	if not vehicle:
		frappe.throw(_("Vehicle is not provided to make Vehicle Odometer Log"))

	date = getdate(date)

	doc = frappe.new_doc("Vehicle Log")
	doc.vehicle = vehicle
	doc.date = date
	doc.odometer = cint(odometer)
	doc.project = project

	doc.flags.ignore_permissions = ignore_permissions
	doc.flags.from_project_update = from_project_update
	doc.save()
	doc.submit()

	return doc.name


def odometer_log_exists(vehicle, odometer):
	if not vehicle:
		frappe.throw(_("No Vehicle Provided"))

	return frappe.db.exists("Vehicle Log", {
		"vehicle": vehicle,
		"odometer": cint(odometer),
		"docstatus": 1
	})
