# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import BOMUpdateLog

import frappe
from frappe import _
from pypika.terms import ExistsCriterion


def replace_bom(boms: dict, log_name: str) -> None:
	"Replace current BOM with new BOM in parent BOMs."

	current_bom = boms.get("current_bom")
	new_bom = boms.get("new_bom")

	update_new_bom_in_bom_items(current_bom, new_bom)

	frappe.cache().delete_key("bom_children")
	parent_boms = sort_children_first(get_ancestor_boms(new_bom))

	for bom in parent_boms:
		bom_obj = frappe.get_doc("BOM", bom)
		# this is only used for versioning and we do not want
		# to make separate db calls by using load_doc_before_save
		# which proves to be expensive while doing bulk replace
		bom_obj._doc_before_save = copy.deepcopy(bom_obj)
		bom_obj.update_exploded_items()
		bom_obj.calculate_cost(save_updates=True)
		bom_obj.db_update()
		bom_obj.flags.updater_reference = {
			"doctype": "BOM Update Log",
			"docname": log_name,
			"label": _("via BOM Update Tool"),
		}
		bom_obj.save_version()


def update_cost_in_level(doc: "BOMUpdateLog", bom_list: list[str], batch_name: int | str) -> None:
	"Updates Cost for BOMs within a given level. Runs via background jobs."

	try:
		status = frappe.db.get_value("BOM Update Log", doc.name, "status")
		if status == "Failed":
			return

		update_cost_in_boms(bom_list=bom_list)  # main updation logic

		bom_batch = frappe.qb.DocType("BOM Update Batch")
		(
			frappe.qb.update(bom_batch)
			.set(bom_batch.boms_updated, json.dumps(bom_list))
			.set(bom_batch.status, "Completed")
			.where(bom_batch.name == batch_name)
		).run()
	except Exception:
		handle_exception(doc)
	finally:
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep


def get_ancestor_boms(new_bom: str) -> list:
	"""Return every ancestor BOM of `new_bom` (BOMs that consume it, transitively) in one recursive
	CTE built with frappe.qb -- portable across postgres and mariadb 10.2+. `UNION` makes it
	cycle-safe (it stops once no new BOM is reached); a BOM that is its own ancestor is rejected."""
	links = get_bom_links_query().as_("bom_links")
	tree = frappe.qb.Table("ancestor_boms")

	seed = frappe.qb.from_(links).select(links.parent.as_("bom")).where(links.bom_no == new_bom)
	recursion = frappe.qb.from_(links).join(tree).on(links.bom_no == tree.bom).select(links.parent)
	ancestors = (
		frappe.qb.with_(seed + recursion, "ancestor_boms", recursive=True).from_(tree).select(tree.bom)
	).run(pluck=True)

	if new_bom in ancestors:
		frappe.throw(_("BOM recursion: {0} cannot be an ancestor of itself").format(new_bom))

	return ancestors


def get_bom_links_query():
	bom_item = frappe.qb.DocType("BOM Item")
	bom_operation = frappe.qb.DocType("BOM Operation")

	return (
		frappe.qb.from_(bom_item)
		.select(bom_item.parent, bom_item.bom_no)
		.where((bom_item.docstatus < 2) & (bom_item.parenttype == "BOM"))
	) + (
		frappe.qb.from_(bom_operation)
		.select(bom_operation.parent, bom_operation.bom_no)
		.where((bom_operation.docstatus < 2) & (bom_operation.parenttype == "BOM"))
	)


def update_new_bom_in_bom_items(current_bom: str, new_bom: str) -> None:
	for doctype in ("BOM Item", "BOM Operation"):
		table = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(table)
			.set(table.bom_no, new_bom)
			.where((table.bom_no == current_bom) & (table.docstatus < 2) & (table.parenttype == "BOM"))
		).run()


def sort_children_first(boms: list[str]) -> list[str]:
	if len(boms) < 2:
		return boms

	bom_links = get_bom_links_query().as_("bom_links")
	links = (
		frappe.qb.from_(bom_links)
		.select(bom_links.parent, bom_links.bom_no)
		.where(bom_links.parent.isin(boms) & bom_links.bom_no.isin(boms))
	).run(as_dict=True)

	pending_children = defaultdict(set)
	parents_of = defaultdict(set)
	for link in links:
		pending_children[link.parent].add(link.bom_no)
		parents_of[link.bom_no].add(link.parent)

	ordered = []
	ready = [bom for bom in boms if not pending_children[bom]]
	while ready:
		bom = ready.pop()
		ordered.append(bom)
		for parent in parents_of[bom]:
			pending_children[parent].discard(bom)
			if not pending_children[parent]:
				ready.append(parent)

	return ordered


