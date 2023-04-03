# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING, Dict, Optional, Union

from typing_extensions import Literal

if TYPE_CHECKING:
	from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import BOMUpdateLog

import frappe
from frappe.model.document import Document


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

	update_log = create_bom_update_log(boms=boms)
	return update_log


@frappe.whitelist()
def enqueue_update_cost() -> "BOMUpdateLog":
	"""Returns a BOM Update Log (that queues a job) for BOM Cost Updation."""
	update_log = create_bom_update_log(update_type="Update Cost")
	return update_log


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
	return frappe.get_doc(
		{
			"doctype": "BOM Update Log",
			"current_bom": current_bom,
			"new_bom": new_bom,
			"update_type": update_type,
		}
	).submit()
