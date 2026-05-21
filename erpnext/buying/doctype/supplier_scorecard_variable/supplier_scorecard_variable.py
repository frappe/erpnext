# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import sys

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import getdate


class VariablePathNotFound(frappe.ValidationError):
	pass


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


def get_item_workdays(scorecard):
	"""Gets the number of days in this period"""
	supplier = frappe.get_doc("Supplier", scorecard.supplier)
	total_item_days = frappe.db.sql(
		"""
			SELECT
				SUM(DATEDIFF( %(end_date)s, po_item.schedule_date) * (po_item.qty))
			FROM
				`tabPurchase Order Item` po_item,
				`tabPurchase Order` po
			WHERE
				po.supplier = %(supplier)s
				AND po_item.received_qty < po_item.qty
				AND po_item.schedule_date BETWEEN %(start_date)s AND %(end_date)s
				AND po_item.parent = po.name""",
		{"supplier": supplier.name, "start_date": scorecard.start_date, "end_date": scorecard.end_date},
		as_dict=0,
	)[0][0]

	if not total_item_days:
		total_item_days = 0
	return total_item_days


def get_total_cost_of_shipments(scorecard):
	"""Gets the total cost of all shipments in the period (based on Purchase Orders)"""

	from frappe.query_builder.functions import Sum

	PO = frappe.qb.DocType("Purchase Order")
	PO_Item = frappe.qb.DocType("Purchase Order Item")

	query = (
		frappe.qb.from_(PO_Item)
		.join(PO)
		.on(PO_Item.parent == PO.name)
		.select(Sum(PO_Item.base_amount))
		.where(PO.supplier == scorecard.supplier)
		.where(PO_Item.schedule_date[scorecard.start_date : scorecard.end_date])  # Syntaxe BETWEEN
		.where(PO_Item.docstatus == 1)
	)

	result = query.run(as_list=True)
	total_cost = result[0][0] if result and result[0][0] is not None else 0
	return total_cost


def get_cost_of_delayed_shipments(scorecard):
	"""Gets the total cost of all delayed shipments in the period (based on Purchase Receipts - POs)"""
	return get_total_cost_of_shipments(scorecard) - get_cost_of_on_time_shipments(scorecard)


def get_cost_of_on_time_shipments(scorecard):
	"""Gets the total cost of all on_time shipments in the period (based on Purchase Receipts)"""
	supplier = frappe.get_doc("Supplier", scorecard.supplier)

	# Look up all PO Items with delivery dates between our dates

	total_delivered_on_time_costs = frappe.db.sql(
		"""
			SELECT
				SUM(pr_item.base_amount)
			FROM
				`tabPurchase Order Item` po_item,
				`tabPurchase Receipt Item` pr_item,
				`tabPurchase Order` po,
				`tabPurchase Receipt` pr
			WHERE
				po.supplier = %(supplier)s
				AND po_item.schedule_date BETWEEN %(start_date)s AND %(end_date)s
				AND po_item.schedule_date >= pr.posting_date
				AND pr_item.docstatus = 1
				AND pr_item.purchase_order_item = po_item.name
				AND po_item.parent = po.name
				AND pr_item.parent = pr.name""",
		{"supplier": supplier.name, "start_date": scorecard.start_date, "end_date": scorecard.end_date},
		as_dict=0,
	)[0][0]

	if total_delivered_on_time_costs:
		return total_delivered_on_time_costs
	else:
		return 0


