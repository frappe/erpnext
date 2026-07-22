from collections.abc import Iterator

import frappe
from frappe.model.meta import Meta


class DraftLinkFinder:
	"""Finds draft documents of a target DocType that link back to a source document
	through parent-level or child-table Link / Dynamic Link fields."""

	def __init__(self, source_doctype: str, source_name: str, target_doctype: str) -> None:
		self.source_doctype = source_doctype
		self.source_name = source_name
		self.target_doctype = target_doctype

	def find(self) -> list[str]:
		if not frappe.db.exists("DocType", self.target_doctype):
			return []
		if not frappe.has_permission(self.target_doctype):
			return []

		names: set[str] = set()
		for filters in self._link_filters():
			names.update(frappe.get_list(self.target_doctype, filters=filters, pluck="name", limit=0))
		return sorted(names)

	def _link_filters(self) -> Iterator[list]:
		target_meta = frappe.get_meta(self.target_doctype)
		for meta in [target_meta, *self._child_metas(target_meta)]:
			yield from self._link_field_filters(meta)
			yield from self._dynamic_link_field_filters(meta)

	def _child_metas(self, target_meta: Meta) -> list[Meta]:
		return [frappe.get_meta(df.options) for df in target_meta.get_table_fields()]

	def _link_field_filters(self, meta: Meta) -> Iterator[list]:
		for field in meta.get_link_fields():
			if field.options == self.source_doctype:
				yield [self._draft_filter(), [meta.name, field.fieldname, "=", self.source_name]]

	def _dynamic_link_field_filters(self, meta: Meta) -> Iterator[list]:
		for field in meta.get_dynamic_link_fields():
			yield [
				self._draft_filter(),
				[meta.name, field.options, "=", self.source_doctype],
				[meta.name, field.fieldname, "=", self.source_name],
			]

	def _draft_filter(self) -> list:
		return [self.target_doctype, "docstatus", "=", 0]


@frappe.whitelist()
def get_existing_drafts(source_doctype: str, source_name: str, target_doctype: str) -> list[str]:
	"""Draft documents of *target_doctype* created from the given source document."""
	return DraftLinkFinder(source_doctype, source_name, target_doctype).find()
