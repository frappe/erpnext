# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController
from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import schedule_project_templates_after_delivery


class VehicleDelivery(VehicleTransactionController):
	def get_feed(self):
		return _("To {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleDelivery, self).validate()
		self.validate_party_mandatory()
		self.validate_return()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def on_submit(self):
		self.update_stock_ledger()
		self.update_vehicle_warranty_no()
		self.update_vehicle_booking_order_delivery()
		self.make_vehicle_log()
		self.add_vehicle_maintenance_schedule()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_vehicle_booking_order_delivery()
		self.cancel_vehicle_log()
		self.remove_vehicle_maintenance_schedule()

	def validate_return(self):
		if cint(self.is_return) and self.vehicle:
			sle_exists = frappe.db.sql("""
				select name
				from `tabStock Ledger Entry`
				where serial_no = %(vehicle)s and actual_qty > 0
					and timestamp(posting_date, posting_time) < timestamp(%(posting_date)s, %(posting_time)s)
				limit 1
			""", {
				'vehicle': self.vehicle,
				'posting_date': self.posting_date,
				'posting_time': self.posting_time,
			})

			if not sle_exists:
				frappe.throw(_("Cannot create a Vehicle Delivery Return for Vehicle {0} becuase it hasn't been received yet")
					.format(self.vehicle))

	def set_title(self):
		self.title = "{0}{1}".format(self.customer_name or self.customer, ' ({0})'.format(self.get('received_by')) if self.get('received_by') else '')

	def add_vehicle_maintenance_schedule(self):
		serial_no = self.get_serial_no()
		if serial_no:
			args = frappe._dict({
				'reference_name': self.name,
				'reference_doctype': self.doctype,
				'reference_date': self.posting_date,
				'customer': self.customer,
				'customer_name': self.customer_name,
				'contact_person': self.contact_person,
				'contact_display': self.contact_display,
				'contact_mobile': self.contact_mobile,
				'contact_phone': self.contact_phone,
				'contact_email': self.contact_email
			})
			schedule_project_templates_after_delivery(serial_no, args)
