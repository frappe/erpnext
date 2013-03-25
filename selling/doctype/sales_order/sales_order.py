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
import webnotes.utils
import json

from webnotes.utils import cstr, flt, getdate
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
	

from controllers.selling_controller import SellingController

class DocType(SellingController):
	def __init__(self, doc, doclist=None):
		self.doc = doc
		if not doclist: doclist = []
		self.doclist = doclist
		self.tname = 'Sales Order Item'
		self.fname = 'sales_order_details'
		self.person_tname = 'Target Detail'
		self.partner_tname = 'Partner Target Detail'
		self.territory_tname = 'Territory Target Detail'
		
	def pull_quotation_details(self):
		self.doclist = self.doc.clear_table(self.doclist, 'other_charges')
		self.doclist = self.doc.clear_table(self.doclist, 'sales_order_details')
		self.doclist = self.doc.clear_table(self.doclist, 'sales_team')
		self.doclist = self.doc.clear_table(self.doclist, 'tc_details')
		if self.doc.quotation_no:				
			get_obj('DocType Mapper', 'Quotation-Sales Order').dt_map('Quotation', 'Sales Order', self.doc.quotation_no, self.doc, self.doclist, "[['Quotation', 'Sales Order'],['Quotation Item', 'Sales Order Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team'],['TC Detail','TC Detail']]")			
		else:
			msgprint("Please select Quotation whose details need to pull")		

		return cstr(self.doc.quotation_no)
	
	def get_contact_details(self):
		get_obj('Sales Common').get_contact_details(self,0)

	def get_comm_rate(self, sales_partner):
		return get_obj('Sales Common').get_comm_rate(sales_partner, self)

	def get_item_details(self, args=None):
		import json
		args = args and json.loads(args) or {}
		if args.get('item_code'):
			return get_obj('Sales Common').get_item_details(args, self)
		else:
			obj = get_obj('Sales Common')
			for doc in self.doclist:
				if doc.fields.get('item_code'):
					arg = {'item_code':doc.fields.get('item_code'), 'income_account':doc.fields.get('income_account'), 
						'cost_center': doc.fields.get('cost_center'), 'warehouse': doc.fields.get('warehouse')};
					ret = obj.get_item_defaults(arg)
					for r in ret:
						if not doc.fields.get(r):
							doc.fields[r] = ret[r]					

	def get_adj_percent(self, arg=''):
		get_obj('Sales Common').get_adj_percent(self)

	def get_available_qty(self,args):
		return get_obj('Sales Common').get_available_qty(eval(args))
	
	def get_rate(self,arg):
		return get_obj('Sales Common').get_rate(arg)

	def load_default_taxes(self):
		self.doclist = get_obj('Sales Common').load_default_taxes(self)

	def get_other_charges(self):
		self.doclist = get_obj('Sales Common').get_other_charges(self)
 
	def get_tc_details(self):
		return get_obj('Sales Common').get_tc_details(self)

	def check_maintenance_schedule(self):
		nm = sql("select t1.name from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2 where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1", self.doc.name)
		nm = nm and nm[0][0] or ''
		
		if not nm:
			return 'No'

	def check_maintenance_visit(self):
		nm = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1 and t1.completion_status='Fully Completed'", self.doc.name)
		nm = nm and nm[0][0] or ''
		
		if not nm:
			return 'No'

	def validate_fiscal_year(self):
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'Sales Order Date')
	
	def validate_reference_value(self):
		get_obj('DocType Mapper', 'Quotation-Sales Order', with_children = 1).validate_reference_value(self, self.doc.name)

	def validate_mandatory(self):
		# validate transaction date v/s delivery date
		if self.doc.delivery_date:
			if getdate(self.doc.transaction_date) > getdate(self.doc.delivery_date):
				msgprint("Expected Delivery Date cannot be before Sales Order Date")
				raise Exception
		# amendment date is necessary if document is amended
		if self.doc.amended_from and not self.doc.amendment_date:
			msgprint("Please Enter Amendment Date")
			raise Exception
	
	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.doc.po_date and self.doc.delivery_date and getdate(self.doc.po_date) > getdate(self.doc.delivery_date):
			msgprint("Expected Delivery Date cannot be before Purchase Order Date")
			raise Exception	
		
		if self.doc.po_no and self.doc.customer:
			so = webnotes.conn.sql("select name from `tabSales Order` \
				where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
				and customer = %s", (self.doc.po_no, self.doc.name, self.doc.customer))
			if so and so[0][0]:
				msgprint("""Another Sales Order (%s) exists against same PO No and Customer. 
					Please be sure, you are not making duplicate entry.""" % so[0][0])
	
	def validate_for_items(self):
		check_list, flag = [], 0
		chk_dupl_itm = []
		# Sales Order Items Validations
		for d in getlist(self.doclist, 'sales_order_details'):
			if self.doc.quotation_no and cstr(self.doc.quotation_no) == cstr(d.prevdoc_docname):
				flag = 1
			if d.prevdoc_docname:
				if self.doc.quotation_date and getdate(self.doc.quotation_date) > getdate(self.doc.transaction_date):
					msgprint("Sales Order Date cannot be before Quotation Date")
					raise Exception
				# validates whether quotation no in doctype and in table is same
				if not cstr(d.prevdoc_docname) == cstr(self.doc.quotation_no):
					msgprint("Items in table does not belong to the Quotation No mentioned.")
					raise Exception

			# validates whether item is not entered twice
			e = [d.item_code, d.description, d.reserved_warehouse, d.prevdoc_docname or '']
			f = [d.item_code, d.description]

			#check item is stock item
			st_itm = sql("select is_stock_item from `tabItem` where name = %s", d.item_code)

			if st_itm and st_itm[0][0] == 'Yes':
				if not d.reserved_warehouse:
					msgprint("""Please enter Reserved Warehouse for item %s 
						as it is stock Item""" % d.item_code, raise_exception=1)
				
				if e in check_list:
					msgprint("Item %s has been entered twice." % d.item_code)
				else:
					check_list.append(e)
			elif st_itm and st_itm[0][0]== 'No':
				if f in chk_dupl_itm:
					msgprint("Item %s has been entered twice." % d.item_code)
				else:
					chk_dupl_itm.append(f)

			# used for production plan
			d.transaction_date = self.doc.transaction_date
			
			tot_avail_qty = sql("select projected_qty from `tabBin` \
				where item_code = '%s' and warehouse = '%s'" % (d.item_code,d.reserved_warehouse))
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0
		
		if getlist(self.doclist, 'sales_order_details') and self.doc.quotation_no and flag == 0:
			msgprint("There are no items of the quotation selected", raise_exception=1)

	def validate_sales_mntc_quotation(self):
		for d in getlist(self.doclist, 'sales_order_details'):
			if d.prevdoc_docname:
				res = sql("select name from `tabQuotation` where name=%s and order_type = %s", (d.prevdoc_docname, self.doc.order_type))
				if not res:
					msgprint("""Order Type (%s) should be same in Quotation: %s \
						and current Sales Order""" % (self.doc.order_type, d.prevdoc_docname))

	def validate_order_type(self):
		#validate delivery date
		if self.doc.order_type == 'Sales' and not self.doc.delivery_date:
			msgprint("Please enter 'Expected Delivery Date'")
			raise Exception
		
		self.validate_sales_mntc_quotation()

	def validate_proj_cust(self):
		if self.doc.project_name and self.doc.customer_name:
			res = sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in project - %s."%(self.doc.customer,self.doc.project_name,self.doc.project_name))
				raise Exception
	
	def validate(self):
		super(DocType, self).validate()
		
		self.validate_fiscal_year()
		self.validate_order_type()
		self.validate_mandatory()
		self.validate_proj_cust()
		self.validate_po()
		#self.validate_reference_value()
		self.validate_for_items()
		sales_com_obj = get_obj(dt = 'Sales Common')
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.check_conversion_rate(self)

		sales_com_obj.validate_max_discount(self,'sales_order_details')
		sales_com_obj.get_allocated_sum(self)
		self.doclist = sales_com_obj.make_packing_list(self,'sales_order_details')
		
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])

		if not self.doc.billing_status: self.doc.billing_status = 'Not Billed'
		if not self.doc.delivery_status: self.doc.delivery_status = 'Not Delivered'
		
	def check_prev_docstatus(self):
		for d in getlist(self.doclist, 'sales_order_details'):
			cancel_quo = sql("select name from `tabQuotation` where docstatus = 2 and name = '%s'" % d.prevdoc_docname)
			if cancel_quo:
				msgprint("Quotation :" + cstr(cancel_quo[0][0]) + " is already cancelled !")
				raise Exception , "Validation Error. "
	
	def update_enquiry_status(self, prevdoc, flag):
		enq = sql("select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s", prevdoc)
		if enq:
			sql("update `tabOpportunity` set status = %s where name=%s",(flag,enq[0][0]))

	def update_prevdoc_status(self, flag):
		for d in getlist(self.doclist, 'sales_order_details'):
			if d.prevdoc_docname:
				if flag=='submit':
					sql("update `tabQuotation` set status = 'Order Confirmed' where name=%s",d.prevdoc_docname)
					
					#update enquiry
					self.update_enquiry_status(d.prevdoc_docname, 'Order Confirmed')
				elif flag == 'cancel':
					chk = sql("select t1.name from `tabSales Order` t1, `tabSales Order Item` t2 where t2.parent = t1.name and t2.prevdoc_docname=%s and t1.name!=%s and t1.docstatus=1", (d.prevdoc_docname,self.doc.name))
					if not chk:
						sql("update `tabQuotation` set status = 'Submitted' where name=%s",d.prevdoc_docname)
						
						#update enquiry
						self.update_enquiry_status(d.prevdoc_docname, 'Quotation Sent')

	def on_submit(self):
		self.check_prev_docstatus()		
		self.update_stock_ledger(update_stock = 1)

		get_obj('Sales Common').check_credit(self,self.doc.grand_total)
		
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.grand_total, self)
		
		self.update_prevdoc_status('submit')
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self):
		# Cannot cancel stopped SO
		if self.doc.status == 'Stopped':
			msgprint("Sales Order : '%s' cannot be cancelled as it is Stopped. Unstop it for any further transactions" %(self.doc.name))
			raise Exception
		self.check_nextdoc_docstatus()
		self.update_stock_ledger(update_stock = -1)
		
		self.update_prevdoc_status('cancel')
		
		webnotes.conn.set(self.doc, 'status', 'Cancelled')
		
	def check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = sql("select t1.name from `tabDelivery Note` t1,`tabDelivery Note Item` t2 where t1.name = t2.parent and t2.prevdoc_docname = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_dn:
			msgprint("Delivery Note : " + cstr(submit_dn[0][0]) + " has been submitted against " + cstr(self.doc.doctype) + ". Please cancel Delivery Note : " + cstr(submit_dn[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
			
		# Checks Sales Invoice
		submit_rv = sql("select t1.name from `tabSales Invoice` t1,`tabSales Invoice Item` t2 where t1.name = t2.parent and t2.sales_order = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Sales Invoice : " + cstr(submit_rv[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Sales Invoice : "+ cstr(submit_rv[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
			
		#check maintenance schedule
		submit_ms = sql("select t1.name from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2 where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1",self.doc.name)
		if submit_ms:
			msgprint("Maintenance Schedule : " + cstr(submit_ms[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Maintenance Schedule : "+ cstr(submit_ms[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
			
		# check maintenance visit
		submit_mv = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1",self.doc.name)
		if submit_mv:
			msgprint("Maintenance Visit : " + cstr(submit_mv[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Maintenance Visit : " + cstr(submit_mv[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
		
		# check production order
		pro_order = sql("""select name from `tabProduction Order` where sales_order = %s and docstatus = 1""", self.doc.name)
		if pro_order:
			msgprint("""Production Order: %s exists against this sales order. 
				Please cancel production order first and then cancel this sales order""" % 
				pro_order[0][0], raise_exception=1)

	def check_modified_date(self):
		mod_db = sql("select modified from `tabSales Order` where name = '%s'" % self.doc.name)
		date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		if date_diff and date_diff[0][0]:
			msgprint("%s: %s has been modified after you have opened. Please Refresh"
				% (self.doc.doctype, self.doc.name), raise_exception=1)

	def stop_sales_order(self):
		self.check_modified_date()
		self.update_stock_ledger(update_stock = -1,is_stopped = 1)
		webnotes.conn.set(self.doc, 'status', 'Stopped')
		msgprint("""%s: %s has been Stopped. To make transactions against this Sales Order 
			you need to Unstop it.""" % (self.doc.doctype, self.doc.name))

	def unstop_sales_order(self):
		self.check_modified_date()
		self.update_stock_ledger(update_stock = 1,is_stopped = 1)
		webnotes.conn.set(self.doc, 'status', 'Submitted')
		msgprint("%s: %s has been Unstopped" % (self.doc.doctype, self.doc.name))


	def update_stock_ledger(self, update_stock, is_stopped = 0):
		for d in self.get_item_list(is_stopped):
			if webnotes.conn.get_value("Item", d['item_code'], "is_stock_item") == "Yes":
				args = {
					"item_code": d['item_code'],
					"reserved_qty": flt(update_stock) * flt(d['reserved_qty']),
					"posting_date": self.doc.transaction_date,
					"voucher_type": self.doc.doctype,
					"voucher_no": self.doc.name,
					"is_amended": self.doc.amended_from and 'Yes' or 'No'
				}
				get_obj('Warehouse', d['reserved_warehouse']).update_bin(args)
				
				
	def get_item_list(self, is_stopped):
		return get_obj('Sales Common').get_item_list( self, is_stopped)

	def on_update(self):
		pass
		
@webnotes.whitelist()
def get_orders():
	# find customer id
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
	
	if customer:
		orders = webnotes.conn.sql("""select 
			name, creation, currency from `tabSales Order`
			where customer=%s
			and docstatus=1
			order by creation desc
			limit 20
			""", customer, as_dict=1)
		for order in orders:
			order.items = webnotes.conn.sql("""select 
				item_name, qty, export_rate, export_amount, delivered_qty, stock_uom
				from `tabSales Order Item` 
				where parent=%s 
				order by idx""", order.name, as_dict=1)
		return orders
	else:
		return []
		
def get_website_args():	
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
	bean = webnotes.bean("Sales Order", webnotes.form_dict.name)
	if bean.doc.customer != customer:
		return {
			"doc": {"name": "Not Allowed"}
		}
	else:
		return {
			"doc": bean.doc,
			"doclist": bean.doclist,
			"webnotes": webnotes,
			"utils": webnotes.utils
		}
		
def get_currency_and_number_format():
	return {
		"global_number_format": webnotes.conn.get_default("number_format") or "#,###.##",
		"currency": webnotes.conn.get_default("currency"),
		"currency_symbols": json.dumps(dict(webnotes.conn.sql("""select name, symbol
			from tabCurrency where ifnull(enabled,0)=1""")))
	}