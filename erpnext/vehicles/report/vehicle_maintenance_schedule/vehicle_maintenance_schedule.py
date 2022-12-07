# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, today
from dateutil.relativedelta import relativedelta
from frappe.contacts.doctype.contact.contact import get_default_contact


def execute(filters=None):
	return VehicleMaintenanceSchedule(filters).run()


class VehicleMaintenanceSchedule:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(filters.from_date or today())
		self.filters.to_date = getdate(filters.to_date or today())

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("Date Range is incorrect"))

	def run(self):
		self.get_data()
		self.process_data()
		self.get_columns()
		return self.columns, self.data

	def get_data(self):
		self.data = frappe.db.sql("""
			SELECT
				msd.scheduled_date as due_date, msd.project_template, ms.name as schedule,
				ms.customer, ms.customer_name, ms.contact_mobile, ms.contact_phone,
				v.name as vehicle, v.item_code, v.delivery_date, v.chassis_no,
				v.engine_no, v.license_plate, v.unregistered, v.variant_of_name,
				v.customer as vehicle_customer, v.customer_name as vehicle_customer_name,
				pt.project_template_name
			FROM `tabMaintenance Schedule Detail` msd
			LEFT JOIN `tabProject Template` pt ON pt.name=msd.project_template
			LEFT JOIN `tabMaintenance Schedule` ms ON ms.name=msd.parent
			LEFT JOIN `tabVehicle` v ON v.name=ms.serial_no
			WHERE ifnull(msd.project_template, '') != ''
				AND msd.scheduled_date BETWEEN %(from_date)s AND %(to_date)s
		""", self.filters, as_dict=1)

	def process_data(self):
		for d in self.data:
			d.disable_item_formatter = 1
			d.contact_no = d.contact_mobile or d.contact_phone

			if not d.variant_of_name:
				d.variant_of_name = d.item_name

			if not d.customer:
				d.customer = d.vehicle_customer
				d.customer_name = d.vehicle_customer_name

			if not d.contact_no:
				contact_id = get_default_contact('Customer', d.customer)
				d.contact_no = frappe.db.get_value("Contact", contact_id, "mobile_no", cache=1)

			d.age = self.get_formatted_duration(getdate(), d.delivery_date)

			if not d.license_plate and d.unregistered:
				d.license_plate = 'Unreg'

		self.data = sorted(self.data, key=lambda d: (getdate(d.due_date), getdate(d.delivery_date)))

	def get_formatted_duration(self, start_date, end_date):
		delta = relativedelta(getdate(start_date), getdate(end_date))
		template = ['Y', 'M', 'D']
		data = [delta.years, delta.months, delta.days]
		duration = " ".join([str(x) + y for x, y in zip(data, template) if x or y=='D'])
		if duration == '0D':
			duration = '-'
		return duration

	def get_columns(self):
		columns = [
			{
				"label": _("Due Date"),
				"fieldname": "due_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Template"),
				"fieldname": "project_template",
				"fieldtype": "Link",
				"options": "Project Template",
				"width": 80
			},
			{
				"label": _("Template Name"),
				"fieldname": "project_template_name",
				"fieldtype": "Data",
				"width": 180
			},
			{
				"label": _("Vehicle"),
				"fieldname": "vehicle",
				"fieldtype": "Link",
				"options": "Vehicle",
				"width": 80
			},
			{
				"label": _("Model"),
				"fieldname": "variant_of_name",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"label": _("Variant Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 120
			},
			{
				"label": _("Reg No"),
				"fieldname": "license_plate",
				"fieldtype": "Data",
				"width": 80
			},
			{
				"label": _("Chassis No"),
				"fieldname": "chassis_no",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Engine No"),
				"fieldname": "engine_no",
				"fieldtype": "Data",
				"width": 115
			},
			{
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Link",
				"options": "Customer",
				"width": 100
			},
			{
				"label": _("Customer Name"),
				"fieldname": "customer_name",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Contact No"),
				"fieldname": "contact_no",
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Delivery Date"),
				"fieldname": "delivery_date",
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Age"),
				"fieldname": "age",
				"fieldtype": "Data",
				"width": 80
			},
			{
				"label": _("Schedule"),
				"fieldname": "schedule",
				"fieldtype": "Link",
				"options": "Maintenance Schedule",
				"width": 80
			},
		]
		self.columns = columns
