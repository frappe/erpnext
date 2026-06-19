# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Child item update service: ChildItemUpdater class and helpers for the update_child_qty_rate API."""

import frappe
from frappe import _
from frappe.model.workflow import get_workflow_name
from frappe.utils import flt, get_link_to_form, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from erpnext.buying.utils import update_last_purchase_rate
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.stock.get_item_details import (
	get_bin_details,
	get_conversion_factor,
	get_item_warehouse_,
)


class ChildItemUpdater:
	"""Validates and applies item-level edits on submitted orders and quotations."""

	def __init__(self, parent_doctype: str, parent_doctype_name: str, child_docname: str = "items"):
		self.parent_doctype = parent_doctype
		self.parent_doctype_name = parent_doctype_name
		self.child_docname = child_docname
		self.parent = frappe.get_doc(parent_doctype, parent_doctype_name)
		self.allow_zero_qty = get_allow_zero_qty(parent_doctype)
		self._ordered_items: dict | None = None
		self._purchased_items: dict | None = None

	def update(self, trans_items: str) -> None:
		"""Process item additions, edits, and deletions from trans_items JSON."""
		from erpnext.buying.doctype.supplier_quotation.supplier_quotation import get_purchased_items
		from erpnext.selling.doctype.quotation.mapper import get_ordered_items

		data = frappe.parse_json(trans_items)
		any_qty_changed = False
		items_added_or_removed = False
		any_conversion_factor_changed = False

		self._check_permissions("write")

		if self.parent_doctype == "Quotation":
			self._ordered_items = get_ordered_items(self.parent.name)
			items_added_or_removed |= validate_and_delete_children(self.parent, data, self._ordered_items)
		elif self.parent_doctype == "Supplier Quotation":
			self._purchased_items = get_purchased_items(self.parent.name)
			items_added_or_removed |= validate_and_delete_children(self.parent, data, self._purchased_items)
		else:
			items_added_or_removed |= validate_and_delete_children(self.parent, data)

		for d in data:
			new_child_flag = False
			rate_unchanged = None

			if not d.get("item_code"):
				continue

			if not d.get("docname"):
				new_child_flag = True
				items_added_or_removed = True
				self._check_permissions("create")
				child_item = self._get_new_child_item(d)
			else:
				self._check_permissions("write")
				child_item = frappe.get_doc(self.parent_doctype + " Item", d.get("docname"))

				change_state = get_child_item_change_state(self.parent_doctype, child_item, d)
				rate_unchanged = change_state.rate_unchanged
				any_conversion_factor_changed |= not change_state.conversion_factor_unchanged
				if is_child_item_unchanged(change_state):
					continue

			self._validate_quantity_and_rate(child_item, d, rate_unchanged)

			if flt(child_item.get("qty")) != flt(d.get("qty")):
				any_qty_changed = True

			if self.parent.doctype in ("Sales Order", "Purchase Order") and self.parent.is_subcontracted:
				self._validate_fg_item_for_subcontracting(d, new_child_flag)
				child_item.fg_item_qty = flt(d["fg_item_qty"])
				if new_child_flag:
					child_item.fg_item = d["fg_item"]

			child_item.qty = flt(d.get("qty"))
			child_item.description = d.get("description")
			update_child_item_rate_and_discount(
				self.parent_doctype, child_item, d, self.allow_zero_qty, rate_unchanged=rate_unchanged
			)
			update_child_item_uom_and_weight(child_item, d)

			if d.get("delivery_date") and self.parent_doctype == "Sales Order":
				child_item.delivery_date = d.get("delivery_date")

			if d.get("schedule_date") and self.parent_doctype == "Purchase Order":
				child_item.schedule_date = d.get("schedule_date")

			if d.get("bom_no") and self.parent_doctype == "Sales Order":
				child_item.bom_no = d.get("bom_no")

			child_item.flags.ignore_validate_update_after_submit = True
			if new_child_flag:
				self.parent.load_from_db()
				child_item.idx = len(self.parent.items) + 1
				child_item.insert()
			else:
				child_item.save(ignore_permissions=True)

		self._post_update(any_qty_changed, items_added_or_removed, any_conversion_factor_changed)

	def _post_update(
		self, any_qty_changed: bool, items_added_or_removed: bool, any_conversion_factor_changed: bool
	) -> None:
		parent = self.parent
		parent.reload()
		parent.flags.ignore_validate_update_after_submit = True
		parent.set_qty_as_per_stock_uom()
		parent.calculate_taxes_and_totals()
		parent.set_total_in_words()

		if self.parent_doctype == "Sales Order" and not parent.is_subcontracted:
			make_packing_list(parent)
			parent.set_gross_profit()

		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			parent.doctype, parent.company, parent.base_grand_total
		)

		if self.parent_doctype != "Supplier Quotation":
			from erpnext.accounts.services.payment_schedule import PaymentScheduleService

			PaymentScheduleService(parent).set_payment_schedule()

		if self.parent_doctype == "Purchase Order":
			parent.validate_minimum_order_qty()
			parent.validate_budget()
			if parent.is_against_so():
				parent.update_status_updater()
		elif self.parent_doctype == "Sales Order":
			parent.check_credit_limit()

		for idx, row in enumerate(parent.get(self.child_docname), start=1):
			row.idx = idx

		parent.save()

		if self.parent_doctype == "Purchase Order":
			update_last_purchase_rate(parent, is_submit=1)

			if any_qty_changed or items_added_or_removed or any_conversion_factor_changed:
				parent.update_prevdoc_status()

			parent.update_requested_qty()
			parent.update_ordered_qty()
			parent.update_ordered_and_reserved_qty()
			parent.update_receiving_percentage()

			if parent.is_subcontracted and not parent.can_update_items():
				frappe.throw(
					_(
						"Items cannot be updated as Subcontracting Order is created against the Purchase Order {0}."
					).format(frappe.bold(parent.name))
				)

		elif self.parent_doctype == "Sales Order":
			if parent.is_subcontracted and not parent.can_update_items():
				frappe.throw(
					_(
						"Items cannot be updated as Subcontracting Inward Order(s) exist against this Subcontracted Sales Order."
					)
				)
			parent.validate_selling_price()
			parent.validate_for_duplicate_items()
			parent.validate_warehouse()
			parent.update_reserved_qty()
			parent.update_project()
			parent.update_prevdoc_status("submit")
			parent.update_delivery_status()

		parent.reload()
		self._validate_workflow()

		if self.parent_doctype in ("Purchase Order", "Sales Order"):
			parent.update_blanket_order()
			parent.update_billing_percentage()
			parent.set_status()

		parent.validate_uom_is_integer("uom", "qty")
		parent.validate_uom_is_integer("stock_uom", "stock_qty")

		if self.parent_doctype == "Sales Order" and not parent.is_subcontracted:
			from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
				cancel_stock_reservation_entries,
				has_reserved_stock,
			)

			if has_reserved_stock(parent.doctype, parent.name):
				cancel_stock_reservation_entries(parent.doctype, parent.name)
				if parent.per_picked == 0:
					parent.create_stock_reservation_entries()

	def _check_permissions(self, perm_type: str = "create") -> None:
		try:
			self.parent.check_permission(perm_type)
		except frappe.PermissionError:
			actions = {"create": "add", "write": "update"}
			frappe.throw(
				_("You do not have permissions to {} items in a {}.").format(
					actions[perm_type], self.parent_doctype
				),
				title=_("Insufficient Permissions"),
			)

	def _validate_workflow(self) -> None:
		workflow = get_workflow_name(self.parent.doctype)
		if not workflow:
			return

		workflow_doc = frappe.get_doc("Workflow", workflow)
		current_state = self.parent.get(workflow_doc.workflow_state_field)
		roles = frappe.get_roles()

		allowed = any(
			state.state == current_state and (not state.allow_edit or state.allow_edit in roles)
			for state in workflow_doc.states
		)

		if not allowed:
			frappe.throw(
				_("You are not allowed to update as per the conditions set in {} Workflow.").format(
					get_link_to_form("Workflow", workflow)
				),
				title=_("Insufficient Permissions"),
			)

	def _get_new_child_item(self, item_row) -> "frappe.model.document.Document":
		child_doctype = self.parent_doctype + " Item"
		return set_order_defaults(
			self.parent_doctype,
			self.parent_doctype_name,
			child_doctype,
			self.child_docname,
			item_row,
		)

	def _validate_quantity_and_rate(self, child_item, new_data: dict, rate_unchanged: bool | None) -> None:
		if not flt(new_data.get("qty")) and not self.allow_zero_qty:
			frappe.throw(
				_("Row #{0}:Quantity for Item {1} cannot be zero.").format(
					new_data.get("idx"), frappe.bold(new_data.get("item_code"))
				),
				title=_("Invalid Qty"),
			)

		qty_limits = {
			"Sales Order": ("delivered_qty", _("Cannot set quantity less than delivered quantity.")),
			"Purchase Order": ("received_qty", _("Cannot set quantity less than received quantity.")),
		}

		if self.parent_doctype in qty_limits:
			qty_field, error_message = qty_limits[self.parent_doctype]
			if flt(new_data.get("qty")) < flt(child_item.get(qty_field)):
				frappe.throw(
					_("Row #{0}:").format(new_data.get("idx")) + error_message,
					title=_("Invalid Qty"),
				)

		if self.parent_doctype not in ("Quotation", "Supplier Quotation"):
			return

		items_map = self._ordered_items if self.parent_doctype == "Quotation" else self._purchased_items
		if not items_map:
			return

		qty_to_check = items_map.get(child_item.name)
		if not qty_to_check:
			return

		if not rate_unchanged:
			frappe.throw(
				_(
					"Cannot update rate as item {0} is already ordered or purchased against this quotation"
				).format(frappe.bold(new_data.get("item_code")))
			)

		if flt(new_data.get("qty")) < qty_to_check:
			frappe.throw(_("Cannot reduce quantity than ordered or purchased quantity"))

	def _validate_fg_item_for_subcontracting(self, new_data: dict, is_new: bool) -> None:
		if is_new:
			if not new_data.get("fg_item"):
				frappe.throw(
					_("Finished Good Item is not specified for service item {0}").format(
						new_data["item_code"]
					)
				)

			is_sub_contracted_item, default_bom = frappe.db.get_value(
				"Item", new_data["fg_item"], ["is_sub_contracted_item", "default_bom"]
			)

			if not is_sub_contracted_item:
				frappe.throw(
					_("Finished Good Item {0} must be a sub-contracted item").format(new_data["fg_item"])
				)
			elif not default_bom:
				frappe.throw(_("Default BOM not found for FG Item {0}").format(new_data["fg_item"]))

		if not new_data.get("fg_item_qty"):
			frappe.throw(_("Finished Good Item {0} Qty can not be zero").format(new_data["fg_item"]))


