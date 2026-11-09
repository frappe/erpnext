# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_conversion_factor


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
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		company_contact_person: DF.Link | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		contact_phone: DF.Data | None
		customer: DF.Link | None
		customer_address: DF.Link | None
		customer_address_display: DF.TextEditor | None
		customer_name: DF.Data | None
		dispatch_address: DF.TextEditor | None
		dispatch_address_name: DF.Link | None
		from_date: DF.Date
		items: DF.Table[BlanketOrderItem]
		naming_series: DF.Literal["MFG-BLR-.YYYY.-"]
		order_date: DF.Date | None
		order_no: DF.Data | None
		shipping_address: DF.TextEditor | None
		shipping_address_name: DF.Link | None
		supplier: DF.Link | None
		supplier_address: DF.Link | None
		supplier_address_display: DF.TextEditor | None
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
		self.set_uom_and_stock_qty()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From date cannot be greater than To date"))

	def set_uom_and_stock_qty(self):
		for row in self.items:
			if not row.item_code:
				continue

			item = frappe.get_cached_value(
				"Item",
				row.item_code,
				["stock_uom", "sales_uom", "purchase_uom"],
				as_dict=True,
			)
			row.stock_uom = item.stock_uom

			if not row.uom:
				if self.blanket_order_type == "Selling":
					row.uom = item.sales_uom or item.stock_uom
				else:
					row.uom = item.purchase_uom or item.stock_uom

			if row.uom == row.stock_uom:
				row.conversion_factor = 1.0
			else:
				row.conversion_factor = get_conversion_factor(row.item_code, row.uom).get(
					"conversion_factor"
				)

			if not row.conversion_factor:
				frappe.throw(_("Row {0}: Conversion Factor is mandatory").format(row.idx))

			row.stock_qty = flt(row.qty) * flt(row.conversion_factor)
			if row.rate:
				row.stock_uom_rate = flt(row.rate) / flt(row.conversion_factor)

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
			if flt(d.qty) < 0:
				frappe.throw(_("Row {0}: Quantity cannot be negative.").format(d.idx))


@frappe.whitelist()
def make_order(source_name: str):
	doctype = frappe.flags.args.doctype

	def update_doc(source_doc, target_doc, source_parent):
		if doctype == "Quotation":
			target_doc.quotation_to = "Customer"
			target_doc.party_name = source_doc.customer

		if doctype == "Purchase Order":
			target_doc.shipping_address = source_doc.shipping_address_name
			target_doc.shipping_address_display = source_doc.shipping_address
			target_doc.billing_address = source_doc.company_address
			target_doc.billing_address_display = source_doc.company_address_display

	def update_item(source, target, source_parent):
		remaining_stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
		conversion_factor = flt(source.conversion_factor) or 1.0
		target_qty = remaining_stock_qty / conversion_factor
		target.qty = target_qty if target_qty >= 0 else 0
		target.rate = source.get("rate")
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
		target.uom = source.get("uom")
		target.stock_uom = source.get("stock_uom")
		target.conversion_factor = conversion_factor
		target.against_blanket_order = 1
		target.blanket_order = source_name

	blanket_order_map = {"doctype": doctype, "postprocess": update_doc}
	if doctype in ("Sales Order", "Quotation"):
		blanket_order_map["field_map"] = {"customer_address_display": "address_display"}
	elif doctype == "Purchase Order":
		blanket_order_map["field_no_map"] = ["shipping_address"]
		blanket_order_map["field_map"] = {"supplier_address_display": "address_display"}

	target_doc = get_mapped_doc(
		"Blanket Order",
		source_name,
		{
			"Blanket Order": blanket_order_map,
			"Blanket Order Item": {
				"doctype": doctype + " Item",
				"field_map": {"rate": "blanket_order_rate", "parent": "blanket_order"},
				"postprocess": update_item,
				"condition": lambda item: not flt(item.stock_qty)
				or (flt(item.stock_qty) - flt(item.ordered_qty)) > 0,
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
						order_data[item.blanket_order][item.item_code] += flt(item.stock_qty)
					else:
						order_data[item.blanket_order][item.item_code] = flt(item.stock_qty)
				else:
					order_data[item.blanket_order] = {item.item_code: flt(item.stock_qty)}

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
						remaining_qty = flt(item.stock_qty) - flt(item.ordered_qty)
						allowed_qty = remaining_qty + (remaining_qty * (allowance / 100))
						if item.stock_qty and allowed_qty < item_data[item.item_code]:
							frappe.throw(
								_(
									"Item {0} cannot be ordered more than {1} against Blanket Order {2}."
								).format(item.item_code, allowed_qty, bo_name)
							)
