# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _, scrub
from frappe.utils import flt, fmt_money
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries, delete_voucher_gl_entries
from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.party import get_party_account
from erpnext.controllers.stock_controller import update_gl_entries_for_reposted_stock_vouchers
from six import string_types
import json


class LandedCostVoucher(AccountsController):
	def __init__(self, *args, **kwargs):
		super(LandedCostVoucher, self).__init__(*args, **kwargs)
		self.status_map = [
			["Draft", None],
			["Submitted", "eval:self.docstatus==1"],
			["Paid", "eval:self.grand_total and self.outstanding_amount <= 0 and self.docstatus==1"],
			["Unpaid", "eval:self.outstanding_amount > 0 and getdate(self.due_date) >= getdate(nowdate()) and self.docstatus==1"],
			["Overdue", "eval:self.outstanding_amount > 0 and getdate(self.due_date) < getdate(nowdate()) and self.docstatus==1"],
			["Cancelled", "eval:self.docstatus==2"],
		]

	def validate(self):
		super(LandedCostVoucher, self).validate()
		self.check_mandatory()
		self.validate_credit_to_account()
		self.validate_purchase_receipts()
		self.set_purchase_receipt_details()
		self.clear_advances_table_if_not_payable()
		self.clear_unallocated_advances("Landed Cost Voucher Advance", "advances")
		self.calculate_taxes_and_totals()
		self.validate_manual_distribution_totals()
		self.set_status()

	def before_submit(self):
		self.validate_manual_distribution_totals(throw=True)
		self.validate_asset_qty_and_status()

	def on_submit(self):
		self.validate_applicable_charges_for_item()
		self.update_against_document_in_jv()
		self.update_landed_cost()
		self.make_gl_entries()

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
		unlink_ref_doc_from_payment_entries(self, validate_permission=True)
		self.update_landed_cost()
		self.make_gl_entries(cancel=True)

	@frappe.whitelist()
	def get_purchase_receipts_from_letter_of_credit(self):
		if self.party_type != "Letter of Credit" or not self.party:
			frappe.throw(_("Please select Letter of Credit first"))

		self.set("purchase_receipts", [])
		precs = frappe.get_all("Purchase Receipt", {
			"company": self.company, "docstatus": 1, "is_return": 0, "letter_of_credit": self.party
		})

		for d in precs:
			self.append("purchase_receipts", {"receipt_document_type": "Purchase Receipt", "receipt_document": d.name})

		pinvs = frappe.get_all("Purchase Invoice", {
			"company": self.company, "docstatus": 1, "is_return": 0, "update_stock": 1, "letter_of_credit": self.party
		})

		for d in pinvs:
			self.append("purchase_receipts", {"receipt_document_type": "Purchase Invoice", "receipt_document": d.name})

		self.set_purchase_receipt_details()

	def set_purchase_receipt_details(self):
		for row in self.get('purchase_receipts'):
			if row.receipt_document_type and row.receipt_document:
				details = frappe.db.get_value(row.receipt_document_type, row.receipt_document,
					['posting_date', 'supplier', 'base_grand_total'], as_dict=1)

				if details:
					row.posting_date = details.posting_date
					row.supplier = details.supplier
					row.grand_total = details.base_grand_total
			else:
				row.posting_date = None
				row.supplier = None
				row.grand_total = None

	@frappe.whitelist()
	def get_items_from_purchase_receipts(self):
		self.set("items", [])

		filter_conditions = []
		filter_values = frappe._dict()
		if self.get("item_group"):
			item_groups = [self.item_group]
			child_item_groups = frappe.get_all("Item Group", filters={"name": ["descendants of", self.item_group]})
			item_groups += [d.name for d in child_item_groups]

			filter_conditions.append("i.item_group in %(item_groups)s")
			filter_values['item_groups'] = item_groups

		if self.get("brand"):
			filter_conditions.append("i.brand = %(brand)s")
			filter_values['brand'] = self.brand

		conditions = " and " + " and ".join(filter_conditions) if filter_conditions else ""

		for pr in self.get("purchase_receipts"):
			if pr.receipt_document_type and pr.receipt_document:
				filter_values['receipt_document'] = pr.receipt_document

				pr_items = frappe.db.sql("""
					select
						pr_item.name, pr_item.item_code, pr_item.item_name,
						pr_item.qty, pr_item.uom, pr_item.total_weight,
						pr_item.base_rate, pr_item.base_amount, pr_item.amount,
						pr_item.purchase_order_item, pr_item.purchase_order,
						pr_item.cost_center, pr_item.is_fixed_asset
					from `tab{doctype} Item` pr_item
					inner join tabItem i on i.name = pr_item.item_code and i.is_stock_item = 1
					where pr_item.parent = %(receipt_document)s {conditions}
				""".format(doctype=pr.receipt_document_type, conditions=conditions), filter_values, as_dict=True)

				for d in pr_items:
					item = self.append("items")
					item.item_code = d.item_code
					item.item_name = d.item_name
					item.qty = d.qty
					item.uom = d.uom
					item.weight = d.total_weight
					item.rate = d.base_rate
					item.cost_center = d.cost_center
					item.amount = d.base_amount
					item.is_fixed_asset = d.is_fixed_asset
					item.purchase_order = d.purchase_order
					item.purchase_order_item = d.purchase_order_item
					if pr.receipt_document_type == "Purchase Receipt":
						item.purchase_receipt = pr.receipt_document
						item.purchase_receipt_item = d.name
					elif pr.receipt_document_type == "Purchase Invoice":
						item.purchase_invoice = pr.receipt_document
						item.purchase_invoice_item = d.name

	def check_mandatory(self):
		if self.party_type not in ["Supplier", "Letter of Credit"]:
			frappe.throw(_("Party Type must be either Supplier or Letter of Credit"))

		if self.is_payable:
			if not self.party:
				frappe.throw(_("Party is mandatory for Payable Landed Cost Voucher"))
			if not self.credit_to:
				frappe.throw(_("Credit To is mandatory Payable Landed Cost Voucher"))

		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Receipt Document"))

	def validate_purchase_receipts(self):
		receipt_documents = []

		for d in self.get("purchase_receipts"):
			fields = ["company", "docstatus", "is_return"]
			if d.receipt_document_type == "Purchase Invoice":
				fields.append("update_stock")

			details = frappe.db.get_value(d.receipt_document_type, d.receipt_document, fields, as_dict=1)

			if details is None:
				frappe.throw(_("Row #{0}: {1} {2} does not exist")
					.format(d.idx, d.receipt_document_type, d.receipt_document))

			if details.docstatus != 1:
				frappe.throw(_("Row #{0}: {1} {2} must be submitted")
					.format(d.idx, d.receipt_document_type, d.receipt_document))

			if details.is_return:
				frappe.throw(_("Row #{0}: {1} {2} must not be a return")
					.format(d.idx, d.receipt_document_type, d.receipt_document))

			if d.receipt_document_type == "Purchase Invoice" and not details.update_stock:
				frappe.throw(_("Row #{0}: {1} {2} does not update stock")
					.format(d.idx, d.receipt_document_type, d.receipt_document))

			if details.company != self.company:
				frappe.throw(_("Row #{0}: {1} {2} does not belong to Company {3}")
					.format(d.idx, d.receipt_document_type, d.receipt_document, self.company))

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

	def clear_advances_table_if_not_payable(self):
		if not self.is_payable:
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

	def validate_manual_distribution_totals(self, throw=False):
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
						fmt_money(item_totals[account_head], digits, self.currency)), raise_exception=throw)

	def validate_credit_to_account(self):
		if self.credit_to:
			account = frappe.db.get_value("Account", self.credit_to,
				["account_type", "report_type", "company"], as_dict=True)

			self.party_account_currency = get_account_currency(self.credit_to)

			if account.report_type != "Balance Sheet":
				frappe.throw(_("Credit To account must be a Balance Sheet account"))

			if account.account_type != "Payable":
				frappe.throw(_("Credit To account must be a Payable account"))

			if account.company != self.company:
				frappe.throw(_("Credit To Account does not belong to Company {0}").format(self.company))

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

		if self.is_payable:
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

		for item in self.items:
			item.item_tax_detail = {}
			item_manual_distribution = item.manual_distribution or {}
			if isinstance(item.manual_distribution, string_types):
				item_manual_distribution = json.loads(item_manual_distribution)

			for tax in self.taxes:
				item.item_tax_detail.setdefault(tax.name, 0)
				distribution_based_on = scrub(tax.distribution_criteria)
				if distribution_based_on == 'manual':
					distribution_amount = flt(item_manual_distribution.get(tax.account_head))
				else:
					if not totals[distribution_based_on]:
						frappe.throw(_("Cannot distribute by {0} because total {0} is 0").format(tax.distribution_criteria))

					ratio = flt(item.get(distribution_based_on)) / flt(totals.get(distribution_based_on))
					distribution_amount = flt(tax.amount) * ratio

				item.item_tax_detail[tax.name] += distribution_amount * flt(self.conversion_rate)

		accumulated_taxes = 0
		for item in self.get("items"):
			item_tax_total = sum(item.item_tax_detail.values())
			item.applicable_charges = item_tax_total
			accumulated_taxes += item_tax_total
			item.item_tax_detail = json.dumps(item.item_tax_detail, separators=(',', ':'))

		if accumulated_taxes != self.base_total_taxes_and_charges:
			diff = self.base_total_taxes_and_charges - accumulated_taxes
			self.items[-1].applicable_charges += diff

	def update_landed_cost(self):
		docs = []
		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)
			docs.append(doc)

			doc.set_landed_cost_voucher_amount()
			doc.update_valuation_rate("items")
			for item in doc.get("items"):
				item.db_update()

		excluded_vouchers = []
		for doc in docs:
			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			delete_voucher_gl_entries(doc.doctype, doc.name)

			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries(repost_future_gle=False)

			excluded_vouchers.append((doc.doctype, doc.name))

		if docs:
			update_gl_entries_for_reposted_stock_vouchers(excluded_vouchers)

	def make_gl_entries(self, cancel=False):
		if flt(self.grand_total) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		if not self.is_payable:
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
					"credit_in_account_currency": grand_total_in_company_currency
						if self.party_account_currency == self.company_currency else self.grand_total,
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
					"against": self.get('party_name') or self.party,
					"cost_center": tax.cost_center or self.get("cost_center"),
					"project": self.project,
					"remarks": remarks
				}, account_currency)
			)

		return gl_entry

	def validate_asset_qty_and_status(self):
		for item in self.get('items'):
			receipt_document = item.get('purchase_receipt') or item.get('purchase_invoice')
			if item.get('is_fixed_asset') and receipt_document:
				receipt_document_type = 'purchase_invoice' if item.purchase_invoice else 'purchase_receipt'
				assets = frappe.db.get_all('Asset', filters={
					receipt_document_type: item.receipt_document,
					'item_code': item.item_code
				}, fields=['name', 'docstatus'])

				if not assets or len(assets) != item.qty:
					frappe.throw(_('There are not enough asset created or linked to {0}. \
						Please create or link {1} Assets with respective document.').format(receipt_document, item.qty))

				for d in assets:
					if d.docstatus == 1:
						frappe.throw(_('{2} <b>{0}</b> has submitted Assets.\
							Remove Item <b>{1}</b> from table to continue.').format(
								receipt_document, item.item_code, item.receipt_document_type))


