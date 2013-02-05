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

from webnotes.utils import cint, cstr, flt, getdate, nowdate, formatdate
from webnotes.model.doc import addchild
from webnotes.model.wrapper import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _
from setup.utils import get_company_currency

get_value = webnotes.conn.get_value

from utilities.transaction_base import TransactionBase


@webnotes.whitelist()
def get_comp_base_currency(arg=None):
	""" get default currency of company"""
	res = webnotes.conn.sql("""select default_currency from `tabCompany`
			where name = %s""", webnotes.form_dict.get('company'))
	return res and res[0][0] or None

@webnotes.whitelist()
def get_price_list_currency(arg=None):
	""" Get all currency in which price list is maintained"""
	plc = webnotes.conn.sql("select distinct ref_currency from `tabItem Price` where price_list_name = %s", webnotes.form_dict['price_list'])
	plc = [d[0] for d in plc]
	base_currency = get_comp_base_currency(webnotes.form_dict['company'])
	return plc, base_currency


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


	# Get Sales Person Details
	# ==========================
	
	# TODO: To be deprecated if not in use
	def get_sales_person_details(self, obj):
		if obj.doc.doctype != 'Quotation':
			obj.doclist = obj.doc.clear_table(obj.doclist,'sales_team')
			idx = 0
			for d in webnotes.conn.sql("select sales_person, allocated_percentage, allocated_amount, incentives from `tabSales Team` where parent = '%s'" % obj.doc.customer):
				ch = addchild(obj.doc, 'sales_team', 'Sales Team', obj.doclist)
				ch.sales_person = d and cstr(d[0]) or ''
				ch.allocated_percentage = d and flt(d[1]) or 0
				ch.allocated_amount = d and flt(d[2]) or 0
				ch.incentives = d and flt(d[3]) or 0
				ch.idx = idx
				idx += 1
		return obj.doclist


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


	# Get customer's primary shipping details
	# ==============================================================
	def get_shipping_details(self, obj = ''):
		det = webnotes.conn.sql("select name, ship_to, shipping_address from `tabShipping Address` where customer = '%s' and docstatus != 2 and ifnull(is_primary_address, 'Yes') = 'Yes'" %(obj.doc.customer), as_dict = 1)
		obj.doc.ship_det_no = det and det[0]['name'] or ''
		obj.doc.ship_to = det and det[0]['ship_to'] or ''
		obj.doc.shipping_address = det and det[0]['shipping_address'] or ''


	# get invoice details
	# ====================
	def get_invoice_details(self, obj = ''):
		if obj.doc.company:
			acc_head = webnotes.conn.sql("select name from `tabAccount` where name = '%s' and docstatus != 2" % (cstr(obj.doc.customer) + " - " + webnotes.conn.get_value('Company', obj.doc.company, 'abbr')))
			obj.doc.debit_to = acc_head and acc_head[0][0] or ''

	
	
	# Get Item Details
	# ===============================================================
	def get_item_details(self, args, obj):
		import json
		if not obj.doc.price_list_name:
			msgprint("Please Select Price List before selecting Items")
			raise Exception
		item = webnotes.conn.sql("select description, item_name, brand, item_group, stock_uom, default_warehouse, default_income_account, default_sales_cost_center, description_html, barcode from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or end_of_life >	now() or end_of_life = '0000-00-00') and (is_sales_item = 'Yes' or is_service_item = 'Yes')" % (args['item_code']), as_dict=1)
		tax = webnotes.conn.sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , args['item_code'])
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'description'			: item and item[0]['description_html'] or item[0]['description'],
			'barcode'				: item and item[0]['barcode'] or '',
			'item_group'			: item and item[0]['item_group'] or '',
			'item_name'				: item and item[0]['item_name'] or '',
			'brand'					: item and item[0]['brand'] or '',
			'stock_uom'				: item and item[0]['stock_uom'] or '',
			'reserved_warehouse'	: item and item[0]['default_warehouse'] or '',
			'warehouse'				: item and item[0]['default_warehouse'] or args.get('warehouse'),
			'income_account'		: item and item[0]['default_income_account'] or args.get('income_account'),
			'cost_center'			: item and item[0]['default_sales_cost_center'] or args.get('cost_center'),
			'qty'					: 1.00,	 # this is done coz if item once fetched is fetched again thn its qty shld be reset to 1
			'adj_rate'				: 0,
			'amount'				: 0,
			'export_amount'			: 0,
			'item_tax_rate'			: json.dumps(t),
			'batch_no'				: ''
		}
		if(obj.doc.price_list_name and item):	#this is done to fetch the changed BASIC RATE and REF RATE based on PRICE LIST
			base_ref_rate =	self.get_ref_rate(args['item_code'], obj.doc.price_list_name, obj.doc.price_list_currency, obj.doc.plc_conversion_rate)
			ret['ref_rate'] = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			ret['export_rate'] = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			ret['base_ref_rate'] = flt(base_ref_rate)
			ret['basic_rate'] = flt(base_ref_rate)
			
		if ret['warehouse'] or ret['reserved_warehouse']:
			av_qty = self.get_available_qty({'item_code': args['item_code'], 'warehouse': ret['warehouse'] or ret['reserved_warehouse']})
			ret.update(av_qty)
			
		# get customer code for given item from Item Customer Detail
		customer_item_code_row = webnotes.conn.sql("""\
			select ref_code from `tabItem Customer Detail`
			where parent = %s and customer_name = %s""",
			(args['item_code'], obj.doc.customer))
		if customer_item_code_row and customer_item_code_row[0][0]:
			ret['customer_item_code'] = customer_item_code_row[0][0]
		
		return ret


	def get_item_defaults(self, args):
		item = webnotes.conn.sql("""select default_warehouse, default_income_account, default_sales_cost_center from `tabItem` 
			where name = '%s' and (ifnull(end_of_life,'') = '' or end_of_life > now() or end_of_life = '0000-00-00') 
			and (is_sales_item = 'Yes' or is_service_item = 'Yes') """ % (args['item_code']), as_dict=1)
		ret = {
			'reserved_warehouse'	: item and item[0]['default_warehouse'] or '',
			'warehouse'				: item and item[0]['default_warehouse'] or args.get('warehouse'),
			'income_account'		: item and item[0]['default_income_account'] or args.get('income_account'),
			'cost_center'			: item and item[0]['default_sales_cost_center'] or args.get('cost_center')
		}

		return ret

	def get_available_qty(self,args):
		tot_avail_qty = webnotes.conn.sql("select projected_qty, actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (args['item_code'], args['warehouse']), as_dict=1)
		ret = {
			 'projected_qty' : tot_avail_qty and flt(tot_avail_qty[0]['projected_qty']) or 0,
			 'actual_qty' : tot_avail_qty and flt(tot_avail_qty[0]['actual_qty']) or 0
		}
		return ret

	
	# ***************** Get Ref rate as entered in Item Master ********************
	def get_ref_rate(self, item_code, price_list_name, price_list_currency, plc_conv_rate):
		ref_rate = webnotes.conn.sql("select ref_rate from `tabItem Price` where parent = %s and price_list_name = %s and ref_currency = %s", (item_code, price_list_name, price_list_currency))
		base_ref_rate = ref_rate and flt(ref_rate[0][0]) * flt(plc_conv_rate) or 0
		return base_ref_rate

	def get_barcode_details(self, barcode):
		item = webnotes.conn.sql("select name, end_of_life, is_sales_item, is_service_item \
			from `tabItem` where barcode = %s", barcode, as_dict=1)
		ret = {}
		if not item:
			msgprint("""No item found for this barcode: %s. 
				May be barcode not updated in item master. Please check""" % barcode)
		elif item[0]['end_of_life'] and getdate(cstr(item[0]['end_of_life'])) < nowdate():
			msgprint("Item: %s has been expired. Please check 'End of Life' field in item master" % item[0]['name'])
		elif item[0]['is_sales_item'] == 'No' and item[0]['is_service_item'] == 'No':
			msgprint("Item: %s is not a sales or service item" % item[0]['name'])
		elif len(item) > 1:
			msgprint("There are multiple item for this barcode. \nPlease select item code manually")
		else:
			ret = {'item_code': item and item[0]['name'] or ''}
			
		return ret

		
	# ****** Re-cancellculates Basic Rate & amount based on Price List Selected ******
	def get_adj_percent(self, obj): 
		for d in getlist(obj.doclist, obj.fname):
			base_ref_rate = self.get_ref_rate(d.item_code, obj.doc.price_list_name, obj.doc.price_list_currency, obj.doc.plc_conversion_rate)
			d.adj_rate = 0
			d.ref_rate = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			d.basic_rate = flt(base_ref_rate)
			d.base_ref_rate = flt(base_ref_rate)
			d.export_rate = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			d.amount = flt(d.qty)*flt(base_ref_rate)
			d.export_amount = flt(d.qty)*flt(base_ref_rate)/flt(obj.doc.conversion_rate)


	# Load Default Taxes
	# ====================
	def load_default_taxes(self, obj):
		if cstr(obj.doc.charge):
			return self.get_other_charges(obj)
		else:
			return self.get_other_charges(obj, 1)

		
	# Get other charges from Master
	# =================================================================================
	def get_other_charges(self,obj, default=0):
		obj.doclist = obj.doc.clear_table(obj.doclist, 'other_charges')
		if not getlist(obj.doclist, 'other_charges'):
			if default: add_cond = 'ifnull(t2.is_default,0) = 1'
			else: add_cond = 't1.parent = "'+cstr(obj.doc.charge)+'"'
			idx = 0
			other_charge = webnotes.conn.sql("""\
				select t1.*
				from
					`tabSales Taxes and Charges` t1,
					`tabSales Taxes and Charges Master` t2
				where
					t1.parent = t2.name and
					t2.company = '%s' and
					%s
				order by t1.idx""" % (obj.doc.company, add_cond), as_dict=1)
			from webnotes.model import default_fields
			for other in other_charge:
				# remove default fields like parent, parenttype etc.
				# from query results
				for field in default_fields:
					if field in other: del other[field]

				d = addchild(obj.doc, 'other_charges', 'Sales Taxes and Charges',
					obj.doclist)
				d.fields.update(other)
				d.rate = flt(d.rate)
				d.tax_amount = flt(d.tax_rate)
				d.included_in_print_rate = cint(d.included_in_print_rate)
				d.idx = idx
				idx += 1
		return obj.doclist
			
	# Get TERMS AND CONDITIONS
	# =======================================================================================
	def get_tc_details(self,obj):
		r = webnotes.conn.sql("select terms from `tabTerms and Conditions` where name = %s", obj.doc.tc_name)
		if r: obj.doc.terms = r[0][0]

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
		
	# Get Commission rate
	# =======================================================================
	def get_comm_rate(self, sales_partner, obj):

		comm_rate = webnotes.conn.sql("select commission_rate from `tabSales Partner` where name = '%s' and docstatus != 2" %(sales_partner), as_dict=1)
		if comm_rate:
			total_comm = flt(comm_rate[0]['commission_rate']) * flt(obj.doc.net_total) / 100
			ret = {
				'commission_rate'		 :	comm_rate and flt(comm_rate[0]['commission_rate']) or 0,
				'total_commission'		:	flt(total_comm)
			}
			return ret
		else:
			msgprint("Business Associate : %s does not exist in the system." % (sales_partner))
			raise Exception

	
	# To verify whether rate entered in details table does not exceed max discount %
	# =======================================================================================
	def validate_max_discount(self,obj, detail_table):
		for d in getlist(obj.doclist, detail_table):
			discount = webnotes.conn.sql("select max_discount from tabItem where name = '%s'" %(d.item_code),as_dict = 1)
			if discount and discount[0]['max_discount'] and (flt(d.adj_rate)>flt(discount[0]['max_discount'])):
				msgprint("You cannot give more than " + cstr(discount[0]['max_discount']) + " % discount on Item Code : "+cstr(d.item_code))
				raise Exception


	# Get sum of allocated % of sales person (it should be 100%)
	# ========================================================================
	# it indicates % contribution of sales person in sales
	def get_allocated_sum(self,obj):
		sum = 0
		for d in getlist(obj.doclist,'sales_team'):
			sum += flt(d.allocated_percentage)
		if (flt(sum) != 100) and getlist(obj.doclist,'sales_team'):
			msgprint("Total Allocated % of Sales Persons should be 100%")
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
			msgprint("Please Enter Appropriate Conversion Rate for Price List Currency to Base Currency ( (%s --> %s)" % (obj.doc.price_list_currency, default_currency), raise_exception = 1)
	


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
		for d in getlist(obj.doclist,obj.fname):
			reserved_wh, reserved_qty = '', 0		# used for delivery note
			qty = flt(d.qty)
			if is_stopped:
				qty = flt(d.qty) > flt(d.delivered_qty) and flt(flt(d.qty) - flt(d.delivered_qty)) or 0
				
			if d.prevdoc_doctype == 'Sales Order':
				# used in delivery note to reduce reserved_qty 
				# Eg.: if SO qty is 10 and there is tolerance of 20%, then it will allow DN of 12.
				# But in this case reserved qty should only be reduced by 10 and not 12.

				tot_qty, max_qty, tot_amt, max_amt, reserved_wh = self.get_curr_and_ref_doc_details(d.doctype, 'prevdoc_detail_docname', d.prevdoc_detail_docname, obj.doc.name, obj.doc.doctype)
				if((flt(tot_qty) + flt(qty) > flt(max_qty))):
					reserved_qty = -(flt(max_qty)-flt(tot_qty))
				else:	
					reserved_qty = - flt(qty)
					
			if obj.doc.doctype == 'Sales Order':
				reserved_wh = d.reserved_warehouse
						
			if self.has_sales_bom(d.item_code):
				for p in getlist(obj.doclist, 'packing_details'):
					if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
						# the packing details table's qty is already multiplied with parent's qty
						il.append({
							'warehouse': p.warehouse,
							'reserved_warehouse': reserved_wh,
							'item_code': p.item_code,
							'qty': flt(p.qty),
							'reserved_qty': (flt(p.qty)/qty)*(reserved_qty),
							'uom': p.uom,
							'batch_no': cstr(p.batch_no).strip(),
							'serial_no': cstr(p.serial_no).strip(),
							'name': d.name
						})
			else:
				il.append({
					'warehouse': d.warehouse,
					'reserved_warehouse': reserved_wh,
					'item_code': d.item_code,
					'qty': qty,
					'reserved_qty': reserved_qty,
					'uom': d.stock_uom,
					'batch_no': cstr(d.batch_no).strip(),
					'serial_no': cstr(d.serial_no).strip(),
					'name': d.name
				})
		return il


	def get_curr_and_ref_doc_details(self, curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name, curr_parent_doctype):
		""" Get qty, amount already billed or delivered against curr line item for current doctype
			For Eg: SO-RV get total qty, amount from SO and also total qty, amount against that SO in RV
		"""
		#Get total qty, amt of current doctype (eg RV) except for qty, amt of this transaction
		if curr_parent_doctype == 'Installation Note':
			curr_det = webnotes.conn.sql("select sum(qty) from `tab%s` where %s = '%s' and docstatus = 1 and parent != '%s'"% (curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name))
			qty, amt = curr_det and flt(curr_det[0][0]) or 0, 0
		else:
			curr_det = webnotes.conn.sql("select sum(qty), sum(amount) from `tab%s` where %s = '%s' and docstatus = 1 and parent != '%s'"% (curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name))
			qty, amt = curr_det and flt(curr_det[0][0]) or 0, curr_det and flt(curr_det[0][1]) or 0

		# get total qty of ref doctype
		so_det = webnotes.conn.sql("select qty, amount, reserved_warehouse from `tabSales Order Item` where name = '%s' and docstatus = 1"% ref_tab_dn)
		max_qty, max_amt, res_wh = so_det and flt(so_det[0][0]) or 0, so_det and flt(so_det[0][1]) or 0, so_det and cstr(so_det[0][2]) or ''
		return qty, max_qty, amt, max_amt, res_wh


	# Make Packing List from Sales BOM
	# =======================================================================
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
		obj.doclist = filter(lambda d: d.name not in delete_list, obj.doclist)
		
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
					
					
	# ****** Check for Item.is_sales_item = 'Yes' and Item.docstatus != 2 *******
	def check_active_sales_items(self,obj):
		for d in getlist(obj.doclist, obj.fname):
			if d.item_code:		# extra condn coz item_code is not mandatory in RV
				valid_item = webnotes.conn.sql("select docstatus,is_sales_item, is_service_item from tabItem where name = %s",d.item_code)
				if valid_item and valid_item[0][0] == 2:
					msgprint("Item : '%s' does not exist in system." %(d.item_code))
					raise Exception
				sales_item = valid_item and valid_item[0][1] or 'No'
				service_item = valid_item and valid_item[0][2] or 'No'
				if sales_item == 'No' and service_item == 'No':
					msgprint("Item : '%s' is neither Sales nor Service Item"%(d.item_code))
					raise Exception


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

	def update_prevdoc_detail(self, is_submit, obj):
		StatusUpdater(obj, is_submit).update()




#
# make item code readonly if (detail no is set)
#


class StatusUpdater:
	"""
		Updates the status of the calling records
		
		From Delivery Note 
			- Update Delivered Qty
			- Update Percent
			- Validate over delivery
			
		From Sales Invoice 
			- Update Billed Amt
			- Update Percent
			- Validate over billing
			
		From Installation Note
			- Update Installed Qty
			- Update Percent Qty
			- Validate over installation
	"""
	def __init__(self, obj, is_submit):
		self.obj = obj # caller object
		self.is_submit = is_submit
		self.tolerance = {}
		self.global_tolerance = None
	
	def update(self):
		self.update_all_qty()
		self.validate_all_qty()
	
	def validate_all_qty(self):
		"""
			Validates over-billing / delivery / installation in Delivery Note, Sales Invoice, Installation Note
			To called after update_all_qty
		"""
		if self.obj.doc.doctype=='Delivery Note':
			self.validate_qty({
				'source_dt'		:'Delivery Note Item',
				'compare_field'	:'delivered_qty',
				'compare_ref_field'	:'qty',
				'target_dt'		:'Sales Order Item',
				'join_field'	:'prevdoc_detail_docname'
			})
		elif self.obj.doc.doctype=='Sales Invoice':
			self.validate_qty({
				'source_dt'		:'Sales Invoice Item',
				'compare_field'	:'billed_amt',
				'compare_ref_field'	:'export_amount',
				'target_dt'		:'Sales Order Item',
				'join_field'	:'so_detail'
			})
			self.validate_qty({
				'source_dt'		:'Sales Invoice Item',
				'compare_field'	:'billed_amt',
				'compare_ref_field'	:'export_amount',
				'target_dt'		:'Delivery Note Item',
				'join_field'	:'dn_detail'
			}, no_tolerance =1)
		elif self.obj.doc.doctype=='Installation Note':
			self.validate_qty({
				'source_dt'		:'Installation Item Details',
				'compare_field'	:'installed_qty',
				'compare_ref_field'	:'qty',
				'target_dt'		:'Delivery Note Item',
				'join_field'	:'dn_detail'
			}, no_tolerance =1)

	
	def get_tolerance_for(self, item_code):
		"""
			Returns the tolerance for the item, if not set, returns global tolerance
		"""
		if self.tolerance.get(item_code):
			return self.tolerance[item_code]
		
		tolerance = flt(webnotes.conn.get_value('Item',item_code,'tolerance') or 0)

		if not tolerance:
			if self.global_tolerance == None:
				self.global_tolerance = flt(webnotes.conn.get_value('Global Defaults',None,'tolerance') or 0)
			tolerance = self.global_tolerance
		
		self.tolerance[item_code] = tolerance
		return tolerance
		
	def check_overflow_with_tolerance(self, item, args):
		"""
			Checks if there is overflow condering a relaxation tolerance
		"""
	
		# check if overflow is within tolerance
		tolerance = self.get_tolerance_for(item['item_code'])
		overflow_percent = ((item[args['compare_field']] - item[args['compare_ref_field']]) / item[args['compare_ref_field']]) * 100
	
		if overflow_percent - tolerance > 0.01:
			item['max_allowed'] = flt(item[args['compare_ref_field']] * (100+tolerance)/100)
			item['reduce_by'] = item[args['compare_field']] - item['max_allowed']
		
			msgprint("""
				Row #%(idx)s: Max %(compare_ref_field)s allowed for <b>Item %(item_code)s</b> against <b>%(parenttype)s %(parent)s</b> is <b>%(max_allowed)s</b>. 
				
				If you want to increase your overflow tolerance, please increase tolerance %% in Global Defaults or Item master. 
				
				Or, you must reduce the %(compare_ref_field)s by %(reduce_by)s
				
				Also, please check if the order item has already been billed in the Sales Order""" % item, raise_exception=1)

	def validate_qty(self, args, no_tolerance=None):
		"""
			Validates qty at row level
		"""
		# get unique transactions to update
		for d in self.obj.doclist:
			if d.doctype == args['source_dt']:
				args['name'] = d.fields[args['join_field']]

				# get all qty where qty > compare_field
				item = webnotes.conn.sql("""
					select item_code, `%(compare_ref_field)s`, `%(compare_field)s`, parenttype, parent from `tab%(target_dt)s` 
					where `%(compare_ref_field)s` < `%(compare_field)s` and name="%(name)s" and docstatus=1
					""" % args, as_dict=1)
				if item:
					item = item[0]
					item['idx'] = d.idx
					item['compare_ref_field'] = args['compare_ref_field'].replace('_', ' ')

					if not item[args['compare_ref_field']]:
						msgprint("As %(compare_ref_field)s for item: %(item_code)s in %(parenttype)s: %(parent)s is zero, system will not check over-delivery or over-billed" % item)
					elif no_tolerance:
						item['reduce_by'] = item[args['compare_field']] - item[args['compare_ref_field']]
						if item['reduce_by'] > .01:
							msgprint("""
								Row #%(idx)s: Max %(compare_ref_field)s allowed for <b>Item %(item_code)s</b> against 
								<b>%(parenttype)s %(parent)s</b> is <b>""" % item 
								+ cstr(item[args['compare_ref_field']]) + """</b>. 
							
								You must reduce the %(compare_ref_field)s by %(reduce_by)s""" % item, raise_exception=1)
					
					else:
						self.check_overflow_with_tolerance(item, args)
						
	
	def update_all_qty(self):
		"""
			Updates delivered / billed / installed qty in Sales Order & Delivery Note
		"""
		if self.obj.doc.doctype=='Delivery Note':
			self.update_qty({
				'target_field'			:'delivered_qty',
				'target_dt'				:'Sales Order Item',
				'target_parent_dt'		:'Sales Order',
				'target_parent_field'	:'per_delivered',
				'target_ref_field'		:'qty',
				'source_dt'				:'Delivery Note Item',
				'source_field'			:'qty',
				'join_field'			:'prevdoc_detail_docname',
				'percent_join_field'	:'prevdoc_docname',
				'status_field'			:'delivery_status',
				'keyword'				:'Delivered'
			})
			
		elif self.obj.doc.doctype=='Sales Invoice':
			self.update_qty({
				'target_field'			:'billed_amt',
				'target_dt'				:'Sales Order Item',
				'target_parent_dt'		:'Sales Order',
				'target_parent_field'	:'per_billed',
				'target_ref_field'		:'export_amount',
				'source_dt'				:'Sales Invoice Item',
				'source_field'			:'export_amount',
				'join_field'			:'so_detail',
				'percent_join_field'	:'sales_order',
				'status_field'			:'billing_status',
				'keyword'				:'Billed'
			})

			self.update_qty({
				'target_field'			:'billed_amt',
				'target_dt'				:'Delivery Note Item',
				'target_parent_dt'		:'Delivery Note',
				'target_parent_field'	:'per_billed',
				'target_ref_field'		:'export_amount',
				'source_dt'				:'Sales Invoice Item',
				'source_field'			:'export_amount',
				'join_field'			:'dn_detail',
				'percent_join_field'	:'delivery_note',
				'status_field'			:'billing_status',
				'keyword'				:'Billed'
			})
			
			if cint(self.obj.doc.is_pos) == 1:
				self.update_qty({
					'target_field'			:'delivered_qty',
					'target_dt'				:'Sales Order Item',
					'target_parent_dt'		:'Sales Order',
					'target_parent_field'	:'per_delivered',
					'target_ref_field'		:'qty',
					'source_dt'				:'Sales Invoice Item',
					'source_field'			:'qty',
					'join_field'			:'so_detail',
					'percent_join_field'	:'sales_order',
					'status_field'			:'delivery_status',
					'keyword'				:'Delivered'
				})
				
		if self.obj.doc.doctype=='Installation Note':
			self.update_qty({
				'target_field'			:'installed_qty',
				'target_dt'				:'Delivery Note Item',
				'target_parent_dt'		:'Delivery Note',
				'target_parent_field'	:'per_installed',
				'target_ref_field'		:'qty',
				'source_dt'				:'Installation Note Item',
				'source_field'			:'qty',
				'join_field'			:'prevdoc_detail_docname',
				'percent_join_field'	:'prevdoc_docname',
				'status_field'			:'installation_status',
				'keyword'				:'Installed'
			})


	def update_qty(self, args):
		"""
			Updates qty at row level
		"""
		# condition to include current record (if submit or no if cancel)
		if self.is_submit:
			args['cond'] = ' or parent="%s"' % self.obj.doc.name
		else:
			args['cond'] = ' and parent!="%s"' % self.obj.doc.name
		
		# update quantities in child table
		for d in self.obj.doclist:
			if d.doctype == args['source_dt']:
				# updates qty in the child table
				args['detail_id'] = d.fields.get(args['join_field'])
			
				if args['detail_id']:
					webnotes.conn.sql("""
						update 
							`tab%(target_dt)s` 
						set 
							%(target_field)s = (select sum(%(source_field)s) from `tab%(source_dt)s` where `%(join_field)s`="%(detail_id)s" and (docstatus=1 %(cond)s))
						where
							name="%(detail_id)s"            
					""" % args)			
		
		# get unique transactions to update
		for name in set([d.fields.get(args['percent_join_field']) for d in self.obj.doclist if d.doctype == args['source_dt']]):
			if name:
				args['name'] = name
				
				# update percent complete in the parent table
				webnotes.conn.sql("""
					update 
						`tab%(target_parent_dt)s` 
					set 
						%(target_parent_field)s = 
							(select sum(if(%(target_ref_field)s > ifnull(%(target_field)s, 0), %(target_field)s, %(target_ref_field)s))/sum(%(target_ref_field)s)*100 from `tab%(target_dt)s` where parent="%(name)s"), 
						modified = now()
					where
						name="%(name)s"
					""" % args)

				# update field
				if args['status_field']:
					webnotes.conn.sql("""
						update
							`tab%(target_parent_dt)s` 
						set
							%(status_field)s = if(ifnull(%(target_parent_field)s,0)<0.001, 'Not %(keyword)s', 
									if(%(target_parent_field)s>=99.99, 'Fully %(keyword)s', 'Partly %(keyword)s')
								)
						where
							name="%(name)s"
					""" % args)

