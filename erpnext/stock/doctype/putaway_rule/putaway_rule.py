# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions
from frappe.utils import cint, cstr, floor, flt, nowdate
from pydantic import InstanceOf

from erpnext import _refuse
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import _get_stock_balance


class PutawayRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		capacity: DF.Float
		company: DF.Link
		conversion_factor: DF.Float
		disable: DF.Check
		item_code: DF.Link
		item_name: DF.Data | None
		priority: DF.Int
		stock_capacity: DF.Float
		stock_uom: DF.Link | None
		uom: DF.Link | None
		warehouse: DF.Link
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_rule()
		self.validate_warehouse_and_company()
		self.set_stock_capacity()
		self.validate_capacity()
		self.validate_priority()

	def validate_duplicate_rule(self):
		existing_rule = frappe.db.exists(
			"Putaway Rule", {"item_code": self.item_code, "warehouse": self.warehouse}
		)
		if existing_rule and existing_rule != self.name:
			frappe.throw(
				_("Putaway Rule already exists for Item {0} in Warehouse {1}.").format(
					frappe.bold(self.item_code), frappe.bold(self.warehouse)
				),
				title=_("Duplicate"),
			)

	def validate_priority(self):
		if self.priority < 1:
			frappe.throw(_("Priority cannot be lesser than 1."), title=_("Invalid Priority"))

	def validate_warehouse_and_company(self):
		company, is_group, disabled = frappe.db.get_value(
			"Warehouse", self.warehouse, ["company", "is_group", "disabled"]
		)
		if (is_group or disabled) and not self.disable:
			frappe.throw(
				_("Warehouse {0} must be an enabled warehouse that is not a group.").format(
					frappe.bold(self.warehouse)
				),
				title=_("Invalid Warehouse"),
			)

		if not self.disable and not frappe.get_cached_value("Item", self.item_code, "is_stock_item"):
			frappe.throw(_("Item {0} is not a stock item.").format(frappe.bold(self.item_code)))

		if company != self.company:
			frappe.throw(
				_("Warehouse {0} does not belong to Company {1}.").format(
					frappe.bold(self.warehouse), frappe.bold(self.company)
				),
				title=_("Invalid Warehouse"),
			)

	def validate_capacity(self):
		stock_uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
		balance_qty = _get_stock_balance(self.item_code, self.warehouse, nowdate())

		if flt(self.stock_capacity) < flt(balance_qty):
			frappe.throw(
				_(
					"Warehouse Capacity for Item '{0}' must be greater than the existing stock level of {1} {2}."
				).format(self.item_code, frappe.bold(balance_qty), stock_uom),
				title=_("Insufficient Capacity"),
			)

		if not self.capacity:
			frappe.throw(_("Capacity must be greater than 0"), title=_("Invalid"))

	def set_stock_capacity(self):
		self.stock_uom = frappe.get_cached_value("Item", self.item_code, "stock_uom")
		self.uom = self.uom or self.stock_uom
		self.conversion_factor = get_conversion_factor(self.item_code, self.uom).get("conversion_factor") or 1
		self.stock_capacity = flt(self.conversion_factor) * flt(self.capacity)


@frappe.whitelist()
def get_available_putaway_capacity(rule):
	frappe.has_permission("Putaway Rule", "read", doc=rule, throw=True)

	return _get_available_putaway_capacity(rule)


def _get_available_putaway_capacity(rule):
	stock_capacity, item_code, warehouse = frappe.db.get_value(
		"Putaway Rule", rule, ["stock_capacity", "item_code", "warehouse"]
	)
	balance_qty = _get_stock_balance(item_code, warehouse, nowdate())
	free_space = flt(stock_capacity) - flt(balance_qty)
	return free_space if free_space > 0 else 0


@frappe.whitelist()
def apply_putaway_rule(
	doctype: str,
	items: InstanceOf[list] | str,
	company: str,
	sync: str | bool | None = None,
	purpose: str | None = None,
):
	if doctype not in ("Purchase Receipt", "Stock Entry"):
		_refuse()
	frappe.has_permission(doctype, "write", throw=True)
	allowed_companies = get_allowed_docs_for_doctype(
		get_user_permissions(frappe.session.user).get("Company", []), doctype
	)
	if allowed_companies and company not in allowed_companies:
		_refuse()
	if not frappe.has_permission("Item", "read"):
		return

	return _apply_putaway_rule(doctype, items, company, sync, purpose)


