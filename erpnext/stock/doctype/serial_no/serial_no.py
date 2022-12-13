# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from frappe.model.naming import make_autoname
from frappe.utils import cint, cstr, flt, add_days, nowdate, getdate
from erpnext.stock.get_item_details import get_reserved_qty_for_so
from frappe import _, ValidationError
from erpnext.controllers.stock_controller import StockController
from six.moves import map
from six import string_types


class SerialNoCannotCreateDirectError(ValidationError): pass
class SerialNoCannotCannotChangeError(ValidationError): pass
class SerialNoNotRequiredError(ValidationError): pass
class SerialNoRequiredError(ValidationError): pass
class SerialNoQtyError(ValidationError): pass
class SerialNoItemError(ValidationError): pass
class SerialNoWarehouseError(ValidationError): pass
class SerialNoBatchError(ValidationError): pass
class SerialNoNotExistsError(ValidationError): pass
class SerialNoDuplicateError(ValidationError): pass


class SerialNo(StockController):
	def __init__(self, *args, **kwargs):
		super(SerialNo, self).__init__(*args, **kwargs)
		self.via_stock_ledger = False

	def validate(self):
		if self.get("__islocal") and self.warehouse and not self.via_stock_ledger:
			frappe.throw(_("New Serial No cannot have Warehouse. Warehouse must be set by Stock Entry or Purchase Receipt"),
				SerialNoCannotCreateDirectError)

		self.validate_item()
		self.validate_warehouse()
		self.update_customer_from_sales_order()

		self.set_maintenance_status()
		self.set_status()

	def on_update(self):
		self.update_vehicle_reference()

	def before_rename(self, old, new, merge=False):
		if merge:
			frappe.throw(_("Sorry, Serial Nos cannot be merged"))

	def after_rename(self, old, new, merge=False):
		"""rename serial_no text fields"""
		docfields = frappe.db.sql("""
			select distinct parent, fieldname
			from tabDocField
			where fieldname in ('serial_no', 'rejected_serial_no', 'current_serial_no')
				and fieldtype in ('Text', 'Small Text', 'Long Text')
		""")

		for dt, fieldname in docfields:
			rows = frappe.db.sql("""
				select name, `{0}`
				from `tab{1}`
				where `{0}` like {2}
			""".format(fieldname, dt, frappe.db.escape('%' + old + '%')))

			for row_name, serial_text in rows:
				serial_nos = map(lambda i: new if i.upper() == old.upper() else i, get_serial_nos(serial_text))
				frappe.db.sql("""
					update `tab{0}`
					set `{1}` = %s
					where name = %s
				""".format(dt, fieldname), ('\n'.join(list(serial_nos)), row_name))

	def set_status(self):
		if self.delivery_document_type:
			self.status = "Delivered"
		elif self.warranty_expiry_date and getdate(self.warranty_expiry_date) <= getdate(nowdate()):
			self.status = "Expired"
		elif not self.warehouse:
			self.status = "Inactive"
		else:
			self.status = "Active"

	def set_maintenance_status(self):
		if not self.warranty_expiry_date and not self.amc_expiry_date:
			self.maintenance_status = None

		if self.warranty_expiry_date and getdate(self.warranty_expiry_date) < getdate(nowdate()):
			self.maintenance_status = "Out of Warranty"

		if self.amc_expiry_date and getdate(self.amc_expiry_date) < getdate(nowdate()):
			self.maintenance_status = "Out of AMC"

		if self.amc_expiry_date and getdate(self.amc_expiry_date) >= getdate(nowdate()):
			self.maintenance_status = "Under AMC"

		if self.warranty_expiry_date and getdate(self.warranty_expiry_date) >= getdate(nowdate()):
			self.maintenance_status = "Under Warranty"

	def validate_warehouse(self):
		if not self.get("__islocal"):
			item_code, warehouse = frappe.db.get_value("Serial No",
				self.name, ["item_code", "warehouse"])
			if not self.via_stock_ledger and item_code != self.item_code and not self.flags.allow_change_item_code:
				frappe.throw(_("Item Code cannot be changed for Serial No."),
					SerialNoCannotCannotChangeError)
			if not self.via_stock_ledger and warehouse != self.warehouse:
				frappe.throw(_("Warehouse cannot be changed for Serial No."),
					SerialNoCannotCannotChangeError)

	def validate_item(self):
		"""
			Validate whether serial no is required for this item
		"""
		item = frappe.get_cached_doc("Item", self.item_code)

		if not item.has_serial_no:
			frappe.throw(_("Item {0} is not setup for Serial Nos. Check Item master").format(self.item_code))

		self.item_group = item.item_group
		self.description = item.description
		self.item_name = item.item_name
		self.brand = item.brand
		self.is_vehicle = item.is_vehicle
		self.warranty_period = item.warranty_period

	def update_customer_from_sales_order(self):
		if self.sales_order and not (self.delivery_document_type and self.delivery_document_no):
			so = frappe.db.get_value("Sales Order", self.sales_order, ["customer", "docstatus"], as_dict=1)
			if so.docstatus == 2:
				frappe.throw(_("Cannot set Sales Order as {0} because it is cancelled").format(self.sales_order))

			self.customer = so.customer

	def set_purchase_details(self, purchase_sle):
		if purchase_sle:
			self.purchase_document_type = purchase_sle.voucher_type
			self.purchase_document_no = purchase_sle.voucher_no
			self.purchase_date = purchase_sle.posting_date
			self.purchase_time = purchase_sle.posting_time
			self.purchase_rate = purchase_sle.incoming_rate

			# If sales return entry
			if self.purchase_document_type == 'Delivery Note':
				self.sales_invoice = None
		else:
			for fieldname in ("purchase_document_type", "purchase_document_no",
				"purchase_date", "purchase_time", "purchase_rate"):
					self.set(fieldname, None)

	def set_sales_details(self, delivery_sle):
		if delivery_sle:
			self.delivery_document_type = delivery_sle.voucher_type
			self.delivery_document_no = delivery_sle.voucher_no
			self.delivery_date = delivery_sle.posting_date or self.delivery_date
			self.delivery_time = delivery_sle.posting_time
			self.is_reserved = 0

			if self.warranty_period:
				self.warranty_expiry_date = add_days(self.delivery_date, cint(self.warranty_period))
		else:
			for fieldname in ("delivery_document_type", "delivery_document_no",
				"delivery_date", "delivery_time",
				"warranty_expiry_date"):
					self.set(fieldname, None)

	def set_party_details(self, purchase_sle, delivery_sle):
		purchase_details = None
		if purchase_sle:
			if purchase_sle.voucher_type in ("Purchase Receipt", "Purchase Invoice"):
				purchase_details = frappe.db.get_value(purchase_sle.voucher_type, purchase_sle.voucher_no,
					["supplier", "supplier_name"], as_dict=1)
			elif purchase_sle.voucher_type == "Vehicle Receipt":
				purchase_details = frappe.db.get_value(purchase_sle.voucher_type, purchase_sle.voucher_no,
					["supplier", "supplier_name", "customer", "customer_name"], as_dict=1)

			if purchase_details:
				self.update(purchase_details)
		else:
			self.supplier = None
			self.supplier_name = None

		sales_details = None
		if delivery_sle:
			if delivery_sle.voucher_type in ("Delivery Note", "Sales Invoice"):
				sales_details = frappe.db.get_value(delivery_sle.voucher_type, delivery_sle.voucher_no,
					["customer", "customer_name"], as_dict=1)
			elif delivery_sle.voucher_type == "Vehicle Delivery":
				sales_details = frappe.db.get_value(delivery_sle.voucher_type, delivery_sle.voucher_no,
					["customer", "customer_name", "vehicle_owner", "vehicle_owner_name"], as_dict=1)

			if sales_details:
				self.update(sales_details)
		else:
			if purchase_details:
				self.customer = purchase_details.get('customer')
				self.customer_name = purchase_details.get('customer_name')
			else:
				self.customer = None
				self.customer_name = None
			self.vehicle_owner = None
			self.vehicle_owner_name = None

		if self.vehicle:
			from erpnext.vehicles.doctype.vehicle_log.vehicle_log import get_last_customer_log
			last_customer_log = get_last_customer_log(self.vehicle, self.purchase_date)

			if last_customer_log:
				self.customer = last_customer_log.get('customer')
				self.customer_name = last_customer_log.get('customer_name')
				self.vehicle_owner = last_customer_log.get('vehicle_owner')
				self.vehicle_owner_name = last_customer_log.get('vehicle_owner_name')

	def get_last_sle(self, serial_no=None):
		if not serial_no:
			serial_no = self.name

		sl_entries = self.get_stock_ledger_entries(serial_no)
		entries = {}

		for i in range(len(sl_entries)):
			sle = sl_entries[i]
			previous_sle = sl_entries[i - 1] if i - 1 >= 0 else None
			next_sle = sl_entries[i + 1] if i + 1 < len(sl_entries) else None

			is_transfer = False
			transfer_sle = next_sle if cint(sle.actual_qty) < 0 else previous_sle

			if transfer_sle and transfer_sle.voucher_type == sle.voucher_type and transfer_sle.voucher_no == sle.voucher_no \
					and cint(transfer_sle.actual_qty) == cint(-1 * sle.actual_qty):
				is_transfer = True

			if not is_transfer:
				if cint(sle.actual_qty) > 0:
					# first receipt or receipt after delivery except returns
					if not entries.get("purchase_sle") or (entries.get("delivery_sle") and sle.voucher_type not in ['Delivery Note', 'Sales Invoice']):
						entries["purchase_sle"] = sle

					entries["delivery_sle"] = None
				else:
					# last delivery
					entries["delivery_sle"] = sle

			# last sle
			entries["last_sle"] = sle

		return entries

	def get_stock_ledger_entries(self, serial_no=None):
		if not serial_no:
			serial_no = self.name

		sl_entries = frappe.db.sql("""
			SELECT voucher_type, voucher_no, voucher_detail_no,
				posting_date, posting_time, incoming_rate, actual_qty, serial_no
			FROM
				`tabStock Ledger Entry`
			WHERE
				item_code=%s AND company = %s AND ifnull(is_cancelled, 'No')='No'
				AND exists(select sr.name from `tabStock Ledger Entry Serial No` sr
					where sr.parent = `tabStock Ledger Entry`.name and sr.serial_no = %s)
			ORDER BY
				posting_date, posting_time, creation
		""", (self.item_code, self.company, serial_no), as_dict=1)

		sl_entries = [sle for sle in sl_entries if serial_no.upper() in get_serial_nos(sle.serial_no)]
		return sl_entries

	def update_serial_no_reference(self, serial_no=None):
		last_sle = self.get_last_sle(serial_no)
		self.set_purchase_details(last_sle.get("purchase_sle"))
		self.set_sales_details(last_sle.get("delivery_sle"))
		self.set_party_details(last_sle.get("purchase_sle"), last_sle.get("delivery_sle"))
		self.set_maintenance_status()
		self.set_status()

	def update_vehicle_reference(self):
		if self.is_vehicle and not self.flags.from_vehicle:
			is_new_vehicle = False
			if not self.vehicle:
				vehicle_doc = frappe.new_doc("Vehicle")
				vehicle_doc.item_code = self.item_code
				vehicle_doc.flags.from_serial_no = self.name
				is_new_vehicle = True
			else:
				vehicle_doc = frappe.get_doc("Vehicle", self.vehicle)

			vehicle_doc.via_stock_ledger = self.via_stock_ledger
			if self.via_stock_ledger:
				vehicle_doc.flags.ignore_version = True

			vehicle_doc.save(ignore_permissions=True)
			self.vehicle = vehicle_doc.name

			if is_new_vehicle:
				frappe.msgprint(_("Created Vehicle {0}").format(frappe.get_desk_link("Vehicle", self.vehicle)))


