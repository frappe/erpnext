# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, getdate, nowdate
import datetime
from webnotes import msgprint, _

from controllers.stock_controller import StockController

class SerialNoCannotCreateDirectError(webnotes.ValidationError): pass
class SerialNoCannotCannotChangeError(webnotes.ValidationError): pass

class DocType(StockController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.via_stock_ledger = False

	def validate(self):
		if self.doc.fields.get("__islocal") and self.doc.warehouse:
			webnotes.throw(_("New Serial No cannot have Warehouse. Warehouse must be set by Stock Entry or Purchase Receipt"), 
				SerialNoCannotCreateDirectError)
			
		self.validate_warranty_status()
		self.validate_amc_status()
		self.validate_warehouse()
		self.validate_item()

	def validate_amc_status(self):
		"""
			validate amc status
		"""
		if (self.doc.maintenance_status == 'Out of AMC' and self.doc.amc_expiry_date and getdate(self.doc.amc_expiry_date) >= datetime.date.today()) or (self.doc.maintenance_status == 'Under AMC' and (not self.doc.amc_expiry_date or getdate(self.doc.amc_expiry_date) < datetime.date.today())):
			msgprint("AMC expiry date and maintenance status mismatch. Please verify", raise_exception=1)

	def validate_warranty_status(self):
		"""
			validate warranty status	
		"""
		if (self.doc.maintenance_status == 'Out of Warranty' and self.doc.warranty_expiry_date and getdate(self.doc.warranty_expiry_date) >= datetime.date.today()) or (self.doc.maintenance_status == 'Under Warranty' and (not self.doc.warranty_expiry_date or getdate(self.doc.warranty_expiry_date) < datetime.date.today())):
			msgprint("Warranty expiry date and maintenance status mismatch. Please verify", raise_exception=1)


	def validate_warehouse(self):
		if not self.doc.fields.get("__islocal"):
			item_code, warehouse = webnotes.conn.get_value("Serial No", 
				self.doc.name, ["item_code", "warehouse"])
			if item_code != self.doc.item_code:
				webnotes.throw(_("Item Code cannot be changed for Serial No."), SerialNoCannotCannotChangeError)
			if not self.via_stock_ledger and warehouse != self.doc.warehouse:
				webnotes.throw(_("Warehouse cannot be changed for Serial No."), SerialNoCannotCannotChangeError)
	

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
			
	def on_trash(self):
		if self.doc.status == 'Delivered':
			msgprint("Cannot trash Serial No : %s as it is already Delivered" % (self.doc.name), raise_exception = 1)
		if self.doc.warehouse:
			webnotes.throw(_("Cannot delete Serial No in warehouse. First remove from warehouse, then delete.") + \
				": " + self.doc.name)

	def on_cancel(self):
		self.on_trash()
	
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
