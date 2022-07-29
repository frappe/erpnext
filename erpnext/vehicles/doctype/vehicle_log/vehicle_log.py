# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, formatdate
from frappe.model.document import Document


class VehicleLog(Document):
	def validate(self):
		self.validate_negative_odometer()
		self.validate_last_odometer()
		self.validate_future_date()
		self.validate_reference()

	def on_submit(self):
		if not self.flags.do_not_update_customer:
			self.update_vehicle_odometer()
			self.update_vehicle_party_details()

		self.update_project_odometer()

	def on_cancel(self):
		if not self.flags.do_not_update_customer:
			self.update_vehicle_odometer()
			self.update_vehicle_party_details()

		self.update_project_odometer()

	def validate_future_date(self):
		if getdate(self.date) > getdate():
			frappe.throw(_("Vehicle Log Date cannot be in the future"))

	def validate_negative_odometer(self):
		if cint(self.odometer) < 0:
			frappe.throw(_("Odometer Reading cannot be negative"))

	def validate_last_odometer(self):
		if not cint(self.odometer):
			return

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

	def validate_reference(self):
		if not self.reference_type or not self.reference_name:
			self.reference_type = None
			self.reference_name = None

		if not self.reference_name and self.project:
			self.reference_type = 'Project'
			self.reference_name = self.project

		if not self.customer:
			self.customer_name = None
		if not self.vehicle_owner:
			self.vehicle_owner = None

	def update_vehicle_odometer(self):
		if not cint(self.odometer):
			return

		odometer = get_vehicle_odometer(self.vehicle)
		frappe.db.set_value("Vehicle", self.vehicle, "last_odometer", odometer, notify=True)

	def update_project_odometer(self):
		if not cint(self.odometer):
			return
		if not self.project:
			return
		if not frappe.get_meta("Project").has_field("applies_to_vehicle"):
			return
		if 'Vehicles' not in frappe.get_active_domains():
			return

		vehicle = frappe.db.get_value("Project", self.project, "applies_to_vehicle")
		if vehicle:
			update_modified = not self.flags.from_project_update

			odo = get_project_odometer(self.project, vehicle)
			frappe.db.set_value("Project", self.project, {
				"vehicle_first_odometer": odo.vehicle_first_odometer,
				"vehicle_last_odometer": odo.vehicle_last_odometer
			}, None, update_modified=update_modified, notify=update_modified)

	def update_vehicle_party_details(self):
		if self.customer:
			sr_no = frappe.get_doc("Serial No", self.vehicle)
			last_sle = sr_no.get_last_sle()
			sr_no.set_party_details(last_sle.get("purchase_sle"), last_sle.get("delivery_sle"))
			sr_no.save(ignore_permissions=True)


@frappe.whitelist()
def make_odometer_log(vehicle, odometer, date=None, project=None, reference_type=None, reference_name=None):
	make_vehicle_log(vehicle, odometer=odometer, date=date, project=project,
		reference_type=reference_type, reference_name=reference_name,
		ignore_permissions=False)


def make_vehicle_log(vehicle, odometer=None, customer=None, vehicle_owner=None, date=None, project=None,
		reference_type=None, reference_name=None, ignore_permissions=True,
		from_project_update=False, do_not_update_customer=False):
	if not vehicle:
		frappe.throw(_("Vehicle is not provided to make Vehicle Odometer Log"))

	date = getdate(date)

	doc = frappe.new_doc("Vehicle Log")
	doc.vehicle = vehicle
	doc.date = date
	doc.project = project
	doc.odometer = cint(odometer)
	doc.customer = customer
	doc.vehicle_owner = vehicle_owner

	if reference_type and reference_name:
		doc.reference_type = reference_type
		doc.reference_name = reference_name

	doc.flags.ignore_permissions = ignore_permissions
	doc.flags.from_project_update = from_project_update
	doc.flags.do_not_update_customer = do_not_update_customer

	doc.save()
	doc.submit()

	return doc.name


@frappe.whitelist()
def get_vehicle_odometer(vehicle, date=None, project=None, ascending=False):
	odometer_log = get_last_odometer_log(vehicle, date, project, ascending)
	return cint(odometer_log.odometer) if odometer_log else 0


@frappe.whitelist()
def get_project_odometer(project, vehicle):
	if project:
		first_odometer = get_vehicle_odometer(vehicle, project=project, ascending=True)
		last_odometer = get_vehicle_odometer(vehicle, project=project, ascending=False)
	else:
		first_odometer = 0
		last_odometer = 0

	return frappe._dict({
		'vehicle_first_odometer': first_odometer,
		'vehicle_last_odometer': last_odometer,
	})


def get_last_odometer_log(vehicle, date=None, project=None, ascending=False, date_operator='<='):
	if not vehicle:
		frappe.throw(_("Vehicle not provided"))

	filters = {
		"vehicle": vehicle,
		"docstatus": 1,
		"odometer": ['>', 0]
	}

	if project:
		filters['project'] = project
	if date:
		filters['date'] = [date_operator, getdate(date)]

	asc_or_desc = "asc" if ascending else "desc"
	order_by = "date {0}, odometer {0}".format(asc_or_desc)

	odometer_log = frappe.get_all("Vehicle Log", filters=filters, fields=['odometer', 'date'], order_by=order_by,
		limit_page_length=1)
	return odometer_log[0] if odometer_log else None


def get_last_customer_log(vehicle, purchase_date=None):
	if not vehicle:
		frappe.throw(_("Vehicle not provided"))

	filters = {
		"vehicle": vehicle,
		"docstatus": 1,
		"customer": ['is', 'set']
	}

	if purchase_date:
		filters['date'] = ['>=', getdate(purchase_date)]

	odometer_log = frappe.get_all("Vehicle Log", filters=filters,
		fields=['customer', 'customer_name', 'vehicle_owner', 'vehicle_owner_name', 'date'],
		order_by="date desc, creation desc", limit_page_length=1)
	return odometer_log[0] if odometer_log else None
