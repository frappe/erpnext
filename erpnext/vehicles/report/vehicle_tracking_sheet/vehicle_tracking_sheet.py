# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, formatdate, format_time, format_datetime, get_time, now_datetime, date_diff
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
import datetime


date_format = "d/MM/Y"
time_format = "hh:mm a"
datetime_format = "{0}, {1}".format(date_format, time_format)


class VehicleServiceTrackingReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.to_date = getdate(self.filters.to_date)

		self.report_date = getdate(self.filters.to_date)
		self.report_time = get_time(now_datetime()) if self.report_date == getdate() else datetime.time.max
		self.report_dt = frappe.utils.combine_datetime(self.report_date, self.report_time)

		if getdate(self.filters.from_date) > self.filters.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

	def run(self):
		self.get_data()
		self.process_data()
		columns = self.get_columns()

		return columns, self.data

	def get_data(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select p.name as project, p.project_name, p.project_type, p.project_workshop, p.company, p.project_status,
				p.customer, p.customer_name, p.contact_mobile, p.contact_mobile_2, p.contact_phone,
				p.insurance_company, p.insurance_company_name,
				p.applies_to_vehicle, p.service_advisor, p.service_manager,
				p.applies_to_item, p.applies_to_item_name, p.applies_to_variant_of, p.applies_to_variant_of_name,
				p.vehicle_license_plate, p.vehicle_chassis_no, p.vehicle_engine_no, p.vehicle_unregistered,
				p.vehicle_received_date, p.vehicle_received_time,
				timestamp(p.vehicle_received_date, p.vehicle_received_time) as vehicle_received_dt,
				p.vehicle_delivered_date, p.vehicle_delivered_time,
				timestamp(p.vehicle_delivered_date, p.vehicle_delivered_time) as vehicle_delivered_dt,
				p.expected_delivery_date, p.expected_delivery_time,
				timestamp(p.expected_delivery_date, p.expected_delivery_time) as expected_delivery_dt,
				p.ready_to_close, p.ready_to_close_dt,
				date(p.ready_to_close_dt) as ready_to_close_date, time(p.ready_to_close_dt) as ready_to_close_time,
				p.billing_status, p.customer_billable_amount, p.total_billable_amount
			from `tabProject` p
			left join `tabItem` item on item.name = p.applies_to_item
			where {0}
			order by p.vehicle_received_date, p.vehicle_received_time
		""".format(conditions), self.filters, as_dict=1)

		return self.data

	def process_data(self):
		for d in self.data:
			# Status
			d.delivered = 1 if d.vehicle_delivered_date else 0
			d.billed = 0 if d.billing_status in ["Not Applicable", "Not Billed"] else 1

			# Date/Time Formatting
			self.set_formatted_datetime(d)

			# Model Name if not a variant
			if not d.applies_to_variant_of_name:
				d.applies_to_variant_of_name = d.applies_to_item_name

			# Unregistered
			if not d.vehicle_license_plate and d.vehicle_unregistered:
				d.vehicle_license_plate = _('Unreg')

			# Is Late
			self.set_late_or_early(d)

	def set_formatted_datetime(self, d):
		d.vehicle_received_date_fmt = formatdate(d.vehicle_received_dt, date_format)
		d.vehicle_received_time_fmt = format_time(d.vehicle_received_dt, time_format)
		d.vehicle_received_dt_fmt = format_datetime(d.vehicle_received_dt, datetime_format)

		d.vehicle_delivered_dt_fmt = format_datetime(d.vehicle_delivered_dt, datetime_format)

		d.ready_to_close_date_fmt = formatdate(d.ready_to_close_dt, date_format)
		d.ready_to_close_time_fmt = format_time(d.ready_to_close_dt, time_format)
		d.ready_to_close_dt_fmt = format_datetime(d.ready_to_close_dt, datetime_format)

		d.expected_delivery_date_fmt = formatdate(d.expected_delivery_date, date_format)
		d.expected_delivery_time_fmt = format_time(d.expected_delivery_time, time_format)
		if d.expected_delivery_date and d.expected_delivery_time:
			d.expected_delivery_dt_fmt = format_datetime(d.expected_delivery_dt, datetime_format)
		elif d.expected_delivery_date:
			d.expected_delivery_dt_fmt = formatdate(d.expected_delivery_date, date_format)

	def set_late_or_early(self, d):
		# only if expected delivery date is set other no late/early marking
		if d.expected_delivery_date:
			compare_date = d.ready_to_close_date if d.ready_to_close_dt else self.report_date
			compare_dt = d.ready_to_close_dt if d.ready_to_close_dt else self.report_dt

			if d.expected_delivery_time:
				if compare_dt > d.expected_delivery_dt:
					d.is_late = 1
					d.is_early = 0

					if date_diff(compare_date, d.expected_delivery_date) > 0:
						d.time_color = 'red'
					else:
						d.time_color = 'orange'
				else:
					d.is_late = 0
					d.is_early = 0

					if d.ready_to_close:
						d.is_early = 1
						d.time_color = 'green'
			else:
				if compare_date > d.expected_delivery_date:
					d.is_late = 1
					d.is_early = 0
					d.time_color = 'red'
				else:
					d.is_late = 0
					d.is_early = 0

					if d.ready_to_close:
						d.is_early = 1
						d.time_color = 'green'

	def get_conditions(self):
		conditions = []

		if self.filters.to_date:
			conditions.append("p.vehicle_received_date <= %(to_date)s")

		if self.filters.from_date:
			conditions.append("(ifnull(p.vehicle_delivered_date, '0000-00-00') = '0000-00-00' or p.vehicle_delivered_date >= %(from_date)s)")

		if self.filters.project_workshop:
			conditions.append("p.project_workshop = %(project_workshop)s")

		if self.filters.service_advisor:
			conditions.append("p.service_advisor = %(service_advisor)s")

		if self.filters.get("status"):
			if self.filters.get("status") == "Closed":
				conditions.append("status in ('Closed', 'Completed')")
			elif self.filters.get("status") == "Cancelled":
				conditions.append( "status = 'Cancelled'")
			elif self.filters.get("status") == "Open":
				conditions.append( "status = 'Open'")
			elif self.filters.get("status") == "Closed or To Close":
				conditions.append("status in ('To Close' ,'Closed', 'Completed')")
			elif self.filters.get("status") == "To Close":
				conditions.append( "status = 'To Close'")
		else:
			conditions.append("status != 'Cancelled'")

		if self.filters.service_manager:
			conditions.append("p.service_manager = %(service_manager)s")

		if self.filters.project_type:
			conditions.append("p.project_type = %(project_type)s")

		if self.filters.customer:
			conditions.append("p.customer = %(customer)s")

		if self.filters.applies_to_vehicle:
			conditions.append("p.applies_to_vehicle = %(applies_to_vehicle)s")

		if self.filters.applies_to_variant_of:
			conditions.append("item.variant_of = %(applies_to_variant_of)s")

		if self.filters.applies_to_item:
			conditions.append("p.applies_to_item = %(applies_to_item)s")

		if self.filters.item_group:
			conditions.append(get_item_group_condition(self.filters.item_group))

		if self.filters.brand:
			conditions.append("item.brand = %(brand)s")

		return " and ".join(conditions) if conditions else ""

	def get_columns(self):
		columns = [
			{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 95,
				"report_time": self.report_time, "report_time_fmt": format_time(self.report_time, time_format)},
			{"label": _("Ready"), "fieldname": "ready_to_close", "fieldtype": "Check", "width": 55},
			{"label": _("Billed"), "fieldname": "billed", "fieldtype": "Check", "width": 55},
			{"label": _("Delivered"), "fieldname": "delivered", "fieldtype": "Check", "width": 55},
			{"label": _("Reg No"), "fieldname": "vehicle_license_plate", "fieldtype": "Data", "width": 80},
			{"label": _("Model"), "fieldname": "applies_to_variant_of_name", "fieldtype": "Data", "width": 120},
			{"label": _("Variant Code"), "fieldname": "applies_to_item", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Service Advisor"), "fieldname": "service_advisor", "fieldtype": "Link", "options": "Sales Person", "width": 120},
			{"label": _("Voice of Customer"), "fieldname": "project_name", "fieldtype": "Data", "width": 150},
			{"label": _("Project Type"), "fieldname": "project_type", "fieldtype": "Link", "options": "Project Type", "width": 100},
			{"label": _("Bill Amount"), "fieldname": "customer_billable_amount", "fieldtype": "Currency", "options": "Company:company:default_currency", "width": 90},
			{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 130},
			{"label": _("Contact #"), "fieldname": "contact_mobile", "fieldtype": "Data", "width": 100},
			{"label": _("Received Date/Time"), "fieldname": "vehicle_received_dt_fmt", "fieldtype": "Data", "width": 135},
			{"label": _("Promised Date/Time"), "fieldname": "expected_delivery_dt_fmt", "fieldtype": "Data", "width": 135},
			{"label": _("Ready Date/Time"), "fieldname": "ready_to_close_dt_fmt", "fieldtype": "Data", "width": 135},
			{"label": _("Delivered Date/Time"), "fieldname": "vehicle_delivered_dt_fmt", "fieldtype": "Data", "width": 135},
		]

		return columns


def execute(filters=None):
	return VehicleServiceTrackingReport(filters).run()
