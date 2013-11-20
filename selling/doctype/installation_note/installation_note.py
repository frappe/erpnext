# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, getdate
from webnotes.model.bean import getlist
from webnotes import msgprint
from stock.utils import get_valid_serial_nos	

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Installation Note Item'
		self.fname = 'installed_item_details'
		self.status_updater = [{
			'source_dt': 'Installation Note Item',
			'target_dt': 'Delivery Note Item',
			'target_field': 'installed_qty',
			'target_ref_field': 'qty',
			'join_field': 'prevdoc_detail_docname',
			'target_parent_dt': 'Delivery Note',
			'target_parent_field': 'per_installed',
			'source_field': 'qty',
			'percent_join_field': 'prevdoc_docname',
			'status_field': 'installation_status',
			'keyword': 'Installed'
		}]

	def validate(self):
		self.validate_fiscal_year()
		self.validate_installation_date()
		self.check_item_table()
		
		from controllers.selling_controller import check_active_sales_items
		check_active_sales_items(self)

	def validate_fiscal_year(self):
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.inst_date, self.doc.fiscal_year, "Installation Date")
	
	def is_serial_no_added(self, item_code, serial_no):
		ar_required = webnotes.conn.get_value("Item", item_code, "has_serial_no")
		if ar_required == 'Yes' and not serial_no:
			msgprint("Serial No is mandatory for item: " + item_code, raise_exception=1)
		elif ar_required != 'Yes' and cstr(serial_no).strip():
			msgprint("If serial no required, please select 'Yes' in 'Has Serial No' in Item :" + 
				item_code, raise_exception=1)
	
	def is_serial_no_exist(self, item_code, serial_no):
		for x in serial_no:
			if not webnotes.conn.exists("Serial No", x):
				msgprint("Serial No " + x + " does not exist in the system", raise_exception=1)
	
	def is_serial_no_installed(self,cur_s_no,item_code):
		for x in cur_s_no:
			status = webnotes.conn.sql("select status from `tabSerial No` where name = %s", x)
			status = status and status[0][0] or ''
			
			if status == 'Installed':
				msgprint("Item "+item_code+" with serial no. " + x + " already installed", 
					raise_exception=1)
	
	def get_prevdoc_serial_no(self, prevdoc_detail_docname):
		serial_nos = webnotes.conn.get_value("Delivery Note Item", 
			prevdoc_detail_docname, "serial_no")
		return get_valid_serial_nos(serial_nos)
		
	def is_serial_no_match(self, cur_s_no, prevdoc_s_no, prevdoc_docname):
		for sr in cur_s_no:
			if sr not in prevdoc_s_no:
				msgprint("Serial No. " + sr + " is not matching with the Delivery Note " + 
					prevdoc_docname, raise_exception = 1)

	def validate_serial_no(self):
		cur_s_no, prevdoc_s_no, sr_list = [], [], []
		for d in getlist(self.doclist, 'installed_item_details'):
			self.is_serial_no_added(d.item_code, d.serial_no)
			if d.serial_no:
				sr_list = get_valid_serial_nos(d.serial_no, d.qty, d.item_code)
				self.is_serial_no_exist(d.item_code, sr_list)
				
				prevdoc_s_no = self.get_prevdoc_serial_no(d.prevdoc_detail_docname)
				if prevdoc_s_no:
					self.is_serial_no_match(sr_list, prevdoc_s_no, d.prevdoc_docname)
				
				self.is_serial_no_installed(sr_list, d.item_code)
		return sr_list

	def validate_installation_date(self):
		for d in getlist(self.doclist, 'installed_item_details'):
			if d.prevdoc_docname:
				d_date = webnotes.conn.get_value("Delivery Note", d.prevdoc_docname, "posting_date")				
				if d_date > getdate(self.doc.inst_date):
					msgprint("Installation Date can not be before Delivery Date " + cstr(d_date) + 
						" for item "+d.item_code, raise_exception=1)
	
	def check_item_table(self):
		if not(getlist(self.doclist, 'installed_item_details')):
			msgprint("Please fetch items from Delivery Note selected", raise_exception=1)
	
	def on_update(self):
		webnotes.conn.set(self.doc, 'status', 'Draft')
	
	def on_submit(self):
		valid_lst = []
		valid_lst = self.validate_serial_no()
		
		for x in valid_lst:
			if webnotes.conn.get_value("Serial No", x, "warranty_period"):
				webnotes.conn.set_value("Serial No", x, "maintenance_status", "Under Warranty")
			webnotes.conn.set_value("Serial No", x, "status", "Installed")

		self.update_prevdoc_status()
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self):
		for d in getlist(self.doclist, 'installed_item_details'):
			if d.serial_no:
				d.serial_no = d.serial_no.replace(",", "\n")
				for sr_no in d.serial_no.split("\n"):
					webnotes.conn.set_value("Serial No", sr_no, "status", "Delivered")

		self.update_prevdoc_status()
		webnotes.conn.set(self.doc, 'status', 'Cancelled')
