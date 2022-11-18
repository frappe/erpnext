# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _
from frappe.utils import flt, cint, cstr, getdate
from frappe.model.utils import get_fetch_values
from erpnext.vehicles.vehicle_additional_service import VehicleAdditionalServiceController
from erpnext.vehicles.vehicle_pricing import calculate_total_price, validate_duplicate_components,\
	validate_component_type, validate_disabled_component, get_pricing_components, get_component_details,\
	pricing_force_fields
from erpnext.accounts.party import validate_party_frozen_disabled
from six import string_types
import json


class VehicleRegistrationOrder(VehicleAdditionalServiceController):
	def get_feed(self):
		return _("From {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def onload(self):
		if self.docstatus == 1:
			self.set_onload('disallow_on_submit', self.get_disallow_on_submit_fields())
			self.set_onload('transfer_letter_exists', self.transfer_letter_exists())
			self.set_onload('registration_receipt_exists', self.registration_receipt_exists())
			self.set_onload('sales_invoice_exists', self.sales_invoice_exists())

	def validate(self):
		super(VehicleRegistrationOrder, self).validate()
		self.validate_duplicate_registration_order()

		self.set_missing_accounts()
		self.validate_common()

	def before_update_after_submit(self):
		self.set_customer_details(for_validate=True)
		self.get_disallow_on_submit_fields()
		self.validate_common()

	def validate_common(self):
		self.validate_registration_party()
		self.validate_pricing_components()
		self.calculate_totals()
		self.calculate_outstanding_amount()
		self.validate_amounts()

		self.validate_account_mandatory()

		self.set_payment_status()
		self.set_invoice_status()
		self.set_registration_receipt_details()
		self.set_status()
		self.set_title()

	def before_submit(self):
		if not self.vehicle and not self.vehicle_booking_order:
			frappe.throw(_("Please set either Vehicle Booking Order or Vehicle"))

	def on_submit(self):
		self.update_vehicle_booking_order_registration()

	def on_cancel(self):
		self.update_vehicle_booking_order_registration()

	def before_print(self, print_settings=None):
		super(VehicleRegistrationOrder, self).before_print(print_settings=print_settings)
		self.customer_total_in_words = frappe.utils.money_in_words(self.customer_total, erpnext.get_company_currency(self.company))
		self.get_customer_payments()

	def get_disallow_on_submit_fields(self):
		if self.is_new():
			return []

		disallowed_fields = []

		# Cannot edit anything after completion or after receiving registration receipt
		if self.status == "Completed":
			excluding_fields = []
			if self.status != "Completed":
				excluding_fields.append('agent_charges')
				excluding_fields.append('agent_total')
				excluding_fields.append('margin_amount')
				excluding_fields.append('status')

			disallowed_fields = self.get_fields_for_disallow_on_submit(excluding_fields)

		else:
			if self.agent_gl_entry_exists():
				disallowed_fields.append(('agent', None))
			if self.registration_receipt_exists():
				disallowed_fields.append(('registration_customer', None))
				disallowed_fields.append(('financer', None))

		self.flags.disallow_on_submit = disallowed_fields
		return disallowed_fields

	def agent_gl_entry_exists(self):
		if not hasattr(self, '_agent_gl_entry_exists'):
			self._agent_gl_entry_exists = frappe.db.exists("GL Entry", {
				'reference_type': self.doctype,
				'reference_name': self.name,
				'party_type': 'Supplier',
				'account': self.agent_account
			})

		return self._agent_gl_entry_exists

	def transfer_letter_exists(self):
		if not hasattr(self, '_transfer_letter_exists'):
			self._transfer_letter_exists = frappe.db.exists("Vehicle Transfer Letter", {
				'vehicle_registration_order': self.name,
				'docstatus': 1
			})

		return self._transfer_letter_exists

	def registration_receipt_exists(self):
		if not hasattr(self, '_registration_receipt_exists'):
			self._registration_receipt_exists = frappe.db.exists("Vehicle Registration Receipt", {
				'vehicle_registration_order': self.name,
				'docstatus': 1
			})

		return self._registration_receipt_exists

	def sales_invoice_exists(self):
		if not hasattr(self, '_sales_invoice_exists'):
			self._sales_invoice_exists = frappe.db.exists("Sales Invoice", {
				'vehicle_registration_order': self.name,
				'docstatus': 1
			})

		return self._sales_invoice_exists

	def set_title(self):
		names = []

		if self.registration_customer_name:
			names.append(self.registration_customer_name)
		if self.customer_name and self.customer != self.registration_customer:
			names.append(self.customer_name)

		self.title = " / ".join(names)

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

	def validate_registration_party(self):
		if self.get('registration_customer'):
			validate_party_frozen_disabled("Customer", self.registration_customer)

		if self.get('registration_customer') and self.get('financer') and self.registration_customer == self.financer:
			frappe.throw(_("Registration Customer and Financer cannot be the same"))

	def validate_vehicle_unregistered(self):
		if self.vehicle:
			license_plate = frappe.db.get_value("Vehicle", self.vehicle, "license_plate")
			if license_plate:
				frappe.throw(_("{0} is already registered: {1}")
					.format(frappe.get_desk_link("Vehicle", self.vehicle), license_plate))

	def validate_pricing_components(self):
		validate_disabled_component(self.get('customer_charges'))
		validate_disabled_component(self.get('authority_charges'))

		validate_duplicate_components(self.get('customer_charges'))
		validate_duplicate_components(self.get('authority_charges'))

		validate_component_type("Registration", self.get('customer_charges'))
		validate_component_type("Registration", self.get('authority_charges'))

	def validate_agent_mandatory(self):
		if not self.agent:
			frappe.throw(_("Please set Agent first"))

	def validate_account_mandatory(self):
		if not self.customer_account:
			frappe.throw(_("Customer Receivable Account is mandatory"))
		if not self.agent_account and self.agent:
			frappe.throw(_("Agent Payable Account is mandatory"))
		if not self.authority_charges_account and cint(self.use_sales_invoice):
			frappe.throw(_("Authority Charges Account is mandatory"))

		if not self.customer_charges_item and cint(self.use_sales_invoice):
			frappe.throw(_("Customer Charges Item is mandatory"))
		if not self.authority_charges_item and cint(self.use_sales_invoice):
			frappe.throw(_("Authority Charges Item is mandatory"))

	def set_missing_accounts(self):
		if not self.customer_account:
			self.customer_account = frappe.get_cached_value("Vehicles Settings", None, "registration_customer_account")
		if not self.agent_account:
			self.agent_account = frappe.get_cached_value("Vehicles Settings", None, "registration_agent_account")
		if not self.authority_charges_account:
			self.authority_charges_account = frappe.get_cached_value("Vehicles Settings", None, "registration_authority_charges_account")

		if not self.customer_charges_item and cint(self.use_sales_invoice):
			self.customer_charges_item = frappe.get_cached_value("Vehicles Settings", None, "registration_customer_charges_item")
		if not self.authority_charges_item and cint(self.use_sales_invoice):
			self.authority_charges_item = frappe.get_cached_value("Vehicles Settings", None, "registration_authority_charges_item")

	def calculate_totals(self):
		calculate_total_price(self, 'customer_charges', 'customer_total')
		calculate_total_price(self, 'authority_charges', 'authority_total')
		calculate_total_price(self, 'agent_charges', 'agent_total')

		self.margin_amount = flt(self.customer_total - self.authority_total - self.agent_total,
			self.precision('margin_amount'))

		self.customer_authority_payment = 0
		for d in self.customer_authority_instruments:
			self.round_floats_in(d, ['instrument_amount'])
			self.customer_authority_payment += d.instrument_amount
		self.customer_authority_payment = flt(self.customer_authority_payment, self.precision('customer_authority_payment'))

		self.calculate_sales_team_contribution(self.get('customer_total'))

	def calculate_outstanding_amount(self):
		if self.docstatus == 0:
			self.customer_payment = 0
			self.customer_closed_amount = 0

			self.authority_payment = 0

			self.agent_payment = 0
			self.agent_closed_amount = 0
		else:
			gl_values = self.get_values_from_gl_entries()
			self.update(gl_values)

		if cint(self.use_sales_invoice):
			self.customer_outstanding = self.get_invoice_outstanding_amount()
		else:
			self.customer_outstanding = flt(self.customer_total) - flt(self.customer_payment) - flt(self.customer_authority_payment)

		self.authority_outstanding = flt(self.authority_total) - flt(self.authority_payment) - flt(self.customer_authority_payment)
		self.agent_outstanding = flt(self.agent_total) - flt(self.agent_payment)

	def get_values_from_gl_entries(self):
		args = {
			'vehicle_registration_order': self.name,
			'customer': self.customer,
			'customer_account': self.customer_account,
			'agent': self.agent,
			'agent_account': self.agent_account,
			'authority_charges_account': cstr(self.authority_charges_account),
			'customer_charges_item': cstr(self.customer_charges_item),
		}

		customer_payment = frappe.db.sql("""
			select sum(gle.credit-gle.debit) as amount
			from `tabGL Entry` gle
			left join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
			left join `tabPayment Entry` pe on gle.voucher_type = 'Payment Entry' and gle.voucher_no = pe.name
			where (jv.vehicle_registration_purpose = 'Customer Payment' or pe.payment_type = 'Receive')
				and gle.against_voucher_type = 'Vehicle Registration Order'
				and gle.against_voucher = %(vehicle_registration_order)s
				and gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s
		""", args)
		customer_payment = flt(customer_payment[0][0]) if customer_payment else 0

		if cint(self.use_sales_invoice):
			invoice_payment = frappe.db.sql("""
				select sum(gle.credit-gle.debit) as amount
				from `tabGL Entry` gle
				inner join `tabSales Invoice` inv on gle.against_voucher = inv.name and gle.against_voucher_type = 'Sales Invoice'
				where gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s
					and inv.vehicle_registration_order = %(vehicle_registration_order)s
			""", args)

			invoice_payment = flt(invoice_payment[0][0]) if invoice_payment else 0
			customer_payment += invoice_payment

		authority_payment = frappe.db.sql("""
			select sum(gle.debit-gle.credit) as amount
			from `tabGL Entry` gle
			inner join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
			where jv.vehicle_registration_purpose = 'Authority Payment'
				and gle.against_voucher_type = 'Vehicle Registration Order'
				and gle.against_voucher = %(vehicle_registration_order)s
				and (
					(gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s)
					or gle.account = %(authority_charges_account)s
				)
		""", args)
		authority_payment = flt(authority_payment[0][0]) if authority_payment else 0

		customer_closed_amount = frappe.db.sql("""
			select sum(gle.debit-gle.credit) as amount
			from `tabGL Entry` gle
			inner join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
			where jv.vehicle_registration_purpose = 'Closing Entry'
				and gle.against_voucher_type = 'Vehicle Registration Order'
				and gle.against_voucher = %(vehicle_registration_order)s
				and gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s
		""", args)
		customer_closed_amount = flt(customer_closed_amount[0][0]) if customer_closed_amount else 0

		if cint(self.use_sales_invoice):
			invoice_closed_amount = frappe.db.sql("""
				select sum(item.base_net_amount)
				from `tabSales Invoice Item` item
				inner join `tabSales Invoice` inv on inv.name = item.parent
				where inv.docstatus = 1 and item.item_code = %(customer_charges_item)s
					and inv.vehicle_registration_order = %(vehicle_registration_order)s
			""", args)
			invoice_closed_amount = flt(invoice_closed_amount[0][0]) if invoice_closed_amount else 0
			customer_closed_amount += invoice_closed_amount

		if self.agent and self.agent_account:
			agent_payment = frappe.db.sql("""
				select sum(gle.debit-gle.credit) as amount
				from `tabGL Entry` gle
				left join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
				left join `tabPayment Entry` pe on gle.voucher_type = 'Payment Entry' and gle.voucher_no = pe.name
				where (jv.vehicle_registration_purpose = 'Agent Payment' or pe.payment_type = 'Pay')
					and gle.against_voucher_type = 'Vehicle Registration Order'
					and gle.against_voucher = %(vehicle_registration_order)s
					and gle.account = %(agent_account)s and gle.party_type = 'Supplier' and gle.party = %(agent)s
			""", args)
			agent_payment = flt(agent_payment[0][0]) if agent_payment else 0

			agent_closed_amount = frappe.db.sql("""
				select sum(gle.credit-gle.debit) as amount
				from `tabGL Entry` gle
				inner join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
				where jv.vehicle_registration_purpose = 'Closing Entry'
					and gle.against_voucher_type = 'Vehicle Registration Order'
					and gle.against_voucher = %(vehicle_registration_order)s
					and gle.account = %(agent_account)s and gle.party_type = 'Supplier' and gle.party = %(agent)s
			""", args)
			agent_closed_amount = flt(agent_closed_amount[0][0]) if agent_closed_amount else 0
		else:
			agent_payment = 0
			agent_closed_amount = 0

		return frappe._dict({
			'customer_payment': customer_payment,
			'customer_closed_amount': customer_closed_amount,
			'authority_payment': authority_payment,
			'agent_payment': agent_payment,
			'agent_closed_amount': agent_closed_amount,
		})

	def get_invoice_outstanding_amount(self):
		outstanding_amount = frappe.db.sql("""
			select sum(outstanding_amount)
			from `tabSales Invoice`
			where docstatus = 1 and vehicle_registration_order = %s
		""", self.name)
		outstanding_amount = flt(outstanding_amount[0][0]) if outstanding_amount else 0
		return outstanding_amount

	def get_customer_payments(self):
		args = {
			'vehicle_registration_order': self.name,
			'customer': self.customer,
			'customer_account': self.customer_account,
		}

		self.customer_payments = frappe.db.sql("""
			select gle.posting_date as date, gle.credit-gle.debit as amount, gle.reference_no
			from `tabGL Entry` gle
			left join `tabJournal Entry` jv on gle.voucher_type = 'Journal Entry' and gle.voucher_no = jv.name
			left join `tabPayment Entry` pe on gle.voucher_type = 'Payment Entry' and gle.voucher_no = pe.name
			where (jv.vehicle_registration_purpose = 'Customer Payment' or pe.payment_type = 'Receive')
				and gle.against_voucher_type = 'Vehicle Registration Order'
				and gle.against_voucher = %(vehicle_registration_order)s
				and gle.account = %(customer_account)s and gle.party_type = 'Customer' and gle.party = %(customer)s
			order by gle.posting_date
		""", args, as_dict=1)

		self.all_customer_payments = self.customer_payments.copy()
		for d in self.customer_authority_instruments:
			self.all_customer_payments.append(frappe._dict({
				'date': d.instrument_date,
				'amount': d.instrument_amount,
				'reference_no': d.instrument_no,
			}))

		self.all_customer_payments = sorted(self.all_customer_payments, key=lambda d: getdate(d.date))

	def validate_amounts(self):
		for field in ['customer_total', 'authority_total', 'agent_total']:
			self.validate_value(field, '>=', 0)

		for d in self.customer_authority_instruments:
			d.validate_value('instrument_amount', '>', 0)

	def get_unclosed_customer_amount(self):
		customer_margin = flt(flt(self.customer_total) - flt(self.authority_total),
			self.precision('customer_total'))
		unclosed_customer_amount = flt(customer_margin - flt(self.customer_closed_amount),
			self.precision('customer_total'))
		return unclosed_customer_amount

	def get_unclosed_agent_amount(self):
		unclosed_agent_amount = flt(flt(self.agent_total) - flt(self.agent_closed_amount),
			self.precision('agent_total'))
		return unclosed_agent_amount

	def get_unclosed_income_amount(self):
		unclosed_customer_amount = self.get_unclosed_customer_amount()
		unclosed_agent_amount = self.get_unclosed_agent_amount()

		unclosed_income_amount = flt(unclosed_customer_amount - unclosed_agent_amount,
			self.precision('margin_amount'))
		return unclosed_income_amount

	def is_unclosed(self, ignore_customer_outstanding=False):
		return self.get_unclosed_customer_amount()\
			or self.get_unclosed_agent_amount()\
			or self.get_unclosed_income_amount()\
			or (self.customer_outstanding and not ignore_customer_outstanding)\
			or self.authority_outstanding

	def set_payment_status(self, update=False):
		self.calculate_outstanding_amount()

		if update:
			self.db_set({
				'customer_payment': self.customer_payment,
				'customer_outstanding': self.customer_outstanding,
				'customer_closed_amount': self.customer_closed_amount,
				'authority_payment': self.authority_payment,
				'authority_outstanding': self.authority_outstanding,
				'agent_payment': self.agent_payment,
				'agent_outstanding': self.agent_outstanding,
				'agent_closed_amount': self.agent_closed_amount,
			})

	def set_invoice_status(self, update=False):
		vehicle_invoice = None
		vehicle_invoice_issue = None
		vehicle_invoice_return = None
		vehicle_invoice_delivery = None

		if self.vehicle:
			vehicle_invoice = frappe.db.get_all("Vehicle Invoice", {"vehicle": self.vehicle, "docstatus": 1},
				['name', 'status', 'issued_for'], order_by="posting_date desc, creation desc")

			vehicle_invoice_delivery = frappe.db.get_all("Vehicle Invoice Delivery",
				{"vehicle": self.vehicle, "docstatus": 1, "is_copy": 0},
				['name', 'posting_date'], order_by="posting_date desc, creation desc")

			vehicle_invoice_issue = frappe.db.sql("""
				select m.name, m.posting_date
				from `tabVehicle Invoice Movement Detail` d
				inner join `tabVehicle Invoice Movement` m on m.name = d.parent
				where m.docstatus = 1 and d.vehicle = %s and m.purpose = 'Issue' and m.issued_for = 'Registration'
				order by m.posting_date desc, m.creation desc
			""", self.vehicle, as_dict=1)

			vehicle_invoice_return = frappe.db.sql("""
				select m.name, m.posting_date
				from `tabVehicle Invoice Movement Detail` d
				inner join `tabVehicle Invoice Movement` m on m.name = d.parent
				where m.docstatus = 1 and d.vehicle = %s and m.purpose = 'Return' and m.issued_for = 'Registration'
				order by m.posting_date desc, m.creation desc
			""", self.vehicle, as_dict=1)

		vehicle_invoice = vehicle_invoice[0] if vehicle_invoice else frappe._dict()
		vehicle_invoice_issue = vehicle_invoice_issue[0] if vehicle_invoice_issue else frappe._dict()
		vehicle_invoice_return = vehicle_invoice_return[0] if vehicle_invoice_return else frappe._dict()
		vehicle_invoice_delivery = vehicle_invoice_delivery[0] if vehicle_invoice_delivery else frappe._dict()

		if vehicle_invoice:
			self.invoice_status = vehicle_invoice.status
			self.invoice_issued_for = vehicle_invoice.issued_for if vehicle_invoice.status == "Issued" else None
			self.invoice_issue_date = vehicle_invoice_issue.posting_date
			self.invoice_return_date = vehicle_invoice_return.posting_date
			self.invoice_delivered_date = vehicle_invoice_delivery.posting_date
		else:
			self.invoice_status = "Not Received"
			self.invoice_issued_for = None
			self.invoice_issue_date = None
			self.invoice_return_date = None
			self.invoice_delivered_date = None

		if update:
			self.db_set({
				"invoice_status": self.invoice_status,
				"invoice_issued_for": self.invoice_issued_for,
				"invoice_issue_date": self.invoice_issue_date,
				"invoice_return_date": self.invoice_return_date,
				"invoice_delivered_date": self.invoice_delivered_date,
			})

	def set_registration_receipt_details(self, update=False):
		fields = ['name', 'vehicle_license_plate',
			'customer', 'customer_name', 'financer', 'financer_name', 'lessee_name',
			'posting_date', 'call_date']

		registration_receipt = frappe.db.get_all("Vehicle Registration Receipt",
			{"vehicle_registration_order": self.name, "docstatus": 1}, fields,
			order_by="posting_date desc, creation desc")

		if not registration_receipt and self.vehicle:
			registration_receipt = frappe.db.get_all("Vehicle Registration Receipt",
				{"vehicle": self.vehicle, "docstatus": 1}, fields,
				order_by="posting_date desc, creation desc")

		registration_receipt = registration_receipt[0] if registration_receipt else frappe._dict()

		if registration_receipt.customer:
			self.registration_customer = registration_receipt.customer
			self.registration_customer_name = registration_receipt.customer_name
			self.lessee_name = registration_receipt.lessee_name
			self.financer = registration_receipt.financer
			self.financer_name = registration_receipt.financer_name

		self.vehicle_license_plate = registration_receipt.vehicle_license_plate
		self.registration_receipt_date = registration_receipt.posting_date
		self.call_date = registration_receipt.call_date

		self.set_title()

		if update:
			self.db_set({
				"registration_customer": self.registration_customer,
				"registration_customer_name": self.registration_customer_name,
				"lessee_name": self.lessee_name,
				"financer": self.financer,
				"financer_name": self.financer_name,
				"vehicle_license_plate": self.vehicle_license_plate,
				"call_date": self.call_date,
				"registration_receipt_date": self.registration_receipt_date,
				"title": self.title,
			})

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status

		if self.docstatus == 2:
			self.status = "Cancelled"

		elif self.docstatus == 1:
			if self.invoice_status == "Not Received":
				self.status = "To Receive Invoice"

			elif self.customer_outstanding > 0 and not cint(self.use_sales_invoice):
				self.status = "To Receive Payment"

			elif self.authority_outstanding > 0:
				self.status = "To Pay Authority"

			elif not self.vehicle_license_plate:
				if self.invoice_status == "In Hand" and not self.invoice_issue_date:
					self.status = "To Issue Invoice"

				else:
					self.status = "To Receive Receipt"
			else:
				if cint(self.use_sales_invoice) and not self.sales_invoice_exists():
					self.status = "To Bill"

				elif self.is_unclosed(ignore_customer_outstanding=cint(self.use_sales_invoice)):
					self.status = "To Close Accounts"

				elif self.invoice_status == "Issued":
					self.status = "To Retrieve Invoice"

				elif self.invoice_status == "In Hand":
					self.status = "To Deliver Invoice"

				elif self.customer_outstanding > 0 and cint(self.use_sales_invoice):
					self.status = "To Receive Payment"

				else:
					self.status = "Completed"

		else:
			self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)


