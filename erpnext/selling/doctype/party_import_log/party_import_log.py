# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Public surface for the Party Import feature.

This module hosts the DocType controller, all whitelisted endpoints the
wizard calls, and the background-job entry point referenced by name from
``enqueue``. Real work lives in sibling modules (``file_reader``,
``column_mapper``, ``dependency_resolver``, ``master_creator``,
``party_creator``, ``import_runner``). Keep this file thin — moving logic
out preserves the wire paths the JS depends on without bloating the
controller file.
"""

import csv
import io
import json
import os

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_manager import get_file_path

from erpnext.selling.doctype.party_import_log.column_mapper import ColumnMapper
from erpnext.selling.doctype.party_import_log.dependency_resolver import DependencyAnalyzer
from erpnext.selling.doctype.party_import_log.file_reader import FileReader
from erpnext.selling.doctype.party_import_log.import_runner import ImportRunner
from erpnext.selling.doctype.party_import_log.samples import samples_for
from erpnext.selling.doctype.party_import_log.schema import (
	MAX_FILE_SIZE_BYTES,
	MAX_ROWS,
	PARTY_TYPES,
	RECENT_ERRORS_LIMIT,
	SAMPLE_ROW_COUNT,
	dependency_fields_for,
	group_field_for,
	name_field_for,
	target_fields_for,
)
from erpnext.selling.doctype.party_import_log.templates import (
	GENERIC,
	SOURCE_FORMATS,
	filename_suffix_for,
	get_template_columns,
	get_template_mappings,
)

DOCTYPE = "Party Import Log"


class PartyImportLog(Document):
	"""Persisted state for one party-import run (one file → one record)."""

	def validate(self):
		if self.party_type not in PARTY_TYPES:
			frappe.throw(_("Party Type must be Customer or Supplier"))
		if self.source_format and self.source_format not in SOURCE_FORMATS:
			frappe.throw(_("Source Format must be one of: {0}").format(", ".join(SOURCE_FORMATS)))

	def get_target_fields(self):
		return target_fields_for(self.party_type)

	def get_dependency_fields(self):
		return dependency_fields_for(self.party_type)

	def get_mappings(self) -> dict:
		return json.loads(self.column_mappings) if self.column_mappings else {}

	def get_resolutions(self) -> dict:
		return json.loads(self.dependency_resolutions) if self.dependency_resolutions else {}

	def get_name_field(self) -> str:
		return name_field_for(self.party_type)

	def get_group_field(self) -> str:
		return group_field_for(self.party_type)


@frappe.whitelist()
def get_party_type_permissions() -> dict:
	"""Return which party types the current user can import.

	Checks the standard Frappe ``import`` permission on Customer / Supplier so
	that this respects any custom role setup without hardcoding role names.
	"""
	return {
		"Customer": bool(frappe.has_permission("Customer", "import")),
		"Supplier": bool(frappe.has_permission("Supplier", "import")),
	}


@frappe.whitelist()
def create_from_file(file_url: str, party_type: str, source_format: str = GENERIC) -> str:
	"""Create a new Party Import Log from an uploaded file."""
	_validate_party_type(party_type)
	if not frappe.has_permission(party_type, "create"):
		frappe.throw(
			_("You don't have permission to create {0} records.").format(party_type),
			frappe.PermissionError,
		)
	doc = frappe.new_doc(DOCTYPE)
	doc.party_type = party_type
	doc.source_format = source_format if source_format in SOURCE_FORMATS else GENERIC
	doc.import_file = file_url
	doc.status = "Mapping"
	doc.insert()
	return doc.name


@frappe.whitelist()
def parse_file(import_name: str) -> dict:
	"""Parse the uploaded file and return columns + sample rows + warnings."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	if not doc.import_file:
		frappe.throw(_("No file attached"))
	_enforce_file_size(doc.import_file)
	warnings: list[str] = []
	rows = FileReader(doc.import_file, warnings).read()
	_enforce_row_count(rows)
	doc.db_set("total_rows", len(rows), update_modified=False)
	return {
		"columns": list(rows[0].keys()),
		"sample_rows": rows[:SAMPLE_ROW_COUNT],
		"total_rows": len(rows),
		"target_fields": doc.get_target_fields(),
		"warnings": warnings,
	}


@frappe.whitelist()
def auto_map_columns(import_name: str) -> dict:
	"""Suggest a target field for each source column using fuzzy matching."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	rows = FileReader(doc.import_file).read()
	if not rows:
		return {}
	template = get_template_mappings(doc.source_format or GENERIC, doc.party_type)
	mapper = ColumnMapper(doc.get_target_fields(), template_synonyms=template)
	return mapper.suggest(list(rows[0].keys()))


@frappe.whitelist()
def set_column_mappings(import_name: str, mappings: str) -> None:
	"""Persist the user's column→field mappings and advance to Resolving."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	doc.column_mappings = json.dumps(_as_dict(mappings))
	doc.status = "Resolving"
	doc.save()