def process_serial_no(sle):
	item_details = get_item_details(sle.item_code)

	set_auto_serial_nos(sle, item_details)
	validate_serial_no_required(sle, item_details)
	validate_serial_no(sle, item_details)

	if not sle.get('skip_update_serial_no'):
		create_missing_serial_nos(sle, item_details)
		update_serial_nos_for_cancel(sle)


def validate_serial_no_required(sle, item_details):
	label_serial_nos = _("Serial Nos") if not item_details.is_vehicle else _("Vehicle")
	label_serialized = _("Serialized") if not item_details.is_vehicle else _("Vehicle")

	serial_nos = get_serial_nos(sle.serial_no)

	if cint(item_details.has_serial_no):
		if not serial_nos and sle.is_cancelled == "No":
			frappe.throw(_("{0} required for {1} Item {2}").format(label_serial_nos, label_serialized, sle.item_code),
				SerialNoRequiredError)
	else:
		if serial_nos:
			frappe.throw(_("Item {0} is not setup for {1}. Column must be blank").format(sle.item_code, label_serial_nos),
				SerialNoNotRequiredError)


def validate_serial_no(sle, item_details):
	label_serial_no = _("Serial No") if not item_details.is_vehicle else _("Vehicle")

	serial_nos = get_serial_nos(sle.serial_no) if sle.serial_no else []

	if serial_nos and sle.is_cancelled == "No":
		validate_serial_no_qty(sle, serial_nos, item_details)

		for serial_no in serial_nos:
			sr = frappe.db.get_value("Serial No", serial_no, ["name", "item_code", "batch_no",
				"sales_order", "is_reserved", "reserved_customer", "reserved_customer_name",
				"delivery_document_no", "delivery_document_type", "warehouse", "is_vehicle",
				"purchase_document_no", "company"], as_dict=1)

			if not sr and cint(sle.actual_qty) < 0:
				frappe.throw(_("{0} {1} is not in stock").format(label_serial_no, serial_no), SerialNoNotExistsError)

			if sr:
				if sr.item_code != sle.item_code:
					frappe.throw(_("{0} {1} does not belong to Item {2}").format(label_serial_no, serial_no,
						sle.item_code), SerialNoItemError)

				if sr.batch_no and sr.batch_no != sle.batch_no and cint(sle.actual_qty) < 0:
					frappe.throw(_("{0} {1} does not belong to Batch {2}").format(label_serial_no, serial_no,
						sle.batch_no), SerialNoBatchError)

				validate_serial_no_reservation(sle, sr)


