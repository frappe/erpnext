# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt

import erpnext
from erpnext.controllers.taxes_and_totals import init_landed_taxes_and_totals
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


class LandedCostVoucher(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.landed_cost_item.landed_cost_item import LandedCostItem
		from erpnext.stock.doctype.landed_cost_purchase_receipt.landed_cost_purchase_receipt import (
			LandedCostPurchaseReceipt,
		)
		from erpnext.stock.doctype.landed_cost_taxes_and_charges.landed_cost_taxes_and_charges import (
			LandedCostTaxesandCharges,
		)

		amended_from: DF.Link | None
		company: DF.Link
		distribute_charges_based_on: DF.Literal["Qty", "Amount", "Distribute Manually"]
		items: DF.Table[LandedCostItem]
		naming_series: DF.Literal["MAT-LCV-.YYYY.-"]
		posting_date: DF.Date
		purchase_receipts: DF.Table[LandedCostPurchaseReceipt]
		taxes: DF.Table[LandedCostTaxesandCharges]
		total_taxes_and_charges: DF.Currency
	# end: auto-generated types

	@frappe.whitelist()
	def get_items_from_purchase_receipts(self):
		self.set("items", [])
		for pr in self.get("purchase_receipts"):
			if pr.receipt_document_type and pr.receipt_document:
				pr_items = get_pr_items(pr)

				for d in pr_items:
					item = self.append("items")
					item.item_code = d.item_code
					item.description = d.description
					item.qty = d.qty
					item.rate = d.base_rate
					item.cost_center = d.cost_center or erpnext.get_default_cost_center(self.company)
					item.amount = d.base_amount
					item.receipt_document_type = pr.receipt_document_type
					item.receipt_document = pr.receipt_document
					item.purchase_receipt_item = d.name
					item.is_fixed_asset = d.is_fixed_asset

	def validate(self):
		self.check_mandatory()
		self.validate_receipt_documents()
		self.validate_line_items()
		init_landed_taxes_and_totals(self)
		self.set_total_taxes_and_charges()
		if not self.get("items"):
			self.get_items_from_purchase_receipts()

		self.set_applicable_charges_on_item()

	def validate_line_items(self):
		for d in self.get("items"):
			if (
				d.docstatus == 0
				and d.purchase_receipt_item
				and not frappe.db.exists(
					d.receipt_document_type + " Item",
					{"name": d.purchase_receipt_item, "parent": d.receipt_document},
				)
			):
				frappe.throw(
					_("Row {0}: {2} Item {1} does not exist in {2} {3}").format(
						d.idx,
						frappe.bold(d.purchase_receipt_item),
						d.receipt_document_type,
						frappe.bold(d.receipt_document),
					),
					title=_("Incorrect Reference Document (Purchase Receipt Item)"),
				)

	def check_mandatory(self):
		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Receipt Document"))

	def validate_receipt_documents(self):
		receipt_documents = []

		for d in self.get("purchase_receipts"):
			docstatus = frappe.db.get_value(d.receipt_document_type, d.receipt_document, "docstatus")
			if docstatus != 1:
				msg = f"Row {d.idx}: {d.receipt_document_type} {frappe.bold(d.receipt_document)} must be submitted"
				frappe.throw(_(msg), title=_("Invalid Document"))

			if d.receipt_document_type == "Purchase Invoice":
				update_stock = frappe.db.get_value(
					d.receipt_document_type, d.receipt_document, "update_stock"
				)
				if not update_stock:
					msg = _("Row {0}: Purchase Invoice {1} has no stock impact.").format(
						d.idx, frappe.bold(d.receipt_document)
					)
					msg += "<br>" + _(
						"Please create Landed Cost Vouchers against Invoices that have 'Update Stock' enabled."
					)
					frappe.throw(msg, title=_("Incorrect Invoice"))

			receipt_documents.append(d.receipt_document)

		for item in self.get("items"):
			if not item.receipt_document:
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))

			elif item.receipt_document not in receipt_documents:
				frappe.throw(
					_("Item Row {0}: {1} {2} does not exist in above '{1}' table").format(
						item.idx, item.receipt_document_type, item.receipt_document
					)
				)

			if not item.cost_center:
				frappe.throw(
					_("Row {0}: Cost center is required for an item {1}").format(item.idx, item.item_code)
				)

	def set_total_taxes_and_charges(self):
		self.total_taxes_and_charges = sum(flt(d.base_amount) for d in self.get("taxes"))

	def set_applicable_charges_on_item(self):
		if self.get("taxes") and self.distribute_charges_based_on != "Distribute Manually":
			total_item_cost = 0.0
			total_charges = 0.0
			item_count = 0
			based_on_field = frappe.scrub(self.distribute_charges_based_on)

			for item in self.get("items"):
				total_item_cost += item.get(based_on_field)

			for item in self.get("items"):
				if not total_item_cost and not item.get(based_on_field):
					frappe.throw(
						_(
							"It's not possible to distribute charges equally when total amount is zero, please set 'Distribute Charges Based On' as 'Quantity'"
						)
					)

				item.applicable_charges = flt(
					flt(item.get(based_on_field))
					* (flt(self.total_taxes_and_charges) / flt(total_item_cost)),
					item.precision("applicable_charges"),
				)
				total_charges += item.applicable_charges
				item_count += 1

			if total_charges != self.total_taxes_and_charges:
				diff = self.total_taxes_and_charges - total_charges
				self.get("items")[item_count - 1].applicable_charges += diff

	def validate_applicable_charges_for_item(self):
		if self.distribute_charges_based_on == "Distribute Manually" and len(self.taxes) > 1:
			frappe.throw(
				_(
					"Please keep one Applicable Charges, when 'Distribute Charges Based On' is 'Distribute Manually'. For more charges, please create another Landed Cost Voucher."
				)
			)

		based_on = self.distribute_charges_based_on.lower()

		if based_on != "distribute manually":
			total = sum(flt(d.get(based_on)) for d in self.get("items"))
		else:
			# consider for proportion while distributing manually
			total = sum(flt(d.get("applicable_charges")) for d in self.get("items"))

		if not total:
			frappe.throw(
				_(
					"Total {0} for all items is zero, may be you should change 'Distribute Charges Based On'"
				).format(based_on)
			)

		total_applicable_charges = sum(flt(d.applicable_charges) for d in self.get("items"))

		precision = get_field_precision(
			frappe.get_meta("Landed Cost Item").get_field("applicable_charges"),
			currency=frappe.get_cached_value("Company", self.company, "default_currency"),
		)

		diff = flt(self.total_taxes_and_charges) - flt(total_applicable_charges)
		diff = flt(diff, precision)

		if abs(diff) < (2.0 / (10**precision)):
			self.items[-1].applicable_charges += diff
		else:
			frappe.throw(
				_(
					"Total Applicable Charges in Purchase Receipt Items table must be same as Total Taxes and Charges"
				)
			)

	def on_submit(self):
		self.validate_applicable_charges_for_item()
		self.update_landed_cost()

	def on_cancel(self):
		self.update_landed_cost()

	def update_landed_cost(self):
		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)
			# check if there are {qty} assets created and linked to this receipt document
			if self.docstatus != 2:
				self.validate_asset_qty_and_status(d.receipt_document_type, doc)

			# set landed cost voucher amount in pr item
			doc.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			doc.update_valuation_rate(reset_outgoing_rate=False)

			# db_update will update and save landed_cost_voucher_amount and voucher_amount in PR
			for item in doc.get("items"):
				item.db_update()

			# asset rate will be updated while creating asset gl entries from PI or PY

			# update latest valuation rate in serial no
			self.update_rate_in_serial_no_for_non_asset_items(doc)

		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)
			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries_on_cancel()

			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.make_bundle_using_old_serial_batch_fields(via_landed_cost_voucher=True)
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			if d.receipt_document_type == "Purchase Receipt":
				doc.make_gl_entries(via_landed_cost_voucher=True)
			else:
				doc.make_gl_entries()
			doc.repost_future_sle_and_gle(via_landed_cost_voucher=True)

	def validate_asset_qty_and_status(self, receipt_document_type, receipt_document):
		for item in self.get("items"):
			if item.is_fixed_asset:
				receipt_document_type = (
					"purchase_invoice"
					if item.receipt_document_type == "Purchase Invoice"
					else "purchase_receipt"
				)
				docs = frappe.db.get_all(
					"Asset",
					filters={
						receipt_document_type: item.receipt_document,
						"item_code": item.item_code,
						"docstatus": ["!=", 2],
					},
					fields=["name", "docstatus"],
				)
				if not docs or len(docs) < item.qty:
					frappe.throw(
						_(
							"There are only {0} asset created or linked to {1}. Please create or link {2} Assets with respective document."
						).format(len(docs), item.receipt_document, item.qty)
					)
				if docs:
					for d in docs:
						if d.docstatus == 1:
							frappe.throw(
								_(
									"{0} <b>{1}</b> has submitted Assets. Remove Item <b>{2}</b> from table to continue."
								).format(item.receipt_document_type, item.receipt_document, item.item_code)
							)

	def update_rate_in_serial_no_for_non_asset_items(self, receipt_document):
		for item in receipt_document.get("items"):
			if not item.is_fixed_asset and item.serial_no:
				serial_nos = get_serial_nos(item.serial_no)
				if serial_nos:
					frappe.db.sql(
						"update `tabSerial No` set purchase_rate=%s where name in ({})".format(
							", ".join(["%s"] * len(serial_nos))
						),
						tuple([item.valuation_rate, *serial_nos]),
					)


def get_pr_items(purchase_receipt):
	item = frappe.qb.DocType("Item")
	pr_item = frappe.qb.DocType(purchase_receipt.receipt_document_type + " Item")
	return (
		frappe.qb.from_(pr_item)
		.inner_join(item)
		.on(item.name == pr_item.item_code)
		.select(
			pr_item.item_code,
			pr_item.description,
			pr_item.qty,
			pr_item.base_rate,
			pr_item.base_amount,
			pr_item.name,
			pr_item.cost_center,
			pr_item.is_fixed_asset,
			ConstantColumn(purchase_receipt.receipt_document_type).as_("receipt_document_type"),
			ConstantColumn(purchase_receipt.receipt_document).as_("receipt_document"),
		)
		.where(
			(pr_item.parent == purchase_receipt.receipt_document)
			& ((item.is_stock_item == 1) | (item.is_fixed_asset == 1))
		)
		.run(as_dict=True)
	)
