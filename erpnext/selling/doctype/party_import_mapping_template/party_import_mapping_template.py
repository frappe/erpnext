# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Controller for the Party Import Mapping Template DocType.

A Party Import Mapping Template stores a user-defined ``{source_column: target_field}``
mapping so it can be reloaded the next time a file with the same column layout is imported.
The actual save/load/delete logic lives in :mod:`party_import_log` alongside the
rest of the import API surface.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.selling.doctype.party_import_log.schema import PARTY_TYPES

DOCTYPE = "Party Import Mapping Template"


class PartyImportMappingTemplate(Document):
	"""User-owned mapping template for the Party Import wizard."""

	def validate(self) -> None:
		if self.party_type not in PARTY_TYPES:
			frappe.throw(_("Party Type must be Customer or Supplier"))
		_validate_mappings_json(self.mappings)


def _validate_mappings_json(value: str) -> None:
	try:
		parsed = json.loads(value)
	except (TypeError, json.JSONDecodeError):
		frappe.throw(_("Mappings must be valid JSON"))
	if not isinstance(parsed, dict):
		frappe.throw(_("Mappings must be a JSON object"))