@frappe.whitelist()
def get_vehicle_registration_order_name(vehicle=None, vehicle_booking_order=None):
	return get_vehicle_registration_order(vehicle, vehicle_booking_order)


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


@frappe.whitelist()
def get_vehicle_registration_order_details(vehicle_registration_order, get_customer=False, get_vehicle=False,
		get_vehicle_booking_order=False):
	details = frappe._dict()
	if vehicle_registration_order:
		details = frappe.db.get_value("Vehicle Registration Order", vehicle_registration_order, [
			'agent', 'agent_name',
			'customer', 'customer_name',
			'registration_customer', 'registration_customer_name',
			'financer', 'financer_name', 'lessee_name',
			'vehicle_booking_order',
			'vehicle', 'item_code', 'item_name',
			'vehicle_chassis_no', 'vehicle_engine_no', 'vehicle_license_plate',
		], as_dict=1) or frappe._dict()

	out = frappe._dict()

	if details:
		out.agent = details.agent
		out.agent_name = details.agent_name

		if cint(get_customer) and details.registration_customer:
			out.customer = details.registration_customer
			out.financer = details.financer
			out.registration_customer_name = details.registration_customer_name

		if cint(get_vehicle_booking_order):
			out.vehicle_booking_order = details.vehicle_booking_order

		if cint(get_vehicle):
			out.vehicle = details.vehicle
			out.item_code = details.item_code
			out.item_name = details.item_name
			out.vehicle_chassis_no = details.vehicle_chassis_no
			out.vehicle_engine_no = details.vehicle_engine_no
			out.vehicle_license_plate = details.vehicle_license_plate

	return out


