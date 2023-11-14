# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING, Dict, Literal, Optional, Union

if TYPE_CHECKING:
	from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import BOMUpdateLog

import frappe
from frappe import _
from frappe.model.document import Document

from ..bom_update_log.bom_update_log import BOMMissingError


class BOMUpdateTool(Document):
	pass


@frappe.whitelist()
def enqueue_replace_bom(
	boms: Optional[Union[Dict, str]] = None, args: Optional[Union[Dict, str]] = None
) -> "BOMUpdateLog":
	"""Returns a BOM Update Log (that queues a job) for BOM Replacement."""
	boms = boms or args
	if isinstance(boms, str):
		boms = json.loads(boms)

	return create_bom_update_log(boms=boms)


@frappe.whitelist()
def enqueue_update_cost() -> "BOMUpdateLog":
	"""Returns a BOM Update Log (that queues a job) for BOM Cost Updation."""
	return create_bom_update_log(update_type="Update Cost")


def auto_update_latest_price_in_all_boms() -> None:
	"""Called via hooks.py."""
	if frappe.db.get_single_value("Manufacturing Settings", "update_bom_costs_automatically"):
		wip_log = frappe.get_all(
			"BOM Update Log",
			{"update_type": "Update Cost", "status": ["in", ["Queued", "In Progress"]]},
			limit_page_length=1,
		)
		if not wip_log:
			create_bom_update_log(update_type="Update Cost")


def create_bom_update_log(
	boms: Optional[Dict[str, str]] = None,
	update_type: Literal["Replace BOM", "Update Cost"] = "Replace BOM",
) -> "BOMUpdateLog":
	"""Creates a BOM Update Log that handles the background job."""

	boms = boms or {}
	current_bom = boms.get("current_bom")
	new_bom = boms.get("new_bom")
	if current_bom:
		current_boms = [current_bom]
	else:
		current_boms = get_old_bom_references(new_bom)
	last_log = None
	for current_bom in current_boms:
		last_log = frappe.get_doc(
			{
				"doctype": "BOM Update Log",
				"current_bom": current_bom,
				"new_bom": new_bom,
				"update_type": update_type,
			}
		).submit()
	if not last_log:
		raise BOMMissingError
	return last_log


@frappe.whitelist()
def get_old_bom_references(new_bom_name):
	"""Return a list of BOM names from BOM Items where the item BOM is not the new BOM"""
	result = []
	if new_bom_name:
		item_code = frappe.db.get_value("BOM", new_bom_name, "item")
		# result only if there is work to do
		data = frappe.db.get_all(
			"BOM Item",
			filters={
				"item_code": item_code,
				"bom_no": ("!=", new_bom_name),
				"parenttype": "BOM",
				"parentfield": "items",
				"docstatus": ("<", 2),
			},
			fields=["name", "parent", "bom_no"],
		)
		missing = [x["parent"] for x in data if not x["bom_no"]]
		tofix = [x["name"] for x in data if not x["bom_no"]]
		result = list(set(x["bom_no"] for x in data if x["bom_no"]))
		if missing:
			title = _("BOM Update Fix")
			msg = _("Fixing empty BOM references found for item {0} in BOMs:<br>{1}").format(
				item_code, missing
			)
			if frappe.local.is_ajax:
				frappe.msgprint(title=title, msg=msg, indicator="red")
			frappe.log_error(title=title, message=msg, reference_doctype="BOM", reference_name=missing[0])
			for name in tofix:
				frappe.db.set_value(
					"BOM Item",
					name,
					{
						"bom_no": result[0] if result else new_bom_name,
						"do_not_explode": 1,
					},
				)
	return result


def update_default_bom_automatically(bom, method):
	"""Automatic default BOM update on bom on_update_after_submit & on_submit hooks"""
	if frappe.db.get_single_value("Manufacturing Settings", "update_default_bom_automatically"):
		item_code = bom.get("item")
		# may not be a default BOM
		default_bom = frappe.db.get_all(
			"BOM", filters={"item": item_code, "is_default": 1, "docstatus": ("<", 2)}, fields=["name"]
		)
		if default_bom:
			new_bom = default_bom[0]["name"]
			try:
				create_bom_update_log(boms={"new_bom": new_bom}, update_type="Replace BOM")
			except BOMMissingError:
				pass