@frappe.whitelist()
def analyze_dependencies(import_name: str) -> dict:
	"""Return distinct dependency values + whether each one already exists."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	rows = FileReader(doc.import_file).read()
	analyzer = DependencyAnalyzer(doc.get_dependency_fields(), doc.get_mappings())
	return analyzer.analyze(rows)


@frappe.whitelist()
def set_dependency_resolutions(import_name: str, resolutions: str) -> None:
	"""Persist the user's per-master decisions and advance to Reviewing."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	doc.dependency_resolutions = json.dumps(_as_dict(resolutions))
	doc.status = "Reviewing"
	doc.save()


@frappe.whitelist()
def dry_run(import_name: str) -> dict:
	"""Validate every row and return the Review-step summary."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	rows = FileReader(doc.import_file).read()
	return ImportRunner(doc).dry_run(rows)


@frappe.whitelist()
def save_row_override(import_name: str, row: int, overrides: str) -> dict:
	"""Persist user edits for one row and re-validate it.

	``overrides`` is a JSON string keyed by target field. Empty values clear the
	override for that field. The endpoint returns the row's new classification
	(``create`` / ``update`` / ``skip`` / ``error``) and the corrected values so
	the wizard can patch its state without a full dry-run.
	"""
	doc = frappe.get_doc(DOCTYPE, import_name)
	row_number = int(row)
	new_overrides = _clean_overrides(_as_dict(overrides))
	_merge_row_override(doc, row_number, new_overrides)
	doc.save()

	runner = ImportRunner(doc)
	source_row = _read_source_row(doc, row_number)
	if source_row is None:
		return {"action": "error", "message": _("Row no longer exists in the source file")}
	result = runner._classify(source_row, row_number)
	values = runner._effective_values(source_row, row_number)
	return {**result, "values": values, "row": row_number}


def _clean_overrides(overrides: dict) -> dict:
	"""Drop empty-string values so the editor can clear an override by leaving the field blank."""
	return {key: value for key, value in overrides.items() if value not in (None, "")}


def _merge_row_override(doc, row_number: int, overrides: dict) -> None:
	all_overrides = json.loads(doc.row_overrides or "{}")
	key = str(row_number)
	if overrides:
		all_overrides[key] = overrides
	else:
		all_overrides.pop(key, None)
	doc.row_overrides = json.dumps(all_overrides)


def _read_source_row(doc, row_number: int) -> dict | None:
	rows = FileReader(doc.import_file).read()
	index = row_number - 2
	if 0 <= index < len(rows):
		return rows[index]
	return None


@frappe.whitelist()
def start_import(import_name: str) -> str:
	"""Reset counters and enqueue the background import job."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	_reset_run_state(doc)
	doc.save()
	enqueue(
		method="erpnext.selling.doctype.party_import_log.party_import_log.run_import",
		queue="long",
		timeout=3600,
		import_name=import_name,
		now=False,
		enqueue_after_commit=True,
	)
	return import_name