@frappe.whitelist()
def update_child_qty_rate(
	parent_doctype: str, trans_items: str, parent_doctype_name: str, child_docname: str = "items"
) -> None:
	ChildItemUpdater(parent_doctype, parent_doctype_name, child_docname).update(trans_items)


def set_order_defaults(
	parent_doctype: str,
	parent_doctype_name: str,
	child_doctype: str,
	child_docname: str,
	trans_item: dict,
) -> "frappe.model.document.Document":
	"""Return a new child item populated with item master defaults."""
	from erpnext.accounts.services.taxes import add_taxes_from_tax_template, set_child_tax_template_and_map

	p_doc = frappe.get_doc(parent_doctype, parent_doctype_name)
	child_item = frappe.new_doc(child_doctype, parent_doc=p_doc, parentfield=child_docname)
	item = frappe.get_doc("Item", trans_item.get("item_code"))

	for field in ("item_code", "item_name", "description", "item_group", "weight_per_unit", "weight_uom"):
		child_item.update({field: item.get(field)})

	date_fieldname = "delivery_date" if child_doctype == "Sales Order Item" else "schedule_date"
	child_item.update({date_fieldname: trans_item.get(date_fieldname) or p_doc.get(date_fieldname)})
	child_item.stock_uom = item.stock_uom
	child_item.uom = trans_item.get("uom") or item.stock_uom
	child_item.warehouse = get_item_warehouse_(p_doc, item, overwrite_warehouse=True)
	conversion_factor = flt(get_conversion_factor(item.item_code, child_item.uom).get("conversion_factor"))
	child_item.conversion_factor = flt(trans_item.get("conversion_factor")) or conversion_factor
	child_item.update(get_bin_details(child_item.item_code, child_item.warehouse, p_doc.get("company")))

	if child_doctype in ("Purchase Order Item", "Supplier Quotation Item"):
		child_item.base_rate = 1
		child_item.base_amount = 1

	if child_doctype == "Sales Order Item":
		child_item.warehouse = get_item_warehouse_(p_doc, item, overwrite_warehouse=True)
		if not child_item.warehouse:
			frappe.throw(
				_(
					"Cannot find a default warehouse for item {0}. Please set one in the Item Master or in Stock Settings."
				).format(frappe.bold(item.item_code))
			)

	set_child_tax_template_and_map(item, child_item, p_doc)
	add_taxes_from_tax_template(child_item, p_doc)
	return child_item


