# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.naming import make_autoname
from frappe.utils import cint, cstr, flt, add_days, nowdate, getdate
from erpnext.stock.get_item_details import get_reserved_qty_for_so
from erpnext.stock.stock_ledger import get_allow_negative_stock

from frappe import _, ValidationError

from erpnext.controllers.stock_controller import StockController
from six.moves import map
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
			frappe.throw(_("New Serial No cannot have Warehouse. Warehouse must be set by Stock Entry or Purchase Receipt"), SerialNoCannotCreateDirectError)

		self.set_maintenance_status()
		self.validate_warehouse()
		self.validate_item()
		self.update_customer_from_sales_order()
		self.set_status()

	def on_update(self):
		self.update_vehicle_reference()

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
			if not self.via_stock_ledger and item_code != self.item_code:
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
		if item.has_serial_no!=1:
			frappe.throw(_("Item {0} is not setup for Serial Nos. Check Item master").format(self.item_code))

		self.item_group = item.item_group
		self.description = item.description
		self.item_name = item.item_name
		self.brand = item.brand
		self.is_vehicle = item.is_vehicle
		self.warranty_period = item.warranty_period

	def update_customer_from_sales_order(self):
		if self.sales_order:
			so = frappe.db.get_value("Sales Order", self.sales_order, ["customer", "docstatus"], as_dict=1)

			if so.docstatus == 2:
				frappe.throw(_("Cannot set Sales Order as {0} because it is cancelled").format(self.sales_order))

			if not (self.delivery_document_type and self.delivery_document_no):
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
			self.delivery_date = delivery_sle.posting_date
			self.delivery_time = delivery_sle.posting_time

			if self.warranty_period:
				self.warranty_expiry_date	= add_days(cstr(delivery_sle.posting_date),
					cint(self.warranty_period))
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
			last_date = None
			dates = [self.purchase_date, self.delivery_date]
			dates = [getdate(d) for d in dates if d]
			if dates:
				last_date = max(dates)

			filters = {"vehicle": self.vehicle, "docstatus": 1}
			if last_date:
				filters['posting_date'] = ['>=', last_date]

			transfer_letter_details = frappe.get_all("Vehicle Transfer Letter", fields=['customer', 'customer_name'],
				filters=filters, order_by="posting_date desc, creation desc", limit=1)

			if transfer_letter_details:
				self.update(transfer_letter_details[0])
				self.vehicle_owner = None
				self.vehicle_owner_name = None

	def get_last_sle(self, serial_no=None):
		entries = {}
		sle_dict = self.get_stock_ledger_entries(serial_no)
		if sle_dict:
			if sle_dict.get("incoming", []):
				entries["purchase_sle"] = sle_dict["incoming"][0]

			if len(sle_dict.get("incoming", [])) - len(sle_dict.get("outgoing", [])) > 0:
				entries["last_sle"] = sle_dict["incoming"][0]
			else:
				entries["last_sle"] = sle_dict["outgoing"][0]
				entries["delivery_sle"] = sle_dict["outgoing"][0]

		return entries

	def get_stock_ledger_entries(self, serial_no=None):
		sle_dict = {}
		if not serial_no:
			serial_no = self.name

		for sle in frappe.db.sql("""
			SELECT voucher_type, voucher_no, voucher_detail_no,
				posting_date, posting_time, incoming_rate, actual_qty, serial_no
			FROM
				`tabStock Ledger Entry`
			WHERE
				item_code=%s AND company = %s AND ifnull(is_cancelled, 'No')='No'
				AND (serial_no = %s
					OR serial_no like %s
					OR serial_no like %s
					OR serial_no like %s
				)
			ORDER BY
				posting_date desc, posting_time desc, creation desc""",
			(self.item_code, self.company,
				serial_no, serial_no+'\n%', '%\n'+serial_no, '%\n'+serial_no+'\n%'), as_dict=1):
				if serial_no.upper() in get_serial_nos(sle.serial_no):
					if cint(sle.actual_qty) > 0:
						sle_dict.setdefault("incoming", []).append(sle)
					else:
						sle_dict.setdefault("outgoing", []).append(sle)

		return sle_dict

	def on_trash(self):
		sl_entries = frappe.db.sql("""select serial_no from `tabStock Ledger Entry`
			where serial_no like %s and item_code=%s and ifnull(is_cancelled, 'No')='No'""",
			("%%%s%%" % self.name, self.item_code), as_dict=True)

		# Find the exact match
		sle_exists = False
		for d in sl_entries:
			if self.name.upper() in get_serial_nos(d.serial_no):
				sle_exists = True
				break

		if sle_exists:
			frappe.throw(_("Cannot delete Serial No {0}, as it is used in stock transactions").format(self.name))

	def before_rename(self, old, new, merge=False):
		if merge:
			frappe.throw(_("Sorry, Serial Nos cannot be merged"))

	def after_rename(self, old, new, merge=False):
		"""rename serial_no text fields"""
		for dt in frappe.db.sql("""select parent from tabDocField
			where fieldname='serial_no' and fieldtype in ('Text', 'Small Text', 'Long Text')"""):

			for item in frappe.db.sql("""select name, serial_no from `tab%s`
				where serial_no like %s""" % (dt[0], frappe.db.escape('%' + old + '%'))):

				serial_nos = map(lambda i: new if i.upper()==old.upper() else i, item[1].split('\n'))
				frappe.db.sql("""update `tab%s` set serial_no = %s
					where name=%s""" % (dt[0], '%s', '%s'),
					('\n'.join(list(serial_nos)), item[0]))

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

			vehicle_doc.save(ignore_permissions=True)
			self.vehicle = vehicle_doc.name

			if is_new_vehicle:
				frappe.msgprint(_("Created Vehicle {0}").format(frappe.get_desk_link("Vehicle", self.vehicle)))

