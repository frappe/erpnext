# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""End-to-end execution of a Party Import: dry-run preview and real run.

The dry-run walks every row to give the user a "what's going to happen"
preview without touching the database. The execute path commits in
batches and publishes realtime progress so the wizard can show a live
progress bar.
"""

import json

import frappe
from frappe import _
from frappe.utils import cstr, now_datetime

from erpnext.selling.doctype.party_import_log.dependency_resolver import (
	DependencyResolver,
	source_for_target,
)
from erpnext.selling.doctype.party_import_log.master_creator import MasterCreator
from erpnext.selling.doctype.party_import_log.party_creator import PartyCreator
from erpnext.selling.doctype.party_import_log.schema import (
	DRY_RUN_ERROR_LIMIT,
	IMPORT_BATCH_SIZE,
	INLINE_EDIT_ERROR_LIMIT,
	dependency_fields_for,
	name_field_for,
)


class ImportRunner:
	"""Shared decision/IO surface for dry-run previews and real imports."""

	def __init__(self, doc):
		self.doc = doc
		self.party_type = doc.party_type
		self.mappings = doc.get_mappings()
		self.resolutions = doc.get_resolutions()
		raw_overrides = getattr(doc, "row_overrides", None)
		self.row_overrides = (
			json.loads(raw_overrides) if isinstance(raw_overrides, str) and raw_overrides else {}
		)
		self.resolver = DependencyResolver(self.resolutions)
		self.dependency_fields = dependency_fields_for(self.party_type)
		self.name_field = name_field_for(self.party_type)
		self.source_for_name = source_for_target(self.mappings, self.name_field)
		self.creator = PartyCreator(self.party_type, self.mappings, self.resolver)

	def dry_run(self, rows: list[dict]) -> dict:
		"""Walk every row, classifying without committing. Returns the review payload."""
		to_create, to_update, errors = 0, 0, []
		for index, row in enumerate(rows, start=2):
			result = self._classify(row, index)
			if result["action"] == "error":
				errors.append({"row": index, "message": result["message"]})
			elif result["action"] == "create":
				to_create += 1
			elif result["action"] == "update":
				to_update += 1
		skipped = len(rows) - to_create - to_update - len(errors)
		editable = len(errors) < INLINE_EDIT_ERROR_LIMIT
		visible_cap = INLINE_EDIT_ERROR_LIMIT if editable else DRY_RUN_ERROR_LIMIT
		return {
			"total_rows": len(rows),
			"to_create": to_create,
			"to_update": to_update,
			"to_skip": skipped,
			"errors": self._enrich_errors(errors[:visible_cap], rows),
			"error_count": len(errors),
			"editable": editable,
			"inline_edit_limit": INLINE_EDIT_ERROR_LIMIT,
			"masters_to_create": self.resolver.masters_to_create(),
		}

	def _enrich_errors(self, errors: list[dict], rows: list[dict]) -> list[dict]:
		"""Attach the effective {target_field: value} map to each error for the inline editor."""
		enriched = []
		for err in errors:
			row_num = err["row"]
			source_row = rows[row_num - 2] if 0 <= row_num - 2 < len(rows) else {}
			values = self._effective_values(source_row, row_num)
			enriched.append({**err, "values": values})
		return enriched

	def _effective_values(self, source_row: dict, row_number: int) -> dict:
		"""What the user sees in the inline editor for one row: mapped value, overridden if set."""
		values: dict = {}
		for source, target in self.mappings.items():
			if not target:
				continue
			values[target] = source_row.get(source, "")
		values.update(self.row_overrides.get(str(row_number), {}))
		return values

	def execute(self, rows: list[dict]) -> None:
		"""Create masters, then commit parties in batches with realtime progress."""
		self._create_masters()
		batch_state = _BatchState(total=len(rows))
		for batch_start in range(0, len(rows), IMPORT_BATCH_SIZE):
			batch = rows[batch_start : batch_start + IMPORT_BATCH_SIZE]
			self._run_batch(batch, batch_start, batch_state)
			self._commit_progress(batch_state)
			self._publish_progress(batch_state)
		self._finalize()

	def _classify(self, row: dict, row_number: int) -> dict:
		party_name = self._row_party_name(row, row_number)
		if not party_name:
			return {"action": "error", "message": _("Missing {0}").format(self.name_field)}
		if self.resolver.should_skip_row(row, self.mappings, self.dependency_fields):
			return {"action": "skip"}
		existing = frappe.db.exists(self.party_type, {self.name_field: party_name})
		return {"action": "update" if existing else "create"}

	def _run_batch(self, batch: list[dict], batch_start: int, state: "_BatchState") -> None:
		for offset, row in enumerate(batch):
			row_number = batch_start + offset + 2
			state.imported += 1
			try:
				outcome = self._process_row(row, row_number)
				state.record(outcome)
			except Exception as exc:
				state.errors_count += 1
				state.errors.append({"row": row_number, "message": cstr(exc)})

	def _process_row(self, row: dict, row_number: int) -> str:
		party_name = self._row_party_name(row, row_number)
		if not party_name:
			raise frappe.ValidationError(_("Missing {0}").format(self.name_field))
		if self.resolver.should_skip_row(row, self.mappings, self.dependency_fields):
			return "skipped"
		existing = frappe.db.exists(self.party_type, {self.name_field: party_name})
		overrides = self.row_overrides.get(str(row_number))
		if existing:
			if self.doc.conflict_policy == "Skip":
				return "skipped"
			self.creator.update(existing, row, self.doc.conflict_policy, overrides=overrides)
			return "updated"
		self.creator.create(row, overrides=overrides)
		return "created"

	def _create_masters(self) -> None:
		creator = MasterCreator(self.resolver, self.dependency_fields)
		created = creator.create_all()
		self.doc.created_masters = json.dumps(created)
		self.doc.save(ignore_permissions=True)
		frappe.db.commit()

	def _row_party_name(self, row: dict, row_number: int) -> str:
		override = self.row_overrides.get(str(row_number), {}).get(self.name_field)
		if override:
			return str(override).strip()
		if not self.source_for_name:
			return ""
		return (row.get(self.source_for_name) or "").strip()

	def _commit_progress(self, state: "_BatchState") -> None:
		self.doc.db_set("imported_rows", state.imported, update_modified=False)
		self.doc.db_set("created_rows", state.created, update_modified=False)
		self.doc.db_set("updated_rows", state.updated, update_modified=False)
		self.doc.db_set("skipped_rows", state.skipped, update_modified=False)
		self.doc.db_set("error_rows", state.errors_count, update_modified=False)
		self.doc.db_set("error_log", json.dumps(state.errors), update_modified=False)
		frappe.db.commit()

	def _publish_progress(self, state: "_BatchState") -> None:
		frappe.publish_realtime(
			"party_import_progress",
			{
				"import_name": self.doc.name,
				"imported": state.imported,
				"total": state.total,
				"created": state.created,
				"updated": state.updated,
				"skipped": state.skipped,
				"errors": state.errors_count,
			},
			user=self.doc.owner,
		)

	def _finalize(self) -> None:
		self.doc.reload()
		self.doc.status = "Completed"
		self.doc.completed_at = now_datetime()
		self.doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.publish_realtime(
			"party_import_complete",
			{"import_name": self.doc.name, "status": "Completed"},
			user=self.doc.owner,
		)


class _BatchState:
	"""Mutable counters threaded through one import run."""

	def __init__(self, total: int):
		self.total = total
		self.imported = 0
		self.created = 0
		self.updated = 0
		self.skipped = 0
		self.errors_count = 0
		self.errors: list[dict] = []

	def record(self, outcome: str) -> None:
		if outcome == "created":
			self.created += 1
		elif outcome == "updated":
			self.updated += 1
		elif outcome == "skipped":
			self.skipped += 1