def validate_serial_no_qty(sle, serial_nos, item_details):
	if item_details.is_vehicle and abs(sle.actual_qty) != 1:
		frappe.throw(_("Vehicle Item {0} quantity must be 1").format(sle.item_code))

	if cint(sle.actual_qty) != flt(sle.actual_qty):
		frappe.throw(_("Serialized Item {0} quantity {1} cannot be a fraction").format(sle.item_code, sle.actual_qty))

	if len(serial_nos) and len(serial_nos) != abs(cint(sle.actual_qty)):
		frappe.throw(_("{0} Serial Numbers required for Item {1}. You have provided {2}.").format(abs(sle.actual_qty), sle.item_code, len(serial_nos)),
			SerialNoQtyError)

	if len(serial_nos) != len(set(serial_nos)):
		frappe.throw(_("Duplicate Serial No entered for Item {0}").format(sle.item_code), SerialNoDuplicateError)


def validate_serial_no_reservation(sle, sr):
	label_serial_no = _("Vehicle") if sr.is_vehicle else _("Serial No")

	if sr.is_reserved:
		if sr.reserved_customer:
			if sle.party_type != "Customer" or sle.party != sr.reserved_customer:
				frappe.throw(_("Cannot deliver {0} {1} of Item {2} as it is reserved for Customer \
					{3}. Please remove reservation or change Reservation Customer")
					.format(label_serial_no, sr.name, sle.item_code,
					frappe.bold(sr.reserved_customer_name or sr.reserved_customer)))
		else:
			frappe.throw(_("Cannot deliver {0} {1} of Item {2} as it is reserved without a Customer.\
				Please remove reservation or set Reservation Customer")
				.format(label_serial_no, sr.name, sle.item_code))

		if sr.sales_order:
			if sle.voucher_type == "Sales Invoice":
				if not frappe.db.exists("Sales Invoice Item", {"parent": sle.voucher_no,
					"item_code": sle.item_code, "sales_order": sr.sales_order}):
					frappe.throw(_("Cannot deliver {0} {1} of Item {2} as it is reserved \
						to fullfill Sales Order {3}").format(label_serial_no, sr.name, sle.item_code, sr.sales_order))
			elif sle.voucher_type == "Delivery Note":
				if not frappe.db.exists("Delivery Note Item", {"parent": sle.voucher_no,
					"item_code": sle.item_code, "sales_order": sr.sales_order}):
					invoice = frappe.db.get_value("Delivery Note Item", {"parent": sle.voucher_no,
						"item_code": sle.item_code}, "sales_invoice")
					if not invoice or frappe.db.exists("Sales Invoice Item",
							{"parent": invoice, "item_code": sle.item_code,
								"sales_order": sr.sales_order}):
						frappe.throw(_("Cannot deliver {0} {1} of Item {2} as it is reserved to \
							fullfill Sales Order {3}").format(label_serial_no, sr.name, sle.item_code, sr.sales_order))

	# if Sales Order reference in Delivery Note or Invoice validate SO reservations for item
	if sle.voucher_type == "Sales Invoice":
		sales_order = frappe.db.get_value("Sales Invoice Item", {"parent": sle.voucher_no,
			"item_code": sle.item_code}, "sales_order")
		if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
			validate_so_serial_no(sr, sales_order)
	elif sle.voucher_type == "Delivery Note":
		sales_order = frappe.get_value("Delivery Note Item", {"parent": sle.voucher_no,
			"item_code": sle.item_code}, "sales_order")
		if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
			validate_so_serial_no(sr, sales_order)
		else:
			sales_invoice = frappe.get_value("Delivery Note Item", {"parent": sle.voucher_no,
				"item_code": sle.item_code}, "sales_invoice")
			if sales_invoice:
				sales_order = frappe.db.get_value("Sales Invoice Item", {
					"parent": sales_invoice, "item_code": sle.item_code}, "sales_order")
				if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
					validate_so_serial_no(sr, sales_order)