def process_serial_no(sle):
	item_det = get_item_details(sle.item_code)
	validate_serial_no(sle, item_det)
	update_serial_nos(sle, item_det)

def validate_serial_no(sle, item_det):
	label_serial_no = _("Serial No") if not item_det.is_vehicle else _("Vehicle")
	label_serial_nos = _("Serial Numbers") if not item_det.is_vehicle else _("Vehicle")
	label_serialized = _("Serialized") if not item_det.is_vehicle else _("Vehicle")

	serial_nos = get_serial_nos(sle.serial_no) if sle.serial_no else []
	validate_material_transfer_entry(sle)

	if item_det.has_serial_no==0:
		if serial_nos:
			frappe.throw(_("Item {0} is not setup for Serial Nos. Column must be blank").format(sle.item_code),
				SerialNoNotRequiredError)
	elif sle.is_cancelled == "No":
		if serial_nos:
			if item_det.is_vehicle and abs(sle.actual_qty) != 1:
				frappe.throw(_("Vehicle Item {0} quantity must be 1").format(sle.item_code))

			if cint(sle.actual_qty) != flt(sle.actual_qty):
				frappe.throw(_("Serialized Item {0} quantity {1} cannot be a fraction").format(sle.item_code, sle.actual_qty))

			if len(serial_nos) and len(serial_nos) != abs(cint(sle.actual_qty)):
				frappe.throw(_("{0} Serial Numbers required for Item {1}. You have provided {2}.").format(abs(sle.actual_qty), sle.item_code, len(serial_nos)),
					SerialNoQtyError)

			if len(serial_nos) != len(set(serial_nos)):
				frappe.throw(_("Duplicate Serial No entered for Item {0}").format(sle.item_code), SerialNoDuplicateError)

			for serial_no in serial_nos:
				if frappe.db.exists("Serial No", serial_no):
					sr = frappe.db.get_value("Serial No", serial_no, ["name", "item_code", "batch_no", "sales_order",
						"delivery_document_no", "delivery_document_type", "warehouse", "is_vehicle",
						"purchase_document_no", "company"], as_dict=1)

					if sr.item_code!=sle.item_code:
						if not allow_serial_nos_with_different_item(serial_no, sle):
							frappe.throw(_("{0} {1} does not belong to Item {2}").format(label_serial_no, serial_no,
								sle.item_code), SerialNoItemError)

					if cint(sle.actual_qty) > 0 and has_duplicate_serial_no(sr, sle):
						frappe.throw(_("{0} {1} has already been received").format(label_serial_no, serial_no),
							SerialNoDuplicateError)

					if (sr.delivery_document_no and sle.voucher_type not in ['Stock Entry', 'Stock Reconciliation', 'Vehicle Delivery']
						and sle.voucher_type == sr.delivery_document_type):
						return_against = frappe.db.get_value(sle.voucher_type, sle.voucher_no, 'return_against')
						if return_against and return_against != sr.delivery_document_no:
							frappe.throw(_("{0} {1} has been already returned").format(label_serial_no, sr.name))

					if cint(sle.actual_qty) < 0:
						if sr.warehouse!=sle.warehouse:
							frappe.throw(_("{0} {1} does not belong to Warehouse {2}").format(label_serial_no, serial_no,
								sle.warehouse), SerialNoWarehouseError)

						if sle.voucher_type in ("Delivery Note", "Sales Invoice", "Vehicle Delivery"):

							if sr.batch_no and sr.batch_no != sle.batch_no:
								frappe.throw(_("{0} {1} does not belong to Batch {2}").format(label_serial_no, serial_no,
									sle.batch_no), SerialNoBatchError)

							if sle.is_cancelled=="No" and not sr.warehouse:
								frappe.throw(_("{0} {1} does not belong to any Warehouse")
									.format(label_serial_no, serial_no), SerialNoWarehouseError)

							# if Sales Order reference in Serial No validate the Delivery Note or Invoice is against the same
							if sr.sales_order:
								if sle.voucher_type == "Sales Invoice":
									if not frappe.db.exists("Sales Invoice Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code, "sales_order": sr.sales_order}):
										frappe.throw(_("Cannot deliver {0} {1} of Item {2} as it is reserved \
											to fullfill Sales Order {3}").format(label_serial_no, sr.name, sle.item_code, sr.sales_order))
								elif sle.voucher_type == "Delivery Note":
									if not frappe.db.exists("Delivery Note Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code, "against_sales_order": sr.sales_order}):
										invoice = frappe.db.get_value("Delivery Note Item", {"parent": sle.voucher_no,
											"item_code": sle.item_code}, "against_sales_invoice")
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
									"item_code": sle.item_code}, "against_sales_order")
								if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
									validate_so_serial_no(sr, sales_order)
								else:
									sales_invoice = frappe.get_value("Delivery Note Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code}, "against_sales_invoice")
									if sales_invoice:
										sales_order = frappe.db.get_value("Sales Invoice Item", {
											"parent": sales_invoice, "item_code": sle.item_code}, "sales_order")
										if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
											validate_so_serial_no(sr, sales_order)
				elif cint(sle.actual_qty) < 0:
					# transfer out
					frappe.throw(_("{0} {1} not in stock").format(label_serial_no, serial_no), SerialNoNotExistsError)
		elif cint(sle.actual_qty) < 0 or not item_det.serial_no_series:
			frappe.throw(_("{0} required for {1} Item {2}").format(label_serial_nos, label_serialized, sle.item_code),
				SerialNoRequiredError)
	elif serial_nos:
		for serial_no in serial_nos:
			sr = frappe.db.get_value("Serial No", serial_no, ["name", "warehouse"], as_dict=1)
			if sr and cint(sle.actual_qty) < 0 and sr.warehouse != sle.warehouse and not get_allow_negative_stock(sle):
				frappe.throw(_("Cannot cancel {0} {1} because {2} {3} does not belong to the warehouse {4}")
					.format(sle.voucher_type, sle.voucher_no, label_serial_no, serial_no, sle.warehouse))

def validate_material_transfer_entry(sle_doc):
	sle_doc.update({
		"skip_update_serial_no": False,
		"skip_serial_no_validaiton": False
	})

	if (sle_doc.voucher_type == "Stock Entry" and sle_doc.is_cancelled == "No" and
		frappe.get_cached_value("Stock Entry", sle_doc.voucher_no, "purpose") == "Material Transfer"):
		if sle_doc.actual_qty < 0:
			sle_doc.skip_update_serial_no = True
		else:
			sle_doc.skip_serial_no_validaiton = True

def validate_so_serial_no(sr, sales_order,):
	if not sr.sales_order or sr.sales_order!= sales_order:
		label_serial_no = _("Vehicle") if sr.is_vehicle else _("Serial No")
		frappe.throw(_("""Sales Order {0} has reservation for item {1}, you can
		only deliver reserved {1} against {0}. {2} {3} cannot
		be delivered""").format(sales_order, sr.item_code, label_serial_no, sr.name))

def has_duplicate_serial_no(sn, sle):
	if frappe.flags.allow_repost_serial_no:
		return False

	if (sn.warehouse and not sle.skip_serial_no_validaiton
		and sle.voucher_type != 'Stock Reconciliation'):
		return True

	if sn.company != sle.company:
		return False

	status = False
	if sn.purchase_document_no:
		if sle.voucher_type in ['Purchase Receipt', 'Stock Entry', "Purchase Invoice"] and \
			sn.delivery_document_type not in ['Purchase Receipt', 'Stock Entry', "Purchase Invoice"]:
			status = True

		if status and sle.voucher_type == 'Stock Entry':
			purpose, customer_provided = frappe.db.get_value('Stock Entry', sle.voucher_no, ['purpose', 'customer_provided'])
			if purpose != 'Material Receipt' or customer_provided:
				status = False

	return status

def allow_serial_nos_with_different_item(sle_serial_no, sle):
	"""
		Allows same serial nos for raw materials and finished goods
		in Manufacture / Repack type Stock Entry
	"""
	allow_serial_nos = False
	if sle.voucher_type=="Stock Entry" and cint(sle.actual_qty) > 0:
		stock_entry = frappe.get_cached_doc("Stock Entry", sle.voucher_no)
		if stock_entry.purpose in ("Repack", "Manufacture"):
			for d in stock_entry.get("items"):
				if d.serial_no and (d.s_warehouse if sle.is_cancelled=="No" else d.t_warehouse):
					serial_nos = get_serial_nos(d.serial_no)
					if sle_serial_no in serial_nos:
						allow_serial_nos = True

	return allow_serial_nos

def update_serial_nos(sle, item_det):
	if sle.skip_update_serial_no: return
	if sle.is_cancelled == "No" and not sle.serial_no and cint(sle.actual_qty) > 0 \
			and item_det.has_serial_no == 1 and item_det.serial_no_series:
		serial_nos = get_auto_serial_nos(item_det.serial_no_series, sle.actual_qty, item_det.name)
		frappe.db.set(sle, "serial_no", serial_nos)
		validate_serial_no(sle, item_det)
	if sle.serial_no:
		auto_make_serial_nos(sle, item_det)

def get_auto_serial_nos(serial_no_series, qty, item_code):
	serial_nos = []
	for i in range(cint(qty)):
		serial_nos.append(make_autoname(serial_no_series, "Serial No", frappe.get_cached_doc("Item", item_code)))

	return "\n".join(serial_nos)

def auto_make_serial_nos(args, item_det):
	serial_nos = get_serial_nos(args.get('serial_no'))
	created_numbers = []
	for serial_no in serial_nos:
		is_new = False
		if frappe.db.exists("Serial No", serial_no):
			sr = frappe.get_cached_doc("Serial No", serial_no)
		elif args.get('actual_qty', 0) > 0:
			sr = frappe.new_doc("Serial No")
			is_new = True

		sr = update_args_for_serial_no(sr, serial_no, args, is_new=is_new)
		if is_new:
			created_numbers.append(sr.name)

	if not item_det.is_vehicle:
		form_links = list(map(lambda d: frappe.utils.get_link_to_form('Serial No', d), created_numbers))
		if len(form_links) == 1:
			frappe.msgprint(_("Serial No {0} created").format(form_links[0]))
		elif len(form_links) > 0:
			frappe.msgprint(_("The following serial numbers were created: <br> {0}").format(', '.join(form_links)))

def get_item_details(item_code):
	return frappe.db.sql("""select name, has_batch_no, docstatus,
		is_stock_item, has_serial_no, is_vehicle, serial_no_series
		from tabItem where name=%s""", item_code, as_dict=True)[0]

def get_serial_nos(serial_no):
	if isinstance(serial_no, list):
		return serial_no

	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]

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

	if (serial_no_doc.sales_order and args.get("voucher_type") == "Stock Entry"
		and not args.get("actual_qty", 0) > 0):
		serial_no_doc.sales_order = None

	serial_no_doc.validate_item()
	serial_no_doc.update_serial_no_reference(serial_no)

	serial_no_doc.flags.ignore_validate = True

	if is_new:
		serial_no_doc.insert(ignore_permissions=True)
	else:
		serial_no_doc.save(ignore_permissions=True)

	return serial_no_doc

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

						frappe.db.set_value(d.doctype, d.name, to_update, None)
						accepted_serial_nos_updated = True
						if not update_rejected_serial_nos:
							break
				elif update_rejected_serial_nos and abs(sle.actual_qty)==d.rejected_qty \
					and sle.warehouse == d.rejected_warehouse and sle.serial_no != d.rejected_serial_no:
						to_update = frappe._dict()
						to_update.rejected_serial_no = d.rejected_serial_no = sle.serial_no
						if d.get('is_vehicle'):
							to_update.vehicle = d.vehicle = sle.serial_no

						frappe.db.set_value(d.doctype, d.name, to_update, None)
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
