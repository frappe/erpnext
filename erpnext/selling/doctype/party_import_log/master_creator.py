# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Creates master records (Customer Group, Territory, Price List, ...) on demand.

When the user picks "create" for a missing master value in the Resolve step,
this is what does the actual insert. Tree masters (Customer Group, Territory)
support a ``Parent / Child`` notation that creates intermediate nodes too.
"""

import frappe

from erpnext.selling.doctype.party_import_log.dependency_resolver import (
	DependencyResolver,
	split_tree_path,
)
from erpnext.selling.doctype.party_import_log.schema import (
	MASTER_NAME_FIELDS,
	NON_CREATABLE_MASTERS,
	TREE_MASTER_FIELDS,
	TREE_MASTER_ROOTS,
)


class MasterCreator:
	"""Inserts masters flagged as 'create' in the resolution payload."""

	def __init__(
		self,
		resolver: DependencyResolver,
		dependency_fields: dict[str, tuple[str, bool]],
	):
		self.resolver = resolver
		self.is_tree_for = {master_doctype: is_tree for master_doctype, is_tree in dependency_fields.values()}

	def create_all(self) -> dict[str, list[str]]:
		"""Create every master flagged for creation; return {doctype: [created_names]}."""
		created: dict[str, list[str]] = {}
		for master_doctype, by_value in self.resolver.lookup.items():
			if master_doctype in NON_CREATABLE_MASTERS:
				continue
			for value, action in by_value.items():
				if action.get("action") != "create" or frappe.db.exists(master_doctype, value):
					continue
				self._create_one(master_doctype, value)
				created.setdefault(master_doctype, []).append(value)
		return created

	def _create_one(self, master_doctype: str, value: str) -> None:
		try:
			if self.is_tree_for.get(master_doctype):
				self._create_tree(master_doctype, value)
			else:
				self._create_simple(master_doctype, value)
		except Exception as exc:
			frappe.log_error(f"Party Import: master create failed {master_doctype}={value}: {exc}")
			raise

	def _create_simple(self, doctype: str, value: str) -> None:
		name_field = MASTER_NAME_FIELDS.get(doctype, default_name_field(doctype))
		doc = frappe.new_doc(doctype)
		doc.set(name_field, value)
		if doc.meta.get_field("is_group"):
			doc.is_group = 0
		if doctype == "Price List":
			doc.selling = 1
			doc.currency = frappe.defaults.get_global_default("currency") or "INR"
		doc.flags.ignore_permissions = True
		doc.insert()

	def _create_tree(self, doctype: str, value: str) -> None:
		parts = split_tree_path(value)
		if not parts:
			return
		parent_field, name_field = TREE_MASTER_FIELDS.get(doctype, default_tree_fields(doctype))
		current_parent = TREE_MASTER_ROOTS.get(doctype)
		for index, part in enumerate(parts):
			is_leaf = index == len(parts) - 1
			if frappe.db.exists(doctype, part):
				if is_leaf:
					return
				current_parent = part
				continue
			self._insert_tree_node(doctype, part, parent_field, name_field, current_parent, is_leaf)
			current_parent = part

	def _insert_tree_node(
		self,
		doctype: str,
		value: str,
		parent_field: str,
		name_field: str,
		parent: str,
		is_leaf: bool,
	) -> None:
		doc = frappe.new_doc(doctype)
		doc.set(name_field, value)
		doc.set(parent_field, parent)
		doc.is_group = 0 if is_leaf else 1
		doc.flags.ignore_permissions = True
		doc.insert()


def default_name_field(doctype: str) -> str:
	"""Convention for masters not listed in MASTER_NAME_FIELDS."""
	return doctype.lower().replace(" ", "_") + "_name"


def default_tree_fields(doctype: str) -> tuple[str, str]:
	"""Convention for tree masters not listed in TREE_MASTER_FIELDS."""
	slug = doctype.lower().replace(" ", "_")
	return f"parent_{slug}", f"{slug}_name"