@frappe.whitelist()
def get_journal_entry(vehicle_registration_order, purpose):
	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)
	vro_customer_name = vro.registration_customer_name or vro.customer_name

	if vro.docstatus != 1:
		frappe.throw(_("Vehicle Registration Order must be submitted"))

	jv = frappe.new_doc("Journal Entry")
	jv.company = vro.company
	jv.cost_center = frappe.get_cached_value("Vehicles Settings", None, 'registration_cost_center')\
		or erpnext.get_default_cost_center(vro.company)

	jv.vehicle_booking_order = vro.vehicle_booking_order
	jv.applies_to_vehicle = vro.vehicle

	jv.update(get_fetch_values(jv.doctype, "applies_to_vehicle", jv.applies_to_vehicle))
	jv.update(get_fetch_values(jv.doctype, "vehicle_booking_order", jv.vehicle_booking_order))

	jv.vehicle_registration_purpose = purpose

	if purpose == "Customer Payment":
		add_journal_entry_row(jv, vro.customer_outstanding)
		add_journal_entry_row(jv, -1 * vro.customer_outstanding, vro.customer_account, 'Customer', vro.customer, vro.name)
	elif purpose == "Authority Payment":
		if cint(vro.use_sales_invoice):
			add_journal_entry_row(jv, vro.authority_outstanding, vro.authority_charges_account,
				vehicle_registration_order=vro.name, remarks=vro_customer_name)
		else:
			add_journal_entry_row(jv, vro.authority_outstanding, vro.customer_account, 'Customer', vro.customer, vro.name)

		add_journal_entry_row(jv, -1 * vro.authority_outstanding)
	elif purpose == "Agent Payment":
		vro.validate_agent_mandatory()
		add_journal_entry_row(jv, vro.agent_outstanding, vro.agent_account, 'Supplier', vro.agent, vro.name,
			remarks=vro_customer_name)
		add_journal_entry_row(jv, -1 * vro.agent_outstanding)
	elif purpose == "Closing Entry":
		unclosed_customer_amount = vro.get_unclosed_customer_amount()
		unclosed_agent_amount = vro.get_unclosed_agent_amount()
		unclosed_income_amount = vro.get_unclosed_income_amount()

		if unclosed_customer_amount:
			add_journal_entry_row(jv, unclosed_customer_amount, vro.customer_account, 'Customer', vro.customer, vro.name)

		if unclosed_agent_amount:
			vro.validate_agent_mandatory()

			if not flt(vro.agent_closed_amount):
				for d in vro.agent_charges:
					if flt(d.component_amount):
						remarks = vro_customer_name
						if d.component and d.component_type:
							remarks = _(d.component_type)

						add_journal_entry_row(jv, -1 * flt(d.component_amount), vro.agent_account,
							'Supplier', vro.agent, vro.name, remarks=remarks)
			else:
				add_journal_entry_row(jv, -1 * unclosed_agent_amount, vro.agent_account, 'Supplier', vro.agent, vro.name)

		if unclosed_income_amount:
			registration_income_account = frappe.get_cached_value("Vehicles Settings", None, 'registration_income_account')
			add_journal_entry_row(jv, -1 * unclosed_income_amount, registration_income_account)
	else:
		frappe.throw(_("Invalid Purpose"))

	jv.set_exchange_rate()
	jv.set_amounts_in_company_currency()
	jv.set_total_debit_credit()
	jv.set_party_name()

	return jv