def validate_so_serial_no(sr, sales_order):
	if not sr.sales_order or sr.sales_order!= sales_order:
		label_serial_no = _("Vehicle") if sr.is_vehicle else _("Serial No")
		frappe.throw(_("""Sales Order {0} has reservation for item {1}, you can
		only deliver reserved {1} against {0}. {2} {3} cannot
		be delivered""").format(sales_order, sr.item_code, label_serial_no, sr.name))


def validate_serial_no_ledger(serial_nos, item_code, voucher_type, voucher_no, company):
	def throw_already_received(d):
		received_voucher_msg = ""
		if last_receipt_sle:
			if (last_receipt_sle.voucher_type, last_receipt_sle.voucher_no) == (voucher_type, voucher_no):
				received_voucher_msg = " (received in {0} on {1})"\
					.format(frappe.get_desk_link(d.voucher_type, d.voucher_no),
						frappe.format(d.timestamp))
			else:
				received_voucher_msg = " (received in {0} on {1})"\
					.format(frappe.get_desk_link(last_receipt_sle.voucher_type, last_receipt_sle.voucher_no),
						frappe.format(last_receipt_sle.timestamp))

		frappe.throw(_("{0} is already available in Warehouse {1}{2}")
			.format(serial_no_link, current_warehouse, received_voucher_msg), title=_("Already In Stock"))

	def throw_not_available(d):
		issuing_voucher_msg = ""
		if last_issue_sle:
			if (last_issue_sle.voucher_type, last_issue_sle.voucher_no) == (voucher_type, voucher_no):
				issuing_voucher_msg = _(" (already issued in {0} on {1})") \
					.format(frappe.get_desk_link(d.voucher_type, d.voucher_no),
						frappe.format(d.timestamp))
			else:
				issuing_voucher_msg = _(" (already issued in {0} on {1})") \
					.format(frappe.get_desk_link(last_issue_sle.voucher_type, last_issue_sle.voucher_no),
						frappe.format(last_issue_sle.timestamp))

		last_available_sle = get_serial_no_last_available_sle(serial_no_sl_entries, exclude=d.name)
		last_available_msg = ""

		if last_available_sle:
			last_available_msg = _(". However it is available on {0} (received in {1})").format(
				frappe.format(last_available_sle.timestamp),
				frappe.get_desk_link(last_available_sle.voucher_type, last_available_sle.voucher_no))

		frappe.throw(_("{0} is not available in any Warehouse{1}{2}")
			.format(serial_no_link, issuing_voucher_msg, last_available_msg), title=_("Not In Stock"))

	if isinstance(serial_nos, string_types):
		serial_nos = get_serial_nos(serial_nos)

	if not serial_nos:
		return

	is_vehicle = frappe.get_cached_value("Item", item_code, "is_vehicle")

	sl_entries = frappe.db.sql("""
		select name, posting_date, posting_time, creation, voucher_type, voucher_no, serial_no, warehouse, actual_qty,
			timestamp(posting_date, posting_time) as timestamp
		from `tabStock Ledger Entry`
		where item_code=%s and company=%s and ifnull(is_cancelled, 'No')='No'
			and exists(select sr.name from `tabStock Ledger Entry Serial No` sr
				where sr.parent = `tabStock Ledger Entry`.name and sr.serial_no in %s)
		order by posting_date, posting_time, creation
	""", (item_code, company, serial_nos), as_dict=1)

	serial_no_sl_map = {}
	for sle in sl_entries:
		current_sle_serial_nos = get_serial_nos(sle.serial_no)
		for serial_no in current_sle_serial_nos:
			if serial_no in serial_nos:
				serial_no_sl_map.setdefault(serial_no, []).append(sle)

	for serial_no, serial_no_sl_entries in serial_no_sl_map.items():
		serial_no_link = frappe.get_desk_link('Vehicle' if is_vehicle else 'Serial No', serial_no)

		current_warehouse = None
		last_receipt_sle = None
		last_issue_sle = None

		for sle in serial_no_sl_entries:
			# incoming
			if sle.actual_qty > 0:
				# already in stock
				if current_warehouse:
					throw_already_received(sle)

				current_warehouse = sle.warehouse
				last_receipt_sle = sle
			# outgoing
			elif sle.actual_qty < 0:
				# not in stock
				if not current_warehouse:
					throw_not_available(sle)

				# in stock but incorrect warehouse
				elif sle.warehouse != current_warehouse:
					frappe.throw(_("{0} is not available in Warehouse {1}. However it is available in Warehouse {2}")
						.format(serial_no_link, frappe.bold(sle.warehouse), frappe.bold(current_warehouse)))

				current_warehouse = None
				last_issue_sle = sle