def validate_child_on_delete(row, parent, ordered_item=None) -> None:
	"""Raise if a partially transacted child item is being deleted."""
	if parent.doctype == "Sales Order":
		if flt(row.delivered_qty):
			frappe.throw(
				_("Row #{0}: Cannot delete item {1} which has already been delivered").format(
					row.idx, row.item_code
				)
			)
		if flt(row.work_order_qty):
			frappe.throw(
				_("Row #{0}: Cannot delete item {1} which has work order assigned to it.").format(
					row.idx, row.item_code
				)
			)
		if flt(row.ordered_qty):
			frappe.throw(
				_(
					"Row #{0}: Cannot delete item {1} which is already ordered against this Sales Order."
				).format(row.idx, row.item_code)
			)

	if parent.doctype == "Purchase Order" and flt(row.received_qty):
		frappe.throw(
			_("Row #{0}: Cannot delete item {1} which has already been received").format(
				row.idx, row.item_code
			)
		)

	if parent.doctype in ("Purchase Order", "Sales Order") and flt(row.billed_amt):
		frappe.throw(
			_("Row #{0}: Cannot delete item {1} which has already been billed.").format(
				row.idx, row.item_code
			)
		)

	if parent.doctype == "Quotation" and ordered_item and ordered_item.get(row.name):
		frappe.throw(_("Cannot delete an item which has been ordered"))