@frappe.whitelist()
def get_agent_payment_voucher(names):
	if not frappe.has_permission("Journal Entry", "write"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	if isinstance(names, string_types):
		names = json.loads(names)

	total_amount = 0
	company = None

	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = frappe.utils.nowdate()
	jv.vehicle_registration_purpose = 'Agent Payment'

	visited = set()

	for name in names:
		if name in visited or not name:
			continue
		else:
			visited.add(name)

		vro = frappe.get_doc("Vehicle Registration Order", name)

		if vro.docstatus != 1 or not vro.agent:
			continue

		if not company:
			company = vro.company
			jv.company = company
		elif vro.company != company:
			continue

		row = add_journal_entry_row(jv, vro.agent_outstanding, vro.agent_account, 'Supplier', vro.agent, vro.name,
			remarks=vro.registration_customer_name or vro.customer_name)
		row.vehicle_booking_order = vro.vehicle_booking_order
		row.applies_to_vehicle = vro.vehicle
		row.update(get_fetch_values(row.doctype, "applies_to_vehicle", row.applies_to_vehicle))

		total_amount += flt(vro.agent_outstanding)

	if not total_amount:
		frappe.throw(_("No Vehicle Registration Order selected"))

	add_journal_entry_row(jv, -1 * total_amount)

	jv.cost_center = frappe.get_cached_value("Vehicles Settings", None, 'registration_cost_center')
	if not jv.cost_center and company:
		jv.cost_center = erpnext.get_default_cost_center(company)

	jv.set_amounts_in_company_currency()
	jv.set_total_debit_credit()
	jv.set_party_name()

	return jv


def add_journal_entry_row(jv, amount, account=None, party_type=None, party=None, vehicle_registration_order=None,
		remarks=None):
	row = jv.append('accounts')
	row.account = account
	row.debit_in_account_currency = flt(amount) if flt(amount) > 0 else 0
	row.credit_in_account_currency = -flt(amount) if flt(amount) < 0 else 0
	row.party_type = party_type
	row.party = party
	row.user_remark = remarks

	if vehicle_registration_order:
		row.reference_type = "Vehicle Registration Order"
		row.reference_name = vehicle_registration_order

	return row


@frappe.whitelist()
def get_invoice_movement(vehicle_registration_order, purpose):
	if purpose not in ['Issue', 'Return']:
		frappe.throw(_("Invalid Purpose"))

	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)

	if vro.docstatus != 1:
		frappe.throw(_("Vehicle Registration Order must be submitted"))

	invm = frappe.new_doc("Vehicle Invoice Movement")
	invm.company = vro.company

	invm.purpose = purpose
	invm.issued_for = "Registration"
	invm.agent = vro.agent

	row = invm.append('invoices')
	row.vehicle_registration_order = vro.name
	row.vehicle_booking_order = vro.vehicle_booking_order
	row.vehicle = vro.vehicle

	invm.run_method("set_missing_values")

	return invm


