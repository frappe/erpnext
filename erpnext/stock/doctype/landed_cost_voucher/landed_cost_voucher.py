# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, cint
from frappe.model.meta import get_field_precision
from frappe.model.document import Document
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_billed_amount_based_on_pr
from frappe.utils.csvutils import getlink

class LandedCostVoucher(AccountsController):
	def __init__(self, *args, **kwargs):
		super(LandedCostVoucher, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'source_dt': 'Landed Cost Item',
			'target_dt': 'Purchase Order Item',
			'join_field': 'purchase_order_item',
			'target_field': 'billed_amt',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_billed',
			'target_ref_field': 'amount',
			'source_field': 'billable_amt',
			'percent_join_field': 'purchase_order',
			'overflow_type': 'billing'
		}]

	def get_items_from_purchase_receipts(self):
		self.set("items", [])
		for pr in self.get("purchase_receipts"):
			if pr.receipt_document_type and pr.receipt_document:
				if pr.receipt_document_type == "Purchase Invoice":
					po_detail_field = "po_detail"
				else:
					po_detail_field = "purchase_order_item"

				pr_items = frappe.db.sql("""select pr_item.item_code, pr_item.description, pr_item.total_weight,
					pr_item.qty, pr_item.base_rate, pr_item.base_amount, pr_item.amount, pr_item.name,
					pr_item.{po_detail_field}, pr_item.purchase_order, pr_item.cost_center
					from `tab{doctype} Item` pr_item where parent = %s
					and exists(select name from tabItem where name = pr_item.item_code and is_stock_item = 1)
					""".format(doctype=pr.receipt_document_type, po_detail_field=po_detail_field),
					pr.receipt_document, as_dict=True)

				for d in pr_items:
					item = self.append("items")
					item.item_code = d.item_code
					item.description = d.description
					item.qty = d.qty
					item.weight = d.total_weight
					item.rate = d.base_rate
					item.cost_center = d.cost_center or erpnext.get_default_cost_center(self.company)
					item.amount = d.base_amount
					item.billable_amt = d.amount
					item.purchase_order = d.purchase_order
					item.purchase_order_item = d.get(po_detail_field)
					if pr.receipt_document_type == "Purchase Receipt":
						item.purchase_receipt = pr.receipt_document
						item.purchase_receipt_item = d.name
					elif pr.receipt_document_type == "Purchase Invoice":
						item.purchase_invoice = pr.receipt_document
						item.purchase_invoice_item = d.name

	def validate(self):
		super(LandedCostVoucher, self).validate()

		self.check_mandatory()
		self.validate_purchase_receipts()
		self.set_values_for_import_bill()
		self.set_total_taxes_and_charges()
		self.set_status()
		self.set_title()

	def before_submit(self):
		self.validate_applicable_charges_for_item()

	def set_values_for_import_bill(self):
		if cint(self.is_import_bill):
			self.supplier = None
			self.due_date = None

	def check_mandatory(self):
		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Receipt Document"))
		if not cint(self.is_import_bill) and not self.supplier:
			frappe.throw(_("Please select Tax Supplier"))

	def validate_purchase_receipts(self):
		receipt_documents = []

		for d in self.get("purchase_receipts"):
			if cint(self.is_import_bill) and d.receipt_document_type != "Purchase Receipt":
				frappe.throw(_("Receipt document must be a Purchase Receipt"))

			if frappe.db.get_value(d.receipt_document_type, d.receipt_document, "docstatus") != 1:
				frappe.throw(_("Receipt document must be submitted"))
			else:
				receipt_documents.append(d.receipt_document)

		for item in self.get("items"):
			if (not item.purchase_receipt and not item.purchase_invoice) \
					or (item.purchase_receipt and item.purchase_invoice) \
					or (not item.purchase_receipt_item and not item.purchase_invoice_item) \
					or (item.purchase_receipt_item and item.purchase_invoice_item) \
					or (not item.billable_amt and cint(item.is_import_bill)):
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))

			if item.purchase_receipt:
				if item.purchase_receipt not in receipt_documents:
					frappe.throw(_("Item Row {idx}: {doctype} {docname} does not exist in above '{doctype}' table")
						.format(idx=item.idx, doctype="Purchase Receipt", docname=item.purchase_receipt))
			elif item.purchase_invoice:
				if item.purchase_invoice not in receipt_documents:
					frappe.throw(_("Item Row {idx}: {doctype} {docname} does not exist in above '{doctype}' table")
						.format(idx=item.idx, doctype="Purchase Invoice", docname=item.purchase_invoice))

			if not item.cost_center:
				frappe.throw(_("Item Row {0}: Cost center is not set for item {1}")
					.format(item.idx, item.item_code))

	def validate_applicable_charges_for_item(self):
		total_applicable_charges = sum([flt(d.applicable_charges) for d in self.get("items")])

		precision = get_field_precision(frappe.get_meta("Landed Cost Item").get_field("applicable_charges"),
			currency=frappe.get_cached_value('Company',  self.company,  "default_currency"))

		diff = flt(self.total_taxes_and_charges) - flt(total_applicable_charges)
		diff = flt(diff, precision)

		if abs(diff) < (2.0 / (10**precision)):
			self.items[-1].applicable_charges += diff
		else:
			frappe.throw(_("Total Applicable Charges in Purchase Receipt Items table must be same as Total Taxes and Charges"))

	def validate_credit_to_account(self):
		account = frappe.db.get_value("Account", self.credit_to,
			["account_type", "report_type"], as_dict=True)

		if account.report_type != "Balance Sheet":
			frappe.throw(_("Credit To account must be a Balance Sheet account"))

		if self.supplier and account.account_type != "Payable":
			frappe.throw(_("Credit To account must be a Payable account"))

	def set_total_taxes_and_charges(self):
		self.total_taxes_and_charges = sum([flt(d.amount) for d in self.get("taxes")])
		self.outstanding_amount = 0.0 if cint(self.is_import_bill) else self.total_taxes_and_charges

	def set_title(self):
		if cint(self.is_import_bill):
			self.title = self.credit_to
		else:
			self.title = self.supplier_name

	def on_submit(self):
		if cint(self.is_import_bill):
			self.update_billing_status_in_pr()
			self.update_prevdoc_status()
		self.update_landed_cost()
		self.make_gl_entries()

	def on_cancel(self):
		if cint(self.is_import_bill):
			self.update_billing_status_in_pr()
			self.update_prevdoc_status()
		self.update_landed_cost()
		if self.credit_to:
			self.make_gl_entries(cancel=True)

	def update_billing_status_in_pr(self, update_modified=True):
		update_billed_amount_based_on_pr(self, "purchase_receipt_item", None, update_modified)

	def update_landed_cost(self):
		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)

			# set landed cost voucher amount in pr item
			doc.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			doc.update_valuation_rate("items")

			# db_update will update and save landed_cost_voucher_amount and voucher_amount in PR
			for item in doc.get("items"):
				item.db_update()

			# update latest valuation rate in serial no
			self.update_rate_in_serial_no(doc)

			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries_on_cancel(repost_future_gle=False)

			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.update_stock_ledger(via_landed_cost_voucher=True)
			doc.make_gl_entries()

	def update_rate_in_serial_no(self, receipt_document):
		for item in receipt_document.get("items"):
			if item.serial_no:
				serial_nos = get_serial_nos(item.serial_no)
				if serial_nos:
					frappe.db.sql("update `tabSerial No` set purchase_rate=%s where name in ({0})"
						.format(", ".join(["%s"]*len(serial_nos))), tuple([item.valuation_rate] + serial_nos))

	def make_gl_entries(self, cancel=False):
		if flt(self.total_taxes_and_charges) > 0:
			update_outstanding = "No" if cint(self.is_import_bill) else "Yes"
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel, update_outstanding=update_outstanding)

	def get_gl_entries(self):
		gl_entry = []
		self.validate_credit_to_account()

		payable_amount = flt(self.total_taxes_and_charges)

		# payable entry
		if payable_amount:
			gl_entry.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"credit": payable_amount,
					"credit_in_account_currency": payable_amount,
					"against": ",".join([d.account_head for d in self.taxes]),
					"party_type": "Supplier",
					"party": self.supplier,
					"against_voucher_type": self.doctype,
					"against_voucher": self.name
				})
			)

		# expense entries
		for tax in self.taxes:
			gl_entry.append(
				self.get_gl_dict({
					"account": tax.account_head,
					"debit": tax.amount,
					"debit_in_account_currency": tax.amount,
					"against": self.supplier,
					"cost_center": tax.cost_center
				})
			)

		return gl_entry

@frappe.whitelist()
def get_landed_cost_voucher(dt, dn):
	doc = frappe.get_doc(dt, dn)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = doc.company
	lcv.append("purchase_receipts", {
		"receipt_document_type": dt,
		"receipt_document": dn,
		"supplier": doc.supplier,
		"credit_to": doc.credit_to,
		"grand_total": doc.base_grand_total
	})

	lcv.get_items_from_purchase_receipts()
	return lcv
