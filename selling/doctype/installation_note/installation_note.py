# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, getdate
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
from stock.utils import get_valid_serial_nos

sql = webnotes.conn.sql
	

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Installation Note Item'
		self.fname = 'installed_item_details'

	def validate(self):
		self.validate_fiscal_year()
		self.validate_installation_date()
		self.check_item_table()
		sales_com_obj = get_obj(dt = 'Sales Common')
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.get_prevdoc_date(self)
		self.validate_mandatory()
		self.validate_reference_value()
 
	
	#fetch delivery note details
	#====================================
	def pull_delivery_note_details(self):
		self.validate_prev_docname()
		self.doclist = get_obj('DocType Mapper', 'Delivery Note-Installation Note').dt_map('Delivery Note', 'Installation Note', self.doc.delivery_note_no, self.doc, self.doclist, "[['Delivery Note', 'Installation Note'],['Delivery Note Item', 'Installation Note Item']]")
	
	# Validates that Delivery Note is not pulled twice 
	#============================================
	def validate_prev_docname(self):
		for d in getlist(self.doclist, 'installed_item_details'): 
			if self.doc.delivery_note_no == d.prevdoc_docname:
				msgprint(cstr(self.doc.delivery_note_no) + " delivery note details have already been pulled. ")
				raise Exception, "Validation Error. "
	
	#Fiscal Year Validation
	#================================
	def validate_fiscal_year(self):
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.inst_date,'Installation Date')
	
	#	Validate Mandatory 
	#===============================
	def validate_mandatory(self):
		# Amendment Date
		if self.doc.amended_from and not self.doc.amendment_date:
			msgprint("Please Enter Amendment Date")
			raise Exception, "Validation Error. "
	
	# Validate values with reference document
	#----------------------------------------
	def validate_reference_value(self):
		get_obj('DocType Mapper', 'Delivery Note-Installation Note', with_children = 1).validate_reference_value(self, self.doc.name)
	
	#check if serial no added
	#-----------------------------
	def is_serial_no_added(self,item_code,serial_no):
		ar_required = sql("select has_serial_no from tabItem where name = '%s'" % item_code)
		ar_required = ar_required and ar_required[0][0] or ''
		if ar_required == 'Yes' and not serial_no:
			msgprint("Serial No is mandatory for item: "+ item_code)
			raise Exception
		elif ar_required != 'Yes' and cstr(serial_no).strip():
			msgprint("If serial no required, please select 'Yes' in 'Has Serial No' in Item :"+item_code)
			raise Exception
	
	#check if serial no exist in system
	#-------------------------------------
	def is_serial_no_exist(self, item_code, serial_no):
		for x in serial_no:
			chk = sql("select name from `tabSerial No` where name =%s", x)
			if not chk:
				msgprint("Serial No "+x+" does not exist in the system")
				raise Exception
	
	#check if serial no already installed
	#------------------------------------------
	def is_serial_no_installed(self,cur_s_no,item_code):
		for x in cur_s_no:
			status = sql("select status from `tabSerial No` where name = %s", x)
			status = status and status[0][0] or ''
			
			if status == 'Installed':
				msgprint("Item "+item_code+" with serial no. "+x+" already installed")
				raise Exception, "Validation Error."
	
	#get list of serial no from previous_doc
	#----------------------------------------------
	def get_prevdoc_serial_no(self, prevdoc_detail_docname, prevdoc_docname):
		res = sql("select serial_no from `tabDelivery Note Item` where name = '%s' and parent ='%s'" % (prevdoc_detail_docname, prevdoc_docname))
		return get_valid_serial_nos(res[0][0])
		
	#check if all serial nos from current record exist in resp delivery note
	#---------------------------------------------------------------------------------
	def is_serial_no_match(self, cur_s_no, prevdoc_s_no, prevdoc_docname):
		for x in cur_s_no:
			if not(x in prevdoc_s_no):
				msgprint("Serial No. "+x+" not present in the Delivery Note "+prevdoc_docname, raise_exception = 1)
				raise Exception, "Validation Error."
	
	#validate serial number
	#----------------------------------------
	def validate_serial_no(self):
		cur_s_no, prevdoc_s_no, sr_list = [], [], []
		for d in getlist(self.doclist, 'installed_item_details'):
			self.is_serial_no_added(d.item_code, d.serial_no)
			
			if d.serial_no:

				sr_list = get_valid_serial_nos(d.serial_no, d.qty, d.item_code)
				self.is_serial_no_exist(d.item_code, sr_list)
				
				prevdoc_s_no = self.get_prevdoc_serial_no(d.prevdoc_detail_docname, d.prevdoc_docname)
				if prevdoc_s_no:
					self.is_serial_no_match(sr_list, prevdoc_s_no, d.prevdoc_docname)
				
				self.is_serial_no_installed(sr_list, d.item_code)
		return sr_list
	
	#validate installation date
	#-------------------------------
	def validate_installation_date(self):
		for d in getlist(self.doclist, 'installed_item_details'):
			if d.prevdoc_docname:
				d_date = sql("select posting_date from `tabDelivery Note` where name=%s", d.prevdoc_docname)
				d_date = d_date and d_date[0][0] or ''
				
				if d_date > getdate(self.doc.inst_date):
					msgprint("Installation Date can not be before Delivery Date "+cstr(d_date)+" for item "+d.item_code)
					raise Exception
	
	def check_item_table(self):
		if not(getlist(self.doclist, 'installed_item_details')):
			msgprint("Please fetch items from Delivery Note selected")
			raise Exception
	
	def on_update(self):
		webnotes.conn.set(self.doc, 'status', 'Draft')
	
	def on_submit(self):
		valid_lst = []
		valid_lst = self.validate_serial_no()
		
		get_obj("Sales Common").update_prevdoc_detail(1,self)
		
		for x in valid_lst:
			wp = sql("select warranty_period from `tabSerial No` where name = '%s'"% x)
			wp = wp and wp[0][0] or 0
			if wp:
				sql("update `tabSerial No` set maintenance_status = 'Under Warranty' where name = '%s'" % x)
			
			sql("update `tabSerial No` set status = 'Installed' where name = '%s'" % x)
		
		webnotes.conn.set(self.doc, 'status', 'Submitted')

	
	def on_cancel(self):
		cur_s_no = []
		sales_com_obj = get_obj(dt = 'Sales Common')
		sales_com_obj.update_prevdoc_detail(0,self)
		
		for d in getlist(self.doclist, 'installed_item_details'):
			if d.serial_no:
				#get current list of serial no
				cur_serial_no = d.serial_no.replace(' ', '')
				cur_s_no = cur_serial_no.split(',')
		
		for x in cur_s_no:
			sql("update `tabSerial No` set status = 'Delivered' where name = '%s'" % x)
			
		webnotes.conn.set(self.doc, 'status', 'Cancelled')