@frappe.whitelist()
def get_invoice_delivery(vehicle_registration_order):
	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)

	if vro.docstatus != 1:
		frappe.throw(_("Vehicle Registration Order must be submitted"))

	delivery = frappe.new_doc("Vehicle Invoice Delivery")
	delivery.company = vro.company
	delivery.vehicle = vro.vehicle
	delivery.vehicle_booking_order = vro.vehicle_booking_order
	delivery.customer = vro.financer if vro.financer else vro.registration_customer
	delivery.customer_name = vro.financer_name if vro.financer else vro.registration_customer_name

	delivery.run_method("set_missing_values")

	return delivery


@frappe.whitelist()
def get_transfer_letter(vehicle_registration_order):
	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)

	if vro.docstatus != 1:
		frappe.throw(_("Vehicle Registration Order must be submitted"))

	transfer = frappe.new_doc("Vehicle Transfer Letter")
	transfer.company = vro.company
	transfer.vehicle_registration_order = vro.name
	transfer.vehicle = vro.vehicle
	transfer.vehicle_booking_order = vro.vehicle_booking_order
	transfer.customer = vro.registration_customer or vro.customer
	transfer.territory = vro.territory

	transfer.run_method("set_missing_values")

	return transfer


@frappe.whitelist()
def get_registration_receipt(vehicle_registration_order):
	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)

	if vro.docstatus != 1:
		frappe.throw(_("Vehicle Registration Order must be submitted"))

	receipt = frappe.new_doc("Vehicle Registration Receipt")
	receipt.company = vro.company
	receipt.vehicle_registration_order = vro.name
	receipt.customer = vro.registration_customer or vro.customer
	receipt.financer = vro.financer
	receipt.agent = vro.agent
	receipt.vehicle = vro.vehicle
	receipt.vehicle_booking_order = vro.vehicle_booking_order

	receipt.run_method("set_missing_values")

	return receipt


