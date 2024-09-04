from typing import Any, ClassVar

import frappe
from frappe import _
from frappe.model.document import Document


class ItemCastUpdates:
	"""
	A mixin class for item doctypes that need to cast updates to other related doctypes.

	This class provides a framework for fetching updates from one doctype and applying them to another.
	It defines methods for casting updates onto target doctypes and receiving updates from source doctypes.

	To use this class:
	1. Inherit it in your item doctype class.
	2. Implement the _cast_update_from_<source_doctype> method to define how updates are applied.

	Examples:
	 class SalesOrderItem(Document, ItemCastUpdates):
	         def _cast_update_from_sales_invoice_item(self, item: Document) -> dict[str, Any]:
	                 return {
	                        "billed_amt": item.amount,
	                 }
	"""

	# Class dictionary to map source doctype to target doctype field
	ITEM_CAST_UPDATES_DOCTYPE_FIELD_MAP: ClassVar[dict[str, str]] = {}

	def cast_updates_onto(self, target_doctype: str) -> dict[str, Any]:
		link_field: str | None = self.ITEM_CAST_UPDATES_DOCTYPE_FIELD_MAP.get(target_doctype)

		if not link_field:
			frappe.throw(f"Mapping not found for {self.doctype} to {target_doctype}")

		target_item: Document = frappe.get_doc(target_doctype, self.get(link_field))
		assert isinstance(target_item, ItemCastUpdates), f"{target_item} must inherit ItemCastUpdates"
		return target_item.cast_updates_from(self)

	def cast_updates_from(self, item: Document) -> dict[str, Any]:
		method_name: str = f"_cast_update_from_{frappe.scrub(item.doctype)}"
		if hasattr(self, method_name):
			return getattr(self, method_name)(item)
		else:
			frappe.throw(f"Method {method_name} not implemented for {self.doctype}")


class CastUpdates:
	"""
	A class for managing updates across multiple items in a document.

	This class is designed to work with documents that contain multiple items,
	each of which may need to cast updates onto a target doctype. It aggregates
	updates from all items and performs a unified database update for efficiency.

	Usage:
	1. Inherit this class in your main document class.
	2. Ensure that the items in your document inherit from ItemCastUpdates.
	3. Call the cast_updates_onto method with the target doctype when you need to propagate updates.

	Attributes:
	        None

	Methods:
	        cast_updates_onto(target_doctype): Casts updates from all items onto the specified target doctype.
	"""

	def cast_updates_onto(self, target_doctype: str) -> None:
		"""
		Casts updates from all items onto the specified target doctype.

		This method iterates through all items in the document, collects their updates,
		and performs a unified database update. It also updates the modified timestamp
		for all affected documents in the target doctype.

		Args:
		        target_doctype (str): The name of the target doctype to receive updates.

		Returns:
		        None
		"""
		updates: dict[str, dict[str, Any]] = {}
		for item in self.get("items", []):
			assert isinstance(item, ItemCastUpdates), f"{item} must inherit ItemCastUpdates"
			item_updates: dict[str, Any] = item.cast_updates_onto(target_doctype)
			updates.setdefault(item.get(item.ITEM_CAST_UPDATES_DOCTYPE_FIELD_MAP[target_doctype]), {}).update(
				item_updates
			)

		if not updates:
			return

		# Perform a unified update to the database
		for name, data in updates.items():
			frappe.db.set_value(target_doctype, name, data, update_modified=False)

		# Update the status and modified timestamp for the entire document
		for name in updates.keys():
			doc = frappe.get_doc(target_doctype, name)
			if hasattr(doc, "get_status"):
				status = doc.get_status()
			if doc.docstatus.is_submitted() and doc.status != status["status"]:
				doc.add_comment("Label", _(status["status"]), comment_by=self.name)
			doc.db_set(
				{"modified": frappe.utils.now(), "modified_by": self.name, **status},
				update_modified=False,
				notify=True,
			)
