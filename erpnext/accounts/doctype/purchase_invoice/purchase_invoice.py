# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, formatdate, flt, getdate
from frappe import msgprint, _, throw
from erpnext.setup.utils import get_company_currency
import frappe.defaults

from erpnext.controllers.buying_controller import BuyingController
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.accounts.utils import get_account_currency

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class PurchaseInvoice(BuyingController):
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

		if not self.is_return:
			self.po_required()
			self.pr_required()
			self.validate_supplier_invoice()
			self.validate_advance_jv("Purchase Order")

		self.check_active_purchase_items()
		self.check_conversion_rate()
		self.validate_credit_to_acc()
		self.clear_unallocated_advances("Purchase Invoice Advance", "advances")
		self.check_for_stopped_or_closed_status()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")
		self.set_against_expense_account()
		self.validate_write_off_account()
		self.update_valuation_rate("items")
		self.validate_multiple_billing("Purchase Receipt", "pr_detail", "amount",
			"items")
		self.create_remarks()

	def create_remarks(self):
		if not self.remarks:
			if self.bill_no and self.bill_date:
				self.remarks = _("Against Supplier Invoice {0} dated {1}").format(self.bill_no, formatdate(self.bill_date))
			else:
				self.remarks = _("No Remarks")

	def set_missing_values(self, for_validate=False):
		if not self.credit_to:
			self.credit_to = get_party_account("Supplier", self.supplier, self.company)
		if not self.due_date:
			self.due_date = get_due_date(self.posting_date, "Supplier", self.supplier, self.company)

		super(PurchaseInvoice, self).set_missing_values(for_validate)

	def get_advances(self):
		if not self.is_return:
			super(PurchaseInvoice, self).get_advances(self.credit_to, "Supplier", self.supplier,
				"Purchase Invoice Advance", "advances", "debit_in_account_currency", "purchase_order")

	def check_active_purchase_items(self):
		for d in self.get('items'):
			if d.item_code:		# extra condn coz item_code is not mandatory in PV
				if frappe.db.get_value("Item", d.item_code, "is_purchase_item") != 1:
					msgprint(_("Item {0} is not Purchase Item").format(d.item_code), raise_exception=True)

	def check_conversion_rate(self):
		default_currency = get_company_currency(self.company)
		if not default_currency:
			throw(_('Please enter default currency in Company Master'))
		if (self.currency == default_currency and flt(self.conversion_rate) != 1.00) or not self.conversion_rate or (self.currency != default_currency and flt(self.conversion_rate) == 1.00):
			throw(_("Conversion rate cannot be 0 or 1"))

	def validate_credit_to_acc(self):
		account = frappe.db.get_value("Account", self.credit_to,
			["account_type", "report_type", "account_currency"], as_dict=True)

		if account.report_type != "Balance Sheet":
			frappe.throw(_("Credit To account must be a Balance Sheet account"))

		if self.supplier and account.account_type != "Payable":
			frappe.throw(_("Credit To account must be a Payable account"))

		self.party_account_currency = account.account_currency

	def check_for_stopped_or_closed_status(self):
		check_list = []
		pc_obj = frappe.get_doc('Purchase Common')

		for d in self.get('items'):
			if d.purchase_order and not d.purchase_order in check_list and not d.purchase_receipt:
				check_list.append(d.purchase_order)
				pc_obj.check_for_stopped_or_closed_status('Purchase Order', d.purchase_order)

	def validate_with_previous_doc(self):
		super(PurchaseInvoice, self).validate_with_previous_doc({
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

		if cint(frappe.db.get_single_value('Buying Settings', 'maintain_same_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([
				["Purchase Order", "purchase_order", "po_detail"],
				["Purchase Receipt", "purchase_receipt", "pr_detail"]
			])

	def set_against_expense_account(self):
		auto_accounting_for_stock = cint(frappe.defaults.get_global_default("auto_accounting_for_stock"))

		if auto_accounting_for_stock:
			stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")

		against_accounts = []
		stock_items = self.get_stock_items()
		for item in self.get("items"):
			# in case of auto inventory accounting, 
			# against expense account is always "Stock Received But Not Billed"
			# for a stock item and if not epening entry and not drop-ship entry
			
			if auto_accounting_for_stock and item.item_code in stock_items \
				and self.is_opening == 'No' and (not item.po_detail or 
					not frappe.db.get_value("Purchase Order Item", item.po_detail, "delivered_by_supplier")):
				
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
			 for d in self.get('items'):
				 if not d.purchase_order:
					 throw(_("Purchse Order number required for Item {0}").format(d.item_code))

	def pr_required(self):
		stock_items = self.get_stock_items()
		if frappe.db.get_value("Buying Settings", None, "pr_required") == 'Yes':
			 for d in self.get('items'):
				 if not d.purchase_receipt and d.item_code in stock_items:
					 throw(_("Purchase Receipt number required for Item {0}").format(d.item_code))

	def validate_write_off_account(self):
		if self.write_off_amount and not self.write_off_account:
			throw(_("Please enter Write Off Account"))

	def check_prev_docstatus(self):
		for d in self.get('items'):
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
		for d in self.get('advances'):
			if flt(d.allocated_amount) > 0:
				args = {
					'voucher_no' : d.journal_entry,
					'voucher_detail_no' : d.jv_detail_no,
					'against_voucher_type' : 'Purchase Invoice',
					'against_voucher'  : self.name,
					'account' : self.credit_to,
					'party_type': 'Supplier',
					'party': self.supplier,
					'is_advance' : 'Yes',
					'dr_or_cr' : 'debit_in_account_currency',
					'unadjusted_amt' : flt(d.advance_amount),
					'allocated_amt' : flt(d.allocated_amount)
				}
				lst.append(args)

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)

	def on_submit(self):
		super(PurchaseInvoice, self).on_submit()

		self.check_prev_docstatus()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.base_grand_total)

		# this sequence because outstanding may get -negative
		self.make_gl_entries()
		if not self.is_return:
			self.update_against_document_in_jv()
			self.update_prevdoc_status()
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		self.update_project()

	def make_gl_entries(self):
		auto_accounting_for_stock = \
			cint(frappe.defaults.get_global_default("auto_accounting_for_stock"))

		stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
		expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		gl_entries = []

		# parent's gl entry
		if self.base_grand_total:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"party_type": "Supplier",
					"party": self.supplier,
					"against": self.against_expense_account,
					"credit": self.base_grand_total,
					"credit_in_account_currency": self.base_grand_total \
						if self.party_account_currency==self.company_currency else self.grand_total,
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
				}, self.party_account_currency)
			)

		# tax table gl entries
		valuation_tax = {}
		for tax in self.get("taxes"):
			if tax.category in ("Total", "Valuation and Total") and flt(tax.base_tax_amount_after_discount_amount):
				account_currency = get_account_currency(tax.account_head)

				dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"

				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.supplier,
						dr_or_cr: tax.base_tax_amount_after_discount_amount,
						dr_or_cr + "_in_account_currency": tax.base_tax_amount_after_discount_amount \
							if account_currency==self.company_currency \
							else tax.tax_amount_after_discount_amount,
						"cost_center": tax.cost_center
					}, account_currency)
				)

			# accumulate valuation tax
			if self.is_opening == "No" and tax.category in ("Valuation", "Valuation and Total") and flt(tax.base_tax_amount_after_discount_amount):
				if auto_accounting_for_stock and not tax.cost_center:
					frappe.throw(_("Cost Center is required in row {0} in Taxes table for type {1}").format(tax.idx, _(tax.category)))
				valuation_tax.setdefault(tax.cost_center, 0)
				valuation_tax[tax.cost_center] += \
					(tax.add_deduct_tax == "Add" and 1 or -1) * flt(tax.base_tax_amount_after_discount_amount)

		# item gl entries
		negative_expense_to_be_booked = 0.0
		stock_items = self.get_stock_items()
		for item in self.get("items"):
			if flt(item.base_net_amount):
				account_currency = get_account_currency(item.expense_account)
				gl_entries.append(
					self.get_gl_dict({
						"account": item.expense_account,
						"against": self.supplier,
						"debit": item.base_net_amount,
						"debit_in_account_currency": item.base_net_amount \
							if account_currency==self.company_currency else item.net_amount,
						"cost_center": item.cost_center
					}, account_currency)
				)

			if auto_accounting_for_stock and self.is_opening == "No" and \
				item.item_code in stock_items and item.item_tax_amount:
					# Post reverse entry for Stock-Received-But-Not-Billed if it is booked in Purchase Receipt
					if item.purchase_receipt:
						negative_expense_booked_in_pr = frappe.db.sql("""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account=%s""",
							(item.purchase_receipt, expenses_included_in_valuation))

						if not negative_expense_booked_in_pr:
							gl_entries.append(
								self.get_gl_dict({
									"account": stock_received_but_not_billed,
									"against": self.supplier,
									"debit": flt(item.item_tax_amount, self.precision("item_tax_amount", item)),
									"remarks": self.remarks or "Accounting Entry for Stock"
								})
							)

							negative_expense_to_be_booked += flt(item.item_tax_amount, self.precision("item_tax_amount", item))

		if self.is_opening == "No" and negative_expense_to_be_booked and valuation_tax:
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
						"against": self.supplier,
						"credit": applicable_amount,
						"remarks": self.remarks or "Accounting Entry for Stock"
					})
				)

				i += 1

		# writeoff account includes petty difference in the invoice amount
		# and the amount that is paid
		if self.write_off_account and flt(self.write_off_amount):
			write_off_account_currency = get_account_currency(self.write_off_account)

			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"party_type": "Supplier",
					"party": self.supplier,
					"against": self.write_off_account,
					"debit": self.base_write_off_amount,
					"debit_in_account_currency": self.base_write_off_amount \
						if self.party_account_currency==self.company_currency else self.write_off_amount,
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
				}, self.party_account_currency)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": self.supplier,
					"credit": flt(self.base_write_off_amount),
					"credit_in_account_currency": self.base_write_off_amount \
						if write_off_account_currency==self.company_currency else self.write_off_amount,
					"cost_center": self.write_off_cost_center
				})
			)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2))

	def on_cancel(self):
		self.check_for_stopped_or_closed_status()

		if not self.is_return:
			from erpnext.accounts.utils import remove_against_link_from_jv
			remove_against_link_from_jv(self.doctype, self.name)

			self.update_prevdoc_status()
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")
		self.make_gl_entries_on_cancel()
		self.update_project()

	def update_project(self):
		project_list = []
		for d in self.items:
			if d.project_name and d.project_name not in project_list:
				project = frappe.get_doc("Project", d.project_name)
				project.flags.dont_sync_tasks = True
				project.update_purchase_costing()
				project.save()
				project_list.append(d.project_name)

	def validate_supplier_invoice(self):
		if self.bill_date:
			if getdate(self.bill_date) > getdate(self.posting_date):
				frappe.throw("Supplier Invoice Date cannot be greater than Posting Date")
		if self.bill_no:
			if cint(frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness")):
				pi = frappe.db.exists("Purchase Invoice", {"bill_no": self.bill_no,
					"fiscal_year": self.fiscal_year, "name": ("!=", self.name), "docstatus": ("<", 2)})
				if pi:
					frappe.throw("Supplier Invoice No exists in Purchase Invoice {0}".format(pi))

@frappe.whitelist()
def get_expense_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	# expense account can be any Debit account,
	# but can also be a Liability account with account_type='Expense Account' in special circumstances.
	# Hence the first condition is an "OR"
	return frappe.db.sql("""select tabAccount.name from `tabAccount`
			where (tabAccount.report_type = "Profit and Loss"
					or tabAccount.account_type in ("Expense Account", "Fixed Asset", "Temporary"))
				and tabAccount.is_group=0
				and tabAccount.docstatus!=2
				and tabAccount.company = %(company)s
				and tabAccount.{key} LIKE %(txt)s
				{mcond}""".format( key=frappe.db.escape(searchfield), mcond=get_match_cond(doctype) ),
				{ 'company': filters['company'], 'txt': "%%%s%%" % frappe.db.escape(txt) })

@frappe.whitelist()
def make_debit_note(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Purchase Invoice", source_name, target_doc)
