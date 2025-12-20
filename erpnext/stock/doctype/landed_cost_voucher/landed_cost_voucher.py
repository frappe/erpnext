# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import cint, flt

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
		from erpnext.stock.doctype.landed_cost_vendor_invoice.landed_cost_vendor_invoice import (
			LandedCostVendorInvoice,
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
		total_vendor_invoices_cost: DF.Currency
		vendor_invoices: DF.Table[LandedCostVendorInvoice]
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
					item.rate = d.get("base_rate") or d.get("rate")
					item.cost_center = d.cost_center or erpnext.get_default_cost_center(self.company)
					item.amount = d.base_amount
					item.receipt_document_type = pr.receipt_document_type
					item.receipt_document = pr.receipt_document
					item.is_fixed_asset = d.is_fixed_asset

					if pr.receipt_document_type == "Stock Entry":
						item.stock_entry_item = d.name
					else:
						item.purchase_receipt_item = d.name

	def validate(self):
		self.check_mandatory()
		self.validate_receipt_documents()
		self.validate_line_items()
		init_landed_taxes_and_totals(self)
		self.set_total_taxes_and_charges()
		if not self.get("items"):
			self.get_items_from_purchase_receipts()

		self.set_applicable_charges_on_item()
		self.set_total_vendor_invoices_cost()

	def set_total_vendor_invoices_cost(self):
		self.total_vendor_invoices_cost = 0.0
		for row in self.vendor_invoices:
			self.total_vendor_invoices_cost += flt(row.amount)

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

	@frappe.whitelist()
	def get_receipt_document_details(self, receipt_document_type, receipt_document):
		if receipt_document_type in [
			"Purchase Invoice",
			"Purchase Receipt",
			"Subcontracting Receipt",
		]:
			fields = ["supplier", "posting_date"]
			if receipt_document_type == "Subcontracting Receipt":
				fields.append("total as grand_total")
			else:
				fields.append("base_grand_total as grand_total")
		elif receipt_document_type == "Stock Entry":
			fields = ["total_incoming_value as grand_total"]

		return frappe.db.get_value(
			receipt_document_type,
			receipt_document,
			fields,
			as_dict=True,
		)

	def on_submit(self):
		self.validate_applicable_charges_for_item()
		self.update_landed_cost()
		self.update_claimed_landed_cost()

	def on_cancel(self):
		self.update_landed_cost()
		self.update_claimed_landed_cost()

	def update_claimed_landed_cost(self):
		for row in self.vendor_invoices:
			frappe.db.set_value(
				"Purchase Invoice",
				row.vendor_invoice,
				"claimed_landed_cost_amount",
				flt(row.amount, row.precision("amount")) if self.docstatus == 1 else 0.0,
			)

	def update_landed_cost(self):
		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)
			# check if there are {qty} assets created and linked to this receipt document
			if self.docstatus != 2:
				self.validate_asset_qty_and_status(d.receipt_document_type, doc)

			# set landed cost voucher amount in pr item
			doc.set_landed_cost_voucher_amount()

			if d.receipt_document_type == "Subcontracting Receipt":
				doc.calculate_items_qty_and_amount()
			else:
				# set valuation amount in pr item
				doc.update_valuation_rate(reset_outgoing_rate=False)

			# db_update will update and save landed_cost_voucher_amount and voucher_amount in PR
			for item in doc.get("items"):
				item.db_update()

			# asset rate will be updated while creating asset gl entries from PI or PY

			if d.receipt_document_type in ["Stock Entry", "Subcontracting Receipt"]:
				continue

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
					fields=["name", "docstatus", "asset_quantity"],
				)

				total_asset_qty = sum((cint(d.asset_quantity)) for d in docs)

				if not docs or total_asset_qty < item.qty:
					frappe.throw(
						_(
							"For item <b>{0}</b>, only <b>{1}</b> asset have been created or linked to <b>{2}</b>. "
							"Please create or link <b>{3}</b> more asset with the respective document."
						).format(
							item.item_code, total_asset_qty, item.receipt_document, item.qty - total_asset_qty
						)
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

	@frappe.whitelist()
	def get_vendor_invoice_amount(self, vendor_invoice):
		filters = frappe._dict(
			{
				"name": vendor_invoice,
				"company": self.company,
			}
		)

		query = get_vendor_invoice_query(filters)

		result = query.run(as_dict=True)
		amount = result[0].unclaimed_amount if result else 0.0

		return {
			"amount": amount,
		}


def get_pr_items(purchase_receipt):
	item = frappe.qb.DocType("Item")

	if purchase_receipt.receipt_document_type == "Stock Entry":
		pr_item = frappe.qb.DocType("Stock Entry Detail")
	else:
		pr_item = frappe.qb.DocType(purchase_receipt.receipt_document_type + " Item")

	query = (
		frappe.qb.from_(pr_item)
		.inner_join(item)
		.on(item.name == pr_item.item_code)
		.select(
			pr_item.item_code,
			pr_item.description,
			pr_item.qty,
			pr_item.name,
			pr_item.cost_center,
			ConstantColumn(purchase_receipt.receipt_document_type).as_("receipt_document_type"),
			ConstantColumn(purchase_receipt.receipt_document).as_("receipt_document"),
		)
		.where(
			(pr_item.parent == purchase_receipt.receipt_document)
			& ((item.is_stock_item == 1) | (item.is_fixed_asset == 1))
		)
		.orderby(pr_item.idx)
	)

	if purchase_receipt.receipt_document_type == "Subcontracting Receipt":
		query = query.select(
			pr_item.rate.as_("base_rate"),
			pr_item.amount.as_("base_amount"),
		)

	elif purchase_receipt.receipt_document_type == "Stock Entry":
		query = query.select(
			pr_item.basic_rate.as_("base_rate"),
			pr_item.basic_amount.as_("base_amount"),
		)

		query = query.where(pr_item.is_finished_item == 1)
	else:
		query = query.select(
			pr_item.base_rate,
			pr_item.base_amount,
			pr_item.is_fixed_asset,
		)

	return query.run(as_dict=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_vendor_invoices(doctype, txt, searchfield, start, page_len, filters):
	if not frappe.has_permission("Purchase Invoice", "read"):
		return []

	if txt and txt.lower().startswith(("select", "delete", "update")):
		frappe.throw(_("Invalid search query"), title=_("Invalid Query"))

	query = get_vendor_invoice_query(filters)

	if txt:
		query = query.where(doctype.name.like(f"%{txt}%"))

	if start:
		query = query.limit(page_len).offset(start)

	return query.run(as_list=True)


def get_vendor_invoice_query(filters):
	doctype = frappe.qb.DocType("Purchase Invoice")
	child_doctype = frappe.qb.DocType("Purchase Invoice Item")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(doctype)
		.inner_join(child_doctype)
		.on(child_doctype.parent == doctype.name)
		.inner_join(item)
		.on(item.name == child_doctype.item_code)
		.select(
			doctype.name,
			(doctype.base_total - doctype.claimed_landed_cost_amount).as_("unclaimed_amount"),
		)
		.where(
			(doctype.docstatus == 1)
			& (doctype.is_subcontracted == 0)
			& (doctype.is_return == 0)
			& (doctype.update_stock == 0)
			& (doctype.company == filters.get("company"))
			& (item.is_stock_item == 0)
		)
		.having(frappe.qb.Field("unclaimed_amount") > 0)
	)

	if filters.get("name"):
		query = query.where(doctype.name == filters.get("name"))

	return query
