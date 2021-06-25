# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, getdate, cint
from erpnext.controllers.stock_controller import StockController
from erpnext.vehicles.vehicle_booking_controller import validate_vehicle_item
from erpnext.vehicles.doctype.vehicle.vehicle import warn_vehicle_reserved
from erpnext.accounts.party import validate_party_frozen_disabled
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
import json
from six import string_types


force_fields = [
	'customer_name', 'vehicle_owner_name', 'broker_name', 'transporter_name',
	'variant_of', 'variant_of_name',
	'tax_id', 'tax_cnic', 'tax_strn',
	'address_display', 'contact_display', 'contact_email', 'contact_mobile', 'contact_phone',
	'booking_customer_name', 'booking_address_display', 'booking_email', 'booking_mobile', 'booking_phone',
	'booking_tax_id', 'booking_tax_cnic', 'booking_tax_strn', 'receiver_contact_cnic', 'finance_type'
	'receiver_contact_display', 'receiver_contact_email', 'receiver_contact_mobile', 'receiver_contact_phone',
	'vehicle_chassis_no', 'vehicle_engine_no', 'vehicle_license_plate', 'vehicle_unregistered', 'vehicle_color'
]


class VehicleTransactionController(StockController):
	def validate(self):
		if self.meta.has_field('set_posting_time'):
			self.validate_posting_time()

		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)

		if self.get('supplier'):
			self.ensure_supplier_is_not_blocked()

		self.validate_date_with_fiscal_year()

		self.validate_vehicle_booking_order()
		self.validate_project()

		self.validate_party()
		self.validate_vehicle_item()
		self.validate_vehicle()

		self.clean_remarks()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def onload(self):
		if self.docstatus == 0:
			self.set_missing_values()

	def set_missing_values(self, for_validate=False):
		vehicle_booking_order_details = get_vehicle_booking_order_details(self.as_dict())
		for k, v in vehicle_booking_order_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

		vehicle_details = get_vehicle_details(self.as_dict(), get_vehicle_booking_order=False, warn_reserved=for_validate)
		for k, v in vehicle_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

		customer_details = get_customer_details(self.as_dict())
		for k, v in customer_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

		if self.get('item_code'):
			if not self.get('item_name'):
				self.item_name = frappe.get_cached_value("Item", self.item_code, 'item_name')

			self.variant_of = frappe.get_cached_value("Item", self.item_code, 'variant_of')
			self.variant_of_name = frappe.get_cached_value("Item", self.variant_of, 'item_name') if self.variant_of else None

	def update_stock_ledger(self):
		qty = 1 if self.doctype == "Vehicle Receipt" else -1

		# make sl entries for source warehouse first, then do for target warehouse
		sl_entries = [self.get_sl_entries(self, {
			"actual_qty": qty,
			"incoming_rate": 0,
			"party_type": "Supplier" if self.get('supplier') else "Customer",
			"party": self.supplier if self.get('supplier') else self.customer
		})]

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

	def validate_party(self):
		if not self.get('customer') and not self.get('supplier'):
			frappe.throw(_("Party is mandatory"))

		if self.get('supplier'):
			validate_party_frozen_disabled("Supplier", self.supplier)
		elif self.get('customer'):
			validate_party_frozen_disabled("Customer", self.customer)

	def validate_vehicle_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		validate_vehicle_item(item, validate_in_vehicle_booking=False)

	def validate_vehicle(self):
		if self.vehicle:
			vehicle_item_code = frappe.db.get_value("Vehicle", self.vehicle, "item_code")
			if vehicle_item_code != self.item_code:
				frappe.throw(_("Vehicle {0} is not {1}").format(self.vehicle, frappe.bold(self.item_name or self.item_code)))

			if not self.vehicle_booking_order:
				already_booked = frappe.db.get_value("Vehicle Booking Order", {'vehicle': self.vehicle, 'docstatus': 1})
				if already_booked:
					frappe.throw(_("Vehicle {0} is already booked against {1}. Please set Vehicle Booking Order to use this vehicle.")
						.format(self.vehicle, frappe.get_desk_link("Vehicle Booking Order", already_booked)))

		self.serial_no = self.vehicle

	def validate_vehicle_mandatory(self):
		if not self.vehicle:
			frappe.throw(_("Vehicle is mandatory"))

	def validate_vehicle_booking_order(self):
		if self.vehicle_booking_order:
			vbo = frappe.db.get_value("Vehicle Booking Order", self.vehicle_booking_order,
				['docstatus', 'status', 'customer', 'financer', 'supplier', 'item_code', 'vehicle', 'vehicle_delivered_date'],
				as_dict=1)

			if not vbo:
				frappe.throw(_("Vehicle Booking Order {0} does not exist").format(self.vehicle_booking_order))

			if self.get('customer'):
				# Customer must match with booking customer/financer or vehicle owner must be set (and match)
				if self.doctype == "Vehicle Delivery":
					if self.customer not in (vbo.customer, vbo.financer) and not self.vehicle_owner:
						frappe.throw(_("Customer (User) does not match in {0}. Please set Vehicle Owner if the User of the Vehicle is different from the Booking Customer.")
							.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

				elif self.doctype == 'Vehicle Transfer Letter':
					if self.customer in (vbo.customer, vbo.financer):
						frappe.throw(_("Customer (New Owner) cannot be the same as in {0} for transfer")
							.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

				else:
					if self.customer not in (vbo.customer, vbo.financer):
						frappe.throw(_("Customer does not match in {0}")
							.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.get('vehicle_owner'):
				if self.vehicle_owner not in (vbo.customer, vbo.financer):
					frappe.throw(_("Vehicle Owner does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.get('supplier'):
				if self.supplier != vbo.supplier:
					frappe.throw(_("Supplier does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.get('item_code'):
				if self.item_code != vbo.item_code:
					frappe.throw(_("Variant Item Code does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.get('vehicle'):
				if self.vehicle != vbo.vehicle:
					frappe.throw(_("Vehicle does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.doctype == "Vehicle Transfer Letter":
				if getdate(self.posting_date) < getdate(vbo.vehicle_delivered_date):
					frappe.throw(_("Transfer Date cannot be before Delivery Date {0}")
						.format(frappe.format(getdate(vbo.vehicle_delivered_date))))

			if vbo.docstatus != 1:
				frappe.throw(_("Cannot make {0} against {1} because it is not submitted")
					.format(self.doctype, frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if vbo.status == "Cancelled Booking":
				frappe.throw(_("Cannot make {0} against {1} because it is cancelled")
					.format(self.doctype, frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

	def validate_project(self):
		if self.get('project'):
			project = frappe.db.get_value("Project", self.project,
				['customer', 'applies_to_item', 'applies_to_vehicle'], as_dict=1)

			if not project:
				frappe.throw(_("Project {0} does not exist").format(self.project))

			if self.get('customer'):
				if project.customer and self.customer != project.customer:
					frappe.throw(_("Customer does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.get('item_code'):
				if project.applies_to_item and self.item_code != project.applies_to_item:
					frappe.throw(_("Variant Item Code does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

			if self.get('vehicle'):
				if project.applies_to_vehicle and self.vehicle != project.applies_to_vehicle:
					frappe.throw(_("Vehicle does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", self.vehicle_booking_order)))

	def update_vehicle_booking_order(self):
		if self.get('vehicle_booking_order'):
			vbo = frappe.get_doc("Vehicle Booking Order", self.vehicle_booking_order)
			vbo.check_cancelled(throw=True)

			if self.doctype in ['Vehicle Receipt', 'Vehicle Delivery']:
				vbo.update_delivery_status(update=True)
			elif self.doctype in ['Vehicle Invoice Receipt', 'Vehicle Invoice Delivery']:
				vbo.update_invoice_status(update=True)

			vbo.set_status(update=True)
			vbo.notify_update()


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	customer_details = frappe._dict()
	if args.customer:
		customer_details = frappe.get_cached_value("Customer", args.customer,
			['customer_name', 'tax_id', 'tax_cnic', 'tax_strn'], as_dict=1)

	owner_details = frappe._dict()
	if args.vehicle_owner:
		owner_details = frappe.get_cached_value("Customer", args.vehicle_owner,
			['customer_name'], as_dict=1)

	broker_details = frappe._dict()
	if args.broker:
		broker_details = frappe.get_cached_value("Customer", args.broker,
			['customer_name'], as_dict=1)

	transporter_details = frappe._dict()
	if args.transporter:
		transporter_details = frappe.get_cached_value("Supplier", args.transporter,
			['supplier_name'], as_dict=1)

	# Customer Name
	out.customer_name = customer_details.customer_name
	out.vehicle_owner_name = owner_details.customer_name
	out.broker_name = broker_details.customer_name
	out.transporter_name = transporter_details.supplier_name

	# Tax IDs
	out.tax_id = customer_details.tax_id
	out.tax_cnic = customer_details.tax_cnic
	out.tax_strn = customer_details.tax_strn

	# Customer Address
	out.customer_address = args.customer_address
	if not out.customer_address and args.customer:
		out.customer_address = get_default_address("Customer", args.customer)

	out.address_display = get_address_display(out.customer_address)

	# Contact
	out.contact_person = args.contact_person
	if not out.contact_person and args.customer:
		out.contact_person = get_default_contact("Customer", args.customer)

	out.update(get_contact_details(out.contact_person))

	out.receiver_contact = args.receiver_contact
	out.update(get_contact_details(out.receiver_contact, prefix='receiver_'))

	return out


@frappe.whitelist()
def get_vehicle_booking_order_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	booking_details = frappe._dict()
	if args.vehicle_booking_order:
		booking_details = frappe.db.get_value("Vehicle Booking Order", args.vehicle_booking_order,
			['customer', 'customer_name', 'financer', 'finance_type', 'supplier',
				'tax_id', 'tax_cnic', 'tax_strn',
				'address_display', 'contact_email', 'contact_mobile', 'contact_phone',
				'item_code', 'warehouse', 'vehicle',
				'bill_no', 'bill_date'], as_dict=1)

	out = frappe._dict()

	if booking_details:
		if args.doctype == "Vehicle Transfer Letter":
			out.vehicle_owner = booking_details.financer if booking_details.financer and booking_details.finance_type == 'Leased' \
				else booking_details.customer
		else:
			out.customer = booking_details.customer

		out.supplier = booking_details.supplier
		out.item_code = booking_details.item_code
		out.vehicle = booking_details.vehicle
		out.bill_no = booking_details.bill_no
		out.bill_date = booking_details.bill_date

		if args.doctype != "Vehicle Delivery":
			out.warehouse = booking_details.warehouse

	out.booking_customer_name = booking_details.customer_name
	out.booking_tax_id = booking_details.tax_id
	out.booking_tax_cnic = booking_details.tax_cnic
	out.booking_tax_strn = booking_details.tax_strn

	out.booking_address_display = booking_details.address_display
	out.booking_email = booking_details.contact_email
	out.booking_mobile = booking_details.contact_mobile
	out.booking_phone = booking_details.contact_phone

	out.finance_type = booking_details.finance_type

	if args.doctype != "Vehicle Transfer Letter":
		out.vehicle_owner = booking_details.financer if booking_details.financer and booking_details.finance_type == 'Leased' else None

	return out


@frappe.whitelist()
def get_vehicle_details(args, get_vehicle_booking_order=True, get_vehicle_invoice_receipt=False, warn_reserved=True):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	vehicle_details = frappe._dict()
	if args.vehicle:
		vehicle_details = frappe.db.get_value("Vehicle", args.vehicle, [
			'item_code', 'warehouse',
			'chassis_no', 'engine_no',
			'license_plate', 'unregistered',
			'warranty_no',
			'color', 'image'
		], as_dict=1)

		if not vehicle_details:
			frappe.throw(_("Vehicle {0} does not exist").format(args.vehicle))

	if vehicle_details:
		out.item_code = vehicle_details.item_code

	out.vehicle_chassis_no = vehicle_details.chassis_no
	out.vehicle_engine_no = vehicle_details.engine_no
	out.vehicle_license_plate = vehicle_details.license_plate
	out.vehicle_unregistered = vehicle_details.unregistered
	out.vehicle_color = vehicle_details.color
	out.vehicle_warranty_no = vehicle_details.warranty_no
	out.image = vehicle_details.image

	if vehicle_details.warehouse:
		out.warehouse = vehicle_details.warehouse

	if args.vehicle and get_vehicle_booking_order and not args.vehicle_booking_order:
		vehicle_booking_order = get_vehicle_booking_order_from_vehicle(args.vehicle)
		out.vehicle_booking_order = vehicle_booking_order

	if cint(get_vehicle_invoice_receipt):
		from erpnext.vehicles.doctype.vehicle_invoice_delivery.vehicle_invoice_delivery import get_vehicle_invoice_receipt,\
			get_vehicle_invoice_details
		out.vehicle_invoice_receipt = get_vehicle_invoice_receipt(args.vehicle)
		out.update(get_vehicle_invoice_details(out.vehicle_invoice_receipt))

	if warn_reserved and args.doctype == "Vehicle Delivery":
		warn_vehicle_reserved(args.vehicle, args.customer)

	return out


def get_vehicle_booking_order_from_vehicle(vehicle):
	return frappe.db.get_value("Vehicle Booking Order", {"vehicle": vehicle, "docstatus": 1})


@frappe.whitelist()
def get_contact_details(contact=None, prefix=None):
	from frappe.contacts.doctype.contact.contact import get_contact_details

	out = frappe._dict()

	prefix = cstr(prefix)

	contact_details = get_contact_details(contact) if contact else frappe._dict()
	out[prefix + 'contact_display'] = contact_details.get('contact_display')
	out[prefix + 'contact_mobile'] = contact_details.get('contact_mobile')
	out[prefix + 'contact_phone'] = contact_details.get('contact_phone')
	out[prefix + 'contact_email'] = contact_details.get('contact_email')
	out[prefix + 'contact_cnic'] = contact_details.get('contact_cnic')

	return out