def update_bin_on_delete(row, doctype: str) -> None:
	"""Update bin quantities after a child item row is deleted."""
	from erpnext.stock.stock_balance import (
		get_indented_qty,
		get_ordered_qty,
		get_reserved_qty,
		update_bin_qty,
	)

	qty_dict = {}

	if doctype == "Sales Order":
		qty_dict["reserved_qty"] = get_reserved_qty(row.item_code, row.warehouse)
	else:
		if row.material_request_item:
			qty_dict["indented_qty"] = get_indented_qty(row.item_code, row.warehouse)
		qty_dict["ordered_qty"] = get_ordered_qty(row.item_code, row.warehouse)

	if row.warehouse:
		update_bin_qty(row.item_code, row.warehouse, qty_dict)


def validate_and_delete_children(parent, data, ordered_item=None) -> bool:
	"""Delete child rows not present in data; return True if any were removed."""
	updated_item_names = [d.get("docname") for d in data]
	deleted_children = [item for item in parent.items if item.name not in updated_item_names]

	for d in deleted_children:
		validate_child_on_delete(d, parent, ordered_item)
		d.cancel()
		d.delete()

	if parent.doctype == "Purchase Order":
		parent.update_ordered_qty_in_so_for_removed_items(deleted_children)

	if parent.doctype not in ("Quotation", "Supplier Quotation"):
		parent.update_prevdoc_status()
		for d in deleted_children:
			update_bin_on_delete(d, parent.doctype)

	return bool(deleted_children)


def get_allow_zero_qty(parent_doctype: str) -> bool:
	if parent_doctype == "Sales Order":
		return frappe.db.get_single_value("Selling Settings", "allow_zero_qty_in_sales_order") or False
	if parent_doctype == "Purchase Order":
		return frappe.db.get_single_value("Buying Settings", "allow_zero_qty_in_purchase_order") or False
	return False


def get_child_item_change_state(parent_doctype: str, child_item, new_data) -> frappe._dict:
	prev_rate, new_rate = flt(child_item.get("rate")), flt(new_data.get("rate"))
	prev_qty, new_qty = flt(child_item.get("qty")), flt(new_data.get("qty"))
	prev_fg_qty, new_fg_qty = flt(child_item.get("fg_item_qty")), flt(new_data.get("fg_item_qty"))
	prev_con_fac = flt(child_item.get("conversion_factor"))
	new_con_fac = flt(new_data.get("conversion_factor"))

	if parent_doctype == "Sales Order":
		prev_date, new_date = child_item.get("delivery_date"), new_data.get("delivery_date")
	elif parent_doctype == "Purchase Order":
		prev_date, new_date = child_item.get("schedule_date"), new_data.get("schedule_date")
	else:
		prev_date, new_date = None, None

	if parent_doctype in ("Quotation", "Supplier Quotation"):
		date_unchanged = False
	else:
		prev_date = getdate(prev_date) if prev_date else None
		new_date = getdate(new_date) if new_date else None
		date_unchanged = prev_date == new_date

	return frappe._dict(
		rate_unchanged=prev_rate == new_rate,
		qty_unchanged=prev_qty == new_qty,
		fg_qty_unchanged=prev_fg_qty == new_fg_qty,
		uom_unchanged=child_item.get("uom") == new_data.get("uom"),
		conversion_factor_unchanged=prev_con_fac == new_con_fac,
		date_unchanged=date_unchanged,
		description_unchanged=child_item.get("description") == new_data.get("description"),
	)


