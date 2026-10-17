# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, formatdate, getdate, today

from erpnext import get_company_currency
from erpnext.accounts.services.taxes import validate_conversion_rate
from erpnext.controllers.item_close import clear_closed_rows_on_amend, validate_parent_reopen
from erpnext.controllers.status_updater import StatusUpdater
from erpnext.manufacturing.doctype.blanket_order import blanket_order_pricing
from erpnext.stock.doctype.item.item import get_item_defaults

FULFILLED_QTY_FIELD = {"Sales Order": "delivered_qty", "Purchase Order": "received_qty"}

ORDER_DOCTYPES_BY_TYPE = {
	"Selling": ("Sales Order", "Quotation"),
	"Purchasing": ("Purchase Order",),
}

ORDER_TYPE_BY_DOCTYPE = {
	"Sales Order": ("Selling", "customer"),
	"Purchase Order": ("Purchasing", "supplier"),
}


class BlanketOrder(StatusUpdater):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.blanket_order_item.blanket_order_item import BlanketOrderItem

		amended_from: DF.Link | None
		blanket_order_type: DF.Literal["", "Selling", "Purchasing"]
		buying_price_list: DF.Link | None
		company: DF.Link
		conversion_rate: DF.Float
		currency: DF.Link
		customer: DF.Link | None
		customer_name: DF.Data | None
		from_date: DF.Date
		items: DF.Table[BlanketOrderItem]
		naming_series: DF.Literal["MFG-BLR-.YYYY.-"]
		order_date: DF.Date | None
		order_no: DF.Data | None
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link | None
		selling_price_list: DF.Link | None
		status: DF.Literal["Draft", "Submitted", "Closed", "Cancelled"]
		supplier: DF.Link | None
		supplier_name: DF.Data | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		to_date: DF.Date
	# end: auto-generated types

	def before_validate(self):
		if not self.blanket_order_type:
			return

		self.set_currency()
		self.set_conversion_rate()
		blanket_order_pricing.set_price_list(self)

	def validate(self):
		if not self.blanket_order_type:
			return

		self.validate_party()
		self.validate_dates()
		self.validate_duplicate_items()
		self.validate_item_qty()
		self.set_party_item_code()
		self.set_base_rates()
		clear_closed_rows_on_amend(self)

	def before_update_after_submit(self):
		self.validate_dates()

	def on_submit(self):
		self.set_status(update=True)

	def on_cancel(self):
		self.set_status(update=True)

	def update_status(self, status: str) -> None:
		if status != "Closed" and self.status == "Closed":
			validate_parent_reopen(self)

		self.set_status(update=True, status=status)
		self.notify_update()

	def is_item_closable(self, item) -> bool:
		return flt(item.ordered_qty) < flt(item.qty)

	def validate_can_be_ordered(self, order_date) -> None:
		self.validate_is_open()
		self.validate_not_expired(order_date)

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

	def validate_party(self):
		party_field = blanket_order_pricing.get_order_type_config(self.blanket_order_type)["party_field"]
		if not self.get(party_field):
			frappe.throw(
				_("{0} is mandatory for a {1} Blanket Order").format(
					_(self.meta.get_label(party_field)), _(self.blanket_order_type)
				),
				frappe.MandatoryError,
			)

		other_party_field = "supplier" if party_field == "customer" else "customer"
		self.set(other_party_field, None)
		self.set(f"{other_party_field}_name", None)

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

		if self.currency != order_doc.currency:
			frappe.throw(
				_("Blanket Order {0} is in {1}, not {2}").format(
					frappe.bold(self.name), self.currency, order_doc.currency
				)
			)

	def set_order_rates(self, order_doc) -> None:
		rates = {row.item_code: flt(row.rate) for row in self.items}
		for row in order_doc.get("items"):
			if row.blanket_order != self.name or row.item_code not in rates:
				continue

			row.blanket_order_rate = rates[row.item_code]
			expected_rate = flt(
				row.blanket_order_rate * (flt(row.conversion_factor) or 1), row.precision("rate")
			)
			if flt(row.rate, row.precision("rate")) != expected_rate:
				frappe.msgprint(
					_("Row #{0}: Rate {1} differs from the rate {2} agreed in Blanket Order {3}").format(
						row.idx, row.rate, expected_rate, frappe.bold(self.name)
					),
					alert=True,
					indicator="orange",
				)

	def validate_is_open(self) -> None:
		if self.status == "Closed":
			frappe.throw(
				_("Blanket Order {0} is closed").format(frappe.bold(self.name)), frappe.InvalidStatusError
			)

	def validate_items_are_open(self, item_codes: list[str]) -> None:
		for row in self.items:
			if row.closed and row.item_code in item_codes:
				frappe.throw(
					_("Item {0} is closed in Blanket Order {1}").format(
						frappe.bold(row.item_code), frappe.bold(self.name)
					),
					frappe.InvalidStatusError,
				)

	def set_currency(self):
		if self.currency:
			return

		config = blanket_order_pricing.get_order_type_config(self.blanket_order_type)
		party_type = config["party_type"]
		party = self.get(config["party_field"])
		party_currency = frappe.get_cached_value(party_type, party, "default_currency") if party else None
		self.currency = party_currency or get_company_currency(self.company)

	def set_conversion_rate(self):
		company_currency = get_company_currency(self.company)
		if self.currency == company_currency:
			self.conversion_rate = 1.0
		elif not self.conversion_rate:
			self.conversion_rate = blanket_order_pricing.get_exchange_rate_to_company(self, self.currency)

		validate_conversion_rate(
			self.currency,
			self.conversion_rate,
			self.meta.get_translated_label("conversion_rate"),
			self.company,
		)
		self.conversion_rate = flt(self.conversion_rate, self.precision("conversion_rate"))

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From date cannot be greater than To date"))

	def validate_not_expired(self, order_date) -> None:
		if getdate(order_date) < getdate(self.from_date):
			frappe.throw(
				_("Blanket Order {0} is valid from {1}").format(
					frappe.bold(self.name), formatdate(self.from_date)
				),
				title=_("Blanket Order Not Started"),
			)

		if getdate(order_date) > getdate(self.to_date):
			frappe.throw(
				_("Blanket Order {0} expired on {1}").format(
					frappe.bold(self.name), formatdate(self.to_date)
				),
				title=_("Blanket Order Expired"),
			)

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
			Case()
			.when(trans.status.isin(["Stopped", "Closed"]) | (trans_item.closed == 1), fulfilled_qty)
			.else_(trans_item.stock_qty)
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
			if flt(d.qty) <= 0:
				frappe.throw(_("Row {0}: Quantity must be greater than zero.").format(d.idx))

	def set_base_rates(self):
		blanket_order_pricing.set_base_rates(self)


