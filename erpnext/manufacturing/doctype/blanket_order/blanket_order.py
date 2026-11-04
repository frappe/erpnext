# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, getdate

from erpnext.stock.doctype.item.item import get_item_defaults

FULFILLED_QTY_FIELD = {"Sales Order": "delivered_qty", "Purchase Order": "received_qty"}

ORDER_TYPE_BY_DOCTYPE = {
	"Sales Order": ("Selling", "customer"),
	"Purchase Order": ("Purchasing", "supplier"),
}


class BlanketOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.blanket_order_item.blanket_order_item import BlanketOrderItem

		amended_from: DF.Link | None
		blanket_order_type: DF.Literal["", "Selling", "Purchasing"]
		company: DF.Link
		customer: DF.Link | None
		customer_name: DF.Data | None
		from_date: DF.Date
		items: DF.Table[BlanketOrderItem]
		naming_series: DF.Literal["MFG-BLR-.YYYY.-"]
		order_date: DF.Date | None
		order_no: DF.Data | None
		supplier: DF.Link | None
		supplier_name: DF.Data | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		to_date: DF.Date
	# end: auto-generated types

	def validate(self):
		self.validate_dates()
		self.validate_duplicate_items()
		self.validate_item_qty()
		self.set_party_item_code()

	def before_update_after_submit(self):
		self.validate_dates()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From date cannot be greater than To date"))

	def set_party_item_code(self):
		item_ref = {}
		if self.blanket_order_type == "Selling":
			item_ref = self.get_customer_items_ref()
		else:
			item_ref = self.get_supplier_items_ref()

		if not item_ref:
			return

		for row in self.items:
			row.party_item_code = item_ref.get(row.item_code)

	def get_customer_items_ref(self):
		items = [d.item_code for d in self.items]

		return frappe._dict(
			frappe.get_all(
				"Item Customer Detail",
				filters={"parent": ("in", items), "customer_name": self.customer},
				fields=["parent", "ref_code"],
				as_list=True,
			)
		)

	def get_supplier_items_ref(self):
		items = [d.item_code for d in self.items]

		return frappe._dict(
			frappe.get_all(
				"Item Supplier",
				filters={"parent": ("in", items), "supplier": self.supplier},
				fields=["parent", "supplier_part_no"],
				as_list=True,
			)
		)

	def validate_duplicate_items(self):
		item_list = []
		for item in self.items:
			if item.item_code in item_list:
				frappe.throw(_("Note: Item {0} added multiple times").format(frappe.bold(item.item_code)))
			item_list.append(item.item_code)

	def update_ordered_qty(self):
		ref_doctype = "Sales Order" if self.blanket_order_type == "Selling" else "Purchase Order"

		trans = frappe.qb.DocType(ref_doctype)
		trans_item = frappe.qb.DocType(f"{ref_doctype} Item")
		fulfilled_qty = IfNull(trans_item[FULFILLED_QTY_FIELD[ref_doctype]], 0) * trans_item.conversion_factor
		ordered_qty = (
			Case().when(trans.status.isin(["Stopped", "Closed"]), fulfilled_qty).else_(trans_item.stock_qty)
		)

		item_ordered_qty = frappe._dict(
			(
				frappe.qb.from_(trans_item)
				.from_(trans)
				.select(trans_item.item_code, Sum(ordered_qty).as_("qty"))
				.where(
					(trans.name == trans_item.parent)
					& (trans_item.blanket_order == self.name)
					& (trans.docstatus == 1)
				)
				.groupby(trans_item.item_code)
			).run()
		)

		for d in self.items:
			d.db_set("ordered_qty", item_ordered_qty.get(d.item_code, 0))

	def validate_item_qty(self):
		for d in self.items:
			if flt(d.qty) < 0:
				frappe.throw(_("Row {0}: Quantity cannot be negative.").format(d.idx))

	def validate_qty_can_be_ordered(self, item_data: dict, order_doctype: str) -> None:
		allowance = flt(
			frappe.db.get_single_value(
				"Selling Settings" if order_doctype == "Sales Order" else "Buying Settings",
				"blanket_order_allowance",
			)
		)
		for item in self.get("items"):
			if item.item_code not in item_data:
				continue

			precision = item.precision("qty")
			allowed_qty = flt(item.qty + (item.qty * allowance / 100) - item.ordered_qty, precision)
			if item.qty and allowed_qty < flt(item_data[item.item_code], precision):
				frappe.throw(
					_("Item {0} cannot be ordered more than {1} against Blanket Order {2}.").format(
						item.item_code, allowed_qty, self.name
					)
				)

	def validate_order_matches(self, order_doc) -> None:
		order_type, party_field = ORDER_TYPE_BY_DOCTYPE[order_doc.doctype]
		if self.blanket_order_type != order_type:
			frappe.throw(
				_("Blanket Order {0} is a {1} order and cannot be used on a {2}").format(
					frappe.bold(self.name), _(self.blanket_order_type), _(order_doc.doctype)
				)
			)

		if self.get(party_field) != order_doc.get(party_field):
			frappe.throw(
				_("Blanket Order {0} is for {1}, not {2}").format(
					frappe.bold(self.name),
					frappe.bold(self.get(party_field)),
					frappe.bold(order_doc.get(party_field)),
				)
			)


