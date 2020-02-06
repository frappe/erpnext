# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _, scrub
from frappe.utils import flt, cstr, fmt_money
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.doctype.account.account import get_account_currency
from six import string_types
import json

class LandedCostVoucher(AccountsController):
	def __init__(self, *args, **kwargs):
		super(LandedCostVoucher, self).__init__(*args, **kwargs)

	def validate(self):
		super(LandedCostVoucher, self).validate()
		self.check_mandatory()
		self.validate_credit_to_account()
		self.validate_purchase_receipts()
		self.clear_advances_table_if_not_payable()
		self.clear_unallocated_advances("Landed Cost Voucher Advance", "advances")
		self.calculate_taxes_and_totals()
		self.set_status()

	def on_submit(self):
		self.calculate_taxes_and_totals()
		self.validate_applicable_charges_for_item()
		self.update_against_document_in_jv()
		self.update_landed_cost()
		self.make_gl_entries()

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
		unlink_ref_doc_from_payment_entries(self, validate_permission=True)
		self.update_landed_cost()
		self.make_gl_entries(cancel=True)

	def get_items_from_purchase_receipts(self):
		self.set("items", [])
		for pr in self.get("purchase_receipts"):
			if pr.receipt_document_type and pr.receipt_document:
				if pr.receipt_document_type == "Purchase Invoice":
					po_detail_field = "po_detail"
				else:
					po_detail_field = "purchase_order_item"

				pr_items = frappe.db.sql("""
					select
						pr_item.item_code, pr_item.item_name, pr_item.total_weight,
						pr_item.qty, pr_item.base_rate, pr_item.base_amount, pr_item.amount, pr_item.name,
						pr_item.{po_detail_field}, pr_item.purchase_order, pr_item.cost_center
					from `tab{doctype} Item` pr_item
					inner join tabItem i on i.name = pr_item.item_code and i.is_stock_item = 1
					where pr_item.parent = %s
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
		if self.party:
			if not self.credit_to:
				frappe.throw(_("Credit To is mandatory when Payable To is selected"))
			for d in self.taxes:
				if not d.account_head:
					frappe.throw(_("Row #{0}: Tax/Charge Account Head is mandatory when Payable To is selected").format(d.idx))

		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Receipt Document"))

		if self.party_type not in ["Supplier", "Letter of Credit"]:
			frappe.throw(_("Party Type must be Supplier or Letter of Credit"))

	def validate_purchase_receipts(self):
		receipt_documents = []

		for d in self.get("purchase_receipts"):
			docstatus = frappe.db.get_value(d.receipt_document_type, d.receipt_document, "docstatus")
			if docstatus is None:
				frappe.throw(_("Row #{0}: {1} {2} does not exist").format(d.idx, d.receipt_document_type, d.receipt_document))
			if docstatus != 1:
				frappe.throw(_("Row #{0}: {1} {2} must be submitted").format(d.idx, d.receipt_document_type, d.receipt_document))

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
						.format(item.idx, "Purchase Receipt", item.purchase_receipt, "Purchase Receipts"))
			elif item.purchase_invoice:
				if item.purchase_invoice not in receipt_documents:
					frappe.throw(_("Item Row {0}: {1} {2} does not exist in above '{3}' table")
						.format(item.idx, "Purchase Invoice", item.purchase_invoice, "Purchase Receipts"))

			if not item.cost_center:
				frappe.throw(_("Item Row {0}: Cost center is not set for item {1}")
					.format(item.idx, item.item_code))

	def clear_advances_table_if_not_payable(self):
		if not self.party:
			self.advances = []
			self.allocate_advances_automatically = 0

	def validate_applicable_charges_for_item(self):
		if not self.total_taxes_and_charges:
			frappe.throw(_("Total Taxes and Charges can not be 0"))

		total_applicable_charges = sum([flt(d.applicable_charges) for d in self.get("items")])

		precision = self.precision("applicable_charges", "items")
		diff = flt(self.base_total_taxes_and_charges) - flt(total_applicable_charges)

		if abs(diff) > (2.0 / (10**precision)):
			frappe.throw(_("Total Applicable Charges in Purchase Receipt Items table must be same as Total Taxes and Charges"))

	def validate_manual_distribution_totals(self):
		tax_account_totals = {}
		item_totals = {}

		for tax in self.taxes:
			if tax.distribution_criteria == "Manual" and tax.account_head:
				if tax.account_head not in tax_account_totals:
					tax_account_totals[tax.account_head] = 0.0
					item_totals[tax.account_head] = 0.0

				tax_account_totals[tax.account_head] += flt(tax.amount)

		for item in self.items:
			item_manual_distribution = item.manual_distribution or {}
			if isinstance(item_manual_distribution, string_types):
				item_manual_distribution = json.loads(item_manual_distribution)

			for account_head in item_manual_distribution.keys():
				if account_head in item_totals:
					item_totals[account_head] += flt(item_manual_distribution[account_head])

		for account_head in tax_account_totals.keys():
			digits = self.precision("total_taxes_and_charges")
			diff = flt(tax_account_totals[account_head]) - flt(item_totals[account_head])
			diff = flt(diff, digits)

			if abs(diff) > (2.0 / (10**digits)):
				frappe.msgprint(_("Tax amount for {} ({}) does not match the total in the manual distribution table ({})")
					.format(account_head,
						fmt_money(tax_account_totals[account_head], digits, self.currency),
						fmt_money(item_totals[account_head], digits, self.currency)))

	def validate_credit_to_account(self):
		if self.credit_to:
			account = frappe.db.get_value("Account", self.credit_to,
				["account_type", "report_type"], as_dict=True)

			self.party_account_currency = get_account_currency(self.credit_to)

			if account.report_type != "Balance Sheet":
				frappe.throw(_("Credit To account must be a Balance Sheet account"))

			if account.account_type != "Payable":
				frappe.throw(_("Credit To account must be a Payable account"))

	def calculate_taxes_and_totals(self):
		item_total_fields = ['qty', 'amount', 'weight']
		for f in item_total_fields:
			self.set('total_' + f, flt(sum([flt(d.get(f)) for d in self.get("items")]), self.precision('total_' + f)))

		self.total_taxes_and_charges = 0
		for d in self.taxes:
			d.amount = flt(d.amount, d.precision("amount"))
			d.base_amount = flt(d.amount * self.conversion_rate, d.precision("base_amount"))
			self.total_taxes_and_charges += d.amount
		self.total_taxes_and_charges = flt(self.total_taxes_and_charges, self.precision("total_taxes_and_charges"))
		self.base_total_taxes_and_charges = flt(self.total_taxes_and_charges * self.conversion_rate, self.precision("base_total_taxes_and_charges"))

		total_allocated = sum([flt(d.allocated_amount, d.precision("allocated_amount")) for d in self.get("advances")])

		if self.party:
			self.grand_total = flt(self.total_taxes_and_charges, self.precision("grand_total"))
			self.base_grand_total = flt(self.grand_total * self.conversion_rate, self.precision("base_grand_total"))
			self.total_advance = flt(total_allocated, self.precision("total_advance"))
		else:
			self.grand_total = 0
			self.base_grand_total = 0
			self.total_advance = 0

		grand_total = self.grand_total if self.party_account_currency == self.currency else self.base_grand_total
		if grand_total >= 0 and self.total_advance > grand_total:
			frappe.throw(_("Advance amount cannot be greater than {0}").format(grand_total))

		self.outstanding_amount = flt(grand_total - self.total_advance, self.precision("outstanding_amount"))

		self.distribute_applicable_charges_for_item()

	def distribute_applicable_charges_for_item(self):
		totals = {}
		item_total_fields = ['qty', 'amount', 'weight']
		for f in item_total_fields:
			totals[f] = flt(sum([flt(d.get(f)) for d in self.items]))

		charges_map = []
		manual_account_heads = set()
		for tax in self.taxes:
			based_on = scrub(tax.distribution_criteria)

			if based_on == "manual":
				manual_account_heads.add(cstr(tax.account_head))
			else:
				if not totals[based_on]:
					frappe.throw(_("Cannot distribute by {0} because total {0} is 0").format(tax.distribution_criteria))

				charges_map.append([])
				for item in self.items:
					charges_map[-1].append(flt(tax.base_amount) * flt(item.get(based_on)) / flt(totals.get(based_on)))

		if manual_account_heads:
			self.validate_manual_distribution_totals()

		accumulated_taxes = 0.0
		for item_idx, item in enumerate(self.items):
			item_total_tax = 0.0
			for row_charge in charges_map:
				item_total_tax += row_charge[item_idx]

			item_manual_distribution = item.manual_distribution or {}
			if isinstance(item.manual_distribution, string_types):
				item_manual_distribution = json.loads(item_manual_distribution)

			for account_head in item_manual_distribution.keys():
				if account_head in manual_account_heads:
					item_total_tax += flt(item_manual_distribution[account_head]) * flt(self.conversion_rate)

			item.applicable_charges = item_total_tax
			accumulated_taxes += item.applicable_charges

		if accumulated_taxes != self.base_total_taxes_and_charges:
			diff = self.base_total_taxes_and_charges - accumulated_taxes
			self.items[-1].applicable_charges += diff

	def update_landed_cost(self):
		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)
			
			# check if there are {qty} assets created and linked to this receipt document
			self.validate_asset_qty_and_status(d.receipt_document_type, doc)

			# set landed cost voucher amount in pr item
			doc.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			doc.update_valuation_rate("items")

			# db_update will update and save landed_cost_voucher_amount and voucher_amount in PR
			for item in doc.get("items"):
				item.db_update()

			# asset rate will be updated while creating asset gl entries from PI or PY

			# update latest valuation rate in serial no
			update_rate_in_serial_no_for_non_asset_items(doc)

			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries_on_cancel(repost_future_gle=False)

			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries()

	def make_gl_entries(self, cancel=False):
		if flt(self.grand_total) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		if not self.party:
			return []

		gl_entry = []

		# payable entry
		if self.grand_total:
			grand_total_in_company_currency = flt(self.grand_total * self.conversion_rate,
				self.precision("grand_total"))
			gl_entry.append(
				self.get_gl_dict({
					"account": self.credit_to,
					"credit": grand_total_in_company_currency,
					"credit_in_account_currency": grand_total_in_company_currency \
						if self.party_account_currency==self.company_currency else self.grand_total,
					"against": ", ".join(set([d.account_head for d in self.taxes])),
					"party_type": self.party_type,
					"party": self.party,
					"remarks": "Note: {0}".format(self.remarks) if self.remarks else ""
				}, self.party_account_currency)
			)

		# expense entries
		for tax in self.taxes:
			r = []
			if tax.remarks:
				r.append(tax.remarks)
			if self.remarks:
				r.append("Note: {0}".format(self.remarks))
			remarks = "\n".join(r)

			account_currency = get_account_currency(tax.account_head)

			gl_entry.append(
				self.get_gl_dict({
					"account": tax.account_head,
					"debit": tax.base_amount,
					"debit_in_account_currency": tax.base_amount \
						if account_currency == self.company_currency else tax.amount,
					"against": self.party,
					"cost_center": tax.cost_center,
					"project": self.project,
					"remarks": remarks
				}, account_currency)
			)

		return gl_entry

	def validate_asset_qty_and_status(self, receipt_document_type, receipt_document):
		for item in self.get('items'):
			if item.is_fixed_asset:
				receipt_document_type = 'purchase_invoice' if item.receipt_document_type == 'Purchase Invoice' \
						else 'purchase_receipt'
				docs = frappe.db.get_all('Asset', filters={ receipt_document_type: item.receipt_document,
					'item_code': item.item_code }, fields=['name', 'docstatus'])
				if not docs or len(docs) != item.qty:
					frappe.throw(_('There are not enough asset created or linked to {0}. \
						Please create or link {1} Assets with respective document.').format(item.receipt_document, item.qty))
				if docs:
					for d in docs:
						if d.docstatus == 1:
							frappe.throw(_('{2} <b>{0}</b> has submitted Assets.\
								Remove Item <b>{1}</b> from table to continue.').format(
									item.receipt_document, item.item_code, item.receipt_document_type))

def update_rate_in_serial_no_for_non_asset_items(receipt_document):
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
	lcv.project = doc.set_project
	lcv.append("purchase_receipts", {
		"receipt_document_type": dt,
		"receipt_document": dn,
		"supplier": doc.supplier,
		"posting_date": doc.posting_date,
		"grand_total": doc.base_grand_total,
	})

	if doc.get("letter_of_credit"):
		lcv.party_type = "Letter of Credit"
		lcv.party = doc.get("letter_of_credit")

	lcv.get_items_from_purchase_receipts()
	return lcv
