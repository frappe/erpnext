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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, cstr, flt, nowdate, cint, now
from webnotes.model.doc import Document
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import session, msgprint
from stock.utils import get_valid_serial_nos

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist


	def scrub_serial_nos(self, obj, table_name = ''):
		if not table_name:
			table_name = obj.fname
		
		for d in getlist(obj.doclist, table_name):
			if d.serial_no:
				d.serial_no = cstr(d.serial_no).strip().replace(',', '\n')
				d.save()


	def validate_serial_no_warehouse(self, obj, fname):
		for d in getlist(obj.doclist, fname):
			wh = d.warehouse or d.s_warehouse
			if cstr(d.serial_no).strip() and wh:
				serial_nos = get_valid_serial_nos(d.serial_no)
				for s in serial_nos:
					s = s.strip()
					sr_war = webnotes.conn.sql("select warehouse,name from `tabSerial No` where name = '%s'" % (s))
					if not sr_war:
						msgprint("Serial No %s does not exists"%s, raise_exception = 1)
					elif not sr_war[0][0]:
						msgprint("Warehouse not mentioned in the Serial No <b>%s</b>" % s, raise_exception = 1)
					elif sr_war[0][0] != wh:
						msgprint("Serial No : %s for Item : %s doesn't exists in Warehouse : %s" % (s, d.item_code, wh), raise_exception = 1)


	def validate_serial_no(self, obj, fname):
		"""check whether serial no is required"""
		for d in getlist(obj.doclist, fname):
			is_stock_item = webnotes.conn.get_value('Item', d.item_code, 'is_stock_item')
			ar_required = webnotes.conn.get_value('Item', d.item_code, 'has_serial_no')
			
			# [bug fix] need to strip serial nos of all spaces and new lines for validation
			serial_no = cstr(d.serial_no).strip()
			if serial_no:
				if is_stock_item != 'Yes':
					msgprint("Serial No is not required for non-stock item: %s" % d.item_code, raise_exception=1)
				elif ar_required != 'Yes':
					msgprint("If serial no required, please select 'Yes' in 'Has Serial No' in Item :" + d.item_code + \
						', otherwise please remove serial no', raise_exception=1)
			elif ar_required == 'Yes' and not serial_no and d.qty:
				msgprint("Serial no is mandatory for item: "+ d.item_code, raise_exception = 1)

			# validate rejected serial nos
			if fname == 'purchase_receipt_details' and flt(d.rejected_qty) > 0 and ar_required == 'Yes' and not d.rejected_serial_no:
				msgprint("Rejected serial no is mandatory for rejected qty of item: "+ d.item_code, raise_exception = 1)
				

	def set_pur_serial_no_values(self, obj, serial_no, d, s, new_rec, rejected=None):
		item_details = webnotes.conn.sql("""select item_group, warranty_period 
			from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or 
			end_of_life = '0000-00-00' or end_of_life > now()) """ %(d.item_code), as_dict=1)
		
		s.purchase_document_type	=	obj.doc.doctype
		s.purchase_document_no		=	obj.doc.name
		s.purchase_date				=	obj.doc.posting_date
		s.purchase_time				=	obj.doc.posting_time
		s.purchase_rate				=	d.valuation_rate or d.incoming_rate
		s.item_code					=	d.item_code
		s.item_name					=	d.item_name
		s.brand						=	d.brand
		s.description				=	d.description
		s.item_group				=	item_details and item_details[0]['item_group'] or ''
		s.warranty_period			=	item_details and item_details[0]['warranty_period'] or 0
		s.supplier					=	obj.doc.supplier
		s.supplier_name				=	obj.doc.supplier_name
		s.address_display			=	obj.doc.address_display or obj.doc.supplier_address
		s.warehouse					=	rejected and obj.doc.rejected_warehouse \
			or d.warehouse or d.t_warehouse or ""
		s.docstatus					=	0
		s.status					=	'In Store'
		s.modified					=	nowdate()
		s.modified_by				=	session['user']
		s.serial_no					=	serial_no
		s.sle_exists				=	1
		s.company					=	obj.doc.company
		s.save(new_rec)


	def update_serial_purchase_details(self, obj, d, serial_no, is_submit, purpose = '', rejected=None):
		exists = webnotes.conn.sql("select name, status, docstatus from `tabSerial No` where name = '%s'" % (serial_no))
		if is_submit:
			if exists and exists[0][2] != 2 and purpose not in ['Material Transfer', 'Sales Return']:
				msgprint("Serial No: %s already %s" % (serial_no, exists and exists[0][1]), raise_exception = 1)
			elif exists:
				s = Document('Serial No', exists and exists[0][0])
				self.set_pur_serial_no_values(obj, serial_no, d, s, new_rec = 0, rejected=rejected)
			else:
				s = Document('Serial No')
				self.set_pur_serial_no_values(obj, serial_no, d, s, new_rec = 1, rejected=rejected)
		else:
			if exists and exists[0][1] == 'Delivered' and exists[0][2] != 2:
				msgprint("Serial No: %s is already delivered, you can not cancel the document." % serial_no, raise_exception=1)
			elif purpose == 'Material Transfer':
				webnotes.conn.sql("update `tabSerial No` set status = 'In Store', purchase_document_type = '', purchase_document_no = '', warehouse = '%s' where name = '%s'" % (d.s_warehouse, serial_no))				
			elif purpose == 'Sales Return':
				webnotes.conn.sql("update `tabSerial No` set status = 'Delivered', purchase_document_type = '', purchase_document_no = '' where name = '%s'" % serial_no)
			else:
				webnotes.conn.sql("update `tabSerial No` set docstatus = 2, status = 'Not in Use', purchase_document_type = '', purchase_document_no = '', purchase_date = null, purchase_rate = 0, supplier = null, supplier_name = '', supplier_address = '', warehouse = '' where name = '%s'" % serial_no)


	def check_serial_no_exists(self, serial_no, item_code):
		chk = webnotes.conn.sql("select name, status, docstatus, item_code from `tabSerial No` where name = %s", (serial_no), as_dict=1)
		if not chk:
			msgprint("Serial No: %s does not exists in the system" % serial_no, raise_exception=1)
		elif chk and chk[0]['item_code'] != item_code:
			msgprint("Serial No: %s not belong to item: %s" % (serial_no, item_code), raise_exception=1)
		elif chk and chk[0]['docstatus'] == 2:
			msgprint("Serial No: %s of Item : %s is trashed in the system" % (serial_no, item_code), raise_exception = 1)
		elif chk and chk[0]['status'] == 'Delivered':
			msgprint("Serial No: %s of Item : %s is already delivered." % (serial_no, item_code), raise_exception = 1)


	def set_delivery_serial_no_values(self, obj, serial_no):
		s = Document('Serial No', serial_no)
		s.delivery_document_type =	 obj.doc.doctype
		s.delivery_document_no	 =	 obj.doc.name
		s.delivery_date			=	 obj.doc.posting_date
		s.delivery_time			=	 obj.doc.posting_time
		s.customer				=	 obj.doc.customer
		s.customer_name			=	 obj.doc.customer_name
		s.delivery_address	 	=	 obj.doc.address_display
		s.territory				=	 obj.doc.territory
		s.warranty_expiry_date	=	 cint(s.warranty_period) and \
		 	add_days(cstr(obj.doc.posting_date), cint(s.warranty_period)) or s.warranty_expiry_date
		s.docstatus				=	 1
		s.status				=	 'Delivered'
		s.modified				=	 nowdate()
		s.modified_by			=	 session['user']
		s.save()


	def update_serial_delivery_details(self, obj, d, serial_no, is_submit):
		if is_submit:
			self.check_serial_no_exists(serial_no, d.item_code)
			self.set_delivery_serial_no_values(obj, serial_no)
		else:
			webnotes.conn.sql("update `tabSerial No` set docstatus = 0, status = 'In Store', delivery_document_type = '', delivery_document_no = '', delivery_date = null, customer = null, customer_name = '', delivery_address = '', territory = null where name = '%s'" % (serial_no))


	def update_serial_record(self, obj, fname, is_submit = 1, is_incoming = 0):
		for d in getlist(obj.doclist, fname):
			if d.serial_no:
				serial_nos = get_valid_serial_nos(d.serial_no)
				for a in serial_nos:
					serial_no = a.strip()
					if is_incoming:
						self.update_serial_purchase_details(obj, d, serial_no, is_submit)
					else:
						self.update_serial_delivery_details(obj, d, serial_no, is_submit)

			if fname == 'purchase_receipt_details' and d.rejected_qty and d.rejected_serial_no:
				serial_nos = get_valid_serial_nos(d.rejected_serial_no)
				for a in serial_nos:
					self.update_serial_purchase_details(obj, d, a, is_submit, rejected=True)
				
				
	def update_stock(self, values, is_amended = 'No'):
		for v in values:
			sle_id, valid_serial_nos = '', ''
			# get serial nos
			if v.get("serial_no", "").strip():
				valid_serial_nos = get_valid_serial_nos(v["serial_no"], 
					v['actual_qty'], v['item_code'])
				v["serial_no"] = valid_serial_nos and "\n".join(valid_serial_nos) or ""
			
			# reverse quantities for cancel
			if v.get('is_cancelled') == 'Yes':
				v['actual_qty'] = -flt(v['actual_qty'])
				# cancel matching entry
				webnotes.conn.sql("""update `tabStock Ledger Entry` set is_cancelled='Yes',
					modified=%s, modified_by=%s
					where voucher_no=%s and voucher_type=%s""", 
					(now(), webnotes.session.user, v['voucher_no'], v['voucher_type']))

			if v.get("actual_qty"):
				sle_id = self.make_entry(v)
				
			args = v.copy()
			args.update({
				"sle_id": sle_id,
				"is_amended": is_amended
			})
			
			get_obj('Warehouse', v["warehouse"]).update_bin(args)


	def make_entry(self, args):
		args.update({"doctype": "Stock Ledger Entry"})
		if args.get("warehouse"):
			args["warehouse_type"] = webnotes.conn.get_value('Warehouse' , args["warehouse"],
				'warehouse_type')
		sle = webnotes.bean([args])
		sle.ignore_permissions = 1
		sle.insert()
		return sle.doc.name
	
	def repost(self):
		"""
		Repost everything!
		"""
		for wh in webnotes.conn.sql("select name from tabWarehouse"):
			get_obj('Warehouse', wh[0]).repost_stock()
