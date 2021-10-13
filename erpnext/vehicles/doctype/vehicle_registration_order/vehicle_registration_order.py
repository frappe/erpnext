# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate
from erpnext.vehicles.vehicle_additional_service import VehicleAdditionalServiceController
from erpnext.vehicles.vehicle_pricing import calculate_total_price, validate_duplicate_components,\
	validate_component_type, validate_disabled_component, get_pricing_components, get_component_details,\
	pricing_force_fields


class VehicleRegistrationOrder(VehicleAdditionalServiceController):
	def get_feed(self):
		return _("From {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleRegistrationOrder, self).validate()
		self.validate_duplicate_registration_order()
		self.validate_vehicle_unregistered()
		self.validate_choice_number()

		self.validate_pricing_components()
		self.calculate_totals()
		self.calculate_outstanding_amount()

		self.validate_agent_mandatory()
		self.set_missing_accounts()

		self.update_payment_status()
		self.update_invoice_status()
		self.update_registration_number()
		self.set_status()

		self.set_title()

	def before_submit(self):
		if not self.vehicle and not self.vehicle_booking_order:
			frappe.throw(_("Please set either Vehicle Booking Order or Vehicle"))

		self.validate_account_mandatory()

	def on_submit(self):
		self.update_vehicle_booking_order_registration()

	def on_cancel(self):
		self.update_vehicle_booking_order_registration()

	def set_title(self):
		self.title = "{0}{1}".format(self.customer_name or self.customer, ' ({0})'.format(self.get('received_by')) if self.get('received_by') else '')

	def set_missing_values(self, doc=None, for_validate=False):
		super(VehicleRegistrationOrder, self).set_missing_values(doc, for_validate)
		self.set_pricing_details()

	def set_pricing_details(self, update_component_amounts=False):
		if not self.get('customer_charges') and not self.get('authority_charges'):
			pricing_data = get_pricing_components("Registration", self.as_dict(),
				get_selling_components=True, get_buying_components=True)

			for d in pricing_data.selling:
				self.append('customer_charges', d)
			for d in pricing_data.buying:
				self.append('authority_charges', d)
		else:
			for tablefield, selling_or_buying in [('customer_charges', 'selling'), ('authority_charges', 'buying')]:
				for d in self.get(tablefield):
					if d.get('component'):
						component_details = get_component_details(d.component, self.as_dict(),
							selling_or_buying=selling_or_buying)
						for k, v in component_details.component.items():
							if d.meta.has_field(k):
								if k == 'component_amount' and update_component_amounts and v:
									d.set(k, v)
								elif not d.get(k) or k in pricing_force_fields:
									d.set(k, v)

	def validate_duplicate_registration_order(self):
		if self.vehicle:
			registration_order = frappe.db.get_value("Vehicle Registration Order",
				filters={"vehicle": self.vehicle, "docstatus": 1, "name": ['!=', self.name]})

			if registration_order:
				frappe.throw(_("Vehicle Registration Order for {0} already exists in {1}")
					.format(frappe.get_desk_link("Vehicle", self.vehicle),
						frappe.get_desk_link("Vehicle Registration Order", registration_order)))

		if self.vehicle_booking_order:
			registration_order = frappe.db.get_value("Vehicle Registration Order",
				filters={"vehicle_booking_order": self.vehicle_booking_order, "docstatus": 1, "name": ['!=', self.name]})

			if registration_order:
				frappe.throw(_("Vehicle Registration Order for {0} already exists in {1}")
					.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order),
						frappe.get_desk_link("Vehicle Registration Order", registration_order)))

	def validate_vehicle_unregistered(self):
		if self.vehicle:
			license_plate = frappe.db.get_value("Vehicle", self.vehicle, "license_plate")
			if license_plate:
				frappe.throw(_("{0} is already registered: {1}")
					.format(frappe.get_desk_link("Vehicle", self.vehicle), license_plate))

	def validate_choice_number(self):
		if not cint(self.choice_number_required):
			self.choice_number_details = ""

	def validate_pricing_components(self):
		validate_disabled_component(self.get('customer_charges'))
		validate_disabled_component(self.get('authority_charges'))

		validate_duplicate_components(self.get('customer_charges'))
		validate_duplicate_components(self.get('authority_charges'))

		validate_component_type("Registration", self.get('customer_charges'))
		validate_component_type("Registration", self.get('authority_charges'))

	def validate_agent_mandatory(self):
		if flt(self.agent_commission) and not self.agent:
			frappe.throw(_("Registration Agent is mandatory for Registration Agent Commission"))

	def validate_account_mandatory(self):
		if not self.customer_account:
			frappe.throw(_("Customer Receivable Account is mandatory"))
		if not self.agent_account and self.agent:
			frappe.throw(_("Agent Payable Account is mandatory"))

	def set_missing_accounts(self):
		if not self.customer_account:
			self.customer_account = frappe.get_cached_value("Vehicles Settings", None, "registration_customer_account")
		if not self.agent_account:
			self.agent_account = frappe.get_cached_value("Vehicles Settings", None, "registration_customer_account")

	def calculate_totals(self):
		calculate_total_price(self, 'customer_charges', 'customer_total')
		calculate_total_price(self, 'authority_charges', 'authority_total')

		self.round_floats_in(self, ['agent_commission'])

		self.margin_amount = flt(self.customer_total - self.authority_total - self.agent_commission,
			self.precision('margin_amount'))

	def calculate_outstanding_amount(self):
		if self.docstatus == 0:
			self.customer_payment = 0
			self.authority_payment = 0
			self.agent_payment = 0
			self.agent_outstanding = 0
		else:
			gl_values = self.get_values_from_gl_entries()
			self.update(gl_values)

		self.customer_outstanding = flt(self.customer_total) - flt(self.customer_payment)
		self.authority_outstanding = flt(self.authority_total) - flt(self.authority_payment)

	def get_values_from_gl_entries(self):
		args = {
			'vehicle_registration_order': self.name,
			'customer': self.customer,
			'customer_account': self.customer_account,
			'agent': self.agent,
			'agent_account': self.agent_account
		}

		customer_payment = frappe.db.sql("""
			select sum(gle.credit-gle.debit) as amount
			from `tabGL Entry` gle
			left join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
			left join `tabPayment Entry` pe on gle.voucher_type = 'Payment Entry' and gle.voucher_no = pe.name
			where (jv.vehicle_registration_purpose = 'Customer Payment' or pe.payment_type = 'Receive')
				and gle.vehicle_registration_order = %(vehicle_registration_order)s
				and gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s
		""", args)
		customer_payment = flt(customer_payment[0][0]) if customer_payment else 0

		authority_payment = frappe.db.sql("""
			select sum(gle.debit-gle.credit) as amount
			from `tabGL Entry` gle
			inner join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
			where jv.vehicle_registration_purpose = 'Authority Payment'
				and gle.vehicle_registration_order = %(vehicle_registration_order)s
				and gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s
		""", args)
		authority_payment = flt(authority_payment[0][0]) if authority_payment else 0

		if self.agent:
			agent_payment = frappe.db.sql("""
				select sum(gle.debit-gle.credit) as amount
				from `tabGL Entry` gle
				left join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
				left join `tabPayment Entry` pe on gle.voucher_type = 'Payment Entry' and gle.voucher_no = pe.name
				where (jv.vehicle_registration_purpose = 'Agent Payment' or pe.payment_type = 'Pay')
					and gle.vehicle_registration_order = %(vehicle_registration_order)s
					and gle.account = %(agent_account)s and gle.party_type = 'Supplier' and gle.party = %(agent)s
			""", args)
			agent_payment = flt(agent_payment[0][0]) if agent_payment else 0

			agent_outstanding = frappe.db.sql("""
				select sum(gle.credit-gle.debit) as amount
				from `tabGL Entry` gle
				left join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
				left join `tabPayment Entry` pe on gle.voucher_type = 'Payment Entry' and gle.voucher_no = pe.name
				where gle.vehicle_registration_order = %(vehicle_registration_order)s
					and gle.account = %(agent_account)s and gle.party_type = 'Supplier' and gle.party = %(agent)s
			""", args)
			agent_outstanding = flt(agent_outstanding[0][0]) if agent_outstanding else 0
		else:
			agent_payment = 0
			agent_outstanding = 0

		return frappe._dict({
			'customer_payment': customer_payment,
			'authority_payment': authority_payment,
			'agent_payment': agent_payment,
			'agent_outstanding': agent_outstanding,
		})

	def update_payment_status(self, update=False):
		self.calculate_outstanding_amount()

		if update:
			self.db_set({
				'customer_payment': self.customer_payment,
				'customer_outstanding': self.customer_outstanding,
				'authority_payment': self.authority_payment,
				'authority_outstanding': self.authority_outstanding,
				'agent_payment': self.agent_payment,
				'agent_outstanding': self.agent_outstanding,
			})

	def update_invoice_status(self, update=False):
		vehicle_invoice = None

		if self.vehicle:
			vehicle_invoice = frappe.db.get_all("Vehicle Invoice", {"vehicle": self.vehicle, "docstatus": 1},
				['name', 'status', 'issued_for'], order_by="posting_date desc, creation desc")

		vehicle_invoice = vehicle_invoice[0] if vehicle_invoice else frappe._dict()

		if vehicle_invoice:
			self.invoice_status = vehicle_invoice.status
			self.invoice_issued_for = vehicle_invoice.issued_for if vehicle_invoice.status == "Issued" else None
		else:
			self.invoice_status = "Not Received"
			self.invoice_issued_for = None

		if update:
			self.db_set({
				"invoice_status": self.invoice_status,
				"invoice_issued_for": self.invoice_issued_for,
			})

	def update_registration_number(self, update=False):
		pass

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status

		if self.docstatus == 2:
			self.status = "Cancelled"

		elif self.docstatus == 1:
			if self.customer_outstanding > 0:
				self.status = "To Receive Payment"

			elif self.authority_outstanding > 0:
				self.status = "To Pay Authority"

			elif not self.vehicle_license_plate:
				if self.invoice_status == "In Hand":
					self.status = "To Issue Invoice"

				elif self.invoice_status == "Issued" and self.invoice_issued_for == "Registration":
					self.status = "To Receive Receipt"

				else:
					self.status = "To Receive Invoice"
			else:
				if self.invoice_status == "Issued":
					self.status = "To Retrieve Invoice"

				elif self.invoice_status == "In Hand":
					self.status = "To Deliver Invoice"

				elif self.agent_outstanding > 0:
					self.status = "To Pay Agent"

				else:
					self.status = "Completed"

		else:
			self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)


def get_vehicle_registration_order(vehicle=None, vehicle_booking_order=None, fields='name', as_dict=False):
	vehicle_registration_order = None

	if not vehicle and not vehicle_booking_order:
		return vehicle_registration_order

	if vehicle:
		vehicle_registration_order = frappe.db.get_value("Vehicle Registration Order", filters={
			'vehicle': vehicle,
			'docstatus': 1
		}, fieldname=fields, as_dict=as_dict)

	if not vehicle_registration_order and vehicle_booking_order:
		vehicle_registration_order = frappe.db.get_value("Vehicle Registration Order", filters={
			'vehicle_booking_order': vehicle_booking_order,
			'docstatus': 1
		}, fieldname=fields, as_dict=as_dict)

	return vehicle_registration_order
