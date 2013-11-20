# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, getdate, cstr, flt, add_days
import datetime
from webnotes import msgprint, _, ValidationError

from controllers.stock_controller import StockController

class SerialNoCannotCreateDirectError(ValidationError): pass
class SerialNoCannotCannotChangeError(ValidationError): pass
class SerialNoNotRequiredError(ValidationError): pass
class SerialNoRequiredError(ValidationError): pass
class SerialNoQtyError(ValidationError): pass
class SerialNoItemError(ValidationError): pass
class SerialNoWarehouseError(ValidationError): pass
class SerialNoStatusError(ValidationError): pass
class SerialNoNotExistsError(ValidationError): pass
class SerialNoDuplicateError(ValidationError): pass

class DocType(StockController):
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist or []
		self.via_stock_ledger = False

	def validate(self):
		if self.doc.fields.get("__islocal") and self.doc.warehouse:
			webnotes.throw(_("New Serial No cannot have Warehouse. Warehouse must be \
				set by Stock Entry or Purchase Receipt"), SerialNoCannotCreateDirectError)
			
		self.validate_warranty_status()
		self.validate_amc_status()
		self.validate_warehouse()
		self.validate_item()
		self.on_stock_ledger_entry()

	def validate_amc_status(self):
		if (self.doc.maintenance_status == 'Out of AMC' and self.doc.amc_expiry_date and getdate(self.doc.amc_expiry_date) >= datetime.date.today()) or (self.doc.maintenance_status == 'Under AMC' and (not self.doc.amc_expiry_date or getdate(self.doc.amc_expiry_date) < datetime.date.today())):
			webnotes.throw(self.doc.name + ": " + 
				_("AMC expiry date and maintenance status mismatched"))

	def validate_warranty_status(self):
		if (self.doc.maintenance_status == 'Out of Warranty' and self.doc.warranty_expiry_date and getdate(self.doc.warranty_expiry_date) >= datetime.date.today()) or (self.doc.maintenance_status == 'Under Warranty' and (not self.doc.warranty_expiry_date or getdate(self.doc.warranty_expiry_date) < datetime.date.today())):
			webnotes.throw(self.doc.name + ": " + 
				_("Warranty expiry date and maintenance status mismatched"))


	def validate_warehouse(self):
		if not self.doc.fields.get("__islocal"):
			item_code, warehouse = webnotes.conn.get_value("Serial No", 
				self.doc.name, ["item_code", "warehouse"])
			if item_code != self.doc.item_code:
				webnotes.throw(_("Item Code cannot be changed for Serial No."), 
					SerialNoCannotCannotChangeError)
			if not self.via_stock_ledger and warehouse != self.doc.warehouse:
				webnotes.throw(_("Warehouse cannot be changed for Serial No."), 
					SerialNoCannotCannotChangeError)

	def validate_item(self):
		"""
			Validate whether serial no is required for this item
		"""
		item = webnotes.doc("Item", self.doc.item_code)
		if item.has_serial_no!="Yes":
			webnotes.throw(_("Item must have 'Has Serial No' as 'Yes'") + ": " + self.doc.item_code)
			
		self.doc.item_group = item.item_group
		self.doc.description = item.description
		self.doc.item_name = item.item_name
		self.doc.brand = item.brand
		self.doc.warranty_period = item.warranty_period
				
	def set_status(self):
		last_sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` 
			where (serial_no like %s or serial_no like %s or serial_no=%s) 
			and item_code=%s and ifnull(is_cancelled, 'No')='No' 
			order by name desc limit 1""", 
			("%%%s%%" % (self.doc.name+"\n"), "%%%s%%" % ("\n"+self.doc.name), self.doc.name, 
				self.doc.item_code), as_dict=1)
		
		if last_sle:
			if last_sle[0].voucher_type == "Stock Entry":
				document_type = webnotes.conn.get_value("Stock Entry", last_sle[0].voucher_no, 
					"purpose")
			else:
				document_type = last_sle[0].voucher_type

			if last_sle[0].actual_qty > 0:
				if document_type == "Sales Return":
					self.doc.status = "Sales Returned"
				else:
					self.doc.status = "Available"
			else:
				if document_type == "Purchase Return":
					self.doc.status = "Purchase Returned"
				elif last_sle[0].voucher_type in ("Delivery Note", "Sales Invoice"):
					self.doc.status = "Delivered"
				else:
					self.doc.status = "Not Available"
		
	def set_purchase_details(self):
		purchase_sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` 
			where (serial_no like %s or serial_no like %s or serial_no=%s) 
			and item_code=%s and actual_qty > 0 
			and ifnull(is_cancelled, 'No')='No' order by name asc limit 1""", 
			("%%%s%%" % (self.doc.name+"\n"), "%%%s%%" % ("\n"+self.doc.name), self.doc.name, 
				 self.doc.item_code), as_dict=1)

		if purchase_sle:
			self.doc.purchase_document_type = purchase_sle[0].voucher_type
			self.doc.purchase_document_no = purchase_sle[0].voucher_no
			self.doc.purchase_date = purchase_sle[0].posting_date
			self.doc.purchase_time = purchase_sle[0].posting_time
			self.doc.purchase_rate = purchase_sle[0].incoming_rate
			if purchase_sle[0].voucher_type == "Purchase Receipt":
				self.doc.supplier, self.doc.supplier_name = \
					webnotes.conn.get_value("Purchase Receipt", purchase_sle[0].voucher_no, 
						["supplier", "supplier_name"])
		else:
			for fieldname in ("purchase_document_type", "purchase_document_no", 
				"purchase_date", "purchase_time", "purchase_rate", "supplier", "supplier_name"):
					self.doc.fields[fieldname] = None
				
	def set_sales_details(self):
		delivery_sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` 
			where (serial_no like %s or serial_no like %s or serial_no=%s)
			and item_code=%s and actual_qty<0 
			and voucher_type in ('Delivery Note', 'Sales Invoice')
			and ifnull(is_cancelled, 'No')='No' order by name desc limit 1""", 
			("%%%s%%" % (self.doc.name+"\n"), "%%%s%%" % ("\n"+self.doc.name), self.doc.name, 
				 self.doc.item_code), as_dict=1)
		if delivery_sle:
			self.doc.delivery_document_type = delivery_sle[0].voucher_type
			self.doc.delivery_document_no = delivery_sle[0].voucher_no
			self.doc.delivery_date = delivery_sle[0].posting_date
			self.doc.delivery_time = delivery_sle[0].posting_time
			self.doc.customer, self.doc.customer_name = \
				webnotes.conn.get_value(delivery_sle[0].voucher_type, delivery_sle[0].voucher_no, 
					["customer", "customer_name"])
			if self.doc.warranty_period:
				self.doc.warranty_expiry_date	= add_days(cstr(delivery_sle[0].posting_date), 
					cint(self.doc.warranty_period))
		else:
			for fieldname in ("delivery_document_type", "delivery_document_no", 
				"delivery_date", "delivery_time", "customer", "customer_name", 
				"warranty_expiry_date"):
					self.doc.fields[fieldname] = None		
		
	def on_trash(self):
		if self.doc.status == 'Delivered':
			webnotes.throw(_("Delivered Serial No ") + self.doc.name + _(" can not be deleted"))
		if self.doc.warehouse:
			webnotes.throw(_("Cannot delete Serial No in warehouse. \
				First remove from warehouse, then delete.") + ": " + self.doc.name)
	
	def on_rename(self, new, old, merge=False):
		"""rename serial_no text fields"""
		if merge:
			msgprint(_("Sorry. Serial Nos. cannot be merged"), raise_exception=True)
		
		for dt in webnotes.conn.sql("""select parent from tabDocField 
			where fieldname='serial_no' and fieldtype='Text'"""):
			
			for item in webnotes.conn.sql("""select name, serial_no from `tab%s` 
				where serial_no like '%%%s%%'""" % (dt[0], old)):
				
				serial_nos = map(lambda i: i==old and new or i, item[1].split('\n'))
				webnotes.conn.sql("""update `tab%s` set serial_no = %s 
					where name=%s""" % (dt[0], '%s', '%s'),
					('\n'.join(serial_nos), item[0]))
	
	def on_stock_ledger_entry(self):
		if self.via_stock_ledger and not self.doc.fields.get("__islocal"):
			self.set_status()
			self.set_purchase_details()
			self.set_sales_details()

	def on_stock_ledger_entry(self):
		if self.via_stock_ledger and not self.doc.fields.get("__islocal"):
			self.set_status()
			self.set_purchase_details()
			self.set_sales_details()
			
	def on_communication(self):
		return

