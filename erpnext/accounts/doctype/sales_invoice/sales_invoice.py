# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults

from frappe.utils import add_days, cint, cstr, date_diff, flt, getdate, nowdate, \
	get_first_day, get_last_day

from frappe.utils import comma_and, get_url
from frappe.model.doc import make_autoname
from frappe.model.bean import getlist
from frappe.model.code import get_obj
from frappe import _, msgprint

from erpnext.accounts.party import get_party_account, get_due_date

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}

from erpnext.controllers.selling_controller import SellingController

class SalesInvoice(SellingController):
	tname = 'Sales Invoice Item'
	fname = 'entries'
	status_updater = [{
		'source_dt': 'Sales Invoice Item',
		'target_field': 'billed_amt',
		'target_ref_field': 'amount',
		'target_dt': 'Sales Order Item',
		'join_field': 'so_detail',
		'target_parent_dt': 'Sales Order',
		'target_parent_field': 'per_billed',
		'source_field': 'amount',
		'join_field': 'so_detail',
		'percent_join_field': 'sales_order',
		'status_field': 'billing_status',
		'keyword': 'Billed'
	}]

	def validate(self):
		super(DocType, self).validate()
		self.validate_posting_time()
		self.so_dn_required()
		self.validate_proj_cust()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.check_stop_sales_order("sales_order")
		self.validate_customer_account()
		self.validate_debit_acc()
		self.validate_fixed_asset_account()
		self.clear_unallocated_advances("Sales Invoice Advance", "advance_adjustment_details")
		self.add_remarks()

		if cint(self.doc.is_pos):
			self.validate_pos()
			self.validate_write_off_account()

		if cint(self.doc.update_stock):
			self.validate_item_code()
			self.update_current_stock()
			self.validate_delivery_note()

		if not self.doc.is_opening:
			self.doc.is_opening = 'No'

		self.set_aging_date()
		self.set_against_income_account()
		self.validate_c_form()
		self.validate_time_logs_are_submitted()
		self.validate_recurring_invoice()
		self.validate_multiple_billing("Delivery Note", "dn_detail", "amount", 
			"delivery_note_details")

	def on_submit(self):
		if cint(self.doc.update_stock) == 1:			
			self.update_stock_ledger()
		else:
			# Check for Approving Authority
			if not self.doc.recurring_id:
				get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, 
				 	self.doc.company, self.doc.grand_total, self)
				
		self.check_prev_docstatus()
		
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_for_zero_amount_refdoc("Sales Order")
		
		# this sequence because outstanding may get -ve
		self.make_gl_entries()
		self.check_credit_limit(self.doc.debit_to)

		if not cint(self.doc.is_pos) == 1:
			self.update_against_document_in_jv()

		self.update_c_form()
		self.update_time_log_batch(self.doc.name)
		self.convert_to_recurring()

	def before_cancel(self):
		self.update_time_log_batch(None)

	def on_cancel(self):
		if cint(self.doc.update_stock) == 1:
			self.update_stock_ledger()
		
		self.check_stop_sales_order("sales_order")
		
		from erpnext.accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doc.doctype, self.doc.name, "against_invoice")

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_for_zero_amount_refdoc("Sales Order")
		
		self.make_cancel_gl_entries()
		
	def update_status_updater_args(self):
		if cint(self.doc.update_stock):
			self.status_updater.append({
				'source_dt':'Sales Invoice Item',
				'target_dt':'Sales Order Item',
				'target_parent_dt':'Sales Order',
				'target_parent_field':'per_delivered',
				'target_field':'delivered_qty',
				'target_ref_field':'qty',
				'source_field':'qty',
				'join_field':'so_detail',
				'percent_join_field':'sales_order',
				'status_field':'delivery_status',
				'keyword':'Delivered',
				'second_source_dt': 'Delivery Note Item',
				'second_source_field': 'qty',
				'second_join_field': 'prevdoc_detail_docname'
			})
		
	def on_update_after_submit(self):
		self.validate_recurring_invoice()
		self.convert_to_recurring()
		
	def get_portal_page(self):
		return "invoice" if self.doc.docstatus==1 else None
		
	def set_missing_values(self, for_validate=False):
		self.set_pos_fields(for_validate)
		
		if not self.doc.debit_to:
			self.doc.debit_to = get_party_account(self.doc.company, self.doc.customer, "Customer")
		if not self.doc.due_date:
			self.doc.due_date = get_due_date(self.doc.posting_date, self.doc.customer, "Customer",
				self.doc.debit_to, self.doc.company)
		
		super(DocType, self).set_missing_values(for_validate)
					
	def update_time_log_batch(self, sales_invoice):
		for d in self.doclist.get({"doctype":"Sales Invoice Item"}):
			if d.time_log_batch:
				tlb = frappe.bean("Time Log Batch", d.time_log_batch)
				tlb.doc.sales_invoice = sales_invoice
				tlb.update_after_submit()

	def validate_time_logs_are_submitted(self):
		for d in self.doclist.get({"doctype":"Sales Invoice Item"}):
			if d.time_log_batch:
				status = frappe.db.get_value("Time Log Batch", d.time_log_batch, "status")
				if status!="Submitted":
					frappe.msgprint(_("Time Log Batch status must be 'Submitted'") + ":" + d.time_log_batch,
						raise_exception=True)

	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from pos settings"""
		if cint(self.doc.is_pos) != 1:
			return
		
		from erpnext.stock.get_item_details import get_pos_settings_item_details, get_pos_settings	
		pos = get_pos_settings(self.doc.company)
			
		if pos:
			if not for_validate and not self.doc.customer:
				self.doc.customer = pos.customer
				# self.set_customer_defaults()

			for fieldname in ('territory', 'naming_series', 'currency', 'taxes_and_charges', 'letter_head', 'tc_name',
				'selling_price_list', 'company', 'select_print_heading', 'cash_bank_account'):
					if (not for_validate) or (for_validate and not self.doc.fields.get(fieldname)):
						self.doc.fields[fieldname] = pos.get(fieldname)
						
			if not for_validate:
				self.doc.update_stock = cint(pos.get("update_stock"))

			# set pos values in items
			for item in self.get("entries"):
				if item.fields.get('item_code'):
					for fname, val in get_pos_settings_item_details(pos, 
						frappe._dict(item.fields), pos).items():
						
						if (not for_validate) or (for_validate and not item.fields.get(fname)):
							item.fields[fname] = val

			# fetch terms	
			if self.doc.tc_name and not self.doc.terms:
				self.doc.terms = frappe.db.get_value("Terms and Conditions", self.doc.tc_name, "terms")
			
			# fetch charges
			if self.doc.charge and not len(self.get("other_charges")):
				self.set_taxes("other_charges", "taxes_and_charges")
	
	def get_advances(self):
		super(DocType, self).get_advances(self.doc.debit_to, 
			"Sales Invoice Advance", "advance_adjustment_details", "credit")
		
	def get_company_abbr(self):
		return frappe.db.sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]

	def update_against_document_in_jv(self):
		"""
			Links invoice and advance voucher:
				1. cancel advance voucher
				2. split into multiple rows if partially adjusted, assign against voucher
				3. submit advance voucher
		"""
		
		lst = []
		for d in self.get('advance_adjustment_details'):
			if flt(d.allocated_amount) > 0:
				args = {
					'voucher_no' : d.journal_voucher, 
					'voucher_detail_no' : d.jv_detail_no, 
					'against_voucher_type' : 'Sales Invoice', 
					'against_voucher'  : self.doc.name,
					'account' : self.doc.debit_to, 
					'is_advance' : 'Yes', 
					'dr_or_cr' : 'credit', 
					'unadjusted_amt' : flt(d.advance_amount),
					'allocated_amt' : flt(d.allocated_amount)
				}
				lst.append(args)
		
		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)
			
	def validate_customer_account(self):
		"""Validates Debit To Account and Customer Matches"""
		if self.doc.customer and self.doc.debit_to and not cint(self.doc.is_pos):
			acc_head = frappe.db.sql("select master_name from `tabAccount` where name = %s and docstatus != 2", self.doc.debit_to)
			
			if (acc_head and cstr(acc_head[0][0]) != cstr(self.doc.customer)) or \
				(not acc_head and (self.doc.debit_to != cstr(self.doc.customer) + " - " + self.get_company_abbr())):
				msgprint("Debit To: %s do not match with Customer: %s for Company: %s.\n If both correctly entered, please select Master Type \
					and Master Name in account master." %(self.doc.debit_to, self.doc.customer,self.doc.company), raise_exception=1)


	def validate_debit_acc(self):
		if frappe.db.get_value("Account", self.doc.debit_to, "report_type") != "Balance Sheet":
			frappe.throw(_("Account must be a balance sheet account"))
			
	def validate_fixed_asset_account(self):
		"""Validate Fixed Asset and whether Income Account Entered Exists"""
		for d in self.get('entries'):
			item = frappe.db.sql("""select name,is_asset_item,is_sales_item from `tabItem` 
				where name = %s and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' 
					or end_of_life > now())""", d.item_code)
			acc =	frappe.db.sql("""select account_type from `tabAccount` 
				where name = %s and docstatus != 2""", d.income_account)
			if not acc:
				msgprint("Account: "+d.income_account+" does not exist in the system", raise_exception=True)
			elif item and item[0][1] == 'Yes' and not acc[0][0] == 'Fixed Asset':
				msgprint("Please select income head with account type 'Fixed Asset' as Item %s is an asset item" % d.item_code, raise_exception=True)				
		
	def validate_with_previous_doc(self):
		super(DocType, self).validate_with_previous_doc(self.tname, {
			"Sales Order": {
				"ref_dn_field": "sales_order",
				"compare_fields": [["customer", "="], ["company", "="], ["project_name", "="],
					["currency", "="]],
			},
			"Delivery Note": {
				"ref_dn_field": "delivery_note",
				"compare_fields": [["customer", "="], ["company", "="], ["project_name", "="],
					["currency", "="]],
			},
		})
		
		if cint(frappe.defaults.get_global_default('maintain_same_sales_rate')):
			super(DocType, self).validate_with_previous_doc(self.tname, {
				"Sales Order Item": {
					"ref_dn_field": "so_detail",
					"compare_fields": [["rate", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True
				},
				"Delivery Note Item": {
					"ref_dn_field": "dn_detail",
					"compare_fields": [["rate", "="]],
					"is_child_table": True
				}
			})
			

	def set_aging_date(self):
		if self.doc.is_opening != 'Yes':
			self.doc.aging_date = self.doc.posting_date
		elif not self.doc.aging_date:
			msgprint("Aging Date is mandatory for opening entry")
			raise Exception
			

	def set_against_income_account(self):
		"""Set against account for debit to account"""
		against_acc = []
		for d in self.get('entries'):
			if d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.doc.against_income_account = ','.join(against_acc)


	def add_remarks(self):
		if not self.doc.remarks: self.doc.remarks = 'No Remarks'


	def so_dn_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		dic = {'Sales Order':'so_required','Delivery Note':'dn_required'}
		for i in dic:
			if frappe.db.get_value('Selling Settings', None, dic[i]) == 'Yes':
				for d in self.get('entries'):
					if frappe.db.get_value('Item', d.item_code, 'is_stock_item') == 'Yes' \
						and not d.fields[i.lower().replace(' ','_')]:
						msgprint("%s is mandatory for stock item which is not mentioed against item: %s"%(i,d.item_code), raise_exception=1)


	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.doc.project_name and self.doc.customer:
			res = frappe.db.sql("""select name from `tabProject` 
				where name = %s and (customer = %s or 
					ifnull(customer,'')='')""", (self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in that project."%(self.doc.customer,self.doc.project_name))
				raise Exception

	def validate_pos(self):
		if not self.doc.cash_bank_account and flt(self.doc.paid_amount):
			msgprint("Cash/Bank Account is mandatory for POS, for making payment entry")
			raise Exception
		if flt(self.doc.paid_amount) + flt(self.doc.write_off_amount) \
				- flt(self.doc.grand_total) > 1/(10**(self.precision("grand_total") + 1)):
			frappe.throw(_("""(Paid amount + Write Off Amount) can not be \
				greater than Grand Total"""))


	def validate_item_code(self):
		for d in self.get('entries'):
			if not d.item_code:
				msgprint("Please enter Item Code at line no : %s to update stock or remove check from Update Stock in Basic Info Tab." % (d.idx),
				raise_exception=True)
				
	def validate_delivery_note(self):
		for d in self.get("entries"):
			if d.delivery_note:
				msgprint("""Stock update can not be made against Delivery Note""", raise_exception=1)


	def validate_write_off_account(self):
		if flt(self.doc.write_off_amount) and not self.doc.write_off_account:
			msgprint("Please enter Write Off Account", raise_exception=1)


	def validate_c_form(self):
		""" Blank C-form no if C-form applicable marked as 'No'"""
		if self.doc.amended_from and self.doc.c_form_applicable == 'No' and self.doc.c_form_no:
			frappe.db.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.doc.amended_from,	self.doc.c_form_no))

			frappe.db.set(self.doc, 'c_form_no', '')
			
	def update_current_stock(self):
		for d in self.get('entries'):
			if d.item_code and d.warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
				d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

		for d in self.get('packing_details'):
			bin = frappe.db.sql("select actual_qty, projected_qty from `tabBin` where item_code =	%s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
			d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0
	 
	
	def get_warehouse(self):
		w = frappe.db.sql("""select warehouse from `tabPOS Setting` 
			where ifnull(user,'') = %s and company = %s""", 
			(frappe.session['user'], self.doc.company))
		w = w and w[0][0] or ''
		if not w:
			ps = frappe.db.sql("""select name, warehouse from `tabPOS Setting` 
				where ifnull(user,'') = '' and company = %s""", self.doc.company)
			if not ps:
				msgprint("To make POS entry, please create POS Setting from Accounts --> POS Setting page and refresh the system.", raise_exception=True)
			elif not ps[0][1]:
				msgprint("Please enter warehouse in POS Setting")
			else:
				w = ps[0][1]
		return w

	def on_update(self):
		if cint(self.doc.update_stock) == 1:
			# Set default warehouse from pos setting
			if cint(self.doc.is_pos) == 1:
				w = self.get_warehouse()
				if w:
					for d in self.get('entries'):
						if not d.warehouse:
							d.warehouse = cstr(w)

			from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
			make_packing_list(self, 'entries')
		else:
			self.set('packing_details', [])
			
		if cint(self.doc.is_pos) == 1:
			if flt(self.doc.paid_amount) == 0:
				if self.doc.cash_bank_account: 
					frappe.db.set(self.doc, 'paid_amount', 
						(flt(self.doc.grand_total) - flt(self.doc.write_off_amount)))
				else:
					# show message that the amount is not paid
					frappe.db.set(self.doc,'paid_amount',0)
					frappe.msgprint("Note: Payment Entry will not be created since 'Cash/Bank Account' was not specified.")
		else:
			frappe.db.set(self.doc,'paid_amount',0)
		
	def check_prev_docstatus(self):
		for d in self.get('entries'):
			if d.sales_order:
				submitted = frappe.db.sql("""select name from `tabSales Order` 
					where docstatus = 1 and name = %s""", d.sales_order)
				if not submitted:
					msgprint("Sales Order : "+ cstr(d.sales_order) +" is not submitted")
					raise Exception , "Validation Error."

			if d.delivery_note:
				submitted = frappe.db.sql("""select name from `tabDelivery Note` 
					where docstatus = 1 and name = %s""", d.delivery_note)
				if not submitted:
					msgprint("Delivery Note : "+ cstr(d.delivery_note) +" is not submitted")
					raise Exception , "Validation Error."

	def update_stock_ledger(self):
		sl_entries = []
		for d in self.get_item_list():
			if frappe.db.get_value("Item", d.item_code, "is_stock_item") == "Yes" \
					and d.warehouse:
				sl_entries.append(self.get_sl_entries(d, {
					"actual_qty": -1*flt(d.qty),
					"stock_uom": frappe.db.get_value("Item", d.item_code, "stock_uom")
				}))
		
		self.make_sl_entries(sl_entries)
		
	def make_gl_entries(self, update_gl_entries_after=True):
		gl_entries = self.get_gl_entries()
		
		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			
			update_outstanding = cint(self.doc.is_pos) and self.doc.write_off_account \
				and 'No' or 'Yes'
			make_gl_entries(gl_entries, cancel=(self.doc.docstatus == 2), 
				update_outstanding=update_outstanding, merge_entries=False)
			
			if update_gl_entries_after and cint(self.doc.update_stock) \
				and cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
					self.update_gl_entries_after()
				
	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import merge_similar_entries
		
		gl_entries = []
		
		self.make_customer_gl_entry(gl_entries)
		
		self.make_tax_gl_entries(gl_entries)
		
		self.make_item_gl_entries(gl_entries)
		
		# merge gl entries before adding pos entries
		gl_entries = merge_similar_entries(gl_entries)
		
		self.make_pos_gl_entries(gl_entries)
		
		return gl_entries
		
	def make_customer_gl_entry(self, gl_entries):
		if self.doc.grand_total:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.doc.debit_to,
					"against": self.doc.against_income_account,
					"debit": self.doc.grand_total,
					"remarks": self.doc.remarks,
					"against_voucher": self.doc.name,
					"against_voucher_type": self.doc.doctype,
				})
			)
				
	def make_tax_gl_entries(self, gl_entries):
		for tax in self.get("other_charges"):
			if flt(tax.tax_amount_after_discount_amount):
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.doc.debit_to,
						"credit": flt(tax.tax_amount_after_discount_amount),
						"remarks": self.doc.remarks,
						"cost_center": tax.cost_center
					})
				)
				
	def make_item_gl_entries(self, gl_entries):			
		# income account gl entries	
		for item in self.get("entries"):
			if flt(item.base_amount):
				gl_entries.append(
					self.get_gl_dict({
						"account": item.income_account,
						"against": self.doc.debit_to,
						"credit": item.base_amount,
						"remarks": self.doc.remarks,
						"cost_center": item.cost_center
					})
				)
				
		# expense account gl entries
		if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")) \
				and cint(self.doc.update_stock):
			gl_entries += super(DocType, self).get_gl_entries()
				
	def make_pos_gl_entries(self, gl_entries):
		if cint(self.doc.is_pos) and self.doc.cash_bank_account and self.doc.paid_amount:
			# POS, make payment entries
			gl_entries.append(
				self.get_gl_dict({
					"account": self.doc.debit_to,
					"against": self.doc.cash_bank_account,
					"credit": self.doc.paid_amount,
					"remarks": self.doc.remarks,
					"against_voucher": self.doc.name,
					"against_voucher_type": self.doc.doctype,
				})
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.doc.cash_bank_account,
					"against": self.doc.debit_to,
					"debit": self.doc.paid_amount,
					"remarks": self.doc.remarks,
				})
			)
			# write off entries, applicable if only pos
			if self.doc.write_off_account and self.doc.write_off_amount:
				gl_entries.append(
					self.get_gl_dict({
						"account": self.doc.debit_to,
						"against": self.doc.write_off_account,
						"credit": self.doc.write_off_amount,
						"remarks": self.doc.remarks,
						"against_voucher": self.doc.name,
						"against_voucher_type": self.doc.doctype,
					})
				)
				gl_entries.append(
					self.get_gl_dict({
						"account": self.doc.write_off_account,
						"against": self.doc.debit_to,
						"debit": self.doc.write_off_amount,
						"remarks": self.doc.remarks,
						"cost_center": self.doc.write_off_cost_center
					})
				)
			
	def update_c_form(self):
		"""Update amended id in C-form"""
		if self.doc.c_form_no and self.doc.amended_from:
			frappe.db.sql("""update `tabC-Form Invoice Detail` set invoice_no = %s,
				invoice_date = %s, territory = %s, net_total = %s,
				grand_total = %s where invoice_no = %s and parent = %s""", 
				(self.doc.name, self.doc.amended_from, self.doc.c_form_no))

	@property
	def meta(self):
		if not hasattr(self, "_meta"):
			self._meta = frappe.get_doctype(self.doc.doctype)
		return self._meta
	
	def validate_recurring_invoice(self):
		if self.doc.convert_into_recurring_invoice:
			self.validate_notification_email_id()
		
			if not self.doc.recurring_type:
				msgprint(_("Please select: ") + self.meta.get_label("recurring_type"),
				raise_exception=1)
		
			elif not (self.doc.invoice_period_from_date and \
					self.doc.invoice_period_to_date):
				msgprint(comma_and([self.meta.get_label("invoice_period_from_date"),
					self.meta.get_label("invoice_period_to_date")])
					+ _(": Mandatory for a Recurring Invoice."),
					raise_exception=True)
	
	def convert_to_recurring(self):
		if self.doc.convert_into_recurring_invoice:
			if not self.doc.recurring_id:
				frappe.db.set(self.doc, "recurring_id",
					make_autoname("RECINV/.#####"))
			
			self.set_next_date()

		elif self.doc.recurring_id:
			frappe.db.sql("""update `tabSales Invoice`
				set convert_into_recurring_invoice = 0
				where recurring_id = %s""", (self.doc.recurring_id,))
			
	def validate_notification_email_id(self):
		if self.doc.notification_email_address:
			email_list = filter(None, [cstr(email).strip() for email in
				self.doc.notification_email_address.replace("\n", "").split(",")])
			
			from frappe.utils import validate_email_add
			for email in email_list:
				if not validate_email_add(email):
					msgprint(self.meta.get_label("notification_email_address") \
						+ " - " + _("Invalid Email Address") + ": \"%s\"" % email,
						raise_exception=1)
					
		else:
			msgprint("Notification Email Addresses not specified for recurring invoice",
				raise_exception=1)
				
	def set_next_date(self):
		""" Set next date on which auto invoice will be created"""
		if not self.doc.repeat_on_day_of_month:
			msgprint("""Please enter 'Repeat on Day of Month' field value. 
				The day of the month on which auto invoice 
				will be generated e.g. 05, 28 etc.""", raise_exception=1)
		
		next_date = get_next_date(self.doc.posting_date,
			month_map[self.doc.recurring_type], cint(self.doc.repeat_on_day_of_month))
		
		frappe.db.set(self.doc, 'next_date', next_date)
	
def get_next_date(dt, mcount, day=None):
	dt = getdate(dt)
	
	from dateutil.relativedelta import relativedelta
	dt += relativedelta(months=mcount, day=day)
	
	return dt
	
def manage_recurring_invoices(next_date=None, commit=True):
	""" 
		Create recurring invoices on specific date by copying the original one
		and notify the concerned people
	"""
	next_date = next_date or nowdate()
	recurring_invoices = frappe.db.sql("""select name, recurring_id
		from `tabSales Invoice` where ifnull(convert_into_recurring_invoice, 0)=1
		and docstatus=1 and next_date=%s
		and next_date <= ifnull(end_date, '2199-12-31')""", next_date)
	
	exception_list = []
	for ref_invoice, recurring_id in recurring_invoices:
		if not frappe.db.sql("""select name from `tabSales Invoice`
				where posting_date=%s and recurring_id=%s and docstatus=1""",
				(next_date, recurring_id)):
			try:
				ref_wrapper = frappe.bean('Sales Invoice', ref_invoice)
				new_invoice_wrapper = make_new_invoice(ref_wrapper, next_date)
				send_notification(new_invoice_wrapper)
				if commit:
					frappe.db.commit()
			except:
				if commit:
					frappe.db.rollback()

					frappe.db.begin()
					frappe.db.sql("update `tabSales Invoice` set \
						convert_into_recurring_invoice = 0 where name = %s", ref_invoice)
					notify_errors(ref_invoice, ref_wrapper.doc.customer, ref_wrapper.doc.owner)
					frappe.db.commit()

				exception_list.append(frappe.get_traceback())
			finally:
				if commit:
					frappe.db.begin()
			
	if exception_list:
		exception_message = "\n\n".join([cstr(d) for d in exception_list])
		raise Exception, exception_message

def make_new_invoice(ref_wrapper, posting_date):
	from frappe.model.bean import clone
	from erpnext.accounts.utils import get_fiscal_year
	new_invoice = clone(ref_wrapper)
	
	mcount = month_map[ref_wrapper.doc.recurring_type]
	
	invoice_period_from_date = get_next_date(ref_wrapper.doc.invoice_period_from_date, mcount)
	
	# get last day of the month to maintain period if the from date is first day of its own month 
	# and to date is the last day of its own month
	if (cstr(get_first_day(ref_wrapper.doc.invoice_period_from_date)) == \
			cstr(ref_wrapper.doc.invoice_period_from_date)) and \
		(cstr(get_last_day(ref_wrapper.doc.invoice_period_to_date)) == \
			cstr(ref_wrapper.doc.invoice_period_to_date)):
		invoice_period_to_date = get_last_day(get_next_date(ref_wrapper.doc.invoice_period_to_date,
			mcount))
	else:
		invoice_period_to_date = get_next_date(ref_wrapper.doc.invoice_period_to_date, mcount)
	
	new_invoice.doc.fields.update({
		"posting_date": posting_date,
		"aging_date": posting_date,
		"due_date": add_days(posting_date, cint(date_diff(ref_wrapper.doc.due_date,
			ref_wrapper.doc.posting_date))),
		"invoice_period_from_date": invoice_period_from_date,
		"invoice_period_to_date": invoice_period_to_date,
		"fiscal_year": get_fiscal_year(posting_date)[0],
		"owner": ref_wrapper.doc.owner,
	})
	
	new_invoice.submit()
	
	return new_invoice
	
def send_notification(new_rv):
	"""Notify concerned persons about recurring invoice generation"""
	
	from frappe.core.doctype.print_format.print_format import get_html
	frappe.sendmail(new_rv.doc.notification_email_address, 
		subject="New Invoice : " + new_rv.doc.name, 
		message = get_html(new_rv.doc, new_rv.doclist, "SalesInvoice"))
		
def notify_errors(inv, customer, owner):
	from frappe.utils.user import get_system_managers
	
	frappe.sendmail(recipients=get_system_managers() + [frappe.db.get_value("User", owner, "email")],
		subject="[Urgent] Error while creating recurring invoice for %s" % inv,
		message = frappe.get_template("template/emails/recurring_invoice_failed.html").render({
			"name": inv,
			"customer": customer
		}))
	
	assign_task_to_owner(inv, "Recurring Invoice Failed", recipients)

def assign_task_to_owner(inv, msg, users):
	for d in users:
		from frappe.widgets.form import assign_to
		args = {
			'assign_to' 	:	d,
			'doctype'		:	'Sales Invoice',
			'name'			:	inv,
			'description'	:	msg,
			'priority'		:	'Urgent'
		}
		assign_to.add(args)

@frappe.whitelist()
def get_bank_cash_account(mode_of_payment):
	val = frappe.db.get_value("Mode of Payment", mode_of_payment, "default_account")
	if not val:
		frappe.msgprint("Default Bank / Cash Account not set in Mode of Payment: %s. Please add a Default Account in Mode of Payment master." % mode_of_payment)
	return {
		"cash_bank_account": val
	}

@frappe.whitelist()
def get_income_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	# income account can be any Credit account, 
	# but can also be a Asset account with account_type='Income Account' in special circumstances. 
	# Hence the first condition is an "OR"
	return frappe.db.sql("""select tabAccount.name from `tabAccount` 
			where (tabAccount.report_type = "Profit and Loss"
					or tabAccount.account_type = "Income Account") 
				and tabAccount.group_or_ledger="Ledger" 
				and tabAccount.docstatus!=2
				and ifnull(tabAccount.master_type, "")=""
				and ifnull(tabAccount.master_name, "")=""
				and tabAccount.company = '%(company)s' 
				and tabAccount.%(key)s LIKE '%(txt)s'
				%(mcond)s""" % {'company': filters['company'], 'key': searchfield, 
			'txt': "%%%s%%" % txt, 'mcond':get_match_cond(doctype)})


@frappe.whitelist()
def make_delivery_note(source_name, target_doclist=None):
	from frappe.model.mapper import get_mapped_doclist
	
	def set_missing_values(source, target):
		bean = frappe.bean(target)
		bean.run_method("onload_post_render")
		
	def update_item(source_doc, target_doc, source_parent):
		target_doc.base_amount = (flt(source_doc.qty) - flt(source_doc.delivered_qty)) * \
			flt(source_doc.base_rate)
		target_doc.amount = (flt(source_doc.qty) - flt(source_doc.delivered_qty)) * \
			flt(source_doc.rate)
		target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)
	
	doclist = get_mapped_doclist("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Delivery Note", 
			"validation": {
				"docstatus": ["=", 1]
			}
		}, 
		"Sales Invoice Item": {
			"doctype": "Delivery Note Item", 
			"field_map": {
				"name": "prevdoc_detail_docname", 
				"parent": "against_sales_invoice", 
				"serial_no": "serial_no"
			},
			"postprocess": update_item
		}, 
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges", 
			"add_if_empty": True
		}, 
		"Sales Team": {
			"doctype": "Sales Team", 
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doclist, set_missing_values)
	
	return [d.fields for d in doclist]