def is_child_item_unchanged(change_state: frappe._dict) -> bool:
	return (
		change_state.rate_unchanged
		and change_state.qty_unchanged
		and change_state.fg_qty_unchanged
		and change_state.conversion_factor_unchanged
		and change_state.uom_unchanged
		and change_state.date_unchanged
		and change_state.description_unchanged
	)


def update_child_item_rate_and_discount(
	parent_doctype: str,
	child_item,
	new_data,
	allow_zero_qty: bool,
	rate_unchanged: bool | None = None,
) -> None:
	rate_precision = child_item.precision("rate") or 2
	qty_precision = child_item.precision("qty") or 2

	if rate_unchanged is None:
		rate_unchanged = flt(child_item.get("rate")) == flt(new_data.get("rate"))

	if not rate_unchanged and not child_item.get("qty") and allow_zero_qty:
		frappe.throw(_("Rate of '{}' items cannot be changed").format(frappe.bold(_("Unit Price"))))

	row_rate = flt(new_data.get("rate"), rate_precision)

	if parent_doctype in ("Purchase Order", "Sales Order"):
		amount_below_billed_amt = flt(child_item.billed_amt, rate_precision) > flt(
			row_rate * flt(new_data.get("qty"), qty_precision), rate_precision
		)
		if amount_below_billed_amt and row_rate > 0.0:
			frappe.throw(
				_(
					"Row #{0}: Cannot set Rate if the billed amount is greater than the amount for Item {1}."
				).format(child_item.idx, child_item.item_code)
			)

	child_item.rate = row_rate

	if parent_doctype not in ("Sales Order", "Purchase Order") or not flt(child_item.price_list_rate):
		return

	if flt(child_item.rate) > flt(child_item.price_list_rate):
		child_item.discount_percentage = 0
		child_item.margin_type = "Amount"
		child_item.margin_rate_or_amount = flt(
			child_item.rate - child_item.price_list_rate,
			child_item.precision("margin_rate_or_amount"),
		)
		child_item.rate_with_margin = child_item.rate
	else:
		child_item.discount_percentage = flt(
			(1 - flt(child_item.rate) / flt(child_item.price_list_rate)) * 100.0,
			child_item.precision("discount_percentage"),
		)
		child_item.discount_amount = flt(child_item.price_list_rate) - flt(child_item.rate)
		child_item.margin_type = ""
		child_item.margin_rate_or_amount = 0
		child_item.rate_with_margin = 0


def update_child_item_uom_and_weight(child_item, new_data) -> None:
	conv_fac_precision = child_item.precision("conversion_factor") or 2

	if new_data.get("conversion_factor"):
		if child_item.stock_uom == child_item.uom:
			child_item.conversion_factor = 1
		else:
			child_item.conversion_factor = flt(new_data.get("conversion_factor"), conv_fac_precision)

	if new_data.get("uom"):
		child_item.uom = new_data.get("uom")
		conversion_factor = flt(
			get_conversion_factor(child_item.item_code, child_item.uom).get("conversion_factor")
		)
		child_item.conversion_factor = (
			flt(new_data.get("conversion_factor"), conv_fac_precision) or conversion_factor
		)

	if child_item.get("weight_per_unit"):
		child_item.total_weight = flt(
			child_item.weight_per_unit * child_item.qty * child_item.conversion_factor,
			child_item.precision("total_weight"),
		)


def check_if_child_table_updated(
	child_table_before_update, child_table_after_update, fields_to_check
) -> bool:
	"""Return True if any accounting-relevant field changed in a child table."""
	fields_to_check = list(fields_to_check) + get_accounting_dimensions() + ["cost_center", "project"]

	for index, item in enumerate(child_table_before_update):
		for field in fields_to_check:
			if child_table_after_update[index].get(field) != item.get(field):
				return True

	return False
