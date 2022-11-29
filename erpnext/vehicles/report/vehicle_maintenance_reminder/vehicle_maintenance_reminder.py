# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, today, flt, add_months, today
from dateutil.relativedelta import relativedelta
from datetime import datetime

def execute(filters=None):
	return VehicleMaintenanceReminder(filters).run()


class VehicleMaintenanceReminder:
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
		self.project_template_data = frappe.db.sql("""
			SELECT name as project_template, project_template_name, project_template_category, applies_to_item, due_after
			FROM `tabProject Template`
			WHERE due_after > 0 and ifnull(applies_to_item, '') != ''
			ORDER BY due_after ASC
		""", as_dict=1)

		vehicle_or_conditions = self.process_project_template_data()

		vehicle_data = frappe.db.sql("""
			SELECT
				name as vehicle, item_code, item_name, customer, customer_name, delivery_date,
				chassis_no, engine_no, license_plate, unregistered, variant_of, variant_of_nam e
			FROM `tabVehicle`
			WHERE {0} and ifnull(delivery_document_no, '') != ''
		""".format(vehicle_or_conditions), self.filters, as_dict=1)

		self.data = vehicle_data


	def process_project_template_data(self):
		vehicle_or_conditions = []
		applies_to_item_cache = frappe._dict()

		for d in self.project_template_data:
			template_condition = []
			if d.applies_to_item:
				if d.applies_to_item not in applies_to_item_cache:
					item_codes = frappe.db.get_all("Item", filters={'variant_of': d.applies_to_item}, fields="item_code")
					item_codes = [d.applies_to_item] + [i.item_code for i in item_codes]
					applies_to_item_cache[d.applies_to_item] = item_codes
				else:
					item_codes = applies_to_item_cache[d.applies_to_item]

				template_condition.append("item_code in ({0})"
					.format(", ".join([frappe.db.escape(item_code) for item_code in item_codes])))

			delivery_from_date = self.filters.from_date - relativedelta(months=d.due_after)
			delivery_to_date = self.filters.to_date - relativedelta(months=d.due_after)
			template_condition.append("delivery_date between {0} and {1}".format(
				frappe.db.escape(delivery_from_date),
				frappe.db.escape(delivery_to_date)
			))
			d.from_date, d.to_date = delivery_from_date, delivery_to_date

			vehicle_or_conditions.append(" and ".join(template_condition))

		vehicle_or_conditions = " or ".join(vehicle_or_conditions)
		return vehicle_or_conditions

	def process_data(self):
		for d in self.data:
			rd = relativedelta(getdate(), d.delivery_date)
			duration_list = [str(x) + y for x, y in zip([rd.years, rd.months, rd.days], ['Y', 'M', 'D'])
				if x or y=='D']
			d.age = " ".join(duration_list)

			for p in self.project_template_data:
				if p.applies_to_item in [d.variant_of, d.item_code]\
						and p.from_date <= d.delivery_date <= p.to_date:
					d.update(p)
					break
			
			d.due_date = d.delivery_date + relativedelta(months=p.due_after)
			if not d.license_plate and d.unregistered:
				d.license_plate = 'Unreg'

	def get_columns(self):
		columns = [
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
				"label": _("Vehicle"),
				"fieldname": "vehicle",
				"fieldtype": "Link",
				"options": "Vehicle",
				"width": 80
			},
			{
				"label": _("Variant Code"),
				"fieldname": "item_code",
				"fieldtype": "Data",
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
				"label": _("Project Template"),
				"fieldname": "project_template",
				"fieldtype": "Link",
				"options": "Project Template",
				"width": 150
			},
			{
				"label": _("Due Date"),
				"fieldname": "due_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Project template Name"),
				"fieldname": "project_template_name",
				"fieldtype": "Data",
				"width": 180
			},
			{
				"label": _("Service Type"),
				"fieldname": "project_template_category",
				"fieldtype": "Data",
				"width": 100
			}
		]
		self.columns = columns
