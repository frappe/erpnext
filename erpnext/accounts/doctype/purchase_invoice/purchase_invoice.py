# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint, cstr, flt, formatdate

from frappe import msgprint, _, throw
from erpnext.setup.utils import get_company_currency

import frappe.defaults

from erpnext.controllers.buying_controller import BuyingController
from erpnext.accounts.party import get_party_account, get_due_date

form_grid_templates = {
	"entries": "templates/form_grid/item_grid.html"
}

class PurchaseInvoice(BuyingController):
	tname = 'Purchase Invoice Item'
	fname = 'entries'

	def __init__(self, arg1, arg2=None):
		super(PurchaseInvoice, self).__init__(arg1, arg2)
		self.status_updater = [{
			'source_dt': 'Purchase Invoice Item',
			'target_dt': 'Purchase Order Item',
			'join_field': 'po_detail',
			'target_field': 'billed_amt',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_billed',
			'target_ref_field': 'amount',
			'source_field': 'amount',
			'percent_join_field': 'purchase_order',
			'overflow_type': 'billing'
		}]

	def validate(self):
		if not self.is_opening:
			self.is_opening = 'No'

		super(PurchaseInvoice, self).validate()

		self.po_required()
		self.pr_required()
		self.check_active_purchase_items()
		self.check_conversion_rate()
		self.validate_credit_acc()
		self.clear_unallocated_advances("Purchase Invoice Advance", "advance_allocation_details")
		self.check_for_acc_head_of_supplier()
		self.check_for_stopped_status()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")
		self.set_aging_date()
		frappe.get_doc("Account", self.credit_to).validate_due_date(self.posting_date, self.due_date)
		self.set_against_expense_account()
		self.validate_write_off_account()
		self.update_valuation_rate("entries")
		self.validate_multiple_billing("Purchase Receipt", "pr_detail", "amount",
			"purchase_receipt_details")
		self.create_remarks()

	def create_remarks(self):
		if not self.remarks:
			if self.bill_no and self.bill_date:
				self.remarks = _("Against Supplier Invoice {0} dated {1}").format(self.bill_no, formatdate(self.bill_date))
			else:
				self.remarks = _("No Remarks")

	def set_missing_values(self, for_validate=False):
		if not self.credit_to:
			self.credit_to = get_party_account(self.company, self.supplier, "Supplier")
		if not self.due_date:
			self.due_date = get_due_date(self.posting_date, self.supplier, "Supplier",
				self.credit_to, self.company)

		super(PurchaseInvoice, self).set_missing_values(for_validate)

	def get_advances(self):
		super(PurchaseInvoice, self).get_advances(self.credit_to,
			"Purchase Invoice Advance", "advance_allocation_details", "debit")

	def check_active_purchase_items(self):
		for d in self.get('entries'):
			if d.item_code:		# extra condn coz item_code is not mandatory in PV
				if frappe.db.get_value("Item", d.item_code, "is_purchase_item") != 'Yes':
					msgprint(_("Item {0} is not Purchase Item").format(d.item_code), raise_exception=True)

	def check_conversion_rate(self):
		default_currency = get_company_currency(self.company)
		if not default_currency:
			throw(_('Please enter default currency in Company Master'))
		if (self.currency == default_currency and flt(self.conversion_rate) != 1.00) or not self.conversion_rate or (self.currency != default_currency and flt(self.conversion_rate) == 1.00):
			throw(_("Conversion rate cannot be 0 or 1"))

	def validate_credit_acc(self):
		if frappe.db.get_value("Account", self.credit_to, "report_type") != "Balance Sheet":
			frappe.throw(_("Account must be a balance sheet account"))

	# Validate Acc Head of Supplier and Credit To Account entered
	# ------------------------------------------------------------
	def check_for_acc_head_of_supplier(self):
		if self.supplier and self.credit_to:
			acc_head = frappe.db.sql("select master_name from `tabAccount` where name = %s", self.credit_to)

			if (acc_head and cstr(acc_head[0][0]) != cstr(self.supplier)) or (not acc_head and (self.credit_to != cstr(self.supplier) + " - " + self.company_abbr)):
				msgprint("Credit To: %s do not match with Supplier: %s for Company: %s.\n If both correctly entered, please select Master Type and Master Name in account master." %(self.credit_to,self.supplier,self.company), raise_exception=1)

	# Check for Stopped PO
	# ---------------------
	def check_for_stopped_status(self):
		check_list = []
		for d in self.get('entries'):
			if d.purchase_order and not d.purchase_order in check_list and not d.purchase_receipt:
				check_list.append(d.purchase_order)
				stopped = frappe.db.sql("select name from `tabPurchase Order` where status = 'Stopped' and name = %s", d.purchase_order)
				if stopped:
					throw(_("Purchase Order {0} is 'Stopped'").format(d.purchase_order))

	def validate_with_previous_doc(self):
		super(PurchaseInvoice, self).validate_with_previous_doc(self.tname, {
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "po_detail",
				"compare_fields": [["project_name", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Purchase Receipt": {
				"ref_dn_field": "purchase_receipt",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Receipt Item": {
				"ref_dn_field": "pr_detail",
				"compare_fields": [["project_name", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True
			}
		})

		if cint(frappe.defaults.get_global_default('maintain_same_rate')):
			super(PurchaseInvoice, self).validate_with_previous_doc(self.tname, {
				"Purchase Order Item": {
					"ref_dn_field": "po_detail",
					"compare_fields": [["rate", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True
				},
				"Purchase Receipt Item": {
					"ref_dn_field": "pr_detail",
					"compare_fields": [["rate", "="]],
					"is_child_table": True
				}
			})


	def set_aging_date(self):
		if self.is_opening != 'Yes':
			self.aging_date = self.posting_date
		elif not self.aging_date:
			throw(_("Ageing date is mandatory for opening entry"))

	def set_against_expense_account(self):
		auto_accounting_for_stock = cint(frappe.defaults.get_global_default("auto_accounting_for_stock"))

		if auto_accounting_for_stock:
			stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")

		against_accounts = []
		stock_items = self.get_stock_items()
		for item in self.get("entries"):
			if auto_accounting_for_stock and item.item_code in stock_items \
					and self.is_opening == 'No':
				# in case of auto inventory accounting, against expense account is always
				# Stock Received But Not Billed for a stock item
				item.expense_account = stock_not_billed_account
				item.cost_center = None

				if stock_not_billed_account not in against_accounts:
					against_accounts.append(stock_not_billed_account)

			elif not item.expense_account:
				throw(_("Expense account is mandatory for item {0}").format(item.item_code or item.item_name))

			elif item.expense_account not in against_accounts:
				# if no auto_accounting_for_stock or not a stock item
				against_accounts.append(item.expense_account)

		self.against_expense_account = ",".join(against_accounts)

	def po_required(self):
		if frappe.db.get_value("Buying Settings", None, "po_required") == 'Yes':
			 for d in self.get('entries'):
				 if not d.purchase_order:
					 throw(_("Purchse Order number required for Item {0}").format(d.item_code))

	def pr_required(self):
		if frappe.db.get_value("Buying Settings", None, "pr_required") == 'Yes':
			 for d in self.get('entries'):
				 if not d.purchase_receipt:
					 throw(_("Purchase Receipt number required for Item {0}").format(d.item_code))

	def validate_write_off_account(self):
		if self.write_off_amount and not self.write_off_account:
			throw(_("Please enter Write Off Account"))

	def check_prev_docstatus(self):
		for d in self.get('entries'):
			if d.purchase_order:
				submitted = frappe.db.sql("select name from `tabPurchase Order` where docstatus = 1 and name = %s", d.purchase_order)
				if not submitted:
					frappe.throw(_("Purchase Order {0} is not submitted").format(d.purchase_order))
			if d.purchase_receipt:
				submitted = frappe.db.sql("select name from `tabPurchase Receipt` where docstatus = 1 and name = %s", d.purchase_receipt)
				if not submitted:
					frappe.throw(_("Purchase Receipt {0} is not submitted").format(d.purchase_receipt))


	def update_against_document_in_jv(self):
		"""
			Links invoice and advance voucher:
				1. cancel advance voucher
				2. split into multiple rows if partially adjusted, assign against voucher
				3. submit advance voucher
		"""

		lst = []
		for d in self.get('advance_allocation_details'):
			if flt(d.allocated_amount) > 0:
				args = {
					'voucher_no' : d.journal_voucher,
					'voucher_detail_no' : d.jv_detail_no,
					'against_voucher_type' : 'Purchase Invoice',
					'against_voucher'  : self.name,
					'account' : self.credit_to,
					'is_advance' : 'Yes',
					'dr_or_cr' : 'debit',
					'unadjusted_amt' : flt(d.advance_amount),
					'allocated_amt' : flt(d.allocated_amount)
				}
				lst.append(args)

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)

	def on_submit(self):
		self.check_prev_docstatus()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.grand_total)

		# this sequence because outstanding may get -negative
		self.make_gl_entries()
		self.update_against_document_in_jv()
		self.update_prevdoc_status()
		self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

	def make_gl_entries(self):
		auto_accounting_for_stock = \
			cint(frappe.defaults.get_global_default("auto_accounting_for_stock"))

		stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
		expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		gl_entries = []

		# parent's gl entry
		if self.grand_total:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"against": self.against_expense_account,
					"credit": self.total_amount_to_pay,
					"remarks": self.remarks,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
				})
			)

		# tax table gl entries
		valuation_tax = {}
		for tax in self.get("other_charges"):
			if tax.category in ("Total", "Valuation and Total") and flt(tax.tax_amount):
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.credit_to,
						"debit": tax.add_deduct_tax == "Add" and tax.tax_amount or 0,
						"credit": tax.add_deduct_tax == "Deduct" and tax.tax_amount or 0,
						"remarks": self.remarks,
						"cost_center": tax.cost_center
					})
				)

			# accumulate valuation tax
			if tax.category in ("Valuation", "Valuation and Total") and flt(tax.tax_amount):
				if auto_accounting_for_stock and not tax.cost_center:
					frappe.throw(_("Cost Center is required in row {0} in Taxes table for type {1}").format(tax.idx, _(tax.category)))
				valuation_tax.setdefault(tax.cost_center, 0)
				valuation_tax[tax.cost_center] += \
					(tax.add_deduct_tax == "Add" and 1 or -1) * flt(tax.tax_amount)

		# item gl entries
		negative_expense_to_be_booked = 0.0
		stock_items = self.get_stock_items()
		for item in self.get("entries"):
			if flt(item.base_amount):
				gl_entries.append(
					self.get_gl_dict({
						"account": item.expense_account,
						"against": self.credit_to,
						"debit": item.base_amount,
						"remarks": self.remarks,
						"cost_center": item.cost_center
					})
				)

			if auto_accounting_for_stock and item.item_code in stock_items and item.item_tax_amount:
					# Post reverse entry for Stock-Received-But-Not-Billed if it is booked in Purchase Receipt
					negative_expense_booked_in_pi = None
					if item.purchase_receipt:
						negative_expense_booked_in_pi = frappe.db.sql("""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account=%s""",
							(item.purchase_receipt, expenses_included_in_valuation))

					if not negative_expense_booked_in_pi:
						gl_entries.append(
							self.get_gl_dict({
								"account": stock_received_but_not_billed,
								"against": self.credit_to,
								"debit": flt(item.item_tax_amount, self.precision("item_tax_amount", item)),
								"remarks": self.remarks or "Accounting Entry for Stock"
							})
						)

						negative_expense_to_be_booked += flt(item.item_tax_amount, self.precision("item_tax_amount", item))

		if negative_expense_to_be_booked and valuation_tax:
			# credit valuation tax amount in "Expenses Included In Valuation"
			# this will balance out valuation amount included in cost of goods sold

			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = negative_expense_to_be_booked
			i = 1
			for cost_center, amount in valuation_tax.items():
				if i == len(valuation_tax):
					applicable_amount = amount_including_divisional_loss
				else:
					applicable_amount = negative_expense_to_be_booked * (amount / total_valuation_amount)
					amount_including_divisional_loss -= applicable_amount

				gl_entries.append(
					self.get_gl_dict({
						"account": expenses_included_in_valuation,
						"cost_center": cost_center,
						"against": self.credit_to,
						"credit": applicable_amount,
						"remarks": self.remarks or "Accounting Entry for Stock"
					})
				)

				i += 1

		# writeoff account includes petty difference in the invoice amount
		# and the amount that is paid
		if self.write_off_account and flt(self.write_off_amount):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": self.credit_to,
					"credit": flt(self.write_off_amount),
					"remarks": self.remarks,
					"cost_center": self.write_off_cost_center
				})
			)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2))

	def on_cancel(self):
		from erpnext.accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doctype, self.name, "against_voucher")

		self.update_prevdoc_status()
		self.update_billing_status_for_zero_amount_refdoc("Purchase Order")
		self.make_gl_entries_on_cancel()

	def on_update(self):
		pass

@frappe.whitelist()
def get_expense_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	# expense account can be any Debit account,
	# but can also be a Liability account with account_type='Expense Account' in special circumstances.
	# Hence the first condition is an "OR"
	return frappe.db.sql("""select tabAccount.name from `tabAccount`
			where (tabAccount.report_type = "Profit and Loss"
					or tabAccount.account_type = "Expense Account")
				and tabAccount.group_or_ledger="Ledger"
				and tabAccount.docstatus!=2
				and ifnull(tabAccount.master_type, "")=""
				and ifnull(tabAccount.master_name, "")=""
				and tabAccount.company = '%(company)s'
				and tabAccount.%(key)s LIKE '%(txt)s'
				%(mcond)s""" % {'company': filters['company'], 'key': searchfield,
			'txt': "%%%s%%" % txt, 'mcond':get_match_cond(doctype)})