def get_total_days_late(scorecard):
	"""Gets the number of item days late in the period (based on Purchase Receipts vs POs)"""
	supplier = frappe.get_doc("Supplier", scorecard.supplier)
	total_delivered_late_days = frappe.db.sql(
		"""
			SELECT
				SUM(DATEDIFF(pr.posting_date,po_item.schedule_date)* pr_item.qty)
			FROM
				`tabPurchase Order Item` po_item,
				`tabPurchase Receipt Item` pr_item,
				`tabPurchase Order` po,
				`tabPurchase Receipt` pr
			WHERE
				po.supplier = %(supplier)s
				AND po_item.schedule_date BETWEEN %(start_date)s AND %(end_date)s
				AND po_item.schedule_date < pr.posting_date
				AND pr_item.docstatus = 1
				AND pr_item.purchase_order_item = po_item.name
				AND po_item.parent = po.name
				AND pr_item.parent = pr.name""",
		{"supplier": supplier.name, "start_date": scorecard.start_date, "end_date": scorecard.end_date},
		as_dict=0,
	)[0][0]
	if not total_delivered_late_days:
		total_delivered_late_days = 0

	total_missed_late_days = frappe.db.sql(
		"""
			SELECT
				SUM(DATEDIFF( %(end_date)s, po_item.schedule_date) * (po_item.qty - po_item.received_qty))
			FROM
				`tabPurchase Order Item` po_item,
				`tabPurchase Order` po
			WHERE
				po.supplier = %(supplier)s
				AND po_item.received_qty < po_item.qty
				AND po_item.schedule_date BETWEEN %(start_date)s AND %(end_date)s
				AND po_item.parent = po.name""",
		{"supplier": supplier.name, "start_date": scorecard.start_date, "end_date": scorecard.end_date},
		as_dict=0,
	)[0][0]

	if not total_missed_late_days:
		total_missed_late_days = 0
	return total_missed_late_days + total_delivered_late_days


def get_on_time_shipments(scorecard):
	"""Gets the number of late shipments (counting each item) in the period (based on Purchase Receipts vs POs)"""

	supplier = frappe.get_doc("Supplier", scorecard.supplier)

	# Look up all PO Items with delivery dates between our dates
	total_items_delivered_on_time = frappe.db.sql(
		"""
			SELECT
				COUNT(pr_item.qty)
			FROM
				`tabPurchase Order Item` po_item,
				`tabPurchase Receipt Item` pr_item,
				`tabPurchase Order` po,
				`tabPurchase Receipt` pr
			WHERE
				po.supplier = %(supplier)s
				AND po_item.schedule_date BETWEEN %(start_date)s AND %(end_date)s
				AND po_item.schedule_date <= pr.posting_date
				AND po_item.qty = pr_item.qty
				AND pr_item.docstatus = 1
				AND pr_item.purchase_order_item = po_item.name
				AND po_item.parent = po.name
				AND pr_item.parent = pr.name""",
		{"supplier": supplier.name, "start_date": scorecard.start_date, "end_date": scorecard.end_date},
		as_dict=0,
	)[0][0]

	if not total_items_delivered_on_time:
		total_items_delivered_on_time = 0
	return total_items_delivered_on_time


def get_late_shipments(scorecard):
	"""Gets the number of late shipments (counting each item) in the period (based on Purchase Receipts vs POs)"""
	return get_total_shipments(scorecard) - get_on_time_shipments(scorecard)


def get_total_received(scorecard):
	"""Gets the total number of received shipments in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Count(pr_item.base_amount))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return result[0][0] if result and result[0][0] else 0


def get_total_received_amount(scorecard):
	"""Gets the total amount (in company currency) received in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Sum(pr_item.received_qty * pr_item.base_rate))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.flt(result[0][0]) if result else 0.0


def get_total_received_items(scorecard):
	"""Gets the total number of received shipments in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Sum(pr_item.received_qty))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.flt(result[0][0]) if result else 0.0


def get_total_rejected_amount(scorecard):
	"""Gets the total amount (in company currency) rejected in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Sum(pr_item.rejected_qty * pr_item.base_rate))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.flt(result[0][0]) if result else 0.0


def get_total_rejected_items(scorecard):
	"""Gets the total number of rejected items in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Sum(pr_item.rejected_qty))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.flt(result[0][0]) if result else 0.0


def get_total_accepted_amount(scorecard):
	"""Gets the total amount (in company currency) accepted in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Sum(pr_item.qty * pr_item.base_rate))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.flt(result[0][0]) if result else 0.0


