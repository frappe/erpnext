# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, getdate, cint
from erpnext.controllers.stock_controller import StockController
from erpnext.vehicles.utils import validate_vehicle_item
from erpnext.vehicles.doctype.vehicle.vehicle import warn_vehicle_reserved
from erpnext.accounts.party import validate_party_frozen_disabled
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.vehicles.doctype.vehicle_log.vehicle_log import make_odometer_log, odometer_log_exists, get_vehicle_odometer
import json
from six import string_types


force_fields = [
	'customer_name', 'vehicle_owner_name', 'broker_name', 'transporter_name',
	'variant_of', 'variant_of_name',
	'tax_id', 'tax_cnic', 'tax_strn',
	'address_display', 'contact_display', 'contact_email', 'contact_mobile', 'contact_phone', 'territory',
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

	def onload(self):
		if self.docstatus == 0:
			self.set_missing_values()

	def set_missing_values(self, doc=None, for_validate=False):
		self.set_vehicle_booking_order_details(doc, for_validate=for_validate)
		self.set_vehicle_details(doc, for_validate=for_validate)
		self.set_item_details(doc, for_validate=for_validate)
		self.set_customer_details(for_validate=for_validate)

	def set_vehicle_booking_order_details(self, doc=None, for_validate=False):
		args = self.as_dict()
		if doc:
			args.update(doc.as_dict())
			args.doctype = self.doctype
			args.name = self.name
		else:
			doc = self

		vehicle_booking_order_details = get_vehicle_booking_order_details(args)
		for k, v in vehicle_booking_order_details.items():
			if doc.meta.has_field(k) and (not doc.get(k) or k in force_fields):
				doc.set(k, v)

	def set_vehicle_details(self, doc=None, for_validate=False, update=False):
		args = self.as_dict()
		if doc:
			args.update(doc.as_dict())
			args.doctype = self.doctype
			args.name = self.name
		else:
			doc = self

		vehicle_details = get_vehicle_details(args, get_vehicle_booking_order=False, warn_reserved=for_validate)
		values = {}
		for k, v in vehicle_details.items():
			if doc.meta.has_field(k) and (not doc.get(k) or k in force_fields):
				if k == "vehicle_license_plate" and self.doctype == "Vehicle Registration Order":
					continue

				values[k] = v

		for k, v in values.items():
			doc.set(k, v)

		if update:
			doc.db_set(values)

	def set_item_details(self, doc=None, for_validate=False, force=False):
		if not doc:
			doc = self

		if doc.get('item_code'):
			if not doc.get('item_name') or force:
				doc.item_name = frappe.get_cached_value("Item", doc.item_code, 'item_name')

			doc.variant_of = frappe.get_cached_value("Item", doc.item_code, 'variant_of')
			doc.variant_of_name = frappe.get_cached_value("Item", doc.variant_of, 'item_name') if doc.variant_of else None

	def set_customer_details(self, for_validate=False):
		customer_details = get_customer_details(self.as_dict())
		for k, v in customer_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

	def update_stock_ledger(self):
		qty = 1 if self.doctype == "Vehicle Receipt" else -1
		if self.get('is_return'):
			qty = -1 * qty

		# make sl entries for source warehouse first, then do for target warehouse
		sl_entries = [self.get_sl_entries(self, {
			"actual_qty": qty,
			"incoming_rate": 0,
			"party_type": "Supplier" if self.get('supplier') else "Customer",
			"party": self.supplier if self.get('supplier') else self.customer
		})]

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

	def make_gl_entries(self, gl_entries=None, repost_future_gle=True, from_repost=False):
		pass

	def validate_party_mandatory(self):
		if not self.get('customer') and not self.get('supplier'):
			frappe.throw(_("Party is mandatory"))

	def validate_party(self):
		if self.get('supplier'):
			validate_party_frozen_disabled("Supplier", self.supplier)
		if self.get('agent'):
			validate_party_frozen_disabled("Supplier", self.agent)
		elif self.get('customer'):
			validate_party_frozen_disabled("Customer", self.customer)

	def validate_vehicle_item(self, doc=None):
		if not doc:
			doc = self

		item = frappe.get_cached_doc("Item", doc.item_code)
		validate_vehicle_item(item, validate_in_vehicle_booking=False)

	def validate_vehicle(self, doc=None):
		if not doc:
			doc = self

		if doc.get('vehicle'):
			vehicle_item_code = frappe.db.get_value("Vehicle", doc.vehicle, "item_code")
			if vehicle_item_code != doc.item_code:
				frappe.throw(_("Vehicle {0} is not {1}").format(doc.vehicle, frappe.bold(doc.item_name or doc.item_code)))

			if doc.meta.has_field('vehicle_booking_order') and not doc.get('vehicle_booking_order'):
				already_booked = get_vehicle_booking_order_from_vehicle(doc.vehicle, {
					'status': ['not in', ['Completed', 'Cancelled Booking']]
				})
				if already_booked:
					frappe.throw(_("Vehicle {0} is already booked against {1}. Please set Vehicle Booking Order to use this vehicle.")
						.format(doc.vehicle, frappe.get_desk_link("Vehicle Booking Order", already_booked)))

		if doc.meta.has_field('serial_no'):
			doc.serial_no = doc.vehicle

	def validate_vehicle_mandatory(self):
		if self.meta.has_field('vehicle') and not self.get('vehicle'):
			frappe.throw(_("Vehicle is mandatory"))

	def validate_vehicle_booking_order(self, doc=None):
		if not doc:
			doc = self

		if doc.get('vehicle_booking_order'):
			vbo = frappe.db.get_value("Vehicle Booking Order", doc.vehicle_booking_order, [
					'docstatus', 'status',
					'customer', 'financer', 'supplier',
					'item_code', 'vehicle',
					'vehicle_delivered_date', 'vehicle_received_date'
			], as_dict=1)

			if not vbo:
				frappe.throw(_("Vehicle Booking Order {0} does not exist").format(doc.vehicle_booking_order))

			if vbo.docstatus != 1:
				frappe.throw(_("Cannot make {0} against {1} because it is not submitted")
					.format(self.doctype, frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if vbo.status == "Cancelled Booking":
				frappe.throw(_("Cannot make {0} against {1} because it is cancelled")
					.format(self.doctype, frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if self.get('customer'):
				# Customer must match with booking customer/financer or vehicle owner must be set (and match)
				if self.doctype == "Vehicle Delivery":
					if self.customer not in (vbo.customer, vbo.financer) and not self.vehicle_owner:
						frappe.throw(_("Customer (User) does not match in {0}. Please set Vehicle Owner if the User of the Vehicle is different from the Booking Customer.")
							.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

				elif self.doctype == 'Vehicle Transfer Letter':
					if self.customer in (vbo.customer, vbo.financer):
						frappe.throw(_("Customer (New Owner) cannot be the same as in {0} for transfer")
							.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

				else:
					if self.customer not in (vbo.customer, vbo.financer):
						frappe.throw(_("Customer does not match in {0}")
							.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if self.get('vehicle_owner'):
				if self.vehicle_owner not in (vbo.customer, vbo.financer):
					frappe.throw(_("Vehicle Owner does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if self.get('supplier'):
				if self.supplier != vbo.supplier:
					frappe.throw(_("Supplier does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if doc.get('item_code'):
				if doc.item_code != vbo.item_code:
					frappe.throw(_("Variant Item Code does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if doc.meta.has_field('vehicle'):
				if cstr(doc.get('vehicle')) != cstr(vbo.get('vehicle')):
					frappe.throw(_("Vehicle does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if self.doctype == "Vehicle Transfer Letter":
				if getdate(self.posting_date) < getdate(vbo.vehicle_received_date):
					frappe.throw(_("Transfer Date cannot be before Receiving Date {0}")
						.format(frappe.format(getdate(vbo.vehicle_received_date)) if vbo.vehicle_received_date else ""))

			if self.doctype == "Vehicle Receipt" and not cint(self.get('is_return')) and vbo.vehicle_received_date:
				frappe.throw(_("Cannot create Vehicle Receipt against {0} because Vehicle has already been received")
					.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

			if self.doctype == "Vehicle Delivery" and cint(self.get('is_return')) and not vbo.vehicle_received_date:
				frappe.throw(_("Cannot create Vehicle Delivery Return against {0} because Vehicle has not yet been received")
					.format(frappe.get_desk_link("Vehicle Booking Order", doc.vehicle_booking_order)))

	def validate_project(self):
		if self.get('project'):
			project = frappe.db.get_value("Project", self.project,
				['customer', 'applies_to_item', 'applies_to_vehicle'], as_dict=1)

			if not project:
				frappe.throw(_("Project {0} does not exist").format(self.project))

			if self.get('customer'):
				if project.customer and self.customer != project.customer:
					frappe.throw(_("Customer does not match in {0}")
						.format(frappe.get_desk_link("Project", self.project)))

			if self.get('item_code'):
				if project.applies_to_item and self.item_code != project.applies_to_item:
					frappe.throw(_("Variant Item Code does not match in {0}")
						.format(frappe.get_desk_link("Project", self.project)))

			if self.get('vehicle'):
				if project.applies_to_vehicle and self.vehicle != project.applies_to_vehicle:
					frappe.throw(_("Vehicle does not match in {0}")
						.format(frappe.get_desk_link("Project", self.project)))

	def validate_vehicle_registration_order(self, doc=None):
		if not doc:
			doc = self

		if doc.get('vehicle_registration_order'):
			vro = frappe.db.get_value("Vehicle Registration Order", doc.vehicle_registration_order,
				['docstatus', 'agent', 'vehicle_booking_order', 'item_code', 'vehicle'], as_dict=1)

			if not vro:
				frappe.throw(_("Vehicle Registration Order {0} does not exist").format(doc.vehicle_registration_order))

			if vro.docstatus != 1:
				frappe.throw(_("Cannot make {0} against {1} because it is not submitted")
					.format(self.doctype,
					frappe.get_desk_link("Vehicle Registration Order", doc.vehicle_registration_order)))

			if self.meta.has_field('agent'):
				if cstr(self.agent) != cstr(vro.agent):
					frappe.throw(_("Agent does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Registration Order", doc.vehicle_registration_order)))

			if doc.get('item_code'):
				if doc.item_code != vro.item_code:
					frappe.throw(_("Variant Item Code does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Registration Order", doc.vehicle_registration_order)))

			if doc.get('vehicle'):
				if doc.vehicle != cstr(vro.vehicle):
					frappe.throw(_("Vehicle does not match in {0}")
						.format(frappe.get_desk_link("Vehicle Registration Order", doc.vehicle_registration_order)))

	def update_vehicle_booking_order_delivery(self, doc=None):
		if not doc:
			doc = self

		if doc.get('vehicle_booking_order'):
			vbo = frappe.get_doc("Vehicle Booking Order", doc.vehicle_booking_order)
			vbo.check_cancelled(throw=True)
			doc.validate_and_update_booking_vehicle_details(vbo, doc)
			vbo.update_delivery_status(update=True)
			vbo.set_status(update=True)
			vbo.notify_update()

	def update_vehicle_booking_order_invoice(self, doc=None):
		if not doc:
			doc = self

		vehicle_booking_order = self.get_vehicle_booking_order(doc)
		if vehicle_booking_order:
			vbo = frappe.get_doc("Vehicle Booking Order", vehicle_booking_order)
			vbo.check_cancelled(throw=True)
			doc.validate_and_update_booking_vehicle_details(vbo, doc)
			vbo.update_invoice_status(update=True)
			vbo.set_status(update=True)
			vbo.notify_update()

	def validate_and_update_booking_vehicle_details(self, vbo_doc, self_doc=None):
		if not self_doc:
			self_doc = self

		if self.docstatus == 2 or not self_doc.get('vehicle'):
			return

		fields = ['vehicle_color', 'vehicle_chassis_no', 'vehicle_engine_no']

		def get_changes(doc1, doc2, for_updating=False):
			changes = {}
			for f in fields:
				if doc1.get(f) and (for_updating or doc2.get(f)) and doc1.get(f) != doc2.get(f):
					if for_updating:
						changes[f] = doc1.get(f)
					else:
						changes[f] = (doc1.get(f), doc2.get(f))

			return changes

		def raise_inconsistent_details_error(changes, doc1, doc2):
			meta = frappe.get_meta(doc1.doctype)
			change_error_list = []
			for f, (doc1_val, doc2_val) in changes.items():
				label = meta.get_label(f)
				change_error_list.append(_("{0}: {1} in {2}, however, {3} in {4}")
					.format(frappe.bold(label), frappe.bold(doc1_val), doc1.doctype, frappe.bold(doc2_val), doc2.doctype))

			change_error_html = "".join(["<li>{0}</li>".format(d) for d in change_error_list])
			frappe.throw(_("""Vehicle details for {0} in {1} do not match with related document {2}<ul>{3}</ul>""")
				.format(frappe.get_desk_link('Vehicle', self_doc.vehicle),
					frappe.get_desk_link(doc1.doctype, doc1.name),
					frappe.get_desk_link(doc2.doctype, doc2.name),
					change_error_html))

		vehicle_receipt = frappe.get_all("Vehicle Receipt",
			fields=['name', "'Vehicle Receipt' as doctype"] + fields, filters={
				'vehicle': self_doc.vehicle,
				'docstatus': 1,
				'is_return': 0
			}, order_by='posting_date desc, creation desc', limit=1)
		vehicle_receipt = vehicle_receipt[0] if vehicle_receipt else None

		vehicle_invoice = frappe.get_all("Vehicle Invoice",
			fields=['name', "'Vehicle Invoice' as doctype"] + fields, filters={
				'vehicle': self_doc.vehicle,
				'docstatus': 1
			}, order_by='posting_date desc, creation desc', limit=1)
		vehicle_invoice = vehicle_invoice[0] if vehicle_invoice else None

		# Difference between Vehicle Receipt and Invoice
		if vehicle_receipt and vehicle_invoice:
			receipt_invoice_changes = get_changes(vehicle_receipt, vehicle_invoice)
			if receipt_invoice_changes:
				raise_inconsistent_details_error(receipt_invoice_changes, vehicle_receipt, vehicle_invoice)

		# Difference between current doc and first source document
		if self.doctype not in ['Vehicle Receipt', 'Vehicle Invoice']:
			validate_against = vehicle_receipt or vehicle_invoice
			if validate_against:
				current_doc_changes = get_changes(self_doc, validate_against)
				if current_doc_changes:
					raise_inconsistent_details_error(current_doc_changes, self_doc, validate_against)

		if vbo_doc.status != "Completed":
			# Update Changes in Vehicle Booking
			vbo_changes = get_changes(self_doc, vbo_doc, for_updating=True)
			if vbo_changes:
				vbo_doc.db_set(vbo_changes, notify=1)

			# Update Changes in Vehicle Registration
			from erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order import get_vehicle_registration_order
			vro_values = get_vehicle_registration_order(vehicle_booking_order=vbo_doc.name,
				fields=['name'] + fields, as_dict=1)
			if vro_values:
				vro_changes = get_changes(self_doc, vro_values, for_updating=True)
				if vro_changes:
					frappe.db.set_value("Vehicle Registration Order", vro_values.name, vro_changes, None, notify=1)

	def update_vehicle_booking_order_registration(self):
		vehicle_booking_order = self.get_vehicle_booking_order()
		if vehicle_booking_order:
			vbo = frappe.get_doc("Vehicle Booking Order", vehicle_booking_order)
			vbo.check_cancelled(throw=True)
			vbo.update_registration_status(update=True)
			vbo.set_status(update=True)
			vbo.notify_update()

	def update_vehicle_invoice(self, doc=None, update_vehicle=True):
		if not doc:
			doc = self

		if doc.get('vehicle_invoice'):
			vinvr = frappe.get_doc("Vehicle Invoice", doc.vehicle_invoice)
			vinvr.set_status(update=True, update_vehicle=update_vehicle)
			vinvr.notify_update()

	def update_vehicle_registration_order(self, doc=None):
		if not doc:
			doc = self

		vehicle_registration_order = self.get_vehicle_registration_order(doc)
		if vehicle_registration_order:
			vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)

			if self.doctype in ['Vehicle Invoice', 'Vehicle Invoice Delivery']:
				vro.update_invoice_status(update=True)

			vro.set_status(update=True)
			vro.notify_update()

	def get_vehicle_booking_order(self, doc=None):
		if not doc:
			doc = self

		vehicle_booking_order = doc.get('vehicle_booking_order')
		if not vehicle_booking_order and doc.get('vehicle'):
			vehicle_booking_order = get_vehicle_booking_order_from_vehicle(doc.vehicle)

		return vehicle_booking_order

	def get_vehicle_registration_order(self, doc=None):
		from erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order import get_vehicle_registration_order

		if not doc:
			doc = self

		vehicle_registration_order = doc.get('vehicle_registration_order')
		if not vehicle_registration_order and (doc.get('vehicle') or doc.get('vehicle_booking_order')):
			vehicle_registration_order = get_vehicle_registration_order(doc.get('vehicle'),
				doc.get('vehicle_booking_order'))

		return vehicle_registration_order

	def make_odometer_log(self):
		if self.meta.has_field('vehicle_log') and cint(self.get('vehicle_odometer')):
			if not odometer_log_exists(self.vehicle, self.vehicle_odometer):
				vehicle_log = make_odometer_log(self.vehicle, self.vehicle_odometer,
					date=self.get('posting_date') or self.get('transaction_date'))
				self.db_set('vehicle_log', vehicle_log)

	def cancel_odometer_log(self):
		if self.meta.has_field('vehicle_log') and self.get('vehicle_log'):
			doc = frappe.get_doc("Vehicle Log", self.vehicle_log)
			doc.flags.ignore_permissions = True
			doc.cancel()

			self.db_set('vehicle_log', None)


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	customer_details = frappe._dict()
	if args.customer:
		customer_details = frappe.get_cached_value("Customer", args.customer,
			['customer_name', 'tax_id', 'tax_cnic', 'tax_strn', 'territory'], as_dict=1)

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
	out.territory = customer_details.territory

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
def get_vehicle_details(args, get_vehicle_booking_order=True, get_vehicle_invoice=False, warn_reserved=True):
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

	if args.vehicle:
		out.vehicle_odometer = get_vehicle_odometer(args.vehicle, date=args.posting_date)

	if vehicle_details.warehouse:
		out.warehouse = vehicle_details.warehouse

	if args.vehicle and get_vehicle_booking_order and not args.vehicle_booking_order:
		status_filters = None
		if args.doctype in ('Vehicle Receipt', 'Vehicle Delivery'):
			if cint(args.is_return):
				status_filters = {'delivery_status': ['=', 'Delivered']}
			else:
				status_filters = {'delivery_status': ['!=', 'Delivered']}

		vehicle_booking_order = get_vehicle_booking_order_from_vehicle(args.vehicle, status_filters)
		if vehicle_booking_order:
			out.vehicle_booking_order = vehicle_booking_order

	if cint(get_vehicle_invoice):
		from erpnext.vehicles.doctype.vehicle_invoice.vehicle_invoice import get_vehicle_invoice,\
			get_vehicle_invoice_details
		out.vehicle_invoice = get_vehicle_invoice(args.vehicle)
		out.update(get_vehicle_invoice_details(out.vehicle_invoice))

	if warn_reserved and args.doctype == "Vehicle Delivery":
		warn_vehicle_reserved(args.vehicle, args.customer)

	return out


def get_vehicle_booking_order_from_vehicle(vehicle, filters=None, fieldname="name", as_dict=False):
	actual_filters = {
		"vehicle": vehicle,
		"docstatus": 1,
		"status": ['!=', 'Cancelled Booking']
	}
	if filters:
		actual_filters.update(filters)

	return frappe.db.get_value("Vehicle Booking Order", actual_filters, fieldname, as_dict=as_dict)


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