def get_serial_no_last_available_sle(sl_entries, exclude=None):
	available_sle = None

	for d in sl_entries:
		if exclude and d.name == exclude:
			continue

		if d.actual_qty > 0:
			if available_sle:
				return None
			available_sle = d
		elif d.actual_qty < 0:
			if not available_sle or d.warehouse != available_sle.warehouse:
				return None
			available_sle = None

	return available_sle


def set_auto_serial_nos(sle, item_details):
	if sle.is_cancelled == "No" and not sle.serial_no and cint(sle.actual_qty) > 0 \
			and item_details.has_serial_no == 1 and item_details.serial_no_series:
		serial_nos = get_auto_serial_nos(item_details.serial_no_series, sle.actual_qty, sle.item_code)
		sle.serial_no = serial_nos


def get_auto_serial_nos(serial_no_series, qty, item_code):
	serial_nos = []
	for i in range(cint(qty)):
		serial_nos.append(make_autoname(serial_no_series, "Serial No", frappe.get_cached_doc("Item", item_code)))

	return "\n".join(serial_nos)


def allow_serial_nos_with_different_item(sle_serial_no, sle):
	"""
		Allows same serial nos for raw materials and finished goods
		in Manufacture / Repack type Stock Entry
	"""
	allow_serial_nos = False
	if sle.voucher_type == "Stock Entry" and cint(sle.actual_qty) > 0:
		stock_entry = frappe.get_cached_doc("Stock Entry", sle.voucher_no)
		if stock_entry.purpose in ("Repack", "Manufacture"):
			for d in stock_entry.get("items"):
				if d.serial_no and (d.s_warehouse if sle.is_cancelled == "No" else d.t_warehouse):
					serial_nos = get_serial_nos(d.serial_no)
					if sle_serial_no in serial_nos:
						allow_serial_nos = True

	return allow_serial_nos