@frappe.whitelist()
def apply_price_list(
	doc: str | dict,
	item_name: str | None = None,
	reset_party_values: bool = False,
	reset_plc_conversion_rate: bool = False,
	reset_conversion_rate: bool = False,
):
	return blanket_order_pricing.apply_price_list(
		doc=doc,
		item_name=item_name,
		reset_party_values=reset_party_values,
		reset_plc_conversion_rate=reset_plc_conversion_rate,
		reset_conversion_rate=reset_conversion_rate,
	)


@frappe.whitelist(methods=["POST"])
def update_status(status: str, name: str):
	blanket_order = frappe.get_doc("Blanket Order", name, check_permission="submit")
	blanket_order.update_status(status)


@frappe.whitelist()
def make_order(source_name: str):
	blanket_order = frappe.get_doc("Blanket Order", source_name, check_permission="read")
	blanket_order.validate_can_be_ordered(today())
	doctype = frappe.flags.args.doctype
	if doctype not in ORDER_DOCTYPES_BY_TYPE[blanket_order.blanket_order_type]:
		frappe.throw(
			_("A {0} cannot be made from a {1} Blanket Order").format(
				_(doctype), _(blanket_order.blanket_order_type)
			)
		)

	def update_doc(source_doc, target_doc, source_parent):
		if doctype == "Quotation":
			target_doc.quotation_to = "Customer"
			target_doc.party_name = source_doc.customer

	def update_item(source, target, source_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if flt(target_qty) >= 0 else 0
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")
			target.against_blanket_order = 1

	target_doc = get_mapped_doc(
		"Blanket Order",
		source_name,
		{
			"Blanket Order": {
				"doctype": doctype,
				"field_no_map": ["naming_series"],
				"postprocess": update_doc,
			},
			"Blanket Order Item": {
				"doctype": doctype + " Item",
				"field_map": {
					"rate": "blanket_order_rate",
					"parent": "blanket_order",
				},
				"postprocess": update_item,
				"condition": lambda item: not item.closed
				and (not flt(item.qty) or (flt(item.qty) - flt(item.ordered_qty)) > 0),
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
			if item.blanket_order:
				stock_qty = flt(item.qty) * (flt(item.conversion_factor) or 1)
				item_data = order_data.setdefault(item.blanket_order, {})
				item_data[item.item_code] = item_data.get(item.item_code, 0) + stock_qty

		for bo_name, item_data in sorted(order_data.items()):
			bo_doc = frappe.get_doc("Blanket Order", bo_name, for_update=True)
			bo_doc.validate_can_be_ordered(order_doc.transaction_date)
			bo_doc.validate_order_matches(order_doc)
			bo_doc.validate_items_are_open(list(item_data))
			bo_doc.validate_qty_can_be_ordered(item_data, order_doc.doctype)
			bo_doc.set_order_rates(order_doc)


def validate_reopen_against_blanket_order(order_doc, rows=None):
	fulfilled_field = FULFILLED_QTY_FIELD[order_doc.doctype]
	if rows is None:
		rows = [item for item in order_doc.get("items") if not item.get("closed")]

	order_data = {}
	for item in rows:
		if item.blanket_order:
			pending_qty = (flt(item.qty) - flt(item.get(fulfilled_field))) * (
				flt(item.conversion_factor) or 1
			)
			item_data = order_data.setdefault(item.blanket_order, {})
			item_data[item.item_code] = item_data.get(item.item_code, 0) + max(pending_qty, 0)

	for bo_name, item_data in sorted(order_data.items()):
		bo_doc = frappe.get_doc("Blanket Order", bo_name, for_update=True)
		bo_doc.validate_qty_can_be_ordered(item_data, order_doc.doctype)


def refresh_blanket_orders_of_fulfilled_rows(doc):
	order_rows = {}
	for args in doc.status_updater:
		if args.get("target_field") not in ("delivered_qty", "received_qty"):
			continue

		if args.get("target_dt") not in ("Sales Order Item", "Purchase Order Item"):
			continue

		rows = order_rows.setdefault(args["target_dt"], set())
		rows.update(d.get(args["join_field"]) for d in doc.get_all_children(args["source_dt"]))

	for order_item_doctype, rows in order_rows.items():
		rows.discard(None)
		if not rows:
			continue

		blanket_orders = frappe.get_all(
			order_item_doctype,
			filters={"name": ("in", list(rows)), "blanket_order": ("is", "set")},
			pluck="blanket_order",
			distinct=True,
		)
		for blanket_order in sorted(blanket_orders):
			frappe.get_doc("Blanket Order", blanket_order, for_update=True).update_ordered_qty()