def update_cost_in_boms(bom_list: list[str]) -> None:
	"Updates cost in given BOMs. Returns current and total updated BOMs."

	for index, bom in enumerate(bom_list):
		bom_doc = frappe.get_doc("BOM", bom, for_update=True)
		bom_doc.calculate_cost(save_updates=True, update_hour_rate=True)
		bom_doc.db_update()

		if (index % 50 == 0) and not frappe.in_test:
			frappe.db.commit()  # nosemgrep


def get_next_higher_level_boms(child_boms: list[str], processed_boms: dict[str, bool]) -> list[str]:
	"Generate immediate higher level dependants with no unresolved dependencies (children)."

	def _all_children_are_processed(parent_bom):
		child_boms = dependency_map.get(parent_bom)
		return all(processed_boms.get(bom) for bom in child_boms)

	dependants_map, dependency_map = _generate_dependence_map()

	dependants = []
	for bom in child_boms:
		# generate list of immediate dependants
		parents = dependants_map.get(bom) or []
		dependants.extend(parents)

	dependants = set(dependants)  # remove duplicates
	resolved_dependants = set()

	# consider only if children are all resolved
	for parent_bom in dependants:
		if _all_children_are_processed(parent_bom):
			resolved_dependants.add(parent_bom)

	return list(resolved_dependants)


def get_leaf_boms() -> list[str]:
	"Get BOMs that have no dependencies."

	bom = frappe.qb.DocType("BOM")
	bom_item = frappe.qb.DocType("BOM Item")
	child_bom = frappe.qb.DocType("BOM").as_("child_bom")

	active_children = (
		frappe.qb.from_(bom_item)
		.join(child_bom)
		.on(child_bom.name == bom_item.bom_no)
		.select(bom_item.name)
		.where(
			(bom_item.parent == bom.name)
			& (bom_item.parenttype == "BOM")
			& (child_bom.docstatus == 1)
			& (child_bom.is_active == 1)
		)
	)

	return (
		frappe.qb.from_(bom)
		.select(bom.name)
		.where((bom.docstatus == 1) & (bom.is_active == 1) & ExistsCriterion(active_children).negate())
	).run(pluck=True)


def _generate_dependence_map() -> defaultdict:
	"""
	Generate maps such as: { BOM-1: [Dependant-BOM-1, Dependant-BOM-2, ..] }.
	Here BOM-1 is the leaf/lower level node/dependency.
	The list contains one level higher nodes/dependants that depend on BOM-1.

	Generate and return the reverse as well.
	"""

	bom = frappe.qb.DocType("BOM")
	bom_item = frappe.qb.DocType("BOM Item")
	child_bom = frappe.qb.DocType("BOM").as_("child_bom")

	bom_items = (
		frappe.qb.from_(bom_item)
		.join(bom)
		.on(bom_item.parent == bom.name)
		.join(child_bom)
		.on(child_bom.name == bom_item.bom_no)
		.select(bom_item.bom_no, bom_item.parent)
		.where(
			(bom.docstatus == 1)
			& (bom.is_active == 1)
			& (child_bom.docstatus == 1)
			& (child_bom.is_active == 1)
			& (bom_item.parenttype == "BOM")
		)
	).run(as_dict=True)

	child_parent_map = defaultdict(list)
	parent_child_map = defaultdict(list)
	for row in bom_items:
		child_parent_map[row.bom_no].append(row.parent)
		parent_child_map[row.parent].append(row.bom_no)

	return child_parent_map, parent_child_map


def set_values_in_log(log_name: str, values: dict[str, Any], commit: bool = False) -> None:
	"Update BOM Update Log record."

	if not values:
		return

	bom_update_log = frappe.qb.DocType("BOM Update Log")
	query = frappe.qb.update(bom_update_log).where(bom_update_log.name == log_name)

	for key, value in values.items():
		query = query.set(key, value)
	query.run()

	if commit and not frappe.in_test:
		frappe.db.commit()  # nosemgrep


def handle_exception(doc: "BOMUpdateLog") -> None:
	"Rolls back and fails BOM Update Log."

	frappe.db.rollback()
	error_log = doc.log_error("BOM Update Tool Error")
	set_values_in_log(doc.name, {"status": "Failed", "error_log": error_log.name})