def create_missing_serial_nos(sle, item_details):
	if not cint(sle.get('actual_qty')) > 0 or sle.get('is_cancelled') == 'Yes':
		return

	serial_nos = get_serial_nos(sle.get('serial_no'))
	if not serial_nos:
		return

	existing_serial_nos = [cstr(d.name).upper() for d in frappe.get_all('Serial No', filters={'name': ['in', serial_nos]})]
	serial_nos_to_create = [sr for sr in serial_nos if sr not in existing_serial_nos]

	created_serial_nos = []
	for serial_no in serial_nos_to_create:
		sr = frappe.new_doc("Serial No")
		sr = update_args_for_serial_no(sr, serial_no, sle, is_new=True)
		created_serial_nos.append(sr.name)

	if not item_details.is_vehicle:
		form_links = list(map(lambda d: frappe.utils.get_link_to_form('Serial No', d), created_serial_nos))
		if len(form_links) == 1:
			frappe.msgprint(_("Serial No {0} created").format(form_links[0]))
		elif len(form_links) > 0:
			frappe.msgprint(_("The following serial numbers were created:<br>{0}").format(', '.join(form_links)))


def update_serial_nos_for_cancel(sle):
	if sle.get('is_cancelled') != 'Yes':
		return

	serial_nos = get_serial_nos(sle.get('serial_no'))
	if not serial_nos:
		return

	for serial_no in serial_nos:
		sr = frappe.get_doc("Serial No", serial_no)
		update_args_for_serial_no(sr, serial_no, sle, is_new=False)