def get_total_accepted_items(scorecard):
	"""Gets the total number of rejected items in the period (based on Purchase Receipts)"""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(frappe.qb.fn.Sum(pr_item.qty))
		.where(pr.supplier == scorecard.supplier)
		.where(pr.posting_date[scorecard.start_date : scorecard.end_date])
		.where(pr_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.flt(result[0][0]) if result else 0.0


def get_total_shipments(scorecard):
	"""Gets the total number of ordered shipments to arrive in the period (based on Purchase Receipts)"""
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")

	query = (
		frappe.qb.from_(po)
		.join(po_item)
		.on(po_item.parent == po.name)
		.select(frappe.qb.fn.Count(po_item.base_amount))
		.where(po.supplier == scorecard.supplier)
		.where(po_item.schedule_date[scorecard.start_date : scorecard.end_date])
		.where(po_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.cint(result[0][0]) if result else 0


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

	query = (
		frappe.qb.from_(rfq)
		.join(rfq_item)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(frappe.qb.fn.Count(rfq.name))
		.where(rfq_sup.supplier == scorecard.supplier)
		.where(rfq.transaction_date[scorecard.start_date : scorecard.end_date])
		.where(rfq_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.cint(result[0][0]) if result else 0


def get_rfq_total_items(scorecard):
	"""Gets the total number of RFQ items sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")

	query = (
		frappe.qb.from_(rfq)
		.join(rfq_item)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.select(frappe.qb.fn.Count(rfq_item.name))
		.where(rfq_sup.supplier == scorecard.supplier)
		.where(rfq.transaction_date[scorecard.start_date : scorecard.end_date])
		.where(rfq_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.cint(result[0][0]) if result else 0


def get_sq_total_number(scorecard):
	"""Gets the total number of RFQ items sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	query = (
		frappe.qb.from_(rfq)
		.join(rfq_item)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.join(sq_item)
		.on(sq_item.request_for_quotation_item == rfq_item.name)
		.join(sq)
		.on(sq_item.parent == sq.name)
		.select(frappe.qb.fn.Count(sq.name))
		.where(rfq_sup.supplier == scorecard.supplier)
		.where(sq.supplier == scorecard.supplier)
		.where(rfq.transaction_date[scorecard.start_date : scorecard.end_date])
		.where(rfq_item.docstatus == 1)
		.where(sq_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.cint(result[0][0]) if result else 0


def get_sq_total_items(scorecard):
	"""Gets the total number of RFQ items sent to supplier"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	query = (
		frappe.qb.from_(rfq)
		.join(rfq_item)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.join(sq_item)
		.on(sq_item.request_for_quotation_item == rfq_item.name)
		.join(sq)
		.on(sq_item.parent == sq.name)
		.select(frappe.qb.fn.Count(sq_item.name))
		.where(rfq_sup.supplier == scorecard.supplier)
		.where(sq.supplier == scorecard.supplier)
		.where(rfq.transaction_date[scorecard.start_date : scorecard.end_date])
		.where(rfq_item.docstatus == 1)
		.where(sq_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.cint(result[0][0]) if result else 0


def get_rfq_response_days(scorecard):
	"""Gets the total number of days it has taken a supplier to respond to rfqs in the period"""
	rfq = frappe.qb.DocType("Request for Quotation")
	rfq_item = frappe.qb.DocType("Request for Quotation Item")
	rfq_sup = frappe.qb.DocType("Request for Quotation Supplier")
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	query = (
		frappe.qb.from_(rfq)
		.join(rfq_item)
		.on(rfq_item.parent == rfq.name)
		.join(rfq_sup)
		.on(rfq_sup.parent == rfq.name)
		.join(sq_item)
		.on(sq_item.request_for_quotation_item == rfq_item.name)
		.join(sq)
		.on(sq_item.parent == sq.name)
		.select(frappe.qb.fn.Sum(frappe.qb.fn.Datediff(sq.transaction_date, rfq.transaction_date)))
		.where(rfq_sup.supplier == scorecard.supplier)
		.where(sq.supplier == scorecard.supplier)
		.where(rfq.transaction_date[scorecard.start_date : scorecard.end_date])
		.where(rfq_item.docstatus == 1)
		.where(sq_item.docstatus == 1)
	)

	result = query.run()
	return frappe.utils.cint(result[0][0]) if result else 0