def process_serial_no(sle):
	item_det = get_item_details(sle.item_code)
	validate_serial_no(sle, item_det)
	update_serial_nos(sle, item_det)
					
def validate_serial_no(sle, item_det):
	if item_det.has_serial_no=="No":
		if sle.serial_no:
			webnotes.throw(_("Serial Number should be blank for Non Serialized Item" + ": " 
				+ sle.item_code), SerialNoNotRequiredError)
	else:
		if sle.serial_no:
			serial_nos = get_serial_nos(sle.serial_no)
			if cint(sle.actual_qty) != flt(sle.actual_qty):
				webnotes.throw(_("Serial No qty cannot be a fraction") + \
					(": %s (%s)" % (sle.item_code, sle.actual_qty)))
			if len(serial_nos) and len(serial_nos) != abs(cint(sle.actual_qty)):
				webnotes.throw(_("Serial Nos do not match with qty") + \
					(": %s (%s)" % (sle.item_code, sle.actual_qty)), SerialNoQtyError)
			
			for serial_no in serial_nos:
				if webnotes.conn.exists("Serial No", serial_no):
					sr = webnotes.bean("Serial No", serial_no)
					
					if sr.doc.item_code!=sle.item_code:
						webnotes.throw(_("Serial No does not belong to Item") + 
							(": %s (%s)" % (sle.item_code, serial_no)), SerialNoItemError)
							
					if sr.doc.warehouse and sle.actual_qty > 0:
						webnotes.throw(_("Same Serial No") + ": " + sr.doc.name + 
							_(" can not be received twice"), SerialNoDuplicateError)
					
					if sle.actual_qty < 0:
						if sr.doc.warehouse!=sle.warehouse:
							webnotes.throw(_("Serial No") + ": " + serial_no + 
								_(" does not belong to Warehouse") + ": " + sle.warehouse, 
								SerialNoWarehouseError)
					
						if sle.voucher_type in ("Delivery Note", "Sales Invoice") \
							and sr.doc.status != "Available":
							webnotes.throw(_("Serial No status must be 'Available' to Deliver") 
								+ ": " + serial_no, SerialNoStatusError)
				elif sle.actual_qty < 0:
					# transfer out
					webnotes.throw(_("Serial No must exist to transfer out.") + \
						": " + serial_no, SerialNoNotExistsError)
		elif not item_det.serial_no_series:
			webnotes.throw(_("Serial Number Required for Serialized Item" + ": " 
				+ sle.item_code), SerialNoRequiredError)
				