@frappe.whitelist()
def make_sales_invoice(vehicle_registration_order):
	from erpnext.controllers.accounts_controller import get_taxes_and_charges, get_default_taxes_and_charges

	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)

	if vro.docstatus != 1:
		frappe.throw(_("Vehicle Registration Order must be submitted"))
	if not cint(vro.use_sales_invoice):
		frappe.throw(_("Sales Invoice not required"))

	cost_center = frappe.get_cached_value("Vehicles Settings", None, 'registration_cost_center')\
		or erpnext.get_default_cost_center(vro.company)

	invoice = frappe.new_doc("Sales Invoice")
	invoice.company = vro.company
	invoice.vehicle_registration_order = vro.name
	invoice.customer = vro.customer
	invoice.transaction_type = frappe.get_cached_value("Vehicles Settings", None, "registration_transaction_type")
	invoice.debit_to = vro.customer_account

	invoice.vehicle_booking_order = vro.vehicle_booking_order
	invoice.applies_to_vehicle = vro.vehicle
	invoice.update(get_fetch_values(invoice.doctype, "applies_to_vehicle", invoice.applies_to_vehicle))
	invoice.update(get_fetch_values(invoice.doctype, "applies_to_item", invoice.applies_to_item))

	customer_item = invoice.append('items')
	customer_item.item_code = vro.customer_charges_item
	customer_item.qty = 1
	customer_item.rate = vro.customer_total - vro.authority_total
	customer_item.cost_center = cost_center

	authority_item = invoice.append('items')
	authority_item.item_code = vro.authority_charges_item
	authority_item.qty = 1
	authority_item.rate = vro.authority_total
	authority_item.income_account = vro.authority_charges_account
	customer_item.cost_center = cost_center

	invoice.run_method("set_missing_values")

	if invoice.taxes_and_charges:
		invoice.set("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", invoice.taxes_and_charges))
	else:
		default_tax = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=invoice.company)
		invoice.update(default_tax)

	invoice.run_method("calculate_taxes_and_totals")
	invoice.run_method("set_payment_schedule")
	invoice.run_method("set_due_date")

	return invoice
