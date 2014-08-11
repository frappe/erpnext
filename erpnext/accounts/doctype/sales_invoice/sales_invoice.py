# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults

from frappe.utils import add_days, cint, cstr, date_diff, flt, getdate, nowdate, \
	get_first_day, get_last_day
from frappe.model.naming import make_autoname
from frappe import _, msgprint, throw

from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.controllers.stock_controller import update_gl_entries_after
from frappe.model.mapper import get_mapped_doc

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}

from erpnext.controllers.selling_controller import SellingController

form_grid_templates = {
	"entries": "templates/form_grid/item_grid.html"
}

class SalesInvoice(SellingController):
	tname = 'Sales Invoice Item'
	fname = 'entries'

	def __init__(self, arg1, arg2=None):
		super(SalesInvoice, self).__init__(arg1, arg2)
		self.status_updater = [{
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
			'keyword': 'Billed',
			'overflow_type': 'billing'
		}]

	def validate(self):
		super(SalesInvoice, self).validate()
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

		if cint(self.is_pos):
			self.validate_pos()
			self.validate_write_off_account()

		if cint(self.update_stock):
			self.validate_item_code()
			self.update_current_stock()
			self.validate_delivery_note()

		if not self.is_opening:
			self.is_opening = 'No'

		self.set_aging_date()
		frappe.get_doc("Account", self.debit_to).validate_due_date(self.posting_date, self.due_date)
		self.set_against_income_account()
		self.validate_c_form()
		self.validate_time_logs_are_submitted()
		self.validate_recurring_invoice()
		self.validate_multiple_billing("Delivery Note", "dn_detail", "amount",
			"delivery_note_details")

	def on_submit(self):
		if cint(self.update_stock) == 1:
			self.update_stock_ledger()
		else:
			# Check for Approving Authority
			if not self.recurring_id:
				frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
				 	self.company, self.grand_total, self)

		self.check_prev_docstatus()

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_for_zero_amount_refdoc("Sales Order")

		# this sequence because outstanding may get -ve
		self.make_gl_entries()
		self.check_credit_limit(self.debit_to)

		if not cint(self.is_pos) == 1:
			self.update_against_document_in_jv()

		self.update_c_form()
		self.update_time_log_batch(self.name)
		self.convert_to_recurring()

	def before_cancel(self):
		self.update_time_log_batch(None)

	def on_cancel(self):
		if cint(self.update_stock) == 1:
			self.update_stock_ledger()

		self.check_stop_sales_order("sales_order")

		from erpnext.accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doctype, self.name, "against_invoice")

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_for_zero_amount_refdoc("Sales Order")

		self.make_gl_entries_on_cancel()

	def update_status_updater_args(self):
		if cint(self.update_stock):
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
				'second_join_field': 'prevdoc_detail_docname',
				'overflow_type': 'delivery'
			})

	def on_update_after_submit(self):
		self.validate_recurring_invoice()
		self.convert_to_recurring()

	def get_portal_page(self):
		return "invoice" if self.docstatus==1 else None

	def set_missing_values(self, for_validate=False):
		self.set_pos_fields(for_validate)

		if not self.debit_to:
			self.debit_to = get_party_account(self.company, self.customer, "Customer")
		if not self.due_date:
			self.due_date = get_due_date(self.posting_date, self.customer, "Customer",
				self.debit_to, self.company)

		super(SalesInvoice, self).set_missing_values(for_validate)

	def update_time_log_batch(self, sales_invoice):
		for d in self.get(self.fname):
			if d.time_log_batch:
				tlb = frappe.get_doc("Time Log Batch", d.time_log_batch)
				tlb.sales_invoice = sales_invoice
				tlb.ignore_validate_update_after_submit = True
				tlb.save()

	def validate_time_logs_are_submitted(self):
		for d in self.get(self.fname):
			if d.time_log_batch:
				status = frappe.db.get_value("Time Log Batch", d.time_log_batch, "status")
				if status!="Submitted":
					frappe.throw(_("Time Log Batch {0} must be 'Submitted'").format(d.time_log_batch))

	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from pos settings"""
		if cint(self.is_pos) != 1:
			return

		from erpnext.stock.get_item_details import get_pos_settings_item_details, get_pos_settings
		pos = get_pos_settings(self.company)

		if pos:
			if not for_validate and not self.customer:
				self.customer = pos.customer
				# self.set_customer_defaults()

			for fieldname in ('territory', 'naming_series', 'currency', 'taxes_and_charges', 'letter_head', 'tc_name',
				'selling_price_list', 'company', 'select_print_heading', 'cash_bank_account'):
					if (not for_validate) or (for_validate and not self.get(fieldname)):
						self.set(fieldname, pos.get(fieldname))

			if not for_validate:
				self.update_stock = cint(pos.get("update_stock"))

			# set pos values in items
			for item in self.get("entries"):
				if item.get('item_code'):
					for fname, val in get_pos_settings_item_details(pos,
						frappe._dict(item.as_dict()), pos).items():

						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			# fetch terms
			if self.tc_name and not self.terms:
				self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

			# fetch charges
			if self.taxes_and_charges and not len(self.get("other_charges")):
				self.set_taxes("other_charges", "taxes_and_charges")

	def get_advances(self):
		super(SalesInvoice, self).get_advances(self.debit_to,
			"Sales Invoice Advance", "advance_adjustment_details", "credit")

	def get_company_abbr(self):
		return frappe.db.sql("select abbr from tabCompany where name=%s", self.company)[0][0]

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
					'against_voucher'  : self.name,
					'account' : self.debit_to,
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
		if self.customer and self.debit_to and not cint(self.is_pos):
			acc_head = frappe.db.sql("select master_name from `tabAccount` where name = %s and docstatus != 2", self.debit_to)

			if (acc_head and cstr(acc_head[0][0]) != cstr(self.customer)) or \
				(not acc_head and (self.debit_to != cstr(self.customer) + " - " + self.get_company_abbr())):
				msgprint("Debit To: %s do not match with Customer: %s for Company: %s.\n If both correctly entered, please select Master Type \
					and Master Name in account master." %(self.debit_to, self.customer,self.company), raise_exception=1)


	def validate_debit_acc(self):
		if frappe.db.get_value("Account", self.debit_to, "report_type") != "Balance Sheet":
			frappe.throw(_("Account must be a balance sheet account"))

	def validate_fixed_asset_account(self):
		"""Validate Fixed Asset and whether Income Account Entered Exists"""
		for d in self.get('entries'):
			item = frappe.db.sql("""select name,is_asset_item,is_sales_item from `tabItem`
				where name = %s""", d.item_code)
			acc = frappe.db.sql("""select account_type from `tabAccount`
				where name = %s and docstatus != 2""", d.income_account)
			if item and item[0][1] == 'Yes' and acc and acc[0][0] != 'Fixed Asset':
				msgprint(_("Account {0} must be of type 'Fixed Asset' as Item {1} is an Asset Item").format(acc[0][0], d.item_code), raise_exception=True)

	def validate_with_previous_doc(self):
		super(SalesInvoice, self).validate_with_previous_doc(self.tname, {
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
			super(SalesInvoice, self).validate_with_previous_doc(self.tname, {
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
		if self.is_opening != 'Yes':
			self.aging_date = self.posting_date
		elif not self.aging_date:
			throw(_("Ageing Date is mandatory for opening entry"))

	def set_against_income_account(self):
		"""Set against account for debit to account"""
		against_acc = []
		for d in self.get('entries'):
			if d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.against_income_account = ','.join(against_acc)


	def add_remarks(self):
		if not self.remarks: self.remarks = 'No Remarks'


	def so_dn_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		dic = {'Sales Order':'so_required','Delivery Note':'dn_required'}
		for i in dic:
			if frappe.db.get_value('Selling Settings', None, dic[i]) == 'Yes':
				for d in self.get('entries'):
					if frappe.db.get_value('Item', d.item_code, 'is_stock_item') == 'Yes' \
						and not d.get(i.lower().replace(' ','_')):
						msgprint(_("{0} is mandatory for Item {1}").format(i,d.item_code), raise_exception=1)


	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project_name and self.customer:
			res = frappe.db.sql("""select name from `tabProject`
				where name = %s and (customer = %s or
					ifnull(customer,'')='')""", (self.project_name, self.customer))
			if not res:
				throw(_("Customer {0} does not belong to project {1}").format(self.customer,self.project_name))

	def validate_pos(self):
		if not self.cash_bank_account and flt(self.paid_amount):
			frappe.throw(_("Cash or Bank Account is mandatory for making payment entry"))

		if flt(self.paid_amount) + flt(self.write_off_amount) \
				- flt(self.grand_total) > 1/(10**(self.precision("grand_total") + 1)):
			frappe.throw(_("""Paid amount + Write Off Amount can not be greater than Grand Total"""))


	def validate_item_code(self):
		for d in self.get('entries'):
			if not d.item_code:
				msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

	def validate_delivery_note(self):
		for d in self.get("entries"):
			if d.delivery_note:
				msgprint(_("Stock cannot be updated against Delivery Note {0}").format(d.delivery_note), raise_exception=1)


	def validate_write_off_account(self):
		if flt(self.write_off_amount) and not self.write_off_account:
			msgprint(_("Please enter Write Off Account"), raise_exception=1)


	def validate_c_form(self):
		""" Blank C-form no if C-form applicable marked as 'No'"""
		if self.amended_from and self.c_form_applicable == 'No' and self.c_form_no:
			frappe.db.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.amended_from,	self.c_form_no))

			frappe.db.set(self, 'c_form_no', '')

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
		user_pos_setting = frappe.db.sql("""select name, warehouse from `tabPOS Setting`
			where ifnull(user,'') = %s and company = %s""", (frappe.session['user'], self.company))
		warehouse = user_pos_setting[0][1] if user_pos_setting else None

		if not warehouse:
			global_pos_setting = frappe.db.sql("""select name, warehouse from `tabPOS Setting`
				where ifnull(user,'') = '' and company = %s""", self.company)

			if global_pos_setting:
				warehouse = global_pos_setting[0][1]
			elif not user_pos_setting:
				msgprint(_("POS Setting required to make POS Entry"), raise_exception=True)

		return warehouse

	def on_update(self):
		if cint(self.update_stock) == 1:
			# Set default warehouse from pos setting
			if cint(self.is_pos) == 1:
				w = self.get_warehouse()
				if w:
					for d in self.get('entries'):
						if not d.warehouse:
							d.warehouse = cstr(w)

			from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
			make_packing_list(self, 'entries')
		else:
			self.set('packing_details', [])

		if cint(self.is_pos) == 1:
			if flt(self.paid_amount) == 0:
				if self.cash_bank_account:
					frappe.db.set(self, 'paid_amount',
						(flt(self.grand_total) - flt(self.write_off_amount)))
				else:
					# show message that the amount is not paid
					frappe.db.set(self,'paid_amount',0)
					frappe.msgprint(_("Note: Payment Entry will not be created since 'Cash or Bank Account' was not specified"))
		else:
			frappe.db.set(self,'paid_amount',0)

	def check_prev_docstatus(self):
		for d in self.get('entries'):
			if d.sales_order:
				submitted = frappe.db.sql("""select name from `tabSales Order`
					where docstatus = 1 and name = %s""", d.sales_order)
				if not submitted:
					frappe.throw(_("Sales Order {0} is not submitted").format(d.sales_order))

			if d.delivery_note:
				submitted = frappe.db.sql("""select name from `tabDelivery Note`
					where docstatus = 1 and name = %s""", d.delivery_note)
				if not submitted:
					throw(_("Delivery Note {0} is not submitted").format(d.delivery_note))

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

	def make_gl_entries(self, repost_future_gle=True):
		gl_entries = self.get_gl_entries()

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries

			update_outstanding = cint(self.is_pos) and self.write_off_account \
				and 'No' or 'Yes'
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
				update_outstanding=update_outstanding, merge_entries=False)

			if update_outstanding == "No":
				from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
				update_outstanding_amt(self.debit_to, self.doctype, self.name)

			if repost_future_gle and cint(self.update_stock) \
				and cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
					items, warehouse_account = self.get_items_and_warehouse_accounts()
					update_gl_entries_after(self.posting_date, self.posting_time,
						warehouse_account, items)

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
		if self.grand_total:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"against": self.against_income_account,
					"debit": self.grand_total,
					"remarks": self.remarks,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
				})
			)

	def make_tax_gl_entries(self, gl_entries):
		for tax in self.get("other_charges"):
			if flt(tax.tax_amount_after_discount_amount):
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.debit_to,
						"credit": flt(tax.tax_amount_after_discount_amount),
						"remarks": self.remarks,
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
						"against": self.debit_to,
						"credit": item.base_amount,
						"remarks": self.remarks,
						"cost_center": item.cost_center
					})
				)

		# expense account gl entries
		if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")) \
				and cint(self.update_stock):
			gl_entries += super(SalesInvoice, self).get_gl_entries()

	def make_pos_gl_entries(self, gl_entries):
		if cint(self.is_pos) and self.cash_bank_account and self.paid_amount:
			# POS, make payment entries
			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"against": self.cash_bank_account,
					"credit": self.paid_amount,
					"remarks": self.remarks,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
				})
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.cash_bank_account,
					"against": self.debit_to,
					"debit": self.paid_amount,
					"remarks": self.remarks,
				})
			)
			# write off entries, applicable if only pos
			if self.write_off_account and self.write_off_amount:
				gl_entries.append(
					self.get_gl_dict({
						"account": self.debit_to,
						"against": self.write_off_account,
						"credit": self.write_off_amount,
						"remarks": self.remarks,
						"against_voucher": self.name,
						"against_voucher_type": self.doctype,
					})
				)
				gl_entries.append(
					self.get_gl_dict({
						"account": self.write_off_account,
						"against": self.debit_to,
						"debit": self.write_off_amount,
						"remarks": self.remarks,
						"cost_center": self.write_off_cost_center
					})
				)

	def update_c_form(self):
		"""Update amended id in C-form"""
		if self.c_form_no and self.amended_from:
			frappe.db.sql("""update `tabC-Form Invoice Detail` set invoice_no = %s,
				invoice_date = %s, territory = %s, net_total = %s,
				grand_total = %s where invoice_no = %s and parent = %s""",
				(self.name, self.amended_from, self.c_form_no))

	def validate_recurring_invoice(self):
		if self.convert_into_recurring_invoice:
			self.validate_notification_email_id()

			if not self.recurring_type:
				msgprint(_("Please select {0}").format(self.meta.get_label("recurring_type")),
				raise_exception=1)

			elif not (self.invoice_period_from_date and \
					self.invoice_period_to_date):
				throw(_("Invoice Period From and Invoice Period To dates mandatory for recurring invoice"))

	def convert_to_recurring(self):
		if self.convert_into_recurring_invoice:
			if not self.recurring_id:
				frappe.db.set(self, "recurring_id",
					make_autoname("RECINV/.#####"))

			self.set_next_date()

		elif self.recurring_id:
			frappe.db.sql("""update `tabSales Invoice`
				set convert_into_recurring_invoice = 0
				where recurring_id = %s""", (self.recurring_id,))

	def validate_notification_email_id(self):
		if self.notification_email_address:
			email_list = filter(None, [cstr(email).strip() for email in
				self.notification_email_address.replace("\n", "").split(",")])

			from frappe.utils import validate_email_add
			for email in email_list:
				if not validate_email_add(email):
					throw(_("{0} is an invalid email address in 'Notification Email Address'").format(email))

		else:
			throw(_("'Notification Email Addresses' not specified for recurring invoice"))

	def set_next_date(self):
		""" Set next date on which auto invoice will be created"""
		if not self.repeat_on_day_of_month:
			msgprint(_("Please enter 'Repeat on Day of Month' field value"), raise_exception=1)

		next_date = get_next_date(self.posting_date,
			month_map[self.recurring_type], cint(self.repeat_on_day_of_month))

		frappe.db.set(self, 'next_date', next_date)

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
				ref_wrapper = frappe.get_doc('Sales Invoice', ref_invoice)
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
					notify_errors(ref_invoice, ref_wrapper.customer, ref_wrapper.owner)
					frappe.db.commit()

				exception_list.append(frappe.get_traceback())
			finally:
				if commit:
					frappe.db.begin()

	if exception_list:
		exception_message = "\n\n".join([cstr(d) for d in exception_list])
		frappe.throw(exception_message)

def make_new_invoice(ref_wrapper, posting_date):
	from erpnext.accounts.utils import get_fiscal_year
	new_invoice = frappe.copy_doc(ref_wrapper)

	mcount = month_map[ref_wrapper.recurring_type]

	invoice_period_from_date = get_next_date(ref_wrapper.invoice_period_from_date, mcount)

	# get last day of the month to maintain period if the from date is first day of its own month
	# and to date is the last day of its own month
	if (cstr(get_first_day(ref_wrapper.invoice_period_from_date)) == \
			cstr(ref_wrapper.invoice_period_from_date)) and \
		(cstr(get_last_day(ref_wrapper.invoice_period_to_date)) == \
			cstr(ref_wrapper.invoice_period_to_date)):
		invoice_period_to_date = get_last_day(get_next_date(ref_wrapper.invoice_period_to_date,
			mcount))
	else:
		invoice_period_to_date = get_next_date(ref_wrapper.invoice_period_to_date, mcount)

	new_invoice.update({
		"posting_date": posting_date,
		"aging_date": posting_date,
		"due_date": add_days(posting_date, cint(date_diff(ref_wrapper.due_date,
			ref_wrapper.posting_date))),
		"invoice_period_from_date": invoice_period_from_date,
		"invoice_period_to_date": invoice_period_to_date,
		"fiscal_year": get_fiscal_year(posting_date)[0],
		"owner": ref_wrapper.owner,
	})

	new_invoice.submit()

	return new_invoice

def send_notification(new_rv):
	"""Notify concerned persons about recurring invoice generation"""
	frappe.sendmail(new_rv.notification_email_address,
		subject="New Invoice : " + new_rv.name,
		message = _("Please find attached Sales Invoice #{0}").format(new_rv.name),
		attachments = [{
			"fname": new_rv.name + ".pdf",
			"fcontent": frappe.get_print_format(new_rv.doctype, new_rv.name, as_pdf=True)
		}])

def notify_errors(inv, customer, owner):
	from frappe.utils.user import get_system_managers
	recipients=get_system_managers(only_name=True)

	frappe.sendmail(recipients + [frappe.db.get_value("User", owner, "email")],
		subject="[Urgent] Error while creating recurring invoice for %s" % inv,
		message = frappe.get_template("templates/emails/recurring_invoice_failed.html").render({
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
			'priority'		:	'High'
		}
		assign_to.add(args)

@frappe.whitelist()
def get_bank_cash_account(mode_of_payment):
	val = frappe.db.get_value("Mode of Payment", mode_of_payment, "default_account")
	if not val:
		frappe.msgprint(_("Please set default Cash or Bank account in Mode of Payment {0}").format(mode_of_payment))
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
def make_delivery_note(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.base_amount = (flt(source_doc.qty) - flt(source_doc.delivered_qty)) * \
			flt(source_doc.base_rate)
		target_doc.amount = (flt(source_doc.qty) - flt(source_doc.delivered_qty)) * \
			flt(source_doc.rate)
		target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)

	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
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
	}, target_doc, set_missing_values)

	return doclist
