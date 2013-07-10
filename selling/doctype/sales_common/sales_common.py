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

from webnotes.utils import cint, cstr, flt, getdate, nowdate
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
from setup.utils import get_company_currency

get_value = webnotes.conn.get_value

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

		self.doctype_dict = {
			'Sales Order'		: 'Sales Order Item',
			'Delivery Note'		: 'Delivery Note Item',
			'Sales Invoice':'Sales Invoice Item',
			'Installation Note' : 'Installation Note Item'
		}
												 
		self.ref_doctype_dict= {}

		self.next_dt_detail = {
			'delivered_qty' : 'Delivery Note Item',
			'billed_qty'		: 'Sales Invoice Item',
			'installed_qty' : 'Installation Note Item'}

		self.msg = []

	# Get customer's contact person details
	# ==============================================================
	def get_contact_details(self, obj = '', primary = 0):
		cond = " and contact_name = '"+cstr(obj.doc.contact_person)+"'"
		if primary: cond = " and is_primary_contact = 'Yes'"
		contact = webnotes.conn.sql("select contact_name, contact_no, email_id, contact_address from `tabContact` where customer = '%s' and docstatus != 2 %s" %(obj.doc.customer, cond), as_dict = 1)
		if not contact:
			return
		c = contact[0]
		obj.doc.contact_person = c['contact_name'] or ''
		obj.doc.contact_no = c['contact_no'] or ''
		obj.doc.email_id = c['email_id'] or ''
		obj.doc.customer_mobile_no = c['contact_no'] or ''
		if c['contact_address']:
			obj.doc.customer_address = c['contact_address']


	# get invoice details
	# ====================
	def get_invoice_details(self, obj = ''):
		if obj.doc.company:
			acc_head = webnotes.conn.sql("select name from `tabAccount` where name = '%s' and docstatus != 2" % (cstr(obj.doc.customer) + " - " + webnotes.conn.get_value('Company', obj.doc.company, 'abbr')))
			obj.doc.debit_to = acc_head and acc_head[0][0] or ''
			