def get_purchase_landed_cost_gl_details(doc, item):
	filters = {
		"docstatus": 1,
		"applicable_charges": ["!=", 0]
	}
	if doc.doctype == "Purchase Receipt":
		filters["purchase_receipt"] = doc.name
		filters["purchase_receipt_item"] = item.name
	elif doc.doctype == "Purchase Invoice":
		filters["purchase_invoice"] = doc.name
		filters["purchase_invoice_item"] = item.name
	else:
		frappe.throw(_("Landed Cost Voucher not supported for DocType {0}").format(doc.doctype))

	landed_cost_items = frappe.get_all("Landed Cost Item", filters=filters, fields="name, parent, item_tax_detail")

	landed_cost_gl_details = []
	for lc_item in landed_cost_items:
		landed_cost_detail = json.loads(lc_item.item_tax_detail)
		for lc_tax_id, amount in landed_cost_detail.items():
			item_gl_details = frappe._dict()

			item_gl_details.landed_cost_voucher = lc_item.parent
			item_gl_details.landed_cost_voucher_item = lc_item.name
			item_gl_details.landed_cost_tax = lc_tax_id
			item_gl_details.amount = amount

			lc_tax_details = frappe.db.get_value("Landed Cost Taxes and Charges", lc_tax_id,
				('account_head', 'cost_center'), as_dict=1, cache=1)
			item_gl_details.update(lc_tax_details)

			if not item_gl_details.cost_center:
				item_gl_details.cost_center = frappe.db.get_value("Landed Cost Voucher", item_gl_details.landed_cost_voucher,
					"cost_center", cache=1)

			landed_cost_gl_details.append(item_gl_details)

	return landed_cost_gl_details


@frappe.whitelist()
def get_landed_cost_voucher(dt, dn):
	doc = frappe.get_doc(dt, dn)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = doc.company
	lcv.project = doc.get('project')
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


@frappe.whitelist()
def get_party_details(party_type, party, company):
	out = frappe._dict()

	out.currency = erpnext.get_company_currency(company)
	out.credit_to = get_party_account(party_type, party, company)
	if party_type == 'Supplier':
		out.currency = frappe.db.get_value(party_type, party, 'default_currency') or out.currency

	return out
