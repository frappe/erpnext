# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, formatdate, cstr
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController
from six import string_types


class VehicleInvoice(VehicleTransactionController):
	def get_feed(self):
		return _("For {0} | {1}").format(self.get("customer_name") or self.get('customer'), self.get("bill_no"))

	def validate(self):
		super(VehicleInvoice, self).validate()

		self.validate_party_mandatory()
		self.validate_duplicate_invoice()
		self.reset_values()
		self.set_title()
		self.set_status()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def on_submit(self):
		self.update_vehicle()
		self.update_vehicle_booking_order_invoice()
		self.update_vehicle_registration_order()

	def on_cancel(self):
		self.set_status(update=True, update_vehicle=False)
		self.update_vehicle()
		self.update_vehicle_booking_order_invoice()
		self.update_vehicle_registration_order()

	def set_title(self):
		self.title = "{0} - {1}".format(self.get('customer_name') or self.get('customer'), self.get('bill_no'))

	def validate_duplicate_invoice(self):
		if self.vehicle:
			vehicle_invoice = frappe.db.get_value("Vehicle Invoice",
				filters={"vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

			if vehicle_invoice:
				frappe.throw(_("Invoice for {0} has already been received in {1}")
					.format(frappe.get_desk_link("Vehicle", self.vehicle),
						frappe.get_desk_link("Vehicle Invoice", vehicle_invoice)))

	def reset_values(self):
		if not self.employee:
			self.employee_name = None
		if not self.received_by:
			self.received_by_name = None

		if not self.flags.from_vehicle_invoice_movement:
			self.vehicle_invoice_movement = None

	def set_status(self, update=False, status=None, update_modified=True, update_vehicle=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status

		state = get_vehicle_invoice_state(self)
		for k, v in state.items():
			self.set(k, v)

		self.add_status_comment(previous_status)

		if update:
			self.db_set(state, update_modified=update_modified)

			if update_vehicle:
				self.update_vehicle(update_modified=update_modified)

	def update_vehicle(self, update_modified=True):
		if self.vehicle:
			doc = frappe.get_doc("Vehicle", self.vehicle)
			doc.set_invoice_status(update=True, update_modified=update_modified)
			doc.notify_update()

	def update_copy_delivered(self, update_modified=True):
		has_copy_delivery = frappe.db.get_value("Vehicle Invoice Delivery", filters={
			"docstatus": 1,
			"vehicle_invoice": self.name,
			"is_copy": 1
		})
		self.copy_delivered = 1 if has_copy_delivery else 0

		if update_modified:
			self.db_set('copy_delivered', self.copy_delivered)

@frappe.whitelist()
def get_vehicle_invoice_details(vehicle_invoice):
	invoice_details = frappe._dict()
	if vehicle_invoice:
		invoice_details = frappe.db.get_value("Vehicle Invoice", vehicle_invoice, [
			'bill_no', 'bill_date',
			'employee', 'employee_name',
			'agent', 'agent_name',
			'customer', 'customer_name',
		], as_dict=1) or frappe._dict()

	out = frappe._dict()
	out.bill_no = invoice_details.bill_no
	out.bill_date = invoice_details.bill_date
	out.current_employee = invoice_details.employee
	out.current_employee_name = invoice_details.employee_name
	out.current_agent = invoice_details.agent
	out.current_agent_name = invoice_details.agent_name

	if invoice_details.customer_name:
		out.invoice_customer_name = invoice_details.customer_name

	return out


@frappe.whitelist()
def get_vehicle_invoice(vehicle):
	if not vehicle:
		return None

	return frappe.db.get_value("Vehicle Invoice",
		filters={"vehicle": vehicle, "docstatus": 1})


def get_vehicle_invoice_state(vehicle_invoice, posting_date=None):
	# Macros
	def raise_invalid_state_error(action):
		frappe.throw(_("{0}: Cannot {1} invoice because invoice status is {2} on {3}")
			.format(frappe.get_desk_link(trn.doctype, trn.name),
				_(action), state.status, formatdate(trn.posting_date)))

	def raise_invalid_date_error():
		frappe.throw(_("{0} Date {1} cannot be before Vehicle Invoice Received Date {2}")
			.format(frappe.get_desk_link(trn.doctype, trn.name),
				formatdate(trn.posting_date), formatdate(vehicle_invoice.posting_date)))

	def raise_invalid_issued_for_error(action):
		frappe.throw(_("{0}: Cannot {1} invoice because invoice is not issued for {2} on {3}")
			.format(frappe.get_desk_link(trn.doctype, trn.name),
				_(action), state.issued_for, formatdate(trn.posting_date)))

	# Get Doc
	if isinstance(vehicle_invoice, string_types):
		vehicle_invoice = frappe.get_doc("Vehicle Invoice", vehicle_invoice)

	# Initial State
	state = frappe._dict({
		'status': 'In Hand',
		'issued_for': None, 'issue_date': None, 'return_date': None,
		'delivered_to': None, 'delivered_to_name': None, 'delivered_date': None,
		'employee': vehicle_invoice.get('received_by'), 'employee_name': vehicle_invoice.get('received_by_name'),
		'agent': None, 'agent_name': None
	})

	# Non Submitted State
	if vehicle_invoice.docstatus != 1:
		state.status = "Draft" if vehicle_invoice.docstatus == 0 else "Cancelled"
		return state

	# Get Transactions
	transactions = get_vehicle_invoice_transactions(vehicle_invoice.name, posting_date)

	# Process state
	for trn in transactions:
		if getdate(trn.posting_date) < getdate(vehicle_invoice.posting_date):
			raise_invalid_date_error()

		if trn.purpose == "Delivery":
			if state.status != 'In Hand':
				raise_invalid_state_error('Deliver')

			state.status = "Delivered"
			state.delivered_date = trn.posting_date
			state.delivered_to = trn.customer
			state.delivered_to_name = trn.customer_name
			state.employee = None
			state.employee_name = None
			state.agent = None
			state.agent_name = None

		elif trn.purpose == "Issue":
			if state.status != 'In Hand':
				raise_invalid_state_error('Issue')

			state.status = "Issued"
			state.issued_for = trn.issued_for
			state.issue_date = trn.posting_date
			state.return_date = None
			state.agent = trn.agent
			state.agent_name = trn.agent_name
			state.employee = None
			state.employee_name = None

		elif trn.purpose == "Return":
			if state.status != 'Issued':
				raise_invalid_state_error('Return')
			if cstr(state.issued_for) != cstr(trn.issued_for):
				raise_invalid_issued_for_error('Return')

			state.status = "In Hand"
			state.return_date = trn.posting_date
			state.employee = trn.employee
			state.employee_name = trn.employee_name
			state.agent = None
			state.agent_name = None

		elif trn.purpose == "Transfer":
			if state.status != 'In Hand':
				raise_invalid_state_error('Transfer')

			state.employee = trn.employee
			state.employee_name = trn.employee_name

		else:
			frappe.throw(_("Invalid Purpose in {0}")
				.format(frappe.get_desk_link(trn.doctype, trn.name)))

	return state


def get_vehicle_invoice_transactions(vehicle_invoice, posting_date=None):
	filter_values = {
		'vehicle_invoice': vehicle_invoice,
		'posting_date': posting_date
	}
	conditions = ""
	if posting_date:
		conditions += " and trn.posting_date <= %(posting_date)s"

	deliveries = frappe.db.sql("""
			select 'Vehicle Invoice Delivery' as doctype, trn.name,
				trn.posting_date, trn.creation,
				'Delivery' as purpose, trn.customer, trn.customer_name
			from `tabVehicle Invoice Delivery` trn
			where trn.docstatus = 1 and trn.is_copy = 0 and trn.vehicle_invoice = %(vehicle_invoice)s {0}
		""".format(conditions), filter_values, as_dict=1)

	movements = frappe.db.sql("""
			select 'Vehicle Invoice Movement' as doctype, trn.name,
				trn.posting_date, trn.creation,
				trn.purpose, trn.issued_for,
				trn.employee, trn.employee_name,
				trn.agent, trn.agent_name
			from `tabVehicle Invoice Movement Detail` d
			inner join `tabVehicle Invoice Movement` trn on trn.name = d.parent
			where trn.docstatus = 1 and d.vehicle_invoice = %(vehicle_invoice)s and trn.purpose != 'Receive' {0}
		""".format(conditions), filter_values, as_dict=1)

	transactions = deliveries + movements
	transactions = sorted(transactions, key=lambda d: (getdate(d.posting_date), get_datetime(d.creation)))

	return transactions
