# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

from erpnext.stock.doctype.item.item import get_item_defaults


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

		item_ordered_qty = frappe._dict(
			(
				frappe.qb.from_(trans_item)
				.from_(trans)
				.select(trans_item.item_code, Sum(trans_item.stock_qty).as_("qty"))
				.where(
					(trans.name == trans_item.parent)
					& (trans_item.blanket_order == self.name)
					& (trans.docstatus == 1)
					& (trans.status.notin(["Stopped", "Closed"]))
				)
				.groupby(trans_item.item_code)
			).run()
		)

		for d in self.items:
			d.db_set("ordered_qty", item_ordered_qty.get(d.item_code, 0))

	def validate_item_qty(self):
		for d in self.items:
			if d.qty < 0:
				frappe.throw(_("Row {0}: Quantity cannot be negative.").format(d.idx))


@frappe.whitelist()
def make_order(source_name):
	doctype = frappe.flags.args.doctype

	def update_doc(source_doc, target_doc, source_parent):
		if doctype == "Quotation":
			target_doc.quotation_to = "Customer"
			target_doc.party_name = source_doc.customer

	def update_item(source, target, source_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if flt(target_qty) >= 0 else 0
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
				if item.blanket_order in order_data:
					if item.item_code in order_data[item.blanket_order]:
						order_data[item.blanket_order][item.item_code] += item.qty
					else:
						order_data[item.blanket_order][item.item_code] = item.qty
				else:
					order_data[item.blanket_order] = {item.item_code: item.qty}

		if order_data:
			allowance = flt(
				frappe.db.get_single_value(
					"Selling Settings" if order_doc.doctype == "Sales Order" else "Buying Settings",
					"blanket_order_allowance",
				)
			)
			for bo_name, item_data in order_data.items():
				bo_doc = frappe.get_doc("Blanket Order", bo_name)
				for item in bo_doc.get("items"):
					if item.item_code in item_data:
						remaining_qty = item.qty - item.ordered_qty
						allowed_qty = remaining_qty + (remaining_qty * (allowance / 100))
						if item.qty and allowed_qty < item_data[item.item_code]:
							frappe.throw(
								_(
									"Item {0} cannot be ordered more than {1} against Blanket Order {2}."
								).format(item.item_code, allowed_qty, bo_name)
							)
