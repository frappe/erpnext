# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import sys

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Count, Sum
from frappe.utils import getdate


class VariablePathNotFound(frappe.ValidationError):
	pass


DateDiff = CustomFunction("DATEDIFF", ["date1", "date2"])


class SupplierScorecardVariable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		is_custom: DF.Check
		param_name: DF.Data
		path: DF.Data
		variable_label: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_path_exists()

	def validate_path_exists(self):
		if "." in self.path:
			try:
				from erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period import (
					import_string_path,
				)

				import_string_path(self.path)
			except AttributeError:
				frappe.throw(_("Could not find path for " + self.path), VariablePathNotFound)

		else:
			if not hasattr(sys.modules[__name__], self.path):
				frappe.throw(_("Could not find path for " + self.path), VariablePathNotFound)


def get_total_workdays(scorecard):
	"""Gets the number of days in this period"""
	delta = getdate(scorecard.end_date) - getdate(scorecard.start_date)
	return delta.days


def _get_query_value(query):
	result = query.run(as_list=True)
	if result and result[0] and result[0][0] is not None:
		return result[0][0]
	return 0


def get_item_workdays(scorecard):
	"""Gets the number of days in this period"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")

	return _get_query_value(
		frappe.qb.from_(po_item)
		.join(po)
		.on(po_item.parent == po.name)
		.select(Sum(DateDiff(scorecard.end_date, po_item.schedule_date) * po_item.qty))
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.received_qty < po_item.qty)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
		)
	)


def get_total_cost_of_shipments(scorecard):
	"""Gets the total cost of all shipments in the period (based on Purchase Orders)"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")

	return _get_query_value(
		frappe.qb.from_(po_item)
		.join(po)
		.on(po_item.parent == po.name)
		.select(Sum(po_item.base_amount))
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
			& (po_item.docstatus == 1)
		)
	)


def get_cost_of_delayed_shipments(scorecard):
	"""Gets the total cost of all delayed shipments in the period (based on Purchase Receipts - POs)"""
	return get_total_cost_of_shipments(scorecard) - get_cost_of_on_time_shipments(scorecard)


def get_cost_of_on_time_shipments(scorecard):
	"""Gets the total cost of all on_time shipments in the period (based on Purchase Receipts)"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(po_item)
		.join(pr_item)
		.on(pr_item.purchase_order_item == po_item.name)
		.join(po)
		.on(po_item.parent == po.name)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.base_amount))
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
			& (po_item.schedule_date >= pr.posting_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_days_late(scorecard):
	"""Gets the number of item days late in the period (based on Purchase Receipts vs POs)"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	total_delivered_late_days = _get_query_value(
		frappe.qb.from_(po_item)
		.join(pr_item)
		.on(pr_item.purchase_order_item == po_item.name)
		.join(po)
		.on(po_item.parent == po.name)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(DateDiff(pr.posting_date, po_item.schedule_date) * pr_item.qty))
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
			& (po_item.schedule_date < pr.posting_date)
			& (pr_item.docstatus == 1)
		)
	)

	total_missed_late_days = _get_query_value(
		frappe.qb.from_(po_item)
		.join(po)
		.on(po_item.parent == po.name)
		.select(
			Sum(DateDiff(scorecard.end_date, po_item.schedule_date) * (po_item.qty - po_item.received_qty))
		)
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.received_qty < po_item.qty)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
		)
	)

	return total_missed_late_days + total_delivered_late_days


def get_on_time_shipments(scorecard):
	"""Gets the number of late shipments (counting each item) in the period (based on Purchase Receipts vs POs)"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(po_item)
		.join(pr_item)
		.on(pr_item.purchase_order_item == po_item.name)
		.join(po)
		.on(po_item.parent == po.name)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Count(pr_item.qty))
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
			& (po_item.schedule_date <= pr.posting_date)
			& (po_item.qty == pr_item.qty)
			& (pr_item.docstatus == 1)
		)
	)


def get_late_shipments(scorecard):
	"""Gets the number of late shipments (counting each item) in the period (based on Purchase Receipts vs POs)"""
	return get_total_shipments(scorecard) - get_on_time_shipments(scorecard)


def get_total_received(scorecard):
	"""Gets the total number of received shipments in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Count(pr_item.base_amount))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_received_amount(scorecard):
	"""Gets the total amount (in company currency) received in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.received_qty * pr_item.base_rate))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_received_items(scorecard):
	"""Gets the total number of received shipments in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.received_qty))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_rejected_amount(scorecard):
	"""Gets the total amount (in company currency) rejected in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.rejected_qty * pr_item.base_rate))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_rejected_items(scorecard):
	"""Gets the total number of rejected items in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.rejected_qty))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_accepted_amount(scorecard):
	"""Gets the total amount (in company currency) accepted in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.qty * pr_item.base_rate))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_accepted_items(scorecard):
	"""Gets the total number of rejected items in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	return _get_query_value(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.select(Sum(pr_item.qty))
		.where(
			(pr.supplier == scorecard.supplier)
			& (pr.posting_date >= scorecard.start_date)
			& (pr.posting_date <= scorecard.end_date)
			& (pr_item.docstatus == 1)
		)
	)