def update_args_for_serial_no(serial_no_doc, serial_no, args, is_new=False):
	serial_no_doc.update({
		"item_code": args.get("item_code"),
		"company": args.get("company"),
		"batch_no": args.get("batch_no"),
		"via_stock_ledger": args.get("via_stock_ledger") or True,
		"supplier": args.get("supplier"),
		"location": args.get("location"),
		"warehouse": (args.get("warehouse")
			if args.get("actual_qty", 0) > 0 else None)
	})

	if is_new:
		serial_no_doc.serial_no = serial_no

	if serial_no_doc.sales_order and args.get("voucher_type") == "Stock Entry" and cint(args.get("actual_qty")) < 0:
		serial_no_doc.sales_order = None

	serial_no_doc.validate_item()

	if not is_new:
		serial_no_doc.update_serial_no_reference(serial_no)

	serial_no_doc.flags.ignore_validate = True
	serial_no_doc.flags.ignore_version = True
	if is_new:
		serial_no_doc.insert(ignore_permissions=True)
	else:
		serial_no_doc.save(ignore_permissions=True)

	return serial_no_doc


def get_item_details(item_code):
	return frappe.db.sql("""select name, has_batch_no, docstatus,
		is_stock_item, has_serial_no, is_vehicle, serial_no_series
		from tabItem where name=%s""", item_code, as_dict=True)[0]


def get_serial_nos(serial_no):
	if isinstance(serial_no, list):
		return serial_no

	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]


def update_serial_nos_after_submit(controller, parentfield):
	stock_ledger_entries = frappe.db.sql("""select voucher_detail_no, serial_no, actual_qty, warehouse
		from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s""",
		(controller.doctype, controller.name), as_dict=True)

	if not stock_ledger_entries: return

	for d in controller.get(parentfield):
		if d.serial_no:
			continue

		update_rejected_serial_nos = True if (controller.doctype in ("Purchase Receipt", "Purchase Invoice")
			and d.rejected_qty) else False
		accepted_serial_nos_updated = False

		if controller.doctype == "Stock Entry":
			warehouse = d.t_warehouse
			qty = d.transfer_qty
		else:
			warehouse = d.warehouse
			qty = (d.qty if controller.doctype == "Stock Reconciliation"
				else d.stock_qty)
		for sle in stock_ledger_entries:
			if sle.voucher_detail_no==d.name:
				if not accepted_serial_nos_updated and qty and abs(sle.actual_qty)==qty \
					and sle.warehouse == warehouse and sle.serial_no != d.serial_no:
						to_update = frappe._dict()
						to_update.serial_no = d.serial_no = sle.serial_no
						if d.get('is_vehicle'):
							to_update.vehicle = d.vehicle = sle.serial_no

						d.db_set(to_update)
						accepted_serial_nos_updated = True
						if not update_rejected_serial_nos:
							break
				elif update_rejected_serial_nos and abs(sle.actual_qty)==d.rejected_qty \
					and sle.warehouse == d.rejected_warehouse and sle.serial_no != d.rejected_serial_no:
						to_update = frappe._dict()
						to_update.rejected_serial_no = d.rejected_serial_no = sle.serial_no
						if d.get('is_vehicle'):
							to_update.vehicle = d.vehicle = sle.serial_no

						d.db_set(to_update)
						update_rejected_serial_nos = False
						if accepted_serial_nos_updated:
							break


