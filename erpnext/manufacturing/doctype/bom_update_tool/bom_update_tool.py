# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional, Union

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
		update_cost()


def update_cost() -> None:
	"""Updates Cost for all BOMs from bottom to top."""
	bom_list = get_boms_in_bottom_up_order()
	for bom in bom_list:
		bom_doc = frappe.get_cached_doc("BOM", bom)
		bom_doc.calculate_cost(save_updates=True, update_hour_rate=True)
		# bom_doc.update_exploded_items(save=True) #TODO: edit exploded items rate
		bom_doc.db_update()


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


def get_boms_in_bottom_up_order(bom_no: Optional[str] = None) -> List:
	"""
	Eg: Main BOM
	                |- Sub BOM 1
	                                |- Leaf BOM 1
	                |- Sub BOM 2
	                                |- Leaf BOM 2
	Result: [Leaf BOM 1, Leaf BOM 2, Sub BOM 1, Sub BOM 2, Main BOM]
	"""
	leaf_boms = []
	if bom_no:
		leaf_boms.append(bom_no)
	else:
		leaf_boms = _get_leaf_boms()

	child_parent_map = _generate_child_parent_map()
	bom_list = leaf_boms.copy()

	for leaf_bom in leaf_boms:
		parent_list = _get_flat_parent_map(leaf_bom, child_parent_map)

		if not parent_list:
			continue

		bom_list.extend(parent_list)
		bom_list = list(dict.fromkeys(bom_list).keys())  # remove duplicates

	return bom_list


def _generate_child_parent_map():
	bom = frappe.qb.DocType("BOM")
	bom_item = frappe.qb.DocType("BOM Item")

	bom_parents = (
		frappe.qb.from_(bom_item)
		.join(bom)
		.on(bom_item.parent == bom.name)
		.select(bom_item.bom_no, bom_item.parent)
		.where(
			(bom_item.bom_no.isnotnull())
			& (bom_item.bom_no != "")
			& (bom.docstatus == 1)
			& (bom.is_active == 1)
			& (bom_item.parenttype == "BOM")
		)
	).run(as_dict=True)

	child_parent_map = defaultdict(list)
	for bom in bom_parents:
		child_parent_map[bom.bom_no].append(bom.parent)

	return child_parent_map


def _get_flat_parent_map(leaf, child_parent_map):
	"Get ancestors at all levels of a leaf BOM."
	parents_list = []

	def _get_parents(node, parents_list):
		"Returns recursively updated ancestors list."
		first_parents = child_parent_map.get(node)  # immediate parents of node
		if not first_parents:  # top most node
			return parents_list

		parents_list.extend(first_parents)
		parents_list = list(dict.fromkeys(parents_list).keys())  # remove duplicates

		for nth_node in first_parents:
			# recursively find parents
			parents_list = _get_parents(nth_node, parents_list)

		return parents_list

	parents_list = _get_parents(leaf, parents_list)
	return parents_list


def _get_leaf_boms():
	return frappe.db.sql_list(
		"""select name from `tabBOM` bom
		where docstatus=1 and is_active=1
			and not exists(select bom_no from `tabBOM Item`
				where parent=bom.name and ifnull(bom_no, '')!='')"""
	)
