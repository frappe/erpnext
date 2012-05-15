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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists

# -----------------------------------------------------------------------------------------

def get_sr_no_list(sr_nos, qty = 0, item_code = ''):
	serial_nos = cstr(sr_nos).strip().replace(',', '\n').split('\n')
	valid_serial_nos = []
	for val in serial_nos:
		if val:
			if val in valid_serial_nos:
				msgprint("You have entered duplicate serial no: %s" % val, raise_exception=1)
			else:
				valid_serial_nos.append(val.strip())
	if qty and cstr(sr_nos).strip() and len(valid_serial_nos) != abs(qty):
		msgprint("Please enter serial nos for "+ cstr(abs(qty)) + " quantity against item code: " + item_code , raise_exception = 1)
	return valid_serial_nos

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist


	# -----------------
	# scrub serial nos
	# -----------------
	def scrub_serial_nos(self, obj):
		for d in getlist(obj.doclist, obj.fname):
			if d.serial_no:
				d.serial_no = d.serial_no.replace(',', '\n')
				d.save()


	# -----------------------------
	# validate serial no warehouse
	# -----------------------------
	def validate_serial_no_warehouse(self, obj, fname):
		for d in getlist(obj.doclist, fname):
			wh = d.warehouse or d.s_warehouse
			if d.serial_no and wh:
				serial_nos = self.get_sr_no_list(d.serial_no)
				for s in serial_nos:
					s = s.strip()
					sr_war = sql("select warehouse,name from `tabSerial No` where name = '%s'" % (s))
					if not sr_war:
						msgprint("Serial No %s does not exists"%s, raise_exception = 1)
					elif not sr_war[0][0]:
						msgprint("Warehouse not mentioned in the Serial No <b>%s</b>" % s, raise_exception = 1)
					elif sr_war[0][0] != wh:
						msgprint("Serial No : %s for Item : %s doesn't exists in Warehouse : %s" % (s, d.item_code, wh), raise_exception = 1)


	# ------------------------------------
	# check whether serial no is required
	# ------------------------------------
	def validate_serial_no(self, obj, fname):
		for d in getlist(obj.doclist, fname):
			is_stock_item = get_value('Item', d.item_code, 'is_stock_item')
			ar_required = get_value('Item', d.item_code, 'has_serial_no')
			if cstr(d.serial_no).strip():
				if is_stock_item != 'Yes':
					msgprint("Serial No is not required for non-stock item: %s" % d.item_code, raise_exception=1)
				elif ar_required != 'Yes':
					msgprint("If serial no required, please select 'Yes' in 'Has Serial No' in Item :" + d.item_code + \
						', otherwise please remove serial no', raise_exception=1)
			elif ar_required == 'Yes' and not d.serial_no:
				msgprint("Serial no is mandatory for item: "+ d.item_code, raise_exception = 1)

			# validate rejected serial nos
			if fname == 'purchase_receipt_details' and flt(d.rejected_qty) > 0 and ar_required == 'Yes' and not d.rejected_serial_no:
				msgprint("Rejected serial no is mandatory for rejected qty of item: "+ d.item_code, raise_exception = 1)
				
				



	# -------------------
	# get serial no list
	# -------------------
	def get_sr_no_list(self, sr_nos, qty = 0, item_code = ''):
		return get_sr_no_list(sr_nos, qty, item_code)

	# ---------------------
	# set serial no values
	# ---------------------
	def set_pur_serial_no_values(self, obj, serial_no, d, s, new_rec):
		item_details = sql("select item_group, warranty_period from `tabItem` where name = '%s' and \
			(ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life > now()) " %(d.item_code), as_dict=1)
		
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
		s.warehouse					=	d.warehouse or d.t_warehouse
		s.docstatus					=	0
		s.status					=	'In Store'
		s.modified					=	nowdate()
		s.modified_by				=	session['user']
		s.serial_no					=	serial_no
		s.sle_exists				=	1
		s.fiscal_year				=	obj.doc.fiscal_year
		s.company					=	obj.doc.company
		s.save(new_rec)


	# ----------------------------------
	# update serial no purchase details
	# ----------------------------------
	def update_serial_purchase_details(self, obj, d, serial_no, is_submit, purpose = ''):
		exists = sql("select name, status, docstatus from `tabSerial No` where name = '%s'" % (serial_no))
		if is_submit:
			if exists and exists[0][2] != 2 and purpose not in ['Material Transfer', 'Sales Return']:
				msgprint("Serial No: %s already %s" % (serial_no, exists and exists[0][1]), raise_exception = 1)
			elif exists:
				s = Document('Serial No', exists and exists[0][0])
				self.set_pur_serial_no_values(obj, serial_no, d, s, new_rec = 0)
			else:
				s = Document('Serial No')
				self.set_pur_serial_no_values(obj, serial_no, d, s, new_rec = 1)
		else:
			if exists and exists[0][1] == 'Delivered' and exists[0][2] != 2:
				msgprint("Serial No: %s is already delivered, you can not cancel the document." % serial_no, raise_exception=1)
			elif purpose == 'Material Transfer':
				sql("update `tabSerial No` set status = 'In Store', purchase_document_type = '', purchase_document_no = '', warehouse = '%s' where name = '%s'" % (d.s_warehouse, serial_no))				
			elif purpose == 'Sales Return':
				sql("update `tabSerial No` set status = 'Delivered', purchase_document_type = '', purchase_document_no = '' where name = '%s'" % serial_no)
			else:
				sql("update `tabSerial No` set docstatus = 2, status = 'Not in Use', purchase_document_type = '', purchase_document_no = '', purchase_date = null, purchase_rate = 0, supplier = null, supplier_name = '', supplier_address = '', warehouse = '' where name = '%s'" % serial_no)


	# -------------------------------
	# check whether serial no exists
	# -------------------------------
	def check_serial_no_exists(self, serial_no, item_code):
		chk = sql("select name, status, docstatus, item_code from `tabSerial No` where name = %s", (serial_no), as_dict=1)
		if not chk:
			msgprint("Serial No: %s does not exists in the system" % serial_no, raise_exception=1)
		elif chk and chk[0]['item_code'] != item_code:
			msgprint("Serial No: %s not belong to item: %s" % (serial_no, item_code), raise_exception=1)
		elif chk and chk[0]['docstatus'] == 2:
			msgprint("Serial No: %s of Item : %s is trashed in the system" % (serial_no, item_code), raise_exception = 1)
		elif chk and chk[0]['status'] == 'Delivered':
			msgprint("Serial No: %s of Item : %s is already delivered." % (serial_no, item_code), raise_exception = 1)

	# ---------------------
	# set serial no values
	# ---------------------
	def set_delivery_serial_no_values(self, obj, serial_no):
		s = Document('Serial No', serial_no)
		s.delivery_document_type =	 obj.doc.doctype
		s.delivery_document_no	 =	 obj.doc.name
		s.delivery_date					=	 obj.doc.posting_date
		s.delivery_time					=	 obj.doc.posting_time
		s.customer						=	 obj.doc.customer
		s.customer_name					=	 obj.doc.customer_name
		s.delivery_address			 	=	 obj.doc.address_display
		s.territory						=	 obj.doc.territory
		s.warranty_expiry_date	 		=	 s.warranty_period and add_days(cstr(obj.doc.posting_date), s.warranty_period) or ''
		s.docstatus						=	 1
		s.status						=	 'Delivered'
		s.modified						=	 nowdate()
		s.modified_by					=	 session['user']
		s.save()


	# ----------------------------------
	# update serial no delivery details
	# ----------------------------------
	def update_serial_delivery_details(self, obj, d, serial_no, is_submit):
		if is_submit:
			self.check_serial_no_exists(serial_no, d.item_code)
			self.set_delivery_serial_no_values(obj, serial_no)
		else:
			sql("update `tabSerial No` set docstatus = 0, status = 'In Store', delivery_document_type = '', delivery_document_no = '', delivery_date = null, customer = null, customer_name = '', delivery_address = '', territory = null where name = '%s'" % (serial_no))


	# ---------------------
	# update serial record
	# ---------------------
	def update_serial_record(self, obj, fname, is_submit = 1, is_incoming = 0):
		import datetime
		for d in getlist(obj.doclist, fname):
			if d.serial_no:
				serial_nos = self.get_sr_no_list(d.serial_no)
				for a in serial_nos:
					serial_no = a.strip()
					if is_incoming:
						self.update_serial_purchase_details(obj, d, serial_no, is_submit)
					else:
						self.update_serial_delivery_details(obj, d, serial_no, is_submit)

			if fname == 'purchase_receipt_details' and d.rejected_qty and d.rejected_serial_no:
				serial_nos = self.get_sr_no_list(d.rejected_serial_no)
				for a in serial_nos:
					self.update_serial_purchase_details(obj, d, a, is_submit)
				
				


	# -------------
	# update stock
	# -------------
	def update_stock(self, values, is_amended = 'No'):
		for v in values:
			sle_id, serial_nos = '', ''
			# get serial nos
			if v["serial_no"]:
				serial_nos = self.get_sr_no_list(v["serial_no"], v['actual_qty'], v['item_code'])

			# reverse quantities for cancel
			if v['is_cancelled'] == 'Yes':
				v['actual_qty'] = -flt(v['actual_qty'])
				# cancel matching entry
				sql("update `tabStock Ledger Entry` set is_cancelled='Yes' where voucher_no=%s \
					and voucher_type=%s", (v['voucher_no'], v['voucher_type']))

			if v["actual_qty"]:
				sle_id = self.make_entry(v)

			get_obj('Warehouse', v["warehouse"]).update_bin(flt(v["actual_qty"]), 0, 0, 0, 0, v["item_code"], \
				v["posting_date"], sle_id, v["posting_time"], '', v["is_cancelled"],v["voucher_type"],v["voucher_no"], is_amended)


	# -----------
	# make entry
	# -----------
	def make_entry(self, args):
		sle = Document(doctype = 'Stock Ledger Entry')
		for k in args.keys():
			# adds warehouse_type
			if k == 'warehouse':
				sle.fields['warehouse_type'] = get_value('Warehouse' , args[k], 'warehouse_type')
			sle.fields[k] = args[k]
		sle_obj = get_obj(doc=sle)
		
		# validate
		sle_obj.validate()
		sle.save(new = 1)
		return sle.name

	def repost(self):
		"""
		Repost everything!
		"""
		for wh in sql("select name from tabWarehouse"):
			get_obj('Warehouse', wh[0]).repost_stock()
