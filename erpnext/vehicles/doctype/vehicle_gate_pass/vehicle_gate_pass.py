# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, combine_datetime, get_datetime
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController
from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import schedule_next_project_template


class VehicleGatePass(VehicleTransactionController):
	def get_feed(self):
		return _("For {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleGatePass, self).validate()
		self.validate_duplicate_gate_pass()
		self.validate_vehicle_received()
		self.validate_sales_invoice()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def on_submit(self):
		self.update_project_vehicle_status()
		self.make_vehicle_log()
		self.add_vehicle_maintenance_schedule()

	def on_cancel(self):
		self.update_project_vehicle_status()
		self.cancel_vehicle_log()
		self.remove_vehicle_maintenance_schedule(self.project)

	def set_title(self):
		self.title = self.get('customer_name') or self.get('customer')

	def validate_duplicate_gate_pass(self):
		if self.get('project'):
			project_gate_pass = frappe.db.get_value("Vehicle Gate Pass",
				filters={"project": self.project, "vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

			if project_gate_pass:
				frappe.throw(_("Vehicle Gate Pass for {0} already exists in {1}")
					.format(frappe.get_desk_link("Project", self.project),
					frappe.get_desk_link("Vehicle Gate Pass", project_gate_pass)))

		if self.get('sales_invoice'):
			invoice_gate_pass = frappe.db.get_value("Vehicle Gate Pass",
				filters={"sales_invoice": self.sales_invoice, "vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

			if invoice_gate_pass:
				frappe.throw(_("Vehicle Gate Pass for {0} already exists in {1}")
					.format(frappe.get_desk_link("Sales Invoice", self.sales_invoice),
					frappe.get_desk_link("Vehicle Gate Pass", invoice_gate_pass)))

	def validate_sales_invoice(self):
		if self.get('sales_invoice'):
			sales_invoice = frappe.db.get_value("Sales Invoice", self.sales_invoice, ['name', 'docstatus', 'project'],
				as_dict=1)
			if not sales_invoice:
				frappe.throw(_("Sales Invoice {0} does not exist").format(sales_invoice.name))

			if cstr(sales_invoice.project) != cstr(self.project):
				frappe.throw(_("Repair Order does not match in {0}")
					.format(frappe.get_desk_link("Project", self.project)))

			if self.docstatus == 1:
				if sales_invoice.docstatus != 1:
					frappe.throw(_("Sales Invoice {0} is not submitted").format(sales_invoice.name))
			else:
				if sales_invoice.docstatus == 2:
					frappe.throw(_("Sales Invoice {0} is cancelled").format(sales_invoice.name))

	def validate_vehicle_received(self):
		vehicle_service_receipt = frappe.db.get_value("Vehicle Service Receipt",
			fieldname=['name', 'timestamp(posting_date, posting_time) as posting_dt'],
			filters={"project": self.project, "vehicle": self.vehicle, "project_workshop": self.project_workshop, "docstatus": 1},
			order_by='posting_date, posting_time, creation', as_dict=1)

		if vehicle_service_receipt:
			self_posting_dt = combine_datetime(self.posting_date, self.posting_time)
			if self_posting_dt < get_datetime(vehicle_service_receipt.posting_dt):
				frappe.throw(_("Vehicle Gate Pass Delivery Date/Time cannot be before Received Date/Time {0}")
					.format(frappe.bold(frappe.format(vehicle_service_receipt.posting_dt))))
		else:
			frappe.throw(_("Vehicle has not been received in Project Workshop {0} for {1} yet")
				.format(self.project_workshop, frappe.get_desk_link("Project", self.project)))

	def add_vehicle_maintenance_schedule(self):
		if self.get("project"):
			project = frappe.get_doc("Project", self.project).as_dict()
			serial_no = self.vehicle

			args = frappe._dict({
				'reference_name': project.name,
				'reference_doctype': project.doctype,
				'reference_date': project.project_date,
				'customer': project.customer,
				'customer_name': project.customer_name,
				'contact_person': project.contact_person,
				'contact_display': project.contact_display,
				'contact_mobile': project.contact_mobile,
				'contact_phone': project.contact_phone,
				'contact_email': project.contact_email
			})

			for template in project.project_templates:
				schedule_next_project_template(template.project_template, serial_no, args)

	def remove_vehicle_maintenance_schedule(self, reference_doctype=None, reference_name=None):
		if self.get("project"):
			return super().remove_vehicle_maintenance_schedule("Project", self.project)
