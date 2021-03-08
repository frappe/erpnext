# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import cint, cstr, formatdate, flt, getdate, nowdate, get_link_to_form
from frappe import _, throw
import frappe.defaults

from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.controllers.buying_controller import BuyingController
from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_billed_amount_based_on_pr, update_billed_amount_based_on_po
from erpnext.stock import get_warehouse_account_map
from erpnext.accounts.general_ledger import make_gl_entries, merge_similar_entries, delete_gl_entries
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import update_rate_in_serial_no_for_non_asset_items
from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from frappe.model.mapper import get_mapped_doc
from six import iteritems
from erpnext.accounts.doctype.sales_invoice.sales_invoice import validate_inter_company_party, update_linked_doc,\
	unlink_inter_company_doc
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_item_account_wise_additional_cost

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class ConfirmRevaluePurchaseReceipt(frappe.ValidationError):
	pass

class PurchaseInvoice(BuyingController):
	def __init__(self, *args, **kwargs):
		super(PurchaseInvoice, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'source_dt': 'Purchase Invoice Item',
			'target_field': 'billed_qty',
			'target_ref_field': 'qty',
			'target_dt': 'Purchase Order Item',
			'join_field': 'po_detail',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_billed',
			'source_field': 'qty',
			'percent_join_field': 'purchase_order',
			'overflow_type': 'billing',
			'extra_cond': """ and exists(select name from `tabPurchase Invoice` where name=`tabPurchase Invoice Item`.parent
				and (is_return=0 or reopen_order=1))"""
		},
		{
			'source_dt': 'Purchase Invoice Item',
			'target_field': 'billed_amt',
			'target_dt': 'Purchase Order Item',
			'join_field': 'po_detail',
			'source_field': 'amount',
			'extra_cond': """ and exists(select name from `tabPurchase Invoice` where name=`tabPurchase Invoice Item`.parent
				and (is_return=0 or reopen_order=1))"""
		},
		{
			'source_dt': 'Purchase Invoice Item',
			'update_children': self.update_billing_status_in_pr,
			'target_field': 'billed_qty',
			'target_ref_field': 'received_qty',
			'target_dt': 'Purchase Receipt Item',
			'join_field': 'pr_detail',
			'target_parent_dt': 'Purchase Receipt',
			'target_parent_field': 'per_billed',
		},
		{
			'source_dt': 'Purchase Invoice Item',
			'target_dt': 'Purchase Order Item',
			'join_field': 'po_detail',
			'target_field': '(billed_qty + returned_qty)',
			'update_children': False,
			'target_ref_field': 'qty',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_completed',
			'percent_join_field': 'purchase_order'
		},
		{
			'source_dt': 'Purchase Invoice Item',
			'target_dt': 'Purchase Receipt Item',
			'join_field': 'pr_detail',
			'target_field': '(billed_qty + returned_qty)',
			'update_children': False,
			'target_ref_field': 'qty',
			'no_tolerance': 1
		}]

	def update_status_updater_args(self):
		if cint(self.update_stock):
			self.status_updater.append({
				'source_dt':'Purchase Invoice Item',
				'target_dt':'Purchase Order Item',
				'target_parent_dt':'Purchase Order',
				'target_parent_field':'per_received',
				'target_field':'received_qty',
				'target_ref_field':'qty',
				'source_field':'received_qty',
				'join_field':'po_detail',
				'percent_join_field':'purchase_order',
				'second_source_dt': 'Purchase Receipt Item',
				'second_source_field': 'received_qty',
				'second_join_field': 'purchase_order_item',
				'overflow_type': 'receipt',
				'extra_cond': """ and exists(select name from `tabPurchase Invoice`
					where name=`tabPurchase Invoice Item`.parent and update_stock = 1 and (is_return=0 or reopen_order=1))""",
				'second_source_extra_cond': """ and exists (select name from `tabPurchase Receipt`
					where name=`tabPurchase Receipt Item`.parent and (is_return=0 or reopen_order=1))""",
			})
			if cint(self.is_return):
				self.status_updater.append({
					'source_dt': 'Purchase Invoice Item',
					'target_dt': 'Purchase Order Item',
					'join_field': 'po_detail',
					'target_field': 'total_returned_qty',
					'target_parent_dt': 'Purchase Order',
					'source_field': '-1 * received_qty',
					'second_source_dt': 'Purchase Receipt Item',
					'second_source_field': '-1 * received_qty',
					'second_join_field': 'purchase_order_item',
					'extra_cond': """ and exists (select name from `tabPurchase Invoice`
						where name=`tabPurchase Invoice Item`.parent and is_return=1 and update_stock=1)""",
					'second_source_extra_cond': """ and exists (select name from `tabPurchase Receipt`
						where name=`tabPurchase Receipt Item`.parent and is_return=1)"""
				})

	def onload(self):
		super(PurchaseInvoice, self).onload()
		supplier_tds = frappe.db.get_value("Supplier", self.supplier, "tax_withholding_category")
		self.set_onload("supplier_tds", supplier_tds)

	def before_save(self):
		if not self.on_hold:
			self.release_date = ''


	def invoice_is_blocked(self):
		return self.on_hold and (not self.release_date or self.release_date > getdate(nowdate()))

	def validate(self):
		if not self.is_opening:
			self.is_opening = 'No'

		self.validate_posting_time()

		super(PurchaseInvoice, self).validate()

		# apply tax withholding only if checked and applicable
		self.set_tax_withholding()

		if not self.is_return:
			self.po_pr_required()
			self.validate_supplier_invoice()

		self.validate_update_stock_mandatory()

		# validate cash purchase
		if (self.is_paid == 1):
			self.validate_cash()

		# validate service stop date to lie in between start and end date
		validate_service_stop_date(self)

		if self._action=="submit" and self.update_stock:
			self.make_batches('warehouse')

		self.validate_release_date()
		self.check_conversion_rate()
		self.validate_credit_to_acc()
		self.clear_unallocated_advances("Purchase Invoice Advance", "advances")
		self.check_on_hold_or_closed_status()
		self.validate_with_previous_doc()
		self.validate_return_against()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.set_expense_account(for_validate=True)
		self.set_against_expense_account()
		self.validate_write_off_account()
		if frappe.get_cached_value("Accounts Settings", None, "validate_over_billing_in_purchase_invoice"):
			self.validate_multiple_billing("Purchase Receipt", "pr_detail", "amount", "items")
		self.create_remarks()
		self.set_status()
		self.set_title()
		self.validate_purchase_receipt_if_update_stock()
		validate_inter_company_party(self.doctype, self.supplier, self.company, self.inter_company_invoice_reference)

	def validate_release_date(self):
		if self.release_date and getdate(nowdate()) >= getdate(self.release_date):
			frappe.throw(_('Release date must be in the future'))

	def validate_cash(self):
		if not self.cash_bank_account and flt(self.paid_amount):
			frappe.throw(_("Cash or Bank Account is mandatory for making payment entry"))

		if (flt(self.paid_amount) + flt(self.write_off_amount)
			- flt(self.get("rounded_total") or self.grand_total)
			> 1/(10**(self.precision("base_grand_total") + 1))):

			frappe.throw(_("""Paid amount + Write Off Amount can not be greater than Grand Total"""))

	def create_remarks(self):
		if not self.remarks:
			if self.bill_no and self.bill_date:
				self.remarks = _("Against Supplier Invoice {0} dated {1}").format(self.bill_no,
					formatdate(self.bill_date))

	def set_title(self):
		if self.letter_of_credit:
			self.title = "{0}/{1}".format(self.letter_of_credit, self.supplier_name)
		else:
			self.title = self.supplier_name

	def set_missing_values(self, for_validate=False):
		if not self.credit_to:
			billing_party_type, billing_party = self.get_billing_party()
			self.credit_to = get_party_account(billing_party_type, billing_party, self.company,
				transaction_type=self.get('transaction_type'))
			self.party_account_currency = frappe.get_cached_value("Account", self.credit_to, "account_currency")
		if not self.due_date:
			self.due_date = get_due_date(self.posting_date, "Supplier", self.supplier, self.company,  self.bill_date)

		super(PurchaseInvoice, self).set_missing_values(for_validate)

	def check_conversion_rate(self):
		default_currency = erpnext.get_company_currency(self.company)
		if not default_currency:
			throw(_('Please enter default currency in Company Master'))
		if (self.currency == default_currency and flt(self.conversion_rate) != 1.00) or not self.conversion_rate or (self.currency != default_currency and flt(self.conversion_rate) == 1.00):
			throw(_("Conversion rate cannot be 0 or 1"))

	def validate_credit_to_acc(self):
		account = frappe.db.get_value("Account", self.credit_to,
			["account_type", "report_type", "account_currency"], as_dict=True)

		if account.report_type != "Balance Sheet":
			frappe.throw(_("Please ensure {} account is a Balance Sheet account. \
					You can change the parent account to a Balance Sheet account or select a different account.")
				.format(frappe.bold("Credit To")), title=_("Invalid Account"))

		if (self.supplier or self.letter_of_credit) and account.account_type != "Payable":
			frappe.throw(_("Credit To account must be a Payable account"))

		self.party_account_currency = account.account_currency

	def check_on_hold_or_closed_status(self):
		check_list = []

		for d in self.get('items'):
			if d.purchase_order and not d.purchase_order in check_list and not d.purchase_receipt:
				check_list.append(d.purchase_order)
				check_on_hold_or_closed_status('Purchase Order', d.purchase_order)

	def validate_with_previous_doc(self):
		super(PurchaseInvoice, self).validate_with_previous_doc({
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "po_detail",
				"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Purchase Receipt": {
				"ref_dn_field": "purchase_receipt",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Receipt Item": {
				"ref_dn_field": "pr_detail",
				"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="], ["vehicle", "="]],
				"is_child_table": True
			}
		})

		if cint(frappe.db.get_single_value('Buying Settings', 'maintain_same_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([
				["Purchase Order", "purchase_order", "po_detail"],
				["Purchase Receipt", "purchase_receipt", "pr_detail"]
			])

	def check_valuation_amounts_with_previous_doc(self):
		does_revalue = False

		if not self.is_return or not self.update_stock:
			for item in self.items:
				if item.pr_detail:
					pr_item = frappe.db.get_value("Purchase Receipt Item", item.pr_detail,
						["base_net_rate", "item_tax_amount"], as_dict=1)

					if pr_item:
						# if rate is different
						if abs(item.base_net_rate - pr_item.base_net_rate) > 0.1/10**self.precision("base_net_rate", "items"):
							does_revalue = True
							if not cint(self.revalue_purchase_receipt):
								frappe.throw(_("Row {0}: Item Rate does not match the Rate in Purchase Receipt. "
									"Set 'Revalue Purchase Receipt' to confirm.").format(item.idx), ConfirmRevaluePurchaseReceipt)

						# if item tax amount is different
						if abs(item.item_tax_amount - pr_item.item_tax_amount) > 0.1/10**self.precision("item_tax_amount", "items"):
							does_revalue = True
							if not cint(self.revalue_purchase_receipt):
								frappe.throw(_("Row {0}: Item Valuation Tax Amount does not match the Valuation Tax Amount in Purchase Receipt. "
									"Set 'Revalue Purchase Receipt' to confirm.").format(item.idx), ConfirmRevaluePurchaseReceipt)

		if not does_revalue:
			self.revalue_purchase_receipt = 0

	def validate_return_against(self):
		if cint(self.is_return) and self.return_against:
			against_doc = frappe.get_doc("Purchase Invoice", self.return_against)
			if not against_doc:
				frappe.throw(_("Return Against Purchase Invoice {0} does not exist").format(self.return_against))
			if against_doc.company != self.company:
				frappe.throw(_("Return Against Purchase Invoice {0} must be against the same Company").format(self.return_against))
			if against_doc.supplier != self.supplier or against_doc.letter_of_credit != self.letter_of_credit:
				frappe.throw(_("Return Against Purchase Invoice {0} must be against the same Supplier and Letter of Credit").format(self.return_against))
			if against_doc.credit_to != self.credit_to:
				frappe.throw(_("Return Against Purchase Invoice {0} must have the same Credit To account").format(self.return_against))

	def validate_warehouse(self):
		if self.update_stock:
			for d in self.get('items'):
				if not d.warehouse:
					frappe.throw(_("Warehouse required at Row No {0}, please set default warehouse for the item {1} for the company {2}").
						format(d.idx, d.item_code, self.company))

		super(PurchaseInvoice, self).validate_warehouse()

	def validate_item_code(self):
		for d in self.get('items'):
			if not d.item_code:
				frappe.msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

	def set_expense_account(self, for_validate=False):
		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)

		if auto_accounting_for_stock:
			stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")
			stock_items = self.get_stock_items()

		asset_items = [d.is_fixed_asset for d in self.items if d.is_fixed_asset]
		if len(asset_items) > 0:
			asset_received_but_not_billed = self.get_company_default("asset_received_but_not_billed")

		if self.update_stock:
			self.validate_item_code()
			self.validate_warehouse()
			if auto_accounting_for_stock:
				warehouse_account = get_warehouse_account_map(self.company)

		for item in self.get("items"):
			# in case of auto inventory accounting,
			# expense account is always "Stock Received But Not Billed" for a stock item
			# except epening entry, drop-ship entry and fixed asset items
			if item.item_code:
				asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")

			if auto_accounting_for_stock and item.item_code in stock_items \
				and self.is_opening == 'No' and not item.is_fixed_asset \
				and (not item.po_detail or
					not frappe.db.get_value("Purchase Order Item", item.po_detail, "delivered_by_supplier")):

				if self.update_stock:
					item.expense_account = warehouse_account[item.warehouse]["account"]
				else:
					item.expense_account = stock_not_billed_account
			elif item.is_fixed_asset and not is_cwip_accounting_enabled(asset_category):
				item.expense_account = get_asset_category_account('fixed_asset_account', item=item.item_code,
					company = self.company)
			elif item.is_fixed_asset and item.pr_detail:
				item.expense_account = asset_received_but_not_billed
			elif not item.expense_account and for_validate:
				throw(_("Expense account is mandatory for item {0}").format(item.item_code or item.item_name))

	def set_against_expense_account(self):
		against_accounts = []
		for item in self.get("items"):
			if item.expense_account and (item.expense_account not in against_accounts):
				against_accounts.append(item.expense_account)

		self.against_expense_account = ", ".join(against_accounts)

	def po_pr_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		if self.is_return:
			return

		po_required = frappe.get_cached_value("Buying Settings", None, 'po_required') == 'Yes'
		pr_required = frappe.get_cached_value("Buying Settings", None, 'pr_required') == 'Yes'

		if po_required and frappe.get_cached_value('Supplier', self.supplier, 'po_not_required'):
			po_required = False
		if pr_required and frappe.get_cached_value('Supplier', self.supplier, 'pr_not_required'):
			pr_required = False

		if self.get('transaction_type'):
			tt_po_required = frappe.get_cached_value('Transaction Type', self.get('transaction_type'), 'po_required')
			tt_pr_required = frappe.get_cached_value('Transaction Type', self.get('transaction_type'), 'pr_required')
			if tt_po_required:
				po_required = tt_po_required == 'Yes'
			if tt_pr_required:
				pr_required = tt_pr_required == 'Yes'

		if not po_required and not pr_required:
			return

		for d in self.get('items'):
			if not d.item_code:
				continue

			is_stock_item = frappe.get_cached_value('Item', d.item_code, 'is_stock_item')
			if po_required and not d.get('purchase_order'):
				frappe.throw(_("Purchase Order is mandatory for Item {0}").format(d.item_code))
			if pr_required and not d.get('purchase_receipt') and is_stock_item:
				frappe.throw(_("Purchase Receipt is mandatory for Item {0}").format(d.item_code))

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

	def validate_purchase_receipt_if_update_stock(self):
		if not cint(self.is_return) and cint(self.update_stock):
			for item in self.get("items"):
				if item.purchase_receipt:
					frappe.throw(_("Stock cannot be updated against Purchase Receipt {0}")
						.format(item.purchase_receipt))

	def validate_update_stock_mandatory(self):
		if not cint(self.update_stock) and not cint(frappe.db.get_single_value("Accounts Settings", "allow_invoicing_without_updating_stock")) and self.return_against:
			for d in self.items:
				if d.item_code and not d.purchase_receipt and frappe.get_cached_value("Item", d.item_code, "is_stock_item"):
					frappe.throw(_("'Update Stock' must be enabled for stock items if Purchase Invoice is not made from Purchase Receipt."))

	def before_submit(self):
		self.check_valuation_amounts_with_previous_doc()

	def on_submit(self):
		super(PurchaseInvoice, self).on_submit()

		self.check_prev_docstatus()
		self.update_status_updater_args()
		self.update_prevdoc_status()

		self.update_vehicle_booking_order()

		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.base_grand_total)

		if not self.is_return:
			self.update_against_document_in_jv()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.update_stock_ledger()
			from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
			update_serial_nos_after_submit(self, "items")

		if not self.is_return or not self.update_stock:
			self.update_receipts_valuation()

		# this sequence because outstanding may get -negative
		self.make_gl_entries()

		self.validate_zero_outstanding()

		self.update_project()
		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)

	def update_receipts_valuation(self):
		receipt_documents = set([('Purchase Receipt', item.purchase_receipt) for item in self.items if item.purchase_receipt])

		if self.is_return and self.return_against and not self.update_stock:
			if frappe.db.get_value("Purchase Invoice", self.return_against, 'update_stock'):
				receipt_documents.add(('Purchase Invoice', self.return_against))

		for dt, dn in receipt_documents:
			pr_doc = frappe.get_doc(dt, dn)

			# set billed item tax amount and billed net amount in pr item
			if dt == "Purchase Receipt":
				pr_doc.set_billed_valuation_amounts()
			elif dt == "Purchase Invoice":
				pr_doc.set_debit_note_amount()

			# set valuation rate in pr item
			pr_doc.update_valuation_rate("items")

			# db_update will update and save valuation_rate in PR
			for item in pr_doc.get("items"):
				item.db_update()

			# update latest valuation rate in serial no
			update_rate_in_serial_no_for_non_asset_items(pr_doc)

			# update stock & gl entries for cancelled state of PR
			pr_doc.docstatus = 2
			pr_doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			pr_doc.make_gl_entries_on_cancel(repost_future_gle=False)

			# update stock & gl entries for submit state of PR
			pr_doc.docstatus = 1
			pr_doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			pr_doc.make_gl_entries()

	def set_debit_note_amount(self):
		for d in self.items:
			debit_note_amount = frappe.db.sql("""
				select -sum(item.base_net_amount)
				from `tabPurchase Invoice Item` item, `tabPurchase Invoice` inv
				where inv.name=item.parent and item.pi_detail=%s and item.docstatus=1
					and inv.update_stock = 0 and inv.is_return = 1 and inv.return_against = %s
			""",[ d.name, self.name])

			d.debit_note_amount = flt(debit_note_amount[0][0]) if debit_note_amount else 0

	def make_gl_entries(self, gl_entries=None, repost_future_gle=True, from_repost=False):
		if not self.grand_total:
			return
		if not gl_entries:
			gl_entries = self.get_gl_entries()

		if gl_entries:
			make_gl_entries(gl_entries,  cancel=(self.docstatus == 2), merge_entries=False, from_repost=from_repost)

			if (repost_future_gle or self.flags.repost_future_gle) and cint(self.update_stock) and self.auto_accounting_for_stock:
				from erpnext.controllers.stock_controller import update_gl_entries_after
				items, warehouses = self.get_items_and_warehouses()
				update_gl_entries_after(self.posting_date, self.posting_time,
					warehouses, items, company = self.company)

		elif self.docstatus == 2 and cint(self.update_stock) and self.auto_accounting_for_stock:
			delete_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_gl_entries(self, warehouse_account=None):
		self.auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
		if self.auto_accounting_for_stock:
			self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
		else:
			self.stock_received_but_not_billed = None
		self.expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")
		self.negative_expense_to_be_booked = 0.0
		gl_entries = []

		self.make_supplier_gl_entry(gl_entries)
		self.make_item_gl_entries(gl_entries)

		if self.check_asset_cwip_enabled():
			self.get_asset_gl_entry(gl_entries)

		self.make_tax_gl_entries(gl_entries)

		gl_entries = make_regional_gl_entries(gl_entries, self)

		gl_entries = merge_similar_entries(gl_entries)

		self.make_payment_gl_entries(gl_entries)
		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)

		return gl_entries

	def check_asset_cwip_enabled(self):
		# Check if there exists any item with cwip accounting enabled in it's asset category
		for item in self.get("items"):
			if item.item_code and item.is_fixed_asset:
				asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")
				if is_cwip_accounting_enabled(asset_category):
					return 1
		return 0

	def make_supplier_gl_entry(self, gl_entries):
		# Checked both rounding_adjustment and rounded_total
		# because rounded_total had value even before introcution of posting GLE based on rounded total
		grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total

		if grand_total:
			billing_party_type, billing_party = self.get_billing_party()

			# Didnot use base_grand_total to book rounding loss gle
			grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
				self.precision("grand_total"))
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"party_type": billing_party_type,
					"party": billing_party,
					"against": self.against_expense_account,
					"credit": grand_total_in_company_currency,
					"credit_in_account_currency": grand_total_in_company_currency \
						if self.party_account_currency==self.company_currency else grand_total,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else None,
					"against_voucher_type": self.doctype if cint(self.is_return) and self.return_against else None,
					"cost_center": self.cost_center
				}, self.party_account_currency, item=self)
			)

	def make_item_gl_entries(self, gl_entries):
		# item gl entries
		stock_items = self.get_stock_items()
		expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		if self.update_stock and self.auto_accounting_for_stock:
			warehouse_account = get_warehouse_account_map(self.company)
		
		billing_party_type, billing_party = self.get_billing_party()

		voucher_wise_stock_value = {}
		if self.update_stock:
			for d in frappe.get_all('Stock Ledger Entry',
				fields = ["voucher_detail_no", "stock_value_difference"], filters={'voucher_no': self.name}):
				voucher_wise_stock_value.setdefault(d.voucher_detail_no, d.stock_value_difference)

		valuation_tax_accounts = [d.account_head for d in self.get("taxes")
			if d.category in ('Valuation', 'Valuation and Total')
			and flt(d.base_tax_amount_after_discount_amount)]

		for item in self.get("items"):
			if flt(item.base_net_amount):
				account_currency = get_account_currency(item.expense_account)
				if item.item_code:
					asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")

				if self.update_stock and self.auto_accounting_for_stock and item.item_code in stock_items:
					# warehouse account
					warehouse_debit_amount = self.make_stock_adjustment_entry(gl_entries,
						item, voucher_wise_stock_value, account_currency)

					gl_entries.append(
						self.get_gl_dict({
							"account": item.expense_account,
							"against": billing_party,
							"debit": warehouse_debit_amount,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"cost_center": item.cost_center or self.cost_center,
							"project": item.project
						}, account_currency, item=item)
					)

					if flt(item.debit_note_amount):
						gl_entries.append(
							self.get_gl_dict({
								"account": self.stock_received_but_not_billed,
								"against": billing_party,
								"debit": flt(item.debit_note_amount, item.precision("base_net_amount")),
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"cost_center": item.cost_center or self.cost_center,
								"project": item.project
							}, item=item)
						)

					# Amount added through landed-cost-voucher
					if flt(item.landed_cost_voucher_amount):
						gl_entries.append(self.get_gl_dict({
							"account": expenses_included_in_valuation,
							"against": item.expense_account,
							"cost_center": item.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(item.landed_cost_voucher_amount),
							"project": item.project
						}, item=item))

					# sub-contracting warehouse
					if flt(item.rm_supp_cost):
						supplier_warehouse_account = warehouse_account[self.supplier_warehouse]["account"]
						if not supplier_warehouse_account:
							frappe.throw(_("Please set account in Warehouse {0}")
								.format(self.supplier_warehouse))
						gl_entries.append(self.get_gl_dict({
							"account": supplier_warehouse_account,
							"against": item.expense_account,
							"cost_center": item.cost_center or self.cost_center,
							"project": item.project or self.project,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(item.rm_supp_cost)
						}, warehouse_account[self.supplier_warehouse]["account_currency"], item=item))

				elif not item.is_fixed_asset or (item.is_fixed_asset and not is_cwip_accounting_enabled(asset_category)):
					expense_account = (item.expense_account
						if (not item.enable_deferred_expense or self.is_return) else item.deferred_expense_account)

					if not item.is_fixed_asset:
						amount = flt(item.base_net_amount, item.precision("base_net_amount"))
					else:
						amount = flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount"))

					gl_entries.append(self.get_gl_dict({
							"account": expense_account,
							"against": billing_party,
							"debit": amount,
							"cost_center": item.cost_center,
							"project": item.project or self.project
						}, account_currency, item=item))

					# If asset is bought through this document and not linked to PR
					if self.update_stock and item.landed_cost_voucher_amount:
						expenses_included_in_asset_valuation = self.get_company_default("expenses_included_in_asset_valuation")
						# Amount added through landed-cost-voucher
						gl_entries.append(self.get_gl_dict({
							"account": expenses_included_in_asset_valuation,
							"against": expense_account,
							"cost_center": item.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(item.landed_cost_voucher_amount),
							"project": item.project or self.project
						}, item=item))

						gl_entries.append(self.get_gl_dict({
							"account": expense_account,
							"against": expenses_included_in_asset_valuation,
							"cost_center": item.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"debit": flt(item.landed_cost_voucher_amount),
							"project": item.project or self.project
						}, item=item))

						# update gross amount of asset bought through this document
						assets = frappe.db.get_all('Asset',
							filters={ 'purchase_invoice': self.name, 'item_code': item.item_code }
						)
						for asset in assets:
							frappe.db.set_value("Asset", asset.name, "gross_purchase_amount", flt(item.valuation_rate))
							frappe.db.set_value("Asset", asset.name, "purchase_receipt_amount", flt(item.valuation_rate))

			if self.auto_accounting_for_stock and self.is_opening == "No" and not self.update_stock and \
				item.item_code in stock_items and item.item_tax_amount:
						gl_entries.append(
							self.get_gl_dict({
								"account": self.stock_received_but_not_billed,
								"against": billing_party,
								"debit": flt(item.item_tax_amount, item.precision("item_tax_amount")),
								"remarks": self.remarks,
								"cost_center": item.cost_center or self.cost_center,
								"project": item.project or self.project
							}, item=item)
						)

						self.negative_expense_to_be_booked += flt(item.item_tax_amount, \
							item.precision("item_tax_amount"))

	def get_asset_gl_entry(self, gl_entries):
		billing_party_type, billing_party = self.get_billing_party()
		arbnb_account = self.get_company_default("asset_received_but_not_billed")
		eiiav_account = self.get_company_default("expenses_included_in_asset_valuation")

		for item in self.get("items"):
			if item.is_fixed_asset:
				asset_amount = flt(item.net_amount) + flt(item.item_tax_amount/self.conversion_rate)
				base_asset_amount = flt(item.base_net_amount + item.item_tax_amount)

				item_exp_acc_type = frappe.db.get_value('Account', item.expense_account, 'account_type')
				if (not item.expense_account or item_exp_acc_type not in ['Asset Received But Not Billed', 'Fixed Asset']):
					item.expense_account = arbnb_account

				if not self.update_stock:
					arbnb_currency = get_account_currency(item.expense_account)
					gl_entries.append(self.get_gl_dict({
						"account": item.expense_account,
						"against": billing_party,
						"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
						"debit": base_asset_amount,
						"debit_in_account_currency": (base_asset_amount
							if arbnb_currency == self.company_currency else asset_amount),
						"cost_center": item.cost_center or self.cost_center,
						"project": item.project or self.project
					}, item=item))

					if item.item_tax_amount:
						asset_eiiav_currency = get_account_currency(eiiav_account)
						gl_entries.append(self.get_gl_dict({
							"account": eiiav_account,
							"against": billing_party,
							"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
							"cost_center": item.cost_center or self.cost_center,
							"credit": item.item_tax_amount,
							"credit_in_account_currency": (item.item_tax_amount
								if asset_eiiav_currency == self.company_currency else
									item.item_tax_amount / self.conversion_rate)
						}, item=item))
				else:
					cwip_account = get_asset_account("capital_work_in_progress_account", company = self.company)

					cwip_account_currency = get_account_currency(cwip_account)
					gl_entries.append(self.get_gl_dict({
						"account": cwip_account,
						"against": billing_party,
						"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
						"debit": base_asset_amount,
						"debit_in_account_currency": (base_asset_amount
							if cwip_account_currency == self.company_currency else asset_amount),
						"cost_center": self.cost_center,
						"project": item.project or self.project
					}, item=item))

					if item.item_tax_amount and not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
						asset_eiiav_currency = get_account_currency(eiiav_account)
						gl_entries.append(self.get_gl_dict({
							"account": eiiav_account,
							"against": billing_party,
							"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
							"cost_center": item.cost_center or self.cost_center,
							"credit": item.item_tax_amount,
							"project": item.project or self.project,
							"credit_in_account_currency": (item.item_tax_amount
								if asset_eiiav_currency == self.company_currency else
									item.item_tax_amount / self.conversion_rate)
						}, item=item))

					# When update stock is checked
					# Assets are bought through this document then it will be linked to this document
					if self.update_stock:
						if flt(item.landed_cost_voucher_amount):
							gl_entries.append(self.get_gl_dict({
								"account": eiiav_account,
								"against": cwip_account,
								"cost_center": item.cost_center,
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"credit": flt(item.landed_cost_voucher_amount),
								"project": item.project or self.project
							}, item=item))

							gl_entries.append(self.get_gl_dict({
								"account": cwip_account,
								"against": eiiav_account,
								"cost_center": item.cost_center,
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"debit": flt(item.landed_cost_voucher_amount),
								"project": item.project or self.project
							}, item=item))

						# update gross amount of assets bought through this document
						assets = frappe.db.get_all('Asset',
							filters={ 'purchase_invoice': self.name, 'item_code': item.item_code }
						)
						for asset in assets:
							frappe.db.set_value("Asset", asset.name, "gross_purchase_amount", flt(item.valuation_rate))
							frappe.db.set_value("Asset", asset.name, "purchase_receipt_amount", flt(item.valuation_rate))

		return gl_entries

	def make_stock_adjustment_entry(self, gl_entries, item, voucher_wise_stock_value, account_currency):
		net_amt_precision = item.precision("base_net_amount")
		val_rate_db_precision = 6 if cint(item.precision("valuation_rate")) <= 6 else 9

		warehouse_debit_amount = flt(flt(item.valuation_rate, val_rate_db_precision)
			* flt(item.qty)	* flt(item.conversion_factor), net_amt_precision)

		# Stock ledger value is not matching with the warehouse amount
		if (self.update_stock and voucher_wise_stock_value.get(item.name) and
			warehouse_debit_amount != flt(voucher_wise_stock_value.get(item.name), net_amt_precision)):

			stock_adjustment_account = self.get_company_default("stock_adjustment_account")
			stock_amount = flt(voucher_wise_stock_value.get(item.name), net_amt_precision)
			stock_adjustment_amt = warehouse_debit_amount - stock_amount

			gl_entries.append(
				self.get_gl_dict({
					"account": stock_adjustment_account,
					"against": item.expense_account,
					"debit": stock_adjustment_amt,
					"remarks": self.get("remarks") or _("Stock Adjustment"),
					"cost_center": item.cost_center or self.cost_center,
					"project": item.project or self.project
				}, account_currency, item=item)
			)

			warehouse_debit_amount = stock_amount

		return warehouse_debit_amount

	def make_tax_gl_entries(self, gl_entries):
		# tax table gl entries
		billing_party_type, billing_party = self.get_billing_party()
		valuation_tax = {}
		for tax in self.get("taxes"):
			if tax.category in ("Total", "Valuation and Total") and flt(tax.base_tax_amount_after_discount_amount):
				account_currency = get_account_currency(tax.account_head)

				dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"

				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": billing_party,
						dr_or_cr: tax.base_tax_amount_after_discount_amount,
						dr_or_cr + "_in_account_currency": tax.base_tax_amount_after_discount_amount \
							if account_currency==self.company_currency \
							else tax.tax_amount_after_discount_amount,
						"cost_center": tax.cost_center or self.cost_center
					}, account_currency, item=tax)
				)
			# accumulate valuation tax
			if self.is_opening == "No" and tax.category in ("Valuation", "Valuation and Total") and flt(tax.base_tax_amount_after_discount_amount):
				valuation_tax.setdefault(tax.name, 0)
				valuation_tax[tax.name] += \
					(tax.add_deduct_tax == "Add" and 1 or -1) * flt(tax.base_tax_amount_after_discount_amount)

		if self.is_opening == "No" and self.negative_expense_to_be_booked and valuation_tax:
			# credit valuation tax amount in "Expenses Included In Valuation"
			# this will balance out valuation amount included in cost of goods sold

			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = self.negative_expense_to_be_booked
			i = 1
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):
					if i == len(valuation_tax):
						applicable_amount = amount_including_divisional_loss
					else:
						applicable_amount = self.negative_expense_to_be_booked * (valuation_tax[tax.name] / total_valuation_amount)
						amount_including_divisional_loss -= applicable_amount

					gl_entries.append(
						self.get_gl_dict({
							"account": tax.account_head,
							"cost_center": tax.cost_center,
							"against": billing_party,
							"credit": applicable_amount,
							"remarks": self.remarks,
						}, item=tax)
					)

					i += 1

		if self.auto_accounting_for_stock and self.update_stock and valuation_tax:
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):
					gl_entries.append(
						self.get_gl_dict({
							"account": tax.account_head,
							"cost_center": tax.cost_center,
							"against": billing_party,
							"credit": valuation_tax[tax.name],
							"remarks": self.remarks
						}, item=tax)
					)

	def make_payment_gl_entries(self, gl_entries):
		# Make Cash GL Entries
		if cint(self.is_paid) and self.cash_bank_account and self.paid_amount:
			billing_party_type, billing_party = self.get_billing_party()
			bank_account_currency = get_account_currency(self.cash_bank_account)
			# CASH, make payment entries
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"party_type": billing_party_type,
					"party": billing_party,
					"against": self.cash_bank_account,
					"debit": self.base_paid_amount,
					"debit_in_account_currency": self.base_paid_amount \
						if self.party_account_currency==self.company_currency else self.paid_amount,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"project": self.project
				}, self.party_account_currency, item=self)
			)

			gl_entries.append(
				self.get_gl_dict({
					"account": self.cash_bank_account,
					"against": billing_party,
					"credit": self.base_paid_amount,
					"credit_in_account_currency": self.base_paid_amount \
						if bank_account_currency==self.company_currency else self.paid_amount,
					"cost_center": self.cost_center
				}, bank_account_currency, item=self)
			)

	def make_write_off_gl_entry(self, gl_entries):
		# writeoff account includes petty difference in the invoice amount
		# and the amount that is paid
		if self.write_off_account and flt(self.write_off_amount):
			write_off_account_currency = get_account_currency(self.write_off_account)
			billing_party_type, billing_party = self.get_billing_party()

			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"party_type": billing_party_type,
					"party": billing_party,
					"against": self.write_off_account,
					"debit": self.base_write_off_amount,
					"debit_in_account_currency": self.base_write_off_amount \
						if self.party_account_currency==self.company_currency else self.write_off_amount,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"project": self.project
				}, self.party_account_currency, item=self)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": billing_party,
					"credit": flt(self.base_write_off_amount),
					"credit_in_account_currency": self.base_write_off_amount \
						if write_off_account_currency==self.company_currency else self.write_off_amount,
					"cost_center": self.cost_center or self.write_off_cost_center
				}, item=self)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		# if rounding adjustment in small and conversion rate is also small then
		# base_rounding_adjustment may become zero due to small precision
		# eg: rounding_adjustment = 0.01 and exchange rate = 0.05 and precision of base_rounding_adjustment is 2
		#	then base_rounding_adjustment becomes zero and error is thrown in GL Entry
		if self.rounding_adjustment and self.base_rounding_adjustment:
			round_off_account, round_off_cost_center = \
				get_round_off_account_and_cost_center(self.company)
			round_off_account_currency = get_account_currency(round_off_account)
			billing_party_type, billing_party = self.get_billing_party()

			gl_entries.append(
				self.get_gl_dict({
					"account": round_off_account,
					"against": billing_party,
					"debit_in_account_currency": (flt(self.base_rounding_adjustment,
						self.precision("base_rounding_adjustment")) if round_off_account_currency == self.company_currency
						else flt(self.rounding_adjustment, self.precision("rounding_adjustment"))),
					"debit": flt(self.base_rounding_adjustment, self.precision("base_rounding_adjustment")),
					"cost_center": self.cost_center or round_off_cost_center,
				}, round_off_account_currency, item=self))

	def on_cancel(self):
		super(PurchaseInvoice, self).on_cancel()

		self.check_on_hold_or_closed_status()

		self.update_status_updater_args()
		self.update_prevdoc_status()

		self.update_vehicle_booking_order()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.update_stock_ledger()

		if not self.is_return or not self.update_stock:
			self.update_receipts_valuation()

		self.make_gl_entries_on_cancel()
		self.update_project()
		frappe.db.set(self, 'status', 'Cancelled')

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_invoice_reference)

	def update_project(self):
		project_list = []
		for d in self.items:
			if d.project and d.project not in project_list:
				project = frappe.get_doc("Project", d.project)
				project.update_purchase_costing()
				project.db_update()
				project_list.append(d.project)

	def validate_supplier_invoice(self):
		if self.bill_date:
			if getdate(self.bill_date) > getdate(self.posting_date):
				frappe.throw(_("Supplier Invoice Date cannot be greater than Posting Date"))

		if self.bill_no:
			if cint(frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness")):
				fiscal_year = get_fiscal_year(self.posting_date, company=self.company, as_dict=True)

				pi = frappe.db.sql('''select name from `tabPurchase Invoice`
					where
						bill_no = %(bill_no)s
						and supplier = %(supplier)s
						and name != %(name)s
						and docstatus < 2
						and posting_date between %(year_start_date)s and %(year_end_date)s''', {
							"bill_no": self.bill_no,
							"supplier": self.supplier,
							"name": self.name,
							"year_start_date": fiscal_year.year_start_date,
							"year_end_date": fiscal_year.year_end_date
						})

				if pi:
					pi = pi[0][0]
					frappe.throw(_("Supplier Invoice No exists in Purchase Invoice {0}".format(pi)))

	def update_billing_status_in_pr(self, update_modified=True):
		updated_purchase_receipts = []
		for d in self.get("items"):
			if d.pr_detail:
				update_billed_amount_based_on_pr(d.pr_detail, update_modified)
				updated_purchase_receipts.append(d.purchase_receipt)
			elif d.po_detail:
				updated_purchase_receipts += update_billed_amount_based_on_po(d.po_detail, update_modified)

		for pr in set(updated_purchase_receipts):
			frappe.get_doc("Purchase Receipt", pr).update_billing_percentage(update_modified=update_modified)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.due_date = None

	def block_invoice(self, hold_comment=None, release_date=None):
		self.db_set('on_hold', 1)
		self.db_set('hold_comment', cstr(hold_comment))
		self.db_set('release_date', release_date)

	def unblock_invoice(self):
		self.db_set('on_hold', 0)
		self.db_set('release_date', None)

	def set_tax_withholding(self):
		if not self.apply_tds:
			return

		tax_withholding_details = get_party_tax_withholding_details(self, self.tax_withholding_category)

		if not tax_withholding_details:
			return

		accounts = []
		for d in self.taxes:
			if d.account_head == tax_withholding_details.get("account_head"):
				d.update(tax_withholding_details)
			accounts.append(d.account_head)

		if not accounts or tax_withholding_details.get("account_head") not in accounts:
			self.append("taxes", tax_withholding_details)

		to_remove = [d for d in self.taxes
			if not d.tax_amount and d.account_head == tax_withholding_details.get("account_head")]

		for d in to_remove:
			self.remove(d)

		# calculate totals again after applying TDS
		self.calculate_taxes_and_totals()

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status
		precision = self.precision("outstanding_amount")
		outstanding_amount = flt(self.outstanding_amount, precision)
		due_date = getdate(self.due_date)
		nowdate = getdate()

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if outstanding_amount > 0 and due_date < nowdate:
					self.status = "Overdue"
				elif outstanding_amount > 0 and due_date >= nowdate:
					self.status = "Unpaid"
				#Check if outstanding amount is 0 due to debit note issued against invoice
				elif outstanding_amount <= 0 and self.is_return == 0 and frappe.db.get_value('Purchase Invoice', {'is_return': 1, 'return_against': self.name, 'docstatus': 1}):
					self.status = "Debit Note Issued"
				elif self.is_return == 1:
					self.status = "Return"
				elif outstanding_amount<=0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified = update_modified)

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Purchase Invoices'),
	})
	return list_context

