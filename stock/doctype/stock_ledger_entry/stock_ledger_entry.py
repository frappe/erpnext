# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint, ValidationError
from webnotes.utils import cint, flt, getdate, cstr
from webnotes.model.controller import DocListController

class InvalidWarehouseCompany(ValidationError): pass
class SerialNoNotRequiredError(ValidationError): pass
class SerialNoRequiredError(ValidationError): pass
class SerialNoQtyError(ValidationError): pass
class SerialNoItemError(ValidationError): pass
class SerialNoWarehouseError(ValidationError): pass
class SerialNoStatusError(ValidationError): pass
class SerialNoNotExistsError(ValidationError): pass

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().replace(',', '\n').split('\n') if s.strip()]

class DocType(DocListController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		if not hasattr(webnotes, "new_stock_ledger_entries"):
			webnotes.new_stock_ledger_entries = []
		webnotes.new_stock_ledger_entries.append(self.doc)
		self.validate_mandatory()
		self.validate_item()
		self.validate_warehouse_user()
		self.validate_warehouse_company()
		self.actual_amt_check()
		self.check_stock_frozen_date()
		self.scrub_posting_time()
		
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.posting_date, self.doc.fiscal_year, self.meta.get_label("posting_date"))
		
	#check for item quantity available in stock
	def actual_amt_check(self):
		if self.doc.batch_no:
			batch_bal = flt(webnotes.conn.sql("select sum(actual_qty) from `tabStock Ledger Entry` where warehouse = '%s' and item_code = '%s' and batch_no = '%s'"%(self.doc.warehouse,self.doc.item_code,self.doc.batch_no))[0][0])
			self.doc.fields.update({'batch_bal': batch_bal})

			if (batch_bal + self.doc.actual_qty) < 0:
				msgprint("""Not enough quantity (requested: %(actual_qty)s, current: %(batch_bal)s in Batch 
		<b>%(batch_no)s</b> for Item <b>%(item_code)s</b> at Warehouse <b>%(warehouse)s</b> 
		as on %(posting_date)s %(posting_time)s""" % self.doc.fields, raise_exception = 1)

			self.doc.fields.pop('batch_bal')
			 
	def validate_warehouse_user(self):
		if webnotes.session.user=="Administrator":
			return
		warehouse_users = [p[0] for p in webnotes.conn.sql("""select user from `tabWarehouse User`
			where parent=%s""", self.doc.warehouse)]
			
		if warehouse_users and not webnotes.session.user in warehouse_users:
			webnotes.msgprint(_("User not allowed entry in the Warehouse") \
				+ ": " + webnotes.session.user + " / " + self.doc.warehouse, raise_exception = 1)

	def validate_warehouse_company(self):
		warehouse_company = webnotes.conn.get_value("Warehouse", self.doc.warehouse, "company")
		if warehouse_company and warehouse_company != self.doc.company:
			webnotes.msgprint(_("Warehouse does not belong to company.") + " (" + \
				self.doc.warehouse + ", " + self.doc.company +")", 
				raise_exception=InvalidWarehouseCompany)

	def validate_mandatory(self):
		mandatory = ['warehouse','posting_date','voucher_type','voucher_no','actual_qty','company']
		for k in mandatory:
			if not self.doc.fields.get(k):
				msgprint("Stock Ledger Entry: '%s' is mandatory" % k, raise_exception = 1)
			elif k == 'warehouse':
				if not webnotes.conn.sql("select name from tabWarehouse where name = '%s'" % self.doc.fields.get(k)):
					msgprint("Warehouse: '%s' does not exist in the system. Please check." % self.doc.fields.get(k), raise_exception = 1)

	def validate_item(self):
		item_det = webnotes.conn.sql("""select name, has_batch_no, docstatus, 
			is_stock_item, has_serial_no, serial_no_series 
			from tabItem where name=%s""", 
			self.doc.item_code, as_dict=True)[0]

		if item_det.is_stock_item != 'Yes':
			webnotes.throw("""Item: "%s" is not a Stock Item.""" % self.doc.item_code)
			
		# check if batch number is required
		if item_det.has_batch_no =='Yes' and self.doc.voucher_type != 'Stock Reconciliation':
			if not self.doc.batch_no:
				webnotes.throw("Batch number is mandatory for Item '%s'" % self.doc.item_code)
		
			# check if batch belongs to item
			if not webnotes.conn.sql("""select name from `tabBatch` 
				where item='%s' and name ='%s' and docstatus != 2""" % (self.doc.item_code, self.doc.batch_no)):
				webnotes.throw("'%s' is not a valid Batch Number for Item '%s'" % (self.doc.batch_no, self.doc.item_code))
	
		self.validate_serial_no(item_det)
	
	def validate_serial_no(self, item_det):
		if item_det.has_serial_no=="No":
			if self.doc.serial_no:
				webnotes.throw(_("Serial Number should be blank for Non Serialized Item" + ": " + self.doc.item), 
					SerialNoNotRequiredError)
		else:
			if self.doc.serial_no:
				serial_nos = get_serial_nos(self.doc.serial_no)
				if cint(self.doc.actual_qty) != flt(self.doc.actual_qty):
					webnotes.throw(_("Serial No qty cannot be a fraction") + \
						(": %s (%s)" % (self.doc.item_code, self.doc.actual_qty)))
				if len(serial_nos) and len(serial_nos) != abs(cint(self.doc.actual_qty)):
					webnotes.throw(_("Serial Nos do not match with qty") + \
						(": %s (%s)" % (self.doc.item_code, self.doc.actual_qty)), SerialNoQtyError)

				# check serial no exists, if yes then source
				for serial_no in serial_nos:
					if webnotes.conn.exists("Serial No", serial_no):
						sr = webnotes.bean("Serial No", serial_no)

						if sr.doc.item_code!=self.doc.item_code:
							webnotes.throw(_("Serial No does not belong to Item") + \
								(": %s (%s)" % (self.doc.item_code, serial_no)), SerialNoItemError)

						sr.make_controller().via_stock_ledger = True

						if self.doc.actual_qty < 0:
							if sr.doc.warehouse!=self.doc.warehouse:
								webnotes.throw(_("Warehouse does not belong to Item") + \
									(": %s (%s)" % (self.doc.item_code, serial_no)), SerialNoWarehouseError)
								
							if self.doc.voucher_type in ("Delivery Note", "Sales Invoice") \
								and sr.doc.status != "Available":
								webnotes.throw(_("Serial No status must be 'Available' to Deliver") + \
									": " + serial_no, SerialNoStatusError)
								
									
							sr.doc.warehouse = None
							sr.save()
						else:
							sr.doc.warehouse = self.doc.warehouse
							sr.save()
					else:
						if self.doc.actual_qty < 0:
							# transfer out
							webnotes.throw(_("Serial No must exist to transfer out.") + \
								": " + serial_no, SerialNoNotExistsError)
						else:
							# transfer in
							self.make_serial_no(serial_no)
			else:
				if item_det.serial_no_series:
					from webnotes.model.doc import make_autoname
					serial_nos = []
					for i in xrange(cint(self.doc.actual_qty)):
						serial_nos.append(self.make_serial_no(make_autoname(item_det.serial_no_series)))
					self.doc.serial_no = "\n".join(serial_nos)
				else:
					webnotes.throw(_("Serial Number Required for Serialized Item" + ": " + self.doc.item),
						SerialNoRequiredError)
	
	def make_serial_no(self, serial_no):
		sr = webnotes.new_bean("Serial No")
		sr.doc.serial_no = serial_no
		sr.doc.item_code = self.doc.item_code
		sr.doc.purchase_rate = self.doc.incoming_rate
		sr.doc.purchase_document_type = self.doc.voucher_type
		sr.doc.purchase_document_no = self.doc.voucher_no
		sr.doc.purchase_date = self.doc.posting_date
		sr.doc.purchase_time = self.doc.posting_time
		sr.make_controller().via_stock_ledger = True
		sr.insert()
		
		# set warehouse
		sr.doc.warehouse = self.doc.warehouse
		sr.doc.status = "Available"
		sr.save()
		webnotes.msgprint(_("Serial No created") + ": " + sr.doc.name)
		return sr.doc.name
		
	def check_stock_frozen_date(self):
		stock_frozen_upto = webnotes.conn.get_value('Stock Settings', None, 'stock_frozen_upto') or ''
		if stock_frozen_upto:
			stock_auth_role = webnotes.conn.get_value('Stock Settings', None,'stock_auth_role')
			if getdate(self.doc.posting_date) <= getdate(stock_frozen_upto) and not stock_auth_role in webnotes.user.get_roles():
				msgprint("You are not authorized to do / modify back dated stock entries before %s" % getdate(stock_frozen_upto).strftime('%d-%m-%Y'), raise_exception=1)

	def scrub_posting_time(self):
		if not self.doc.posting_time or self.doc.posting_time == '00:0':
			self.doc.posting_time = '00:00'

def update_serial_nos_after_submit(controller, parenttype, parentfield):
	if not hasattr(webnotes, "new_stock_ledger_entries"):
		return
		
	for d in controller.doclist.get({"parentfield": parentfield}):
		serial_no = None
		for sle in webnotes.new_stock_ledger_entries:
			if sle.voucher_detail_no==d.name:
				serial_no = sle.serial_no
				break

		if d.serial_no != serial_no:
			d.serial_no = serial_no
			webnotes.conn.set_value(d.doctype, d.name, "serial_no", serial_no)

def on_doctype_update():
	if not webnotes.conn.sql("""show index from `tabStock Ledger Entry` 
		where Key_name="posting_sort_index" """):
		webnotes.conn.commit()
		webnotes.conn.sql("""alter table `tabStock Ledger Entry` 
			add index posting_sort_index(posting_date, posting_time, name)""")