# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, cint
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_balance_on

class LandedCostVoucher(AccountsController):
	def __init__(self, *args, **kwargs):
		super(LandedCostVoucher, self).__init__(*args, **kwargs)

	def validate(self):
		super(LandedCostVoucher, self).validate()
		self.check_mandatory()
		self.validate_credit_to_account()
		self.validate_purchase_receipts()
		self.clear_unallocated_advances("Landed Cost Voucher Advance", "advances")
		self.calculates_taxes_and_totals()
		self.set_status()

	def before_submit(self):
		self.validate_applicable_charges_for_item()

	def on_submit(self):
		self.update_against_document_in_jv()
		self.update_landed_cost()
		self.make_gl_entries()

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
		if frappe.db.get_single_value('Accounts Settings', 'unlink_payment_on_cancellation_of_invoice'):
			unlink_ref_doc_from_payment_entries(self)
		self.update_landed_cost()
		self.make_gl_entries(cancel=True)

	def get_referenced_taxes(self):
		if self.credit_to and self.party:
			self.set("taxes", [])
			tax_amounts = frappe.db.sql(
				"""select je.reference_account as account_head, sum(ge.debit - ge.credit) as amount
				from `tabGL Entry` as ge, `tabJournal Entry` as je
				where
					ge.account=%s and ge.party_type=%s and ge.party=%s
					and ge.voucher_type='Journal Entry' and ge.voucher_no=je.name
					and je.reference_account is not null and je.reference_account != ''
				group by je.reference_account""", [self.credit_to, self.party_type, self.party], as_dict=True)

			balance = get_balance_on(party_type=self.party_type, party=self.party, company=self.company)

			total_tax_amounts = sum(tax.amount for tax in tax_amounts)
			diff = flt(balance - total_tax_amounts, self.precision("amount", "taxes"))

			if diff:
				tax_amounts.append({
					'remarks': _("Remaining balance"),
					'amount': diff,
					'account_head': None})

			return tax_amounts

	def get_items_from_purchase_receipts(self):
		self.set("items", [])
		for pr in self.get("purchase_receipts"):
			if pr.receipt_document_type and pr.receipt_document:
				if pr.receipt_document_type == "Purchase Invoice":
					po_detail_field = "po_detail"
				else:
					po_detail_field = "purchase_order_item"

				pr_items = frappe.db.sql("""select pr_item.item_code, pr_item.item_name, pr_item.total_weight,
					pr_item.qty, pr_item.base_rate, pr_item.base_amount, pr_item.amount, pr_item.name,
					pr_item.{po_detail_field}, pr_item.purchase_order, pr_item.cost_center
					from `tab{doctype} Item` pr_item where parent = %s
					and exists(select name from tabItem where name = pr_item.item_code and is_stock_item = 1)
					""".format(doctype=pr.receipt_document_type, po_detail_field=po_detail_field),
					pr.receipt_document, as_dict=True)

				for d in pr_items:
					item = self.append("items")
					item.item_code = d.item_code
					item.item_name = d.item_name
					item.qty = d.qty
					item.weight = d.total_weight
					item.rate = d.base_rate
					item.cost_center = d.cost_center or erpnext.get_default_cost_center(self.company)
					item.amount = d.base_amount
					item.purchase_order = d.purchase_order
					item.purchase_order_item = d.get(po_detail_field)
					if pr.receipt_document_type == "Purchase Receipt":
						item.purchase_receipt = pr.receipt_document
						item.purchase_receipt_item = d.name
					elif pr.receipt_document_type == "Purchase Invoice":
						item.purchase_invoice = pr.receipt_document
						item.purchase_invoice_item = d.name

	def check_mandatory(self):
		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Receipt Document"))

		if self.party_type not in ["Supplier", "Letter of Credit"]:
			frappe.throw(_("Party Type must be Supplier or Letter of Credit"))

	def validate_purchase_receipts(self):
		receipt_documents = []

		for d in self.get("purchase_receipts"):
			docstatus = frappe.db.get_value(d.receipt_document_type, d.receipt_document, "docstatus")
			if docstatus != 1:
				frappe.throw(_("Receipt document must be submitted"))

			receipt_documents.append(d.receipt_document)

		for item in self.get("items"):
			if (not item.purchase_receipt and not item.purchase_invoice) \
					or (item.purchase_receipt and item.purchase_invoice) \
					or (not item.purchase_receipt_item and not item.purchase_invoice_item) \
					or (item.purchase_receipt_item and item.purchase_invoice_item):
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))

			if item.purchase_receipt:
				if item.purchase_receipt not in receipt_documents:
					frappe.throw(_("Item Row {0}: {1} {2} does not exist in above '{3}' table")
						.format(item.idx, "Purchase Receipt", item.purchase_receipt), "Purchase Receipts")
			elif item.purchase_invoice:
				if item.purchase_invoice not in receipt_documents:
					frappe.throw(_("Item Row {0}: {1} {2} does not exist in above '{3}' table")
						.format(item.idx, "Purchase Invoice", item.purchase_invoice, "Purchase Receipts"))

			if not item.cost_center:
				frappe.throw(_("Item Row {0}: Cost center is not set for item {1}")
					.format(item.idx, item.item_code))

	def validate_applicable_charges_for_item(self):
		total_applicable_charges = sum([flt(d.applicable_charges) for d in self.get("items")])

		precision = self.precision("applicable_charges", "items")
		diff = flt(self.grand_total) - flt(total_applicable_charges)
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

		if account.account_type != "Payable":
			frappe.throw(_("Credit To account must be a Payable account"))

	def calculates_taxes_and_totals(self):
		total_taxes = sum([flt(d.amount, d.precision("amount")) for d in self.get("taxes")])
		self.grand_total = flt(total_taxes, self.precision("grand_total"))

		total_allocated = sum([flt(d.allocated_amount, d.precision("allocated_amount")) for d in self.get("advances")])
		self.total_advance = flt(total_allocated, self.precision("total_advance"))

		if self.grand_total > 0 and self.total_advance > self.grand_total:
			frappe.throw(_("Advance amount cannot be greater than {0}").format(self.grand_total))

		self.outstanding_amount = self.grand_total - self.total_advance

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
			update_rate_in_serial_no(doc)

			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries_on_cancel(repost_future_gle=False)

			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.update_stock_ledger(via_landed_cost_voucher=True)
			doc.make_gl_entries()

	def make_gl_entries(self, cancel=False):
		if flt(self.grand_total) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []

		payable_amount = flt(self.grand_total)

		# payable entry
		if payable_amount:
			gl_entry.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"credit": payable_amount,
					"credit_in_account_currency": payable_amount,
					"against": ", ".join(set([d.account_head for d in self.taxes])),
					"party_type": self.party_type,
					"party": self.party,
					"remarks": "Note: {0}".format(self.remarks) if self.remarks else ""
				})
			)

		# expense entries
		for tax in self.taxes:
			r = []
			if tax.remarks:
				r.append(tax.remarks)
			if self.remarks:
				r.append("Note: {0}".format(self.remarks))
			remarks = "\n".join(r)

			gl_entry.append(
				self.get_gl_dict({
					"account": tax.account_head,
					"debit": tax.amount,
					"debit_in_account_currency": tax.amount,
					"against": self.party,
					"cost_center": tax.cost_center,
					"remarks": remarks
				})
			)

		return gl_entry

def update_rate_in_serial_no(receipt_document):
	for item in receipt_document.get("items"):
		if item.serial_no:
			serial_nos = get_serial_nos(item.serial_no)
			if serial_nos:
				frappe.db.sql("update `tabSerial No` set purchase_rate=%s where name in ({0})"
					.format(", ".join(["%s"]*len(serial_nos))), tuple([item.valuation_rate] + serial_nos))

@frappe.whitelist()
def get_landed_cost_voucher(dt, dn):
	doc = frappe.get_doc(dt, dn)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = doc.company
	lcv.append("purchase_receipts", {
		"receipt_document_type": dt,
		"receipt_document": dn,
		"supplier": doc.supplier,
		"posting_date": doc.posting_date,
		"grand_total": doc.base_grand_total
	})

	if doc.get("letter_of_credit"):
		lcv.party_type = "Letter of Credit"
		lcv.party = doc.get("letter_of_credit")

	lcv.get_items_from_purchase_receipts()
	return lcv