def get_total_shipments(scorecard):
	"""Gets the total number of ordered shipments to arrive in the period (based on Purchase Receipts)"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")

	return _get_query_value(
		frappe.qb.from_(po_item)
		.join(po)
		.on(po_item.parent == po.name)
		.select(Count(po_item.base_amount))
		.where(
			(po.supplier == scorecard.supplier)
			& (po_item.schedule_date >= scorecard.start_date)
			& (po_item.schedule_date <= scorecard.end_date)
			& (po_item.docstatus == 1)
		)
	)


def get_ordered_qty(scorecard):
	"""Returns the total number of ordered quantity (based on Purchase Orders)"""

	po = frappe.qb.DocType("Purchase Order")

	return (
		frappe.qb.from_(po)
		.select(Sum(po.total_qty))
		.where(
			(po.supplier == scorecard.supplier)
			& (po.docstatus == 1)
			& (po.transaction_date >= scorecard.get("start_date"))
			& (po.transaction_date <= scorecard.get("end_date"))
		)
	).run(as_list=True)[0][0] or 0


def get_invoiced_qty(scorecard):
	"""Returns the total number of invoiced quantity (based on Purchase Invoice)"""

	pi = frappe.qb.DocType("Purchase Invoice")

	return (
		frappe.qb.from_(pi)
		.select(Sum(pi.total_qty))
		.where(
			(pi.supplier == scorecard.supplier)
			& (pi.docstatus == 1)
			& (pi.posting_date >= scorecard.get("start_date"))
			& (pi.posting_date <= scorecard.get("end_date"))
		)
	).run(as_list=True)[0][0] or 0


def get_rfq_total_number(scorecard):
	"""Gets the total number of RFQs sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")

	return _get_query_value(
		frappe.qb.from_(rfq_item)
		.join(rfq)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(Count(rfq.name))
		.where(
			(rfq_sup.supplier == scorecard.supplier)
			& (rfq.transaction_date >= scorecard.start_date)
			& (rfq.transaction_date <= scorecard.end_date)
			& (rfq_item.docstatus == 1)
		)
	)


def get_rfq_total_items(scorecard):
	"""Gets the total number of RFQ items sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")

	return _get_query_value(
		frappe.qb.from_(rfq_item)
		.join(rfq)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(Count(rfq_item.name))
		.where(
			(rfq_sup.supplier == scorecard.supplier)
			& (rfq.transaction_date >= scorecard.start_date)
			& (rfq.transaction_date <= scorecard.end_date)
			& (rfq_item.docstatus == 1)
		)
	)


def get_sq_total_number(scorecard):
	"""Gets the total number of RFQ items sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	return _get_query_value(
		frappe.qb.from_(rfq_item)
		.join(sq_item)
		.on(sq_item.request_for_quotation_item == rfq_item.name)
		.join(sq)
		.on(sq_item.parent == sq.name)
		.join(rfq)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(Count(sq.name))
		.where(
			(rfq_sup.supplier == scorecard.supplier)
			& (rfq.transaction_date >= scorecard.start_date)
			& (rfq.transaction_date <= scorecard.end_date)
			& (sq_item.docstatus == 1)
			& (rfq_item.docstatus == 1)
			& (sq.supplier == scorecard.supplier)
		)
	)


def get_sq_total_items(scorecard):
	"""Gets the total number of RFQ items sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	return _get_query_value(
		frappe.qb.from_(rfq_item)
		.join(sq_item)
		.on(sq_item.request_for_quotation_item == rfq_item.name)
		.join(sq)
		.on(sq_item.parent == sq.name)
		.join(rfq)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(Count(sq_item.name))
		.where(
			(rfq_sup.supplier == scorecard.supplier)
			& (rfq.transaction_date >= scorecard.start_date)
			& (rfq.transaction_date <= scorecard.end_date)
			& (sq_item.docstatus == 1)
			& (sq.supplier == scorecard.supplier)
			& (rfq_item.docstatus == 1)
		)
	)


def get_rfq_response_days(scorecard):
	"""Gets the total number of days it has taken a supplier to respond to rfqs in the period"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	return _get_query_value(
		frappe.qb.from_(rfq_item)
		.join(sq_item)
		.on(sq_item.request_for_quotation_item == rfq_item.name)
		.join(sq)
		.on(sq_item.parent == sq.name)
		.join(rfq)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(Sum(DateDiff(sq.transaction_date, rfq.transaction_date)))
		.where(
			(rfq_sup.supplier == scorecard.supplier)
			& (rfq.transaction_date >= scorecard.start_date)
			& (rfq.transaction_date <= scorecard.end_date)
			& (sq_item.docstatus == 1)
			& (sq.supplier == scorecard.supplier)
			& (rfq_item.docstatus == 1)
		)
	)