#---------------------------------------- Get Tax Details -------------------------------#
	def get_tax_details(self, item_code, obj):
		import json
		tax = webnotes.conn.sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , item_code)
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'item_tax_rate'		:	tax and json.dumps(t) or ''
		}
		return ret

	# Get Serial No Details
	# ==========================================================================
	def get_serial_details(self, serial_no, obj):
		import json
		item = webnotes.conn.sql("select item_code, make, label,brand, description from `tabSerial No` where name = '%s' and docstatus != 2" %(serial_no), as_dict=1)
		tax = webnotes.conn.sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , item[0]['item_code'])
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'item_code'				: item and item[0]['item_code'] or '',
			'make'						 : item and item[0]['make'] or '',
			'label'						: item and item[0]['label'] or '',
			'brand'						: item and item[0]['brand'] or '',
			'description'			: item and item[0]['description'] or '',
			'item_tax_rate'		: json.dumps(t)
		}
		return ret
		
	# To verify whether rate entered in details table does not exceed max discount %
	# =======================================================================================
	def validate_max_discount(self,obj, detail_table):
		for d in getlist(obj.doclist, detail_table):
			discount = webnotes.conn.sql("select max_discount from tabItem where name = '%s'" %(d.item_code),as_dict = 1)
			if discount and discount[0]['max_discount'] and (flt(d.adj_rate)>flt(discount[0]['max_discount'])):
				msgprint("You cannot give more than " + cstr(discount[0]['max_discount']) + " % discount on Item Code : "+cstr(d.item_code))
				raise Exception
			
	# Check Conversion Rate (i.e. it will not allow conversion rate to be 1 for Currency other than default currency set in Global Defaults)
	# ===========================================================================
	def check_conversion_rate(self, obj):
		default_currency = get_company_currency(obj.doc.company)
		if not default_currency:
			msgprint('Message: Please enter default currency in Company Master')
			raise Exception		
		if (obj.doc.currency == default_currency and flt(obj.doc.conversion_rate) != 1.00) or not obj.doc.conversion_rate or (obj.doc.currency != default_currency and flt(obj.doc.conversion_rate) == 1.00):
			msgprint("Please Enter Appropriate Conversion Rate for Customer's Currency to Base Currency (%s --> %s)" % (obj.doc.currency, default_currency), raise_exception = 1)
	
		if (obj.doc.price_list_currency == default_currency and flt(obj.doc.plc_conversion_rate) != 1.00) or not obj.doc.plc_conversion_rate or (obj.doc.price_list_currency != default_currency and flt(obj.doc.plc_conversion_rate) == 1.00):
			msgprint("Please Enter Appropriate Conversion Rate for Price List Currency to Base Currency (%s --> %s)" % (obj.doc.price_list_currency, default_currency), raise_exception = 1)
	


	# Get Tax rate if account type is TAX
	# =========================================================================
	def get_rate(self, arg):
		arg = eval(arg)
		rate = webnotes.conn.sql("select account_type, tax_rate from `tabAccount` where name = '%s' and docstatus != 2" %(arg['account_head']), as_dict=1)
		ret = {'rate' : 0}
		if arg['charge_type'] == 'Actual' and rate[0]['account_type'] == 'Tax':
			msgprint("You cannot select ACCOUNT HEAD of type TAX as your CHARGE TYPE is 'ACTUAL'")
			ret = {
				'account_head'	:	''
			}
		elif rate[0]['account_type'] in ['Tax', 'Chargeable'] and not arg['charge_type'] == 'Actual':
			ret = {
				'rate'	:	rate and flt(rate[0]['tax_rate']) or 0
			}
		return ret


	def get_item_list(self, obj, is_stopped=0):
		"""get item list"""
		il = []
		for d in getlist(obj.doclist, obj.fname):
			reserved_warehouse = ""
			reserved_qty_for_main_item = 0
			
			if obj.doc.doctype == "Sales Order":
				reserved_warehouse = d.reserved_warehouse
				if flt(d.qty) > flt(d.delivered_qty):
					reserved_qty_for_main_item = flt(d.qty) - flt(d.delivered_qty)
				
			if obj.doc.doctype == "Delivery Note" and d.prevdoc_doctype == 'Sales Order':
				# if SO qty is 10 and there is tolerance of 20%, then it will allow DN of 12.
				# But in this case reserved qty should only be reduced by 10 and not 12
				
				already_delivered_qty = self.get_already_delivered_qty(obj.doc.name, 
					d.prevdoc_docname, d.prevdoc_detail_docname)
				so_qty, reserved_warehouse = self.get_so_qty_and_warehouse(d.prevdoc_detail_docname)
				
				if already_delivered_qty + d.qty > so_qty:
					reserved_qty_for_main_item = -(so_qty - already_delivered_qty)
				else:
					reserved_qty_for_main_item = -flt(d.qty)

			if self.has_sales_bom(d.item_code):
				for p in getlist(obj.doclist, 'packing_details'):
					if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
						# the packing details table's qty is already multiplied with parent's qty
						il.append({
							'warehouse': p.warehouse,
							'reserved_warehouse': reserved_warehouse,
							'item_code': p.item_code,
							'qty': flt(p.qty),
							'reserved_qty': (flt(p.qty)/flt(d.qty)) * reserved_qty_for_main_item,
							'uom': p.uom,
							'batch_no': cstr(p.batch_no).strip(),
							'serial_no': cstr(p.serial_no).strip(),
							'name': d.name
						})
			else:
				il.append({
					'warehouse': d.warehouse,
					'reserved_warehouse': reserved_warehouse,
					'item_code': d.item_code,
					'qty': d.qty,
					'reserved_qty': reserved_qty_for_main_item,
					'uom': d.stock_uom,
					'batch_no': cstr(d.batch_no).strip(),
					'serial_no': cstr(d.serial_no).strip(),
					'name': d.name
				})
		return il

	def get_already_delivered_qty(self, dn, so, so_detail):
		qty = webnotes.conn.sql("""select sum(qty) from `tabDelivery Note Item` 
			where prevdoc_detail_docname = %s and docstatus = 1 
			and prevdoc_doctype = 'Sales Order' and prevdoc_docname = %s 
			and parent != %s""", (so_detail, so, dn))
		return qty and flt(qty[0][0]) or 0.0

	def get_so_qty_and_warehouse(self, so_detail):
		so_item = webnotes.conn.sql("""select qty, reserved_warehouse from `tabSales Order Item`
			where name = %s and docstatus = 1""", so_detail, as_dict=1)
		so_qty = so_item and flt(so_item[0]["qty"]) or 0.0
		so_warehouse = so_item and so_item[0]["reserved_warehouse"] or ""
		return so_qty, so_warehouse

	def has_sales_bom(self, item_code):
		return webnotes.conn.sql("select name from `tabSales BOM` where new_item_code=%s and docstatus != 2", item_code)
	
	def get_sales_bom_items(self, item_code):
		return webnotes.conn.sql("""select t1.item_code, t1.qty, t1.uom 
			from `tabSales BOM Item` t1, `tabSales BOM` t2 
			where t2.new_item_code=%s and t1.parent = t2.name""", item_code, as_dict=1)

	def get_packing_item_details(self, item):
		return webnotes.conn.sql("select item_name, description, stock_uom from `tabItem` where name = %s", item, as_dict = 1)[0]

	def get_bin_qty(self, item, warehouse):
		det = webnotes.conn.sql("select actual_qty, projected_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (item, warehouse), as_dict = 1)
		return det and det[0] or ''

	def update_packing_list_item(self,obj, packing_item_code, qty, warehouse, line):
		bin = self.get_bin_qty(packing_item_code, warehouse)
		item = self.get_packing_item_details(packing_item_code)

		# check if exists
		exists = 0
		for d in getlist(obj.doclist, 'packing_details'):
			if d.parent_item == line.item_code and d.item_code == packing_item_code and d.parent_detail_docname == line.name:
				pi, exists = d, 1
				break

		if not exists:
			pi = addchild(obj.doc, 'packing_details', 'Delivery Note Packing Item', 
				obj.doclist)

		pi.parent_item = line.item_code
		pi.item_code = packing_item_code
		pi.item_name = item['item_name']
		pi.parent_detail_docname = line.name
		pi.description = item['description']
		pi.uom = item['stock_uom']
		pi.qty = flt(qty)
		pi.actual_qty = bin and flt(bin['actual_qty']) or 0
		pi.projected_qty = bin and flt(bin['projected_qty']) or 0
		pi.prevdoc_doctype = line.prevdoc_doctype
		if not pi.warehouse:
			pi.warehouse = warehouse
		if not pi.batch_no:
			pi.batch_no = cstr(line.batch_no)
		pi.idx = self.packing_list_idx
		
		# saved, since this function is called on_update of delivery note
		pi.save()
		
		self.packing_list_idx += 1


	def make_packing_list(self, obj, fname):
		"""make packing list for sales bom item"""
		self.packing_list_idx = 0
		parent_items = []
		for d in getlist(obj.doclist, fname):
			warehouse = fname == "sales_order_details" and d.reserved_warehouse or d.warehouse
			if self.has_sales_bom(d.item_code):
				for i in self.get_sales_bom_items(d.item_code):
					self.update_packing_list_item(obj, i['item_code'], flt(i['qty'])*flt(d.qty), warehouse, d)

				if [d.item_code, d.name] not in parent_items:
					parent_items.append([d.item_code, d.name])
				
		obj.doclist = self.cleanup_packing_list(obj, parent_items)
		
		return obj.doclist
		
	def cleanup_packing_list(self, obj, parent_items):
		"""Remove all those child items which are no longer present in main item table"""
		delete_list = []
		for d in getlist(obj.doclist, 'packing_details'):
			if [d.parent_item, d.parent_detail_docname] not in parent_items:
				# mark for deletion from doclist
				delete_list.append(d.name)

		if not delete_list:
			return obj.doclist
		
		# delete from doclist
		obj.doclist = webnotes.doclist(filter(lambda d: d.name not in delete_list, obj.doclist))
		
		# delete from db
		webnotes.conn.sql("""\
			delete from `tabDelivery Note Packing Item`
			where name in (%s)"""
			% (", ".join(["%s"] * len(delete_list))),
			tuple(delete_list))
			
		return obj.doclist
		

	def get_month(self,date):
		"""Get month based on date (required in sales person and sales partner)"""
		month_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
		month_idx = cint(cstr(date).split('-')[1])-1
		return month_list[month_idx]
		
		
	# **** Check for Stop SO as no transactions can be made against Stopped SO. Need to unstop it. ***
	def check_stop_sales_order(self,obj):
		for d in getlist(obj.doclist,obj.fname):
			ref_doc_name = ''
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_doctype == 'Sales Order':
				ref_doc_name = d.prevdoc_docname
			elif d.fields.has_key('sales_order') and d.sales_order and not d.delivery_note:
				ref_doc_name = d.sales_order
			if ref_doc_name:
				so_status = webnotes.conn.sql("select status from `tabSales Order` where name = %s",ref_doc_name)
				so_status = so_status and so_status[0][0] or ''
				if so_status == 'Stopped':
					msgprint("You cannot do any transaction against Sales Order : '%s' as it is Stopped." %(ref_doc_name))
					raise Exception

	def check_active_sales_items(self,obj):
		for d in getlist(obj.doclist, obj.fname):
			if d.item_code:
				item = webnotes.conn.sql("""select docstatus, is_sales_item, 
					is_service_item, default_income_account from tabItem where name = %s""", 
					d.item_code, as_dict=True)[0]
				if item.is_sales_item == 'No' and item.is_service_item == 'No':
					msgprint("Item : '%s' is neither Sales nor Service Item" % (d.item_code))
					raise Exception
				if d.income_account and not item.default_income_account:
					webnotes.conn.set_value("Item", d.item_code, "default_income_account", d.income_account)


# **************************************************************************************************************************************************

	def check_credit(self,obj,grand_total):
		acc_head = webnotes.conn.sql("select name from `tabAccount` where company = '%s' and master_name = '%s'"%(obj.doc.company, obj.doc.customer))
		if acc_head:
			tot_outstanding = 0
			dbcr = webnotes.conn.sql("select sum(debit), sum(credit) from `tabGL Entry` where account = '%s' and ifnull(is_cancelled, 'No')='No'" % acc_head[0][0])
			if dbcr:
				tot_outstanding = flt(dbcr[0][0])-flt(dbcr[0][1])

			exact_outstanding = flt(tot_outstanding) + flt(grand_total)
			get_obj('Account',acc_head[0][0]).check_credit_limit(acc_head[0][0], obj.doc.company, exact_outstanding)

	def validate_fiscal_year(self, fiscal_year, transaction_date, label):
		import accounts.utils
		accounts.utils.validate_fiscal_year(transaction_date, fiscal_year, label)

	def get_prevdoc_date(self, obj):
		for d in getlist(obj.doclist, obj.fname):
			if d.prevdoc_doctype and d.prevdoc_docname:
				if d.prevdoc_doctype == 'Sales Invoice':
					dt = webnotes.conn.sql("select posting_date from `tab%s` where name = '%s'" % (d.prevdoc_doctype, d.prevdoc_docname))
				else:
					dt = webnotes.conn.sql("select transaction_date from `tab%s` where name = '%s'" % (d.prevdoc_doctype, d.prevdoc_docname))
				d.prevdoc_date = (dt and dt[0][0]) and dt[0][0].strftime('%Y-%m-%d') or ''

def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	from controllers.queries import get_match_cond

	if filters.has_key('warehouse'):
		return webnotes.conn.sql("""select batch_no from `tabStock Ledger Entry` sle 
				where item_code = '%(item_code)s' 
					and warehouse = '%(warehouse)s' 
					and ifnull(is_cancelled, 'No') = 'No' 
					and batch_no like '%(txt)s' 
					and exists(select * from `tabBatch` 
							where name = sle.batch_no 
								and expiry_date >= '%(posting_date)s' 
								and docstatus != 2) 
					%(mcond)s
				group by batch_no having sum(actual_qty) > 0 
				order by batch_no desc 
				limit %(start)s, %(page_len)s """ % {'item_code': filters['item_code'], 
					'warehouse': filters['warehouse'], 'posting_date': filters['posting_date'], 
					'txt': "%%%s%%" % txt, 'mcond':get_match_cond(doctype, searchfield), 
					'start': start, 'page_len': page_len})
	else:
		return webnotes.conn.sql("""select name from tabBatch 
				where docstatus != 2 
					and item = '%(item_code)s' 
					and expiry_date >= '%(posting_date)s' 
					and name like '%(txt)s' 
					%(mcond)s 
				order by name desc 
				limit %(start)s, %(page_len)s""" % {'item_code': filters['item_code'], 
				'posting_date': filters['posting_date'], 'txt': "%%%s%%" % txt, 
				'mcond':get_match_cond(doctype, searchfield),'start': start, 
				'page_len': page_len})