@frappe.whitelist()
def make_order(source_name):
	doctype = frappe.flags.args.doctype

	def update_doc(source_doc, target_doc, source_parent):
		if doctype == "Quotation":
			target_doc.quotation_to = "Customer"
			target_doc.party_name = source_doc.customer

	def update_item(source, target, source_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if not flt(target_qty) < 0 else 0
		target.rate = source.get("rate")
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")
			target.against_blanket_order = 1
			target.blanket_order = source_name

	target_doc = get_mapped_doc(
		"Blanket Order",
		source_name,
		{
			"Blanket Order": {"doctype": doctype, "postprocess": update_doc},
			"Blanket Order Item": {
				"doctype": doctype + " Item",
				"field_map": {"rate": "blanket_order_rate", "parent": "blanket_order"},
				"postprocess": update_item,
				"condition": lambda item: not (flt(item.qty)) or (flt(item.qty) - flt(item.ordered_qty)) > 0,
			},
		},
	)

	if target_doc.doctype == "Purchase Order":
		target_doc.set_missing_values()

	return target_doc


def validate_against_blanket_order(order_doc):
	if order_doc.doctype in ("Sales Order", "Purchase Order"):
		order_data = {}
		for item in order_doc.get("items"):
			if item.against_blanket_order and item.blanket_order:
				stock_qty = flt(item.qty) * (flt(item.conversion_factor) or 1)
				item_data = order_data.setdefault(item.blanket_order, {})
				item_data[item.item_code] = item_data.get(item.item_code, 0) + stock_qty

		for bo_name, item_data in sorted(order_data.items()):
			bo_doc = frappe.get_doc("Blanket Order", bo_name, for_update=True)
			bo_doc.validate_order_matches(order_doc)
			bo_doc.validate_qty_can_be_ordered(item_data, order_doc.doctype)


def validate_reopen_against_blanket_order(order_doc):
	fulfilled_field = FULFILLED_QTY_FIELD[order_doc.doctype]
	order_data = {}
	for item in order_doc.get("items"):
		if item.blanket_order:
			pending_qty = (flt(item.qty) - flt(item.get(fulfilled_field))) * (
				flt(item.conversion_factor) or 1
			)
			item_data = order_data.setdefault(item.blanket_order, {})
			item_data[item.item_code] = item_data.get(item.item_code, 0) + max(pending_qty, 0)

	for bo_name, item_data in sorted(order_data.items()):
		bo_doc = frappe.get_doc("Blanket Order", bo_name, for_update=True)
		bo_doc.validate_qty_can_be_ordered(item_data, order_doc.doctype)