def update_maintenance_status():
	serial_nos = frappe.db.sql('''select name from `tabSerial No` where (amc_expiry_date<%s or
		warranty_expiry_date<%s) and maintenance_status not in ('Out of Warranty', 'Out of AMC')''',
		(nowdate(), nowdate()))
	for serial_no in serial_nos:
		doc = frappe.get_doc("Serial No", serial_no[0])
		doc.set_maintenance_status()
		frappe.db.set_value('Serial No', doc.name, 'maintenance_status', doc.maintenance_status)


def get_delivery_note_serial_no(item_code, qty, delivery_note):
	serial_nos = ''
	dn_serial_nos = frappe.db.sql_list(""" select name from `tabSerial No`
		where item_code = %(item_code)s and delivery_document_no = %(delivery_note)s
		and sales_invoice is null limit {0}""".format(cint(qty)), {
		'item_code': item_code,
		'delivery_note': delivery_note
	})

	if dn_serial_nos and len(dn_serial_nos)>0:
		serial_nos = '\n'.join(dn_serial_nos)

	return serial_nos


@frappe.whitelist()
def get_serial_no_item_customer(serial_no):
	details = frappe.db.get_value("Serial No", serial_no, ['item_code', 'customer'], as_dict=1)
	if not details:
		frappe.throw(_("Serial No {0} does not exist").format(serial_no))
	return {
		"item_code": details.item_code,
		"item_name": frappe.db.get_value("Item", details.item_code, "item_name"),
		"customer": details.customer,
		"customer_name": frappe.db.get_value("Customer", details.customer, "customer_name") if details.customer else ""
	}


@frappe.whitelist()
def auto_fetch_serial_number(qty, item_code, warehouse, batch_no=None, sales_order_item=None):
	qty = cint(qty)
	filters = {
		"item_code": item_code,
		"warehouse": warehouse,
		"delivery_document_no": ['is', 'not set'],
		"sales_invoice": ['is', 'not set'],
		"purchase_date": ['is', 'set']
	}
	if batch_no:
		filters['batch_no'] = batch_no

	limit = None if sales_order_item else qty
	serial_numbers = frappe.get_list("Serial No", filters=filters, limit=limit,
		order_by="timestamp(purchase_date, purchase_time)")
	serial_numbers = [d['name'] for d in serial_numbers]

	if sales_order_item:
		batch_condition = "and pr_item.batch_no = %(batch_no)s" if batch_no else ""
		serial_nos_purchased_against_so = frappe.db.sql_list("""
			select pr_item.serial_no
			from `tabPurchase Receipt Item` pr_item
			inner join `tabPurchase Order Item` po_item on po_item.name = pr_item.purchase_order_item
			where pr_item.docstatus = 1 and po_item.sales_order_item = %(sales_order_item)s {0}
		""".format(batch_condition), {
			'sales_order_item': sales_order_item,
			'batch_no': batch_no
		})

		if serial_nos_purchased_against_so:
			preferred_serial_nos = []
			for serial_no_string in serial_nos_purchased_against_so:
				preferred_serial_nos += cstr(serial_no_string).split("\n")
			preferred_serial_nos = [serial_no for serial_no in preferred_serial_nos if serial_no]

			available_preferred_serial_nos = [serial_no for serial_no in serial_numbers if serial_no in preferred_serial_nos]
			unpreferred_serial_nos = [serial_no for serial_no in serial_numbers if serial_no not in available_preferred_serial_nos]

			serial_numbers = available_preferred_serial_nos + unpreferred_serial_nos

	return serial_numbers[:qty]