def get_row_conversion_factor(item):
	if item.uom and item.item_code:
		return flt(get_conversion_factor(item.item_code, item.uom).get("conversion_factor")) or 1.0

	return 1.0


def _apply_putaway_rule(
	doctype: str,
	items: InstanceOf[list] | str,
	company: str,
	sync: str | bool | None = None,
	purpose: str | None = None,
):
	"""Applies Putaway Rule on line items.

	items: List of Purchase Receipt/Stock Entry Items, updated in place.
	InstanceOf preserves the caller's list during argument validation.
	company: Company in the Purchase Receipt/Stock Entry
	doctype: Doctype to apply rule on
	purpose: Purpose of Stock Entry
	sync (optional): Sync with client side only for client side calls
	"""
	if isinstance(items, str):
		items = json.loads(items)

	items_not_accomodated, updated_table = [], []
	item_wise_rules = {}

	for item in items:
		if isinstance(item, dict):
			item = frappe._dict(item)

		source_warehouse = item.get("s_warehouse")
		serial_nos = []
		if item.get("serial_no"):
			serial_nos = get_serial_nos(item.get("serial_no"))

		item.conversion_factor = flt(item.conversion_factor) or get_row_conversion_factor(item)
		pending_qty, item_code = flt(item.qty), item.item_code
		pending_stock_qty = pending_qty * item.conversion_factor
		uom_must_be_whole_number = frappe.get_cached_value("UOM", item.uom, "must_be_whole_number")

		if not pending_qty or not item_code:
			updated_table = add_row(
				item,
				pending_qty,
				source_warehouse or item.warehouse,
				updated_table,
				serial_nos=serial_nos,
				keep_rejected=True,
			)
			continue

		if item_code not in item_wise_rules:
			item_wise_rules[item_code] = get_item_putaway_rules(item_code, company)
		at_capacity, rules = select_vacant_rules(item_wise_rules[item_code], source_warehouse)

		if not rules:
			warehouse = (
				(source_warehouse or item.get("warehouse"))
				if not item.get("t_warehouse")
				else item.get("t_warehouse")
			)

			if at_capacity:
				# rules available, but no free space
				items_not_accomodated.append([item_code, pending_qty])
			else:
				updated_table = add_row(
					item, pending_qty, warehouse, updated_table, serial_nos=serial_nos, keep_rejected=True
				)
			continue

		keep_rejected = True
		for rule in rules:
			if pending_stock_qty > 0 and rule.free_space:
				stock_qty_to_allocate = (
					flt(rule.free_space) if pending_stock_qty >= flt(rule.free_space) else pending_stock_qty
				)
				qty_to_allocate = stock_qty_to_allocate / item.conversion_factor

				if uom_must_be_whole_number:
					qty_to_allocate = floor(qty_to_allocate)
					stock_qty_to_allocate = qty_to_allocate * item.conversion_factor

				if not qty_to_allocate:
					continue

				updated_table = add_row(
					item,
					qty_to_allocate,
					rule.warehouse,
					updated_table,
					rule.name,
					serial_nos=serial_nos,
					keep_rejected=keep_rejected,
				)
				keep_rejected = False

				pending_stock_qty -= stock_qty_to_allocate
				pending_qty -= qty_to_allocate
				rule["free_space"] -= stock_qty_to_allocate

				if pending_stock_qty <= 0:
					break

		# if pending qty after applying all rules, add row without warehouse
		if pending_stock_qty > 0:
			items_not_accomodated.append([item.item_code, pending_qty])

	if items_not_accomodated:
		show_unassigned_items_message(items_not_accomodated)

	if updated_table and _items_changed(items, updated_table, doctype):
		items[:] = updated_table
		frappe.msgprint(_("Applied putaway rules."), alert=True)

	if sync and json.loads(sync):  # sync with client side
		return items


