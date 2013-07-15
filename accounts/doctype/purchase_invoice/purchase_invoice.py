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

from webnotes.utils import add_days, cint, cstr, flt, formatdate
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _
from setup.utils import get_company_currency

import webnotes.defaults

sql = webnotes.conn.sql
	
from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl 
		self.tname = 'Purchase Invoice Item'
		self.fname = 'entries'
		
	def validate(self):
		super(DocType, self).validate()
		
		self.po_required()
		self.pr_required()
		self.check_active_purchase_items()
		self.check_conversion_rate()
		self.validate_bill_no_date()
		self.validate_bill_no()
		self.validate_reference_value()
		self.validate_credit_acc()
		self.clear_unallocated_advances("Purchase Invoice Advance", "advance_allocation_details")
		self.check_for_acc_head_of_supplier()
		self.check_for_stopped_status()

		self.po_list, self.pr_list = [], []
		for d in getlist(self.doclist, 'entries'):
			self.validate_supplier(d)
			self.validate_po_pr(d)
			if not d.purchase_order in self.po_list:
				self.po_list.append(d.purchase_order)
			if not d.purhcase_receipt in self.pr_list:
				self.pr_list.append(d.purchase_receipt)


		if not self.doc.is_opening:
			self.doc.is_opening = 'No'

		self.set_aging_date()

		#set against account for credit to
		self.set_against_expense_account()

		#FY validation
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,
		 	self.doc.posting_date,'Posting Date')
		
		self.validate_write_off_account()
		self.update_raw_material_cost()
		self.update_valuation_rate("entries")

	def get_credit_to(self):
		acc_head = sql("""select name, credit_days from `tabAccount` 
			where (name = %s or (master_name = %s and master_type = 'supplier')) 
			and docstatus != 2 and company = %s""", 
			(cstr(self.doc.supplier) + " - " + self.company_abbr, 
			self.doc.supplier, self.doc.company))

		ret = {}
		if acc_head and acc_head[0][0]:
			ret['credit_to'] = acc_head[0][0]
			if not self.doc.due_date:
				ret['due_date'] = add_days(cstr(self.doc.posting_date), acc_head and cint(acc_head[0][1]) or 0)
		elif not acc_head:
			msgprint("%s does not have an Account Head in %s. You must first create it from the Supplier Master" % (self.doc.supplier, self.doc.company))
		return ret
		
	def get_cust(self):
		ret = {}
		if self.doc.credit_to:
			acc = webnotes.conn.get_value('Account',self.doc.credit_to,['master_name', 'credit_days'])
			ret['supplier'] = acc[0]
			ret['due_date'] = add_days(cstr(self.doc.posting_date), acc and cint(acc[1]) or 0)
			
		return ret
		
	def get_default_values(self, args):
		if isinstance(args, basestring):
			import json
			args = json.loads(args)
		
		out = webnotes._dict()
		
		item = webnotes.conn.sql("""select name, purchase_account, cost_center,
			is_stock_item from `tabItem` where name=%s""", args.get("item_code"), as_dict=1)
		
		if item and item[0]:
			item = item[0]
			
			if cint(webnotes.defaults.get_global_default("auto_inventory_accounting")) and \
				item.is_stock_item == "Yes":
					# unset expense head for stock item and auto inventory accounting
					out.expense_head = out.cost_center = None
			else:
				if not args.get("expense_head"):
					out.expense_head = item.purchase_account
				if not args.get("cost_center"):
					out.cost_center = item.cost_center
		
		return out
			
	def pull_details(self):
		if self.doc.purchase_receipt_main:
			self.validate_duplicate_docname('purchase_receipt')
			self.doclist = get_obj('DocType Mapper', 'Purchase Receipt-Purchase Invoice').dt_map('Purchase Receipt', 'Purchase Invoice', self.doc.purchase_receipt_main, self.doc, self.doclist, "[['Purchase Receipt', 'Purchase Invoice'], ['Purchase Receipt Item', 'Purchase Invoice Item'], ['Purchase Taxes and Charges','Purchase Taxes and Charges']]")

		elif self.doc.purchase_order_main:
			self.validate_duplicate_docname('purchase_order')
			self.doclist = get_obj('DocType Mapper', 'Purchase Order-Purchase Invoice').dt_map('Purchase Order', 'Purchase Invoice', self.doc.purchase_order_main, self.doc, self.doclist, "[['Purchase Order', 'Purchase Invoice'],['Purchase Order Item', 'Purchase Invoice Item'], ['Purchase Taxes and Charges','Purchase Taxes and Charges']]")
		
		self.get_expense_account('entries')

		ret = self.get_credit_to()
		if ret.has_key('credit_to'):
			self.doc.credit_to = ret['credit_to']

	def get_expense_account(self, doctype):
		for d in getlist(self.doclist, doctype):			
			if d.item_code:
				d.fields.update(self.get_default_values(d.fields))

	def get_advances(self):
		super(DocType, self).get_advances(self.doc.credit_to, 
			"Purchase Invoice Advance", "advance_allocation_details", "debit")
		
	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)

	def load_default_taxes(self):
		self.doclist = get_obj('Purchase Common').load_default_taxes(self)
	
	
	def get_purchase_tax_details(self):
		self.doclist =  get_obj('Purchase Common').get_purchase_tax_details(self)


	def get_rate1(self,acc):
		rate = sql("select tax_rate from `tabAccount` where name='%s'"%(acc))
		ret={'add_tax_rate' :rate and flt(rate[0][0]) or 0 }
		return ret

	def validate_duplicate_docname(self,doctype):
		for d in getlist(self.doclist, 'entries'): 
			if doctype == 'purchase_receipt' and cstr(self.doc.purchase_receipt_main) == cstr(d.purchase_receipt):
				msgprint(cstr(self.doc.purchase_receipt_main) + " purchase receipt details have already been pulled.")
				raise Exception , " Validation Error. "

			if doctype == 'purchase_order' and cstr(self.doc.purchase_order_main) == cstr(d.purchase_order) and not d.purchase_receipt:
				msgprint(cstr(self.doc.purchase_order_main) + " purchase order details have already been pulled.")
				raise Exception , " Validation Error. "

	def check_active_purchase_items(self):
		for d in getlist(self.doclist, 'entries'):
			if d.item_code:		# extra condn coz item_code is not mandatory in PV
				valid_item = sql("select docstatus,is_purchase_item from tabItem where name = %s",d.item_code)
				if valid_item[0][0] == 2:
					msgprint("Item : '%s' is Inactive, you can restore it from Trash" %(d.item_code))
					raise Exception
				if not valid_item[0][1] == 'Yes':
					msgprint("Item : '%s' is not Purchase Item"%(d.item_code))
					raise Exception
						
	def check_conversion_rate(self):
		default_currency = get_company_currency(self.doc.company)		
		if not default_currency:
			msgprint('Message: Please enter default currency in Company Master')
			raise Exception
		if (self.doc.currency == default_currency and flt(self.doc.conversion_rate) != 1.00) or not self.doc.conversion_rate or (self.doc.currency != default_currency and flt(self.doc.conversion_rate) == 1.00):
			msgprint("Message: Please Enter Appropriate Conversion Rate.")
			raise Exception				

	# 1. Check whether bill is already booked against this bill no. or not
	# 2. Add Remarks
	# ---------------------------------------------------------------------
	def validate_bill_no(self):
		if self.doc.bill_no and self.doc.bill_no.lower().strip()	not in ['na', 'not applicable', 'none']:
			b_no = sql("select bill_no, name, ifnull(is_opening,'') from `tabPurchase Invoice` where bill_no = '%s' and credit_to = '%s' and docstatus = 1 and name != '%s' " % (self.doc.bill_no, self.doc.credit_to, self.doc.name))
			if b_no and cstr(b_no[0][2]) == cstr(self.doc.is_opening):
				msgprint("Please check you have already booked expense against Bill No. %s in Purchase Invoice %s" % (cstr(b_no[0][0]), cstr(b_no[0][1])))
				raise Exception , "Validation Error"
			if not self.doc.remarks:
				self.doc.remarks = (self.doc.remarks or '') + "\n" + ("Against Bill %s dated %s" % (self.doc.bill_no, formatdate(self.doc.bill_date)))
		else:
			if not self.doc.remarks:
				self.doc.remarks = "No Remarks"
					
	# Validate Bill No Date
	# ---------------------
	def validate_bill_no_date(self):
		if self.doc.bill_no and not self.doc.bill_date and self.doc.bill_no.lower().strip() not in ['na', 'not applicable', 'none']:
			msgprint(_("Please enter Bill Date"), raise_exception=1)

	# 1. Credit To Account Exists
	# 2. Is a Credit Account
	# 3. Is not a PL Account
	# ----------------------------
	def validate_credit_acc(self):
		acc = sql("select debit_or_credit, is_pl_account from tabAccount where name = %s", 
			self.doc.credit_to)
		if not acc:
			msgprint("Account: "+ self.doc.credit_to + "does not exist")
			raise Exception
		elif acc[0][0] and acc[0][0] != 'Credit':
			msgprint("Account: "+ self.doc.credit_to + "is not a credit account")
			raise Exception
		elif acc[0][1] and acc[0][1] != 'No':
			msgprint("Account: "+ self.doc.credit_to + "is a pl account")
			raise Exception
	
	# Validate Acc Head of Supplier and Credit To Account entered
	# ------------------------------------------------------------
	def check_for_acc_head_of_supplier(self): 
		if self.doc.supplier and self.doc.credit_to:
			acc_head = sql("select master_name from `tabAccount` where name = %s", self.doc.credit_to)
			
			if (acc_head and cstr(acc_head[0][0]) != cstr(self.doc.supplier)) or (not acc_head and (self.doc.credit_to != cstr(self.doc.supplier) + " - " + self.company_abbr)):
				msgprint("Credit To: %s do not match with Supplier: %s for Company: %s.\n If both correctly entered, please select Master Type and Master Name in account master." %(self.doc.credit_to,self.doc.supplier,self.doc.company), raise_exception=1)
				
	# Check for Stopped PO
	# ---------------------
	def check_for_stopped_status(self):
		check_list = []
		for d in getlist(self.doclist,'entries'):
			if d.purchase_order and not d.purchase_order in check_list and not d.purchase_receipt:
				check_list.append(d.purhcase_order)
				stopped = sql("select name from `tabPurchase Order` where status = 'Stopped' and name = '%s'" % d.purchase_order)
				if stopped:
					msgprint("One cannot do any transaction against 'Purchase Order' : %s, it's status is 'Stopped'" % (d.purhcase_order))
					raise Exception
					
	# Validate Supplier
	# -----------------
	def validate_supplier(self, d):
		supplier = ''
		if d.purchase_order and not d.purchase_order in self.po_list:
			supplier = sql("select supplier from `tabPurchase Order` where name = '%s'" % d.purchase_order)[0][0]
			if supplier and not cstr(self.doc.supplier) == cstr(supplier):
				msgprint("Supplier name %s do not match with supplier name	of purhase order: %s." %(self.doc.supplier,cstr(d.purchase_order)))
				raise Exception , " Validation Error "

		if d.purchase_receipt and not d.purchase_receipt in self.pr_list:
			supplier = sql("select supplier from `tabPurchase Receipt` where name = '%s'" % d.purchase_receipt)[0][0]
			if supplier and not cstr(self.doc.supplier) == cstr(supplier):
				msgprint("Supplier name %s do not match with supplier name	of %s %s." %(self.doc.supplier,cstr(d.purchase_receipt)))
				raise Exception , " Validation Error "

	# Validate values with reference document
	#----------------------------------------
	def validate_reference_value(self):
		get_obj('DocType Mapper', 'Purchase Order-Purchase Invoice', with_children = 1).validate_reference_value(self, self.doc.name)

				
	# Validate PO and PR
	# -------------------
	def validate_po_pr(self, d):
		# check po / pr for qty and rates and currency and conversion rate

		# currency, import_rate must be equal to currency, import_rate of purchase order
		if d.purchase_order and not d.purchase_order in self.po_list:
			# currency
			currency = cstr(sql("select currency from `tabPurchase Order` where name = '%s'" % d.purchase_order)[0][0])
			if not cstr(currency) == cstr(self.doc.currency):
				msgprint("Purchase Order: " + cstr(d.purchase_order) + " currency : " + cstr(currency) + " does not match with currency of current document.")
				raise Exception
			# import_rate
			rate = flt(sql('select import_rate from `tabPurchase Order Item` where item_code=%s and parent=%s and name = %s', (d.item_code, d.purchase_order, d.po_detail))[0][0])
			if abs(rate - flt(d.import_rate)) > 1 and cint(webnotes.defaults.get_global_default('maintain_same_rate')):
				msgprint("Import Rate for %s in the Purchase Order is %s. Rate must be same as Purchase Order Rate" % (d.item_code,rate))
				raise Exception
									
		if d.purchase_receipt and not d.purchase_receipt in self.pr_list:
			# currency , conversion_rate
			data = sql("select currency, conversion_rate from `tabPurchase Receipt` where name = '%s'" % d.purchase_receipt, as_dict = 1)
			if not cstr(data[0]['currency']) == cstr(self.doc.currency):
				msgprint("Purchase Receipt: " + cstr(d.purchase_receipt) + " currency : " + cstr(data[0]['currency']) + " does not match with currency of current document.")
				raise Exception
					
	def set_aging_date(self):
		if self.doc.is_opening != 'Yes':
			self.doc.aging_date = self.doc.posting_date
		elif not self.doc.aging_date:
			msgprint("Aging Date is mandatory for opening entry")
			raise Exception
			
	def set_against_expense_account(self):
		auto_inventory_accounting = \
			cint(webnotes.defaults.get_global_default("auto_inventory_accounting"))

		if auto_inventory_accounting:
			stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")
		
		against_accounts = []
		for item in self.doclist.get({"parentfield": "entries"}):
			if auto_inventory_accounting and item.item_code in self.stock_items:
				# in case of auto inventory accounting, against expense account is always
				# Stock Received But Not Billed for a stock item
				item.expense_head = item.cost_center = None
				
				if stock_not_billed_account not in against_accounts:
					against_accounts.append(stock_not_billed_account)
			
			elif not item.expense_head:
				msgprint(_("""Expense account is mandatory for item: """) + (item.item_code or item.item_name), 
					raise_exception=1)
			
			elif item.expense_head not in against_accounts:
				# if no auto_inventory_accounting or not a stock item
				against_accounts.append(item.expense_head)
				
		self.doc.against_expense_account = ",".join(against_accounts)

	def po_required(self):
		res = sql("select value from `tabSingles` where doctype = 'Global Defaults' and field = 'po_required'")
		if res and res[0][0] == 'Yes':
			 for d in getlist(self.doclist,'entries'):
				 if not d.purchase_order:
					 msgprint("Purchse Order No. required against item %s"%d.item_code)
					 raise Exception

	def pr_required(self):
		res = sql("select value from `tabSingles` where doctype = 'Global Defaults' and field = 'pr_required'")
		if res and res[0][0] == 'Yes':
			 for d in getlist(self.doclist,'entries'):
				 if not d.purchase_receipt:
					 msgprint("Purchase Receipt No. required against item %s"%d.item_code)
					 raise Exception

	def validate_write_off_account(self):
		if self.doc.write_off_amount and not self.doc.write_off_account:
			msgprint("Please enter Write Off Account", raise_exception=1)

	def check_prev_docstatus(self):
		for d in getlist(self.doclist,'entries'):
			if d.purchase_order:
				submitted = sql("select name from `tabPurchase Order` where docstatus = 1 and name = '%s'" % d.purchase_order)
				if not submitted:
					msgprint("Purchase Order : "+ cstr(d.purchase_order) +" is not submitted")
					raise Exception , "Validation Error."
			if d.purchase_receipt:
				submitted = sql("select name from `tabPurchase Receipt` where docstatus = 1 and name = '%s'" % d.purchase_receipt)
				if not submitted:
					msgprint("Purchase Receipt : "+ cstr(d.purchase_receipt) +" is not submitted")
					raise Exception , "Validation Error."
					
					
	def update_against_document_in_jv(self):
		"""
			Links invoice and advance voucher:
				1. cancel advance voucher
				2. split into multiple rows if partially adjusted, assign against voucher
				3. submit advance voucher
		"""
		
		lst = []
		for d in getlist(self.doclist, 'advance_allocation_details'):
			if flt(d.allocated_amount) > 0:
				args = {
					'voucher_no' : d.journal_voucher, 
					'voucher_detail_no' : d.jv_detail_no, 
					'against_voucher_type' : 'Purchase Invoice', 
					'against_voucher'  : self.doc.name,
					'account' : self.doc.credit_to, 
					'is_advance' : 'Yes', 
					'dr_or_cr' : 'debit', 
					'unadjusted_amt' : flt(d.advance_amount),
					'allocated_amt' : flt(d.allocated_amount)
				}
				lst.append(args)
		
		if lst:
			from accounts.utils import reconcile_against_document
			reconcile_against_document(lst)

	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)

		self.check_prev_docstatus()
		
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype,self.doc.company, self.doc.grand_total)
		
		
		# this sequence because outstanding may get -negative
		self.make_gl_entries()
				
		self.update_against_document_in_jv()
		purchase_controller.update_prevdoc_detail(self, is_submit = 1)


	def make_gl_entries(self):
		from accounts.general_ledger import make_gl_entries
		auto_inventory_accounting = \
			cint(webnotes.defaults.get_global_default("auto_inventory_accounting"))
		
		gl_entries = []
		
		# parent's gl entry
		if self.doc.grand_total:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.doc.credit_to,
					"against": self.doc.against_expense_account,
					"credit": self.doc.total_amount_to_pay,
					"remarks": self.doc.remarks,
					"against_voucher": self.doc.name,
					"against_voucher_type": self.doc.doctype,
				})
			)
	
		# tax table gl entries
		valuation_tax = 0
		for tax in self.doclist.get({"parentfield": "purchase_tax_details"}):
			if tax.category in ("Total", "Valuation and Total") and flt(tax.tax_amount):
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.doc.credit_to,
						"debit": tax.add_deduct_tax == "Add" and tax.tax_amount or 0,
						"credit": tax.add_deduct_tax == "Deduct" and tax.tax_amount or 0,
						"remarks": self.doc.remarks,
						"cost_center": tax.cost_center
					})
				)
			
			# accumulate valuation tax
			if tax.category in ("Valuation", "Valuation and Total") and flt(tax.tax_amount):
				valuation_tax += (tax.add_deduct_tax == "Add" and 1 or -1) * flt(tax.tax_amount)
					
		# item gl entries
		stock_item_and_auto_inventory_accounting = False
		if auto_inventory_accounting:
			stock_account = self.get_company_default("stock_received_but_not_billed")
			
		for item in self.doclist.get({"parentfield": "entries"}):
			if auto_inventory_accounting and item.item_code in self.stock_items:
				if flt(item.valuation_rate):
					# if auto inventory accounting enabled and stock item, 
					# then do stock related gl entries
					# expense will be booked in sales invoice
					stock_item_and_auto_inventory_accounting = True
					
					valuation_amt = (flt(item.amount) + flt(item.item_tax_amount) + 
						flt(item.rm_supp_cost))
					
					gl_entries.append(
						self.get_gl_dict({
							"account": stock_account,
							"against": self.doc.credit_to,
							"debit": valuation_amt,
							"remarks": self.doc.remarks or "Accounting Entry for Stock"
						})
					)
			
			elif flt(item.amount):
				# if not a stock item or auto inventory accounting disabled, book the expense
				gl_entries.append(
					self.get_gl_dict({
						"account": item.expense_head,
						"against": self.doc.credit_to,
						"debit": item.amount,
						"remarks": self.doc.remarks,
						"cost_center": item.cost_center
					})
				)
				
		if stock_item_and_auto_inventory_accounting and valuation_tax:
			# credit valuation tax amount in "Expenses Included In Valuation"
			# this will balance out valuation amount included in cost of goods sold
			gl_entries.append(
				self.get_gl_dict({
					"account": self.get_company_default("expenses_included_in_valuation"),
					"cost_center": self.get_company_default("stock_adjustment_cost_center"),
					"against": self.doc.credit_to,
					"credit": valuation_tax,
					"remarks": self.doc.remarks or "Accounting Entry for Stock"
				})
			)
		
		# writeoff account includes petty difference in the invoice amount 
		# and the amount that is paid
		if self.doc.write_off_account and flt(self.doc.write_off_amount):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.doc.write_off_account,
					"against": self.doc.credit_to,
					"credit": flt(self.doc.write_off_amount),
					"remarks": self.doc.remarks,
					"cost_center": self.doc.write_off_cost_center
				})
			)
		
		if gl_entries:
			make_gl_entries(gl_entries, cancel=(self.doc.docstatus == 2))

	def on_cancel(self):
		from accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doc.doctype, self.doc.name, "against_voucher")
		get_obj(dt = 'Purchase Common').update_prevdoc_detail(self, is_submit = 0)
		
		self.make_cancel_gl_entries()
		
	def on_update(self):
		pass
		
	def update_raw_material_cost(self):
		if self.sub_contracted_items:
			for d in self.doclist.get({"parentfield": "entries"}):
				rm_cost = webnotes.conn.sql(""" select raw_material_cost / quantity 
					from `tabBOM` where item = %s and is_default = 1 and docstatus = 1 
					and is_active = 1 """, (d.item_code,))
				rm_cost = rm_cost and flt(rm_cost[0][0]) or 0
				
				d.conversion_factor = d.conversion_factor or flt(webnotes.conn.get_value(
					"UOM Conversion Detail", {"parent": d.item_code, "uom": d.uom}, 
					"conversion_factor")) or 1
		
				d.rm_supp_cost = rm_cost * flt(d.qty) * flt(d.conversion_factor)