def update_serial_nos(sle, item_det):
	if not sle.serial_no and sle.actual_qty > 0 and item_det.serial_no_series:
		from webnotes.model.doc import make_autoname
		serial_nos = []
		for i in xrange(cint(sle.actual_qty)):
			serial_nos.append(make_autoname(item_det.serial_no_series))
		webnotes.conn.set(sle, "serial_no", "\n".join(serial_nos))
		
	if sle.serial_no:
		serial_nos = get_serial_nos(sle.serial_no)
		for serial_no in serial_nos:
			if webnotes.conn.exists("Serial No", serial_no):
				sr = webnotes.bean("Serial No", serial_no)
				sr.make_controller().via_stock_ledger = True
				sr.doc.warehouse = sle.warehouse if sle.actual_qty > 0 else None
				sr.save()
			elif sle.actual_qty > 0:
				make_serial_no(serial_no, sle)

def get_item_details(item_code):
	return webnotes.conn.sql("""select name, has_batch_no, docstatus, 
		is_stock_item, has_serial_no, serial_no_series 
		from tabItem where name=%s""", item_code, as_dict=True)[0]
		
def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().replace(',', '\n').split('\n') if s.strip()]

def make_serial_no(serial_no, sle):
	sr = webnotes.new_bean("Serial No")
	sr.doc.serial_no = serial_no
	sr.doc.item_code = sle.item_code
	sr.make_controller().via_stock_ledger = True
	sr.insert()
	sr.doc.warehouse = sle.warehouse
	sr.doc.status = "Available"
	sr.save()
	webnotes.msgprint(_("Serial No created") + ": " + sr.doc.name)
	return sr.doc.name
	
def update_serial_nos_after_submit(controller, parentfield):
	stock_ledger_entries = webnotes.conn.sql("""select voucher_detail_no, serial_no
		from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s""", 
		(controller.doc.doctype, controller.doc.name), as_dict=True)
		
	if not stock_ledger_entries: return

	for d in controller.doclist.get({"parentfield": parentfield}):
		serial_no = None
		for sle in stock_ledger_entries:
			if sle.voucher_detail_no==d.name:
				serial_no = sle.serial_no
				break

		if d.serial_no != serial_no:
			d.serial_no = serial_no
			webnotes.conn.set_value(d.doctype, d.name, "serial_no", serial_no)