@erpnext.allow_regional
def make_regional_gl_entries(gl_entries, doc):
	return gl_entries

@frappe.whitelist()
def make_debit_note(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Purchase Invoice", source_name, target_doc)

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	doc = get_mapped_doc("Purchase Invoice", source_name, {
		"Purchase Invoice": {
			"doctype": "Stock Entry",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Purchase Invoice Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"stock_qty": "transfer_qty",
				"batch_no": "batch_no"
			},
		}
	}, target_doc)

	return doc

@frappe.whitelist()
def make_sales_order(customer, source_name, target_doc=None):
	from erpnext.controllers.accounts_controller import get_taxes_and_charges
	from frappe.model.utils import get_fetch_values

	def set_missing_values(source, target):
		target.customer = customer

		target.update(get_fetch_values("Sales Order", 'customer', target.customer))
		target.tax_id, target.tax_cnic, target.tax_strn = frappe.get_value("Customer", customer, ['tax_id', 'tax_cnic', 'tax_strn'])

		default_price_list = frappe.get_value("Customer", customer, "default_price_list")
		if default_price_list:
			target.selling_price_list = default_price_list

		sales_team = frappe.db.get_list("Sales Team", fields=['sales_person', 'allocated_percentage'], filters=[
			["parenttype", "=", "Customer"],
			["parent", "=", customer]
		])
		if sales_team:
			target.sales_team = []
			for sales_person in sales_team:
				d = target.append("sales_team")
				d.update(sales_person)

		for item in target.items:
			item.delivery_date = target.delivery_date

		target.run_method("set_missing_values")

		if target.taxes_and_charges:
			target.set("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", target.taxes_and_charges))
		else:
			default_tax = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=target.company)
			target.update(default_tax)

		target.run_method("calculate_taxes_and_totals")

		# workaround for get_item_details not setting the base_rate hence not calculating the correct gross profit
		for item in target.items:
			item.gross_profit = 0.0

	def update_item(source, target, source_parent):
		target.discount_percentage = 0
		target.price_list_rate = 0
		target.rate = 0

	doc = get_mapped_doc("Purchase Invoice", source_name, {
		"Purchase Invoice": {
			"doctype": "Sales Order",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_no_map": [
				"address_display",
				"shipping_address",
				"shipping_address_name",
				"contact_display",
				"contact_mobile",
				"contact_email",
				"contact_person",
				"taxes_and_charges",
				"taxes",
				"payment_terms_template",
				"payment_schedule",
				"apply_discount_on",
				"additional_discount_percentage",
				"discount_amount"
			],
		},
		"Purchase Invoice Item": {
			"doctype": "Sales Order Item",
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doc

@frappe.whitelist()
def change_release_date(name, release_date=None):
	if frappe.db.exists('Purchase Invoice', name):
		pi = frappe.get_doc('Purchase Invoice', name)
		pi.db_set('release_date', release_date)


@frappe.whitelist()
def unblock_invoice(name):
	if frappe.db.exists('Purchase Invoice', name):
		pi = frappe.get_doc('Purchase Invoice', name)
		pi.unblock_invoice()


@frappe.whitelist()
def block_invoice(name, release_date, hold_comment=None):
	if frappe.db.exists('Purchase Invoice', name):
		pi = frappe.get_doc('Purchase Invoice', name)
		pi.block_invoice(hold_comment, release_date)

@frappe.whitelist()
def make_inter_company_sales_invoice(source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction
	return make_inter_company_transaction("Purchase Invoice", source_name, target_doc)

def on_doctype_update():
	frappe.db.add_index("Purchase Invoice", ["supplier", "is_return", "return_against"])