def _items_changed(old, new, doctype: str) -> bool:
	"""Check if any items changed by application of putaway rules.

	If not, changing item table can have side effects since `name` items also changes.
	"""
	if len(old) != len(new):
		return True

	old = [frappe._dict(item) if isinstance(item, dict) else item for item in old]

	if doctype == "Stock Entry":
		compare_keys = ("item_code", "t_warehouse", "transfer_qty", "serial_no")
		sort_key = lambda item: (  # noqa
			item.item_code,
			cstr(item.t_warehouse),
			flt(item.transfer_qty),
			cstr(item.serial_no),
		)
	else:
		# purchase receipt / invoice
		compare_keys = ("item_code", "warehouse", "stock_qty", "received_qty", "serial_no")
		sort_key = lambda item: (  # noqa
			item.item_code,
			cstr(item.warehouse),
			flt(item.stock_qty),
			flt(item.received_qty),
			cstr(item.serial_no),
		)

	old_sorted = sorted(old, key=sort_key)
	new_sorted = sorted(new, key=sort_key)

	# Once sorted by all relevant keys both tables should align if they are same.
	for old_item, new_item in zip(old_sorted, new_sorted, strict=False):
		for key in compare_keys:
			if old_item.get(key) != new_item.get(key):
				return True
	return False


def get_ordered_putaway_rules(item_code, company, source_warehouse=None):
	"""Returns an ordered list of putaway rules to apply on an item."""
	return select_vacant_rules(get_item_putaway_rules(item_code, company), source_warehouse)


def get_item_putaway_rules(item_code, company):
	rules = frappe.get_all(
		"Putaway Rule",
		fields=["name", "item_code", "stock_capacity", "priority", "warehouse"],
		filters={"item_code": item_code, "company": company, "disable": 0},
		order_by="priority asc, capacity desc",
	)
	for rule in rules:
		balance_qty = _get_stock_balance(rule.item_code, rule.warehouse, nowdate())
		rule["free_space"] = max(flt(rule.stock_capacity) - flt(balance_qty), 0)

	return rules


def select_vacant_rules(rules, source_warehouse=None):
	rules = [rule for rule in rules if rule.warehouse != source_warehouse]
	if not rules:
		return False, None

	vacant_rules = [rule for rule in rules if rule.free_space > 0]
	if not vacant_rules:
		return True, None

	return False, sorted(vacant_rules, key=lambda rule: (rule.priority, -rule.free_space))


def add_row(item, to_allocate, warehouse, updated_table, rule=None, serial_nos=None, keep_rejected=False):
	new_updated_table_row = copy.deepcopy(item)
	new_updated_table_row.idx = 1 if not updated_table else cint(updated_table[-1].idx) + 1
	new_updated_table_row.name = None
	new_updated_table_row.qty = to_allocate

	if item.doctype == "Stock Entry Detail":
		new_updated_table_row.t_warehouse = warehouse
		new_updated_table_row.transfer_qty = flt(to_allocate) * flt(new_updated_table_row.conversion_factor)
	else:
		new_updated_table_row.stock_qty = flt(to_allocate) * flt(new_updated_table_row.conversion_factor)
		new_updated_table_row.warehouse = warehouse
		if not keep_rejected:
			new_updated_table_row.rejected_qty = 0

		new_updated_table_row.received_qty = flt(to_allocate) + flt(new_updated_table_row.rejected_qty)

	if rule:
		new_updated_table_row.putaway_rule = rule

	if serial_nos:
		new_updated_table_row.serial_no = get_serial_nos_to_allocate(
			serial_nos, flt(to_allocate) * flt(new_updated_table_row.conversion_factor or 1)
		)

	new_updated_table_row.serial_and_batch_bundle = ""

	updated_table.append(new_updated_table_row)
	return updated_table


def show_unassigned_items_message(items_not_accomodated):
	msg = _("The following Items, having Putaway Rules, could not be accomodated:") + "<br><br>"
	formatted_item_rows = ""

	for entry in items_not_accomodated:
		item_link = frappe.utils.get_link_to_form("Item", entry[0])
		formatted_item_rows += f"""
			<td>{item_link}</td>
			<td>{frappe.bold(entry[1])}</td>
		</tr>"""

	msg += """
		<table class="table">
			<thead>
				<td>{}</td>
				<td>{}</td>
			</thead>
			{}
		</table>
	""".format(_("Item"), _("Unassigned Qty"), formatted_item_rows)

	frappe.msgprint(msg, title=_("Insufficient Capacity"), is_minimizable=True, wide=True)


def get_serial_nos_to_allocate(serial_nos, to_allocate):
	if serial_nos:
		allocated_serial_nos = serial_nos[0 : cint(to_allocate)]
		serial_nos[:] = serial_nos[cint(to_allocate) :]  # pop out allocated serial nos and modify list
		return "\n".join(allocated_serial_nos) if allocated_serial_nos else ""
	else:
		return ""
