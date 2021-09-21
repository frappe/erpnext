# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController

class VehicleInvoiceReceipt(VehicleTransactionController):
	def get_feed(self):
		return _("From {0} | {1}").format(self.get("suplier_name") or self.get('supplier'), self.get("bill_no"))

	def validate(self):
		super(VehicleInvoiceReceipt, self).validate()

		self.validate_duplicate_invoice_receipt()
		self.set_title()
		self.set_status()

	def on_submit(self):
		self.update_vehicle_booking_order()

	def on_cancel(self):
		self.db_set('status', 'Cancelled')
		self.update_vehicle_booking_order()

	def validate_duplicate_invoice_receipt(self):
		if self.vehicle:
			invoice_receipt = frappe.db.get_value("Vehicle Invoice Receipt",
				filters={"vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

			if invoice_receipt:
				frappe.throw(_("Invoice for {0} has already been received in {1}")
					.format(frappe.get_desk_link("Vehicle", self.vehicle),
						frappe.get_desk_link("Vehicle Invoice Receipt", invoice_receipt)))

	def set_title(self):
		self.title = "{0} ({1})".format(self.get('bill_no'), self.get('supplier_name') or self.get('supplier'))

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status

		if self.docstatus == 2:
			self.status = "Cancelled"

		elif self.docstatus == 1:
			vehicle_invoice_delivery = frappe.db.get_value("Vehicle Invoice Delivery", fieldname=['name', 'posting_date'],
				filters={'vehicle_invoice_receipt': self.name, 'docstatus': 1}, as_dict=1)
			vehicle_invoice_delivery = vehicle_invoice_delivery or frappe._dict()

			self.delivered_date = vehicle_invoice_delivery.posting_date

			if vehicle_invoice_delivery:
				self.status = "Delivered"
			else:
				self.status = "In Hand"

		else:
			self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set({
				'status': self.status,
				'delivered_date': self.delivered_date,
			}, update_modified=update_modified)