@frappe.whitelist()
def get_progress(import_name: str) -> dict:
	"""Snapshot the live progress for the wizard's polling fallback."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	return {
		"status": doc.status,
		"total": doc.total_rows,
		"imported": doc.imported_rows,
		"created": doc.created_rows,
		"updated": doc.updated_rows,
		"skipped": doc.skipped_rows,
		"errors": doc.error_rows,
		"started_at": doc.started_at,
		"completed_at": doc.completed_at,
		"recent_errors": json.loads(doc.error_log or "[]")[-RECENT_ERRORS_LIMIT:],
	}


@frappe.whitelist()
def download_template(party_type: str, with_sample: int = 0, source_format: str = GENERIC):
	"""Stream a CSV template (header row, plus optional sample rows).

	The ``source_format`` knob picks the column shape: ``Generic`` uses the live
	target schema (one column per importable field); a known source system
	(``Tally``, ``QuickBooks``, ``Zoho``, ``HubSpot``, ``Salesforce``) produces
	a CSV with that system's native column headers so a user can fill it in and
	re-upload without renaming columns.
	"""
	_validate_party_type(party_type)
	columns = get_template_columns(source_format, party_type) or [
		(field[0], field[0]) for field in target_fields_for(party_type)
	]
	buffer = io.StringIO()
	writer = csv.writer(buffer)
	writer.writerow([header for header, _ in columns])
	if cint(with_sample):
		for row in samples_for(party_type):
			writer.writerow([row.get(target, "") for _, target in columns])
	format_suffix = filename_suffix_for(source_format)
	sample_suffix = "_sample" if cint(with_sample) else ""
	frappe.response["filename"] = f"{party_type.lower()}_import_template{format_suffix}{sample_suffix}.csv"
	frappe.response["filecontent"] = buffer.getvalue()
	frappe.response["type"] = "binary"


def run_import(import_name: str) -> None:
	"""Background job entry point — referenced by name from ``enqueue``."""
	doc = frappe.get_doc(DOCTYPE, import_name)
	try:
		rows = FileReader(doc.import_file).read()
		ImportRunner(doc).execute(rows)
	except Exception as exc:
		_mark_failed(doc, exc)
		raise


_MAPPING_TEMPLATE_DOCTYPE = "Party Import Mapping Template"


@frappe.whitelist()
def save_mapping_template(template_name: str, party_type: str, mappings: str) -> str:
	"""Create or replace the current user's mapping template with the given name and party type.

	Returns the ``name`` (primary key) of the saved record so the wizard can
	reference it directly for subsequent load/delete calls.
	"""
	_validate_party_type(party_type)
	mappings_json = json.dumps(_as_dict(mappings))
	existing = frappe.db.get_value(
		_MAPPING_TEMPLATE_DOCTYPE,
		{"template_name": template_name, "party_type": party_type, "owner": frappe.session.user},
		"name",
	)
	if existing:
		frappe.db.set_value(
			_MAPPING_TEMPLATE_DOCTYPE,
			existing,
			"mappings",
			mappings_json,
			update_modified=True,
		)
		return existing
	doc = frappe.new_doc(_MAPPING_TEMPLATE_DOCTYPE)
	doc.template_name = template_name
	doc.party_type = party_type
	doc.mappings = mappings_json
	doc.insert(ignore_permissions=False)
	return doc.name


@frappe.whitelist()
def list_mapping_templates(party_type: str) -> list[dict]:
	"""Return all mapping templates the current user owns for the given party type."""
	_validate_party_type(party_type)
	return frappe.get_all(
		_MAPPING_TEMPLATE_DOCTYPE,
		filters={"party_type": party_type, "owner": frappe.session.user},
		fields=["name", "template_name"],
		order_by="template_name asc",
	)


@frappe.whitelist()
def load_mapping_template(name: str) -> dict:
	"""Return the ``{source_column: target_field}`` dict for a saved template."""
	doc = frappe.get_doc(_MAPPING_TEMPLATE_DOCTYPE, name)
	return json.loads(doc.mappings)


@frappe.whitelist()
def delete_mapping_template(name: str) -> None:
	"""Delete a saved mapping template owned by the current user."""
	frappe.delete_doc(_MAPPING_TEMPLATE_DOCTYPE, name, ignore_permissions=False)


def delete_old_draft_imports() -> None:
	"""Scheduled task: delete Draft Party Import Logs older than 90 days."""
	cutoff = frappe.utils.add_days(frappe.utils.today(), -90)
	old_drafts = frappe.get_all(
		DOCTYPE,
		filters={"status": "Draft", "creation": ["<", cutoff]},
		pluck="name",
	)
	for name in old_drafts:
		frappe.delete_doc(DOCTYPE, name, ignore_permissions=True)


def _validate_party_type(party_type: str) -> None:
	if party_type not in PARTY_TYPES:
		frappe.throw(_("Invalid party type"))


def _enforce_file_size(file_url: str) -> None:
	file_path = get_file_path(file_url)
	if os.path.exists(file_path) and os.path.getsize(file_path) > MAX_FILE_SIZE_BYTES:
		size_mb = int(MAX_FILE_SIZE_BYTES / (1024 * 1024))
		frappe.throw(_("File is too large. Maximum size is {0} MB.").format(size_mb))


def _enforce_row_count(rows: list[dict]) -> None:
	if not rows:
		frappe.throw(_("File is empty"))
	if len(rows) > MAX_ROWS:
		frappe.throw(
			_("File has {0:,} rows. Maximum is {1:,} rows. Split the file and import in batches.").format(
				len(rows), MAX_ROWS
			)
		)


def _as_dict(value) -> dict:
	return json.loads(value) if isinstance(value, str) else value


def _reset_run_state(doc) -> None:
	doc.status = "Importing"
	doc.started_at = now_datetime()
	doc.imported_rows = 0
	doc.created_rows = 0
	doc.updated_rows = 0
	doc.skipped_rows = 0
	doc.error_rows = 0
	doc.error_log = "[]"
	doc.created_masters = "{}"


def _mark_failed(doc, exc: Exception) -> None:
	"""Persist failure state via direct DB writes.

	Uses ``frappe.db.set_value`` instead of ``doc.save()`` to bypass the document
	lifecycle (validate, before_save, notifications) — a broken hook anywhere in
	that chain would otherwise mask the original exception and leave the import
	stuck in an inconsistent state.
	"""
	try:
		existing = frappe.db.get_value(DOCTYPE, doc.name, "error_log") or "[]"
		errors = json.loads(existing)
		errors.append({"row": None, "message": str(exc)})
		frappe.db.set_value(
			DOCTYPE,
			doc.name,
			{"status": "Failed", "error_log": json.dumps(errors)},
			update_modified=False,
		)
		frappe.db.commit()
	except Exception:
		frappe.log_error(title=f"Party Import {doc.name}: failed to persist failure state")
