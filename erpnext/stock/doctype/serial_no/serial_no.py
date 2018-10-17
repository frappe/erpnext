# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.naming import make_autoname
from frappe.utils import cint, cstr, flt, add_days, nowdate, getdate
from erpnext.stock.get_item_details import get_reserved_qty_for_so

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
		if self.get("__islocal") and self.warehouse:
			frappe.throw(_("New Serial No cannot have Warehouse. Warehouse must be set by Stock Entry or Purchase Receipt"), SerialNoCannotCreateDirectError)

		self.set_maintenance_status()
		self.validate_warehouse()
		self.validate_item()
		self.on_stock_ledger_entry()

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
		item = frappe.get_doc("Item", self.item_code)
		if item.has_serial_no!=1:
			frappe.throw(_("Item {0} is not setup for Serial Nos. Check Item master").format(self.item_code))

		self.item_group = item.item_group
		self.description = item.description
		self.item_name = item.item_name
		self.brand = item.brand
		self.warranty_period = item.warranty_period

	def set_purchase_details(self, purchase_sle):
		if purchase_sle:
			self.purchase_document_type = purchase_sle.voucher_type
			self.purchase_document_no = purchase_sle.voucher_no
			self.purchase_date = purchase_sle.posting_date
			self.purchase_time = purchase_sle.posting_time
			self.purchase_rate = purchase_sle.incoming_rate
			if purchase_sle.voucher_type == "Purchase Receipt":
				self.supplier, self.supplier_name = \
					frappe.db.get_value("Purchase Receipt", purchase_sle.voucher_no,
						["supplier", "supplier_name"])

			# If sales return entry
			if self.purchase_document_type == 'Delivery Note':
				self.sales_invoice = None
		else:
			for fieldname in ("purchase_document_type", "purchase_document_no",
				"purchase_date", "purchase_time", "purchase_rate", "supplier", "supplier_name"):
					self.set(fieldname, None)

	def set_sales_details(self, delivery_sle):
		if delivery_sle:
			self.delivery_document_type = delivery_sle.voucher_type
			self.delivery_document_no = delivery_sle.voucher_no
			self.delivery_date = delivery_sle.posting_date
			self.delivery_time = delivery_sle.posting_time
			if delivery_sle.voucher_type  in ("Delivery Note", "Sales Invoice"):
				self.customer, self.customer_name = \
					frappe.db.get_value(delivery_sle.voucher_type, delivery_sle.voucher_no,
						["customer", "customer_name"])
			if self.warranty_period:
				self.warranty_expiry_date	= add_days(cstr(delivery_sle.posting_date),
					cint(self.warranty_period))
		else:
			for fieldname in ("delivery_document_type", "delivery_document_no",
				"delivery_date", "delivery_time", "customer", "customer_name",
				"warranty_expiry_date"):
					self.set(fieldname, None)

	def get_last_sle(self):
		entries = {}
		sle_dict = self.get_stock_ledger_entries()
		if sle_dict:
			if sle_dict.get("incoming", []):
				entries["purchase_sle"] = sle_dict["incoming"][0]

			if len(sle_dict.get("incoming", [])) - len(sle_dict.get("outgoing", [])) > 0:
				entries["last_sle"] = sle_dict["incoming"][0]
			else:
				entries["last_sle"] = sle_dict["outgoing"][0]
				entries["delivery_sle"] = sle_dict["outgoing"][0]

		return entries

	def get_stock_ledger_entries(self):
		sle_dict = {}
		for sle in frappe.db.sql("""select * from `tabStock Ledger Entry`
			where serial_no like %s and item_code=%s and ifnull(is_cancelled, 'No')='No'
			order by posting_date desc, posting_time desc, name desc""",
			("%%%s%%" % self.name, self.item_code), as_dict=1):
				if self.name.upper() in get_serial_nos(sle.serial_no):
					if sle.actual_qty > 0:
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
			where fieldname='serial_no' and fieldtype in ('Text', 'Small Text')"""):

			for item in frappe.db.sql("""select name, serial_no from `tab%s`
				where serial_no like '%%%s%%'""" % (dt[0], frappe.db.escape(old))):

				serial_nos = map(lambda i: new if i.upper()==old.upper() else i, item[1].split('\n'))
				frappe.db.sql("""update `tab%s` set serial_no = %s
					where name=%s""" % (dt[0], '%s', '%s'),
					('\n'.join(list(serial_nos)), item[0]))

	def on_stock_ledger_entry(self):
		if self.via_stock_ledger and not self.get("__islocal"):
			last_sle = self.get_last_sle()
			self.set_purchase_details(last_sle.get("purchase_sle"))
			self.set_sales_details(last_sle.get("delivery_sle"))
			self.set_maintenance_status()

def process_serial_no(sle):
	item_det = get_item_details(sle.item_code)
	validate_serial_no(sle, item_det)
	update_serial_nos(sle, item_det)

def validate_serial_no(sle, item_det):
	serial_nos = get_serial_nos(sle.serial_no) if sle.serial_no else []

	if item_det.has_serial_no==0:
		if serial_nos:
			frappe.throw(_("Item {0} is not setup for Serial Nos. Column must be blank").format(sle.item_code),
				SerialNoNotRequiredError)
	elif sle.is_cancelled == "No":
		if serial_nos:
			if cint(sle.actual_qty) != flt(sle.actual_qty):
				frappe.throw(_("Serial No {0} quantity {1} cannot be a fraction").format(sle.item_code, sle.actual_qty))

			if len(serial_nos) and len(serial_nos) != abs(cint(sle.actual_qty)):
				frappe.throw(_("{0} Serial Numbers required for Item {1}. You have provided {2}.").format(abs(sle.actual_qty), sle.item_code, len(serial_nos)),
					SerialNoQtyError)

			if len(serial_nos) != len(set(serial_nos)):
				frappe.throw(_("Duplicate Serial No entered for Item {0}").format(sle.item_code), SerialNoDuplicateError)

			for serial_no in serial_nos:
				if frappe.db.exists("Serial No", serial_no):
					sr = frappe.get_doc("Serial No", serial_no)

					if sr.item_code!=sle.item_code:
						if not allow_serial_nos_with_different_item(serial_no, sle):
							frappe.throw(_("Serial No {0} does not belong to Item {1}").format(serial_no,
								sle.item_code), SerialNoItemError)

					if sle.actual_qty > 0 and has_duplicate_serial_no(sr, sle):
						frappe.throw(_("Serial No {0} has already been received").format(serial_no),
							SerialNoDuplicateError)

					if (sr.delivery_document_no and sle.voucher_type != 'Stock Entry'
						and sle.voucher_type == sr.delivery_document_type):
						return_against = frappe.db.get_value(sle.voucher_type, sle.voucher_no, 'return_against')
						if return_against and return_against != sr.delivery_document_no:
							frappe.throw(_("Serial no {0} has been already returned").format(sr.name))

					if sle.actual_qty < 0:
						if sr.warehouse!=sle.warehouse:
							frappe.throw(_("Serial No {0} does not belong to Warehouse {1}").format(serial_no,
								sle.warehouse), SerialNoWarehouseError)

						if sle.voucher_type in ("Delivery Note", "Sales Invoice"):

							if sr.batch_no and sr.batch_no != sle.batch_no:
								frappe.throw(_("Serial No {0} does not belong to Batch {1}").format(serial_no,
									sle.batch_no), SerialNoBatchError)

							if sle.is_cancelled=="No" and not sr.warehouse:
								frappe.throw(_("Serial No {0} does not belong to any Warehouse")
									.format(serial_no), SerialNoWarehouseError)

							# if Sales Order reference in Serial No validate the Delivery Note or Invoice is against the same
							if sr.sales_order:
								if sle.voucher_type == "Sales Invoice":
									if not frappe.db.exists("Sales Invoice Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code, "sales_order": sr.sales_order}):
										frappe.throw(_("Cannot deliver Serial No {0} of item {1} as it is reserved \
											to fullfill Sales Order {2}").format(sr.name, sle.item_code, sr.sales_order))
								elif sle.voucher_type == "Delivery Note":
									if not frappe.db.exists("Delivery Note Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code, "against_sales_order": sr.sales_order}):
										invoice = frappe.db.get_value("Delivery Note Item", {"parent": sle.voucher_no,
											"item_code": sle.item_code}, "against_sales_invoice")
										if not invoice or frappe.db.exists("Sales Invoice Item",
											{"parent": invoice, "item_code": sle.item_code,
											"sales_order": sr.sales_order}):
											frappe.throw(_("Cannot deliver Serial No {0} of item {1} as it is reserved to \
												fullfill Sales Order {2}").format(sr.name, sle.item_code, sr.sales_order))
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
				elif sle.actual_qty < 0:
					# transfer out
					frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)
		elif sle.actual_qty < 0 or not item_det.serial_no_series:
			frappe.throw(_("Serial Nos Required for Serialized Item {0}").format(sle.item_code),
				SerialNoRequiredError)
	elif serial_nos:
		for serial_no in serial_nos:
			sr = frappe.db.get_value("Serial No", serial_no, ["name", "warehouse"], as_dict=1)
			if sr and sle.actual_qty < 0 and sr.warehouse != sle.warehouse:
				frappe.throw(_("Cannot cancel {0} {1} because Serial No {2} does not belong to the warehouse {3}")
					.format(sle.voucher_type, sle.voucher_no, serial_no, sle.warehouse))

def validate_so_serial_no(sr, sales_order,):
	if not sr.sales_order or sr.sales_order!= sales_order:
		frappe.throw(_("""Sales Order {0} has reservation for item {1}, you can
		only deliver reserved {1} against {0}. Serial No {2} cannot
		be delivered""").format(sales_order, sr.item_code, sr.name))

def has_duplicate_serial_no(sn, sle):
	if sn.warehouse:
		return True

	status = False
	if sn.purchase_document_no:
		if sle.voucher_type in ['Purchase Receipt', 'Stock Entry'] and \
			sn.delivery_document_type not in ['Purchase Receipt', 'Stock Entry']:
			status = True

		if status and sle.voucher_type == 'Stock Entry' and \
			frappe.db.get_value('Stock Entry', sle.voucher_no, 'purpose') != 'Material Receipt':
			status = False

	return status

def allow_serial_nos_with_different_item(sle_serial_no, sle):
	"""
		Allows same serial nos for raw materials and finished goods
		in Manufacture / Repack type Stock Entry
	"""
	allow_serial_nos = False
	if sle.voucher_type=="Stock Entry" and sle.actual_qty > 0:
		stock_entry = frappe.get_doc("Stock Entry", sle.voucher_no)
		if stock_entry.purpose in ("Repack", "Manufacture"):
			for d in stock_entry.get("items"):
				if d.serial_no and (d.s_warehouse if sle.is_cancelled=="No" else d.t_warehouse):
					serial_nos = get_serial_nos(d.serial_no)
					if sle_serial_no in serial_nos:
						allow_serial_nos = True

	return allow_serial_nos

def update_serial_nos(sle, item_det):
	if sle.is_cancelled == "No" and not sle.serial_no and sle.actual_qty > 0 \
			and item_det.has_serial_no == 1 and item_det.serial_no_series:
		serial_nos = get_auto_serial_nos(item_det.serial_no_series, sle.actual_qty)
		frappe.db.set(sle, "serial_no", serial_nos)
		validate_serial_no(sle, item_det)
	if sle.serial_no:
		auto_make_serial_nos(sle)

def get_auto_serial_nos(serial_no_series, qty):
	serial_nos = []
	for i in range(cint(qty)):
		serial_nos.append(make_autoname(serial_no_series, "Serial No"))

	return "\n".join(serial_nos)

def auto_make_serial_nos(args):
	serial_nos = get_serial_nos(args.get('serial_no'))
	for serial_no in serial_nos:
		if frappe.db.exists("Serial No", serial_no):
			sr = frappe.get_doc("Serial No", serial_no)
			sr.via_stock_ledger = True
			sr.item_code = args.get('item_code')
			sr.warehouse = args.get('warehouse') if args.get('actual_qty', 0) > 0 else None
			sr.batch_no = args.get('batch_no')
			sr.location = args.get('location')
			if sr.sales_order and args.get('voucher_type') == "Stock Entry" \
				and not args.get('actual_qty', 0) > 0:
				sr.sales_order = None
			sr.save(ignore_permissions=True)
		elif args.get('actual_qty', 0) > 0:
			make_serial_no(serial_no, args)

def get_item_details(item_code):
	return frappe.db.sql("""select name, has_batch_no, docstatus,
		is_stock_item, has_serial_no, serial_no_series
		from tabItem where name=%s""", item_code, as_dict=True)[0]

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]

def make_serial_no(serial_no, args):
	sr = frappe.new_doc("Serial No")
	sr.warehouse = None
	sr.dont_update_if_missing.append("warehouse")
	sr.flags.ignore_permissions = True
	sr.serial_no = serial_no
	sr.item_code = args.get('item_code')
	sr.company = args.get('company')
	sr.batch_no = args.get('batch_no')
	sr.via_stock_ledger = args.get('via_stock_ledger') or True
	sr.asset = args.get('asset')
	sr.location = args.get('location')

	if args.get('purchase_document_type'):
		sr.purchase_document_type = args.get('purchase_document_type')
		sr.purchase_document_no = args.get('purchase_document_no')

	sr.insert()
	if args.get('warehouse'):
		sr.warehouse = args.get('warehouse')
		sr.save()

	frappe.msgprint(_("Serial No {0} created").format(sr.name))
	return sr.name

def update_serial_nos_after_submit(controller, parentfield):
	stock_ledger_entries = frappe.db.sql("""select voucher_detail_no, serial_no, actual_qty, warehouse
		from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s""",
		(controller.doctype, controller.name), as_dict=True)

	if not stock_ledger_entries: return

	for d in controller.get(parentfield):
		update_rejected_serial_nos = True if (controller.doctype in ("Purchase Receipt", "Purchase Invoice")
			and d.rejected_qty) else False
		accepted_serial_nos_updated = False
		if controller.doctype == "Stock Entry":
			warehouse = d.t_warehouse
			qty = d.transfer_qty
		else:
			warehouse = d.warehouse
			qty = d.stock_qty

		for sle in stock_ledger_entries:
			if sle.voucher_detail_no==d.name:
				if not accepted_serial_nos_updated and qty and abs(sle.actual_qty)==qty \
					and sle.warehouse == warehouse and sle.serial_no != d.serial_no:
						d.serial_no = sle.serial_no
						frappe.db.set_value(d.doctype, d.name, "serial_no", sle.serial_no)
						accepted_serial_nos_updated = True
						if not update_rejected_serial_nos:
							break
				elif update_rejected_serial_nos and abs(sle.actual_qty)==d.rejected_qty \
					and sle.warehouse == d.rejected_warehouse and sle.serial_no != d.rejected_serial_no:
						d.rejected_serial_no = sle.serial_no
						frappe.db.set_value(d.doctype, d.name, "rejected_serial_no", sle.serial_no)
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
