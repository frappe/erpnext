# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController


class VehicleServiceReceipt(VehicleTransactionController):
	def get_feed(self):
		return _("From {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleServiceReceipt, self).validate()
		self.validate_duplicate_receipt()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def on_submit(self):
		self.update_project_vehicle_status()
		self.make_vehicle_log()

	def before_cancel(self):
		self.validate_already_delivered()

	def on_cancel(self):
		self.update_project_vehicle_status()
		self.cancel_vehicle_log()

	def set_title(self):
		self.title = self.get('customer_name') or self.get('customer')

	def validate_duplicate_receipt(self):
		if self.get('project'):
			project_vehicle_service_receipt = frappe.db.get_value("Vehicle Service Receipt",
				filters={"project": self.project, "vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

			if project_vehicle_service_receipt:
				frappe.throw(_("Vehicle Service Receipt for {0} already exists in {1}")
					.format(frappe.get_desk_link("Project", self.project),
					frappe.get_desk_link("Vehicle Gate Pass", project_vehicle_service_receipt)))

	def validate_already_delivered(self):
		project_gate_pass = frappe.db.get_value("Vehicle Gate Pass",
			filters={"project": self.project, "vehicle": self.vehicle, "docstatus": 1})

		if project_gate_pass:
			frappe.throw(_("Cannot cancel because Vehicle Gate Pass for {0} already exists in {1}")
				.format(frappe.get_desk_link("Project", self.project),
				frappe.get_desk_link("Vehicle Gate Pass", project_gate_pass)))
