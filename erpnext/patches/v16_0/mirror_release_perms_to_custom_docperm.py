import json

import frappe
from frappe.utils import cint

# Permission rows added to shipped DocType JSON in this release: `read` where the role reads the
# record's contents, `select` where it only needs the link picker on a master.
#
# A DocType carrying any Custom DocPerm row stops reading the shipped rows at all -- get_valid_perms()
# keeps a shipped DocPerm row only while its parent has no Custom DocPerm row -- so on a site whose
# permissions were customised the new grants never take effect. Mirror them, for those sites only.
#
# Sites that have not customised this DocType are deliberately left alone: they read the shipped JSON
# and already have these rows, and writing Custom DocPerm rows for them would permanently detach the
# DocType from every future permission change.
GRANTS = {
	"Payment Terms Template": {
		"Maintenance Manager": ("read",),
		"Maintenance User": ("read",),
		"Purchase Manager": ("read",),
		"Purchase User": ("read",),
		"Sales Manager": ("read",),
		"Sales User": ("read",),
		# `select`, not `read`: these three write a doctype that links to a terms template, so
		# they need the picker, but they never call get_payment_terms -- its only JS caller is
		# the payment schedule handler on the transaction forms.
		"HR Manager": ("select",),
		"Purchase Master Manager": ("select",),
		"Sales Master Manager": ("select",),
	},
	# `read`, not `select`: the serial/batch selector reads the bundle's entry columns, and a
	# select grant permits the name alone -- it would hand these roles a row of empty fields.
	"Serial and Batch Bundle": {
		"Accounts Manager": ("read",),
		"Accounts User": ("read",),
		"Maintenance Manager": ("read",),
		"Maintenance User": ("read",),
		"Quality Manager": ("read",),
	},
}

# Custom DocPerm defaults `read` and `export` to 1, so every ptype is written explicitly: these rows
# grant exactly what the shipped rows they stand in for grant, and nothing else.
PTYPES = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)

SAVEPOINT = "mirror_release_perms_to_custom_docperm"


def removed_roles(doctype):
	"""Return roles whose rule on `doctype` this site created and then deleted.

	A pair in GRANTS shipped no DocPerm row before this release, so copy_perms() cannot have
	produced a Custom DocPerm row for it. It can therefore be absent only because nobody ever
	added it, or because somebody added it and deleted it again -- including a row this patch
	itself wrote on an earlier run, which a later re-run must not put back. Either deletion
	leaves a trail: hooks.py registers
	make_perm_log on after_delete for every DocType, Custom DocPerm opts in through
	get_permission_log_options(), and permission_log.py writes status="Removed" when the
	document is neither being saved nor inserted. Nothing purges those rows -- Permission Log
	implements no clear_old_logs, so Log Settings cannot register it.

	The parent is carried in `for_document`; the role is inside the `changes` JSON, because
	`parent` is a child-table field and as_dict() strips it there.
	"""
	roles = set()

	for changes in frappe.get_all(
		"Permission Log",
		filters={
			"for_doctype": "DocType",
			"for_document": doctype,
			"reference_type": "Custom DocPerm",
			"status": "Removed",
		},
		pluck="changes",
	):
		try:
			before = (json.loads(changes) or {}).get("from") or {}
		except (TypeError, ValueError):
			# an unreadable entry names no role, so it cannot be matched -- leave it to the row check
			continue

		# an absent permlevel reads as 0, which skips the insert: the conservative direction
		if not cint(before.get("permlevel")):
			role = before.get("role")
			if role:
				roles.add(role)

	return roles


def execute():
	# Permission Log is the only thing that distinguishes a rule the site deleted from one that never
	# existed. Without it that test cannot be evaluated at all, and re-granting a rule an
	# administrator revoked by hand is worse than leaving the gap.
	if not frappe.db.exists("DocType", "Permission Log"):
		print(
			"mirror_release_perms_to_custom_docperm: Permission Log is not installed on this site, "
			"so a rule that was created and later deleted cannot be told apart from one that never "
			"existed. Skipping rather than re-granting a rule the site may have removed."
		)
		return

	for doctype, roles in GRANTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		# only DocTypes already carrying Custom DocPerm rows
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue

		removed = removed_roles(doctype)
		added = False

		for role, ptypes in roles.items():
			if not frappe.db.exists("Role", role):
				continue

			# An existing rule is widened toward what the release ships, never narrowed. Skipping
			# it instead assumes the row records the SITE's decision, and that is false for a row
			# another mirror patch wrote: this patch cannot tell one from the other. A site
			# mirrored by an earlier release already holds `select` here, and leaving it alone
			# means the read grant this release ships never arrives. Widening only toward the
			# release needs no such distinction -- it never removes anything a site chose.
			existing = frappe.db.get_value(
				"Custom DocPerm",
				{"parent": doctype, "role": role, "permlevel": 0},
				# `select` is not in PTYPES -- the insert path sets it separately -- so name it here
				# or a ("select",) grant reads as missing on every run.
				["name", "select", *PTYPES],
				as_dict=True,
			)
			if existing:
				missing = [ptype for ptype in ptypes if not existing.get(ptype)]
				if not missing:
					continue

				try:
					frappe.db.savepoint(SAVEPOINT)
					row = frappe.get_doc("Custom DocPerm", existing.name)
					for ptype in missing:
						row.set(ptype, 1)
					row.save(ignore_permissions=True)
					added = True
					print(f"{doctype} / {role}: widened to {', '.join(missing)}")
				except Exception:
					frappe.db.rollback(save_point=SAVEPOINT)
					frappe.log_error(
						title="Could not widen permission",
						message=f"{doctype} / {role}\n\n{frappe.get_traceback()}",
					)
				continue

			# the site held this rule and deleted it again: that is a decision, not a gap
			if role in removed:
				print(f"{doctype} / {role}: skipped, this site removed the rule")
				continue

			try:
				frappe.db.savepoint(SAVEPOINT)

				row = frappe.new_doc("Custom DocPerm")
				row.update(
					{
						"parent": doctype,
						"parenttype": "DocType",
						"parentfield": "permissions",
						"role": role,
						"permlevel": 0,
						"if_owner": 0,
						"select": 1 if "select" in ptypes else 0,
					}
				)
				for ptype in PTYPES:
					row.set(ptype, 1 if ptype in ptypes else 0)

				row.insert(ignore_permissions=True)
				added = True
			except Exception:
				# Roll back before logging. A failed statement leaves the transaction unusable on
				# Postgres, so log_error() would fail too and the migration would stop with only
				# part of the rows written.
				frappe.db.rollback(save_point=SAVEPOINT)
				frappe.log_error(
					title="Could not add read permission",
					message=f"{doctype} / {role}\n\n{frappe.get_traceback()}",
				)

		if added:
			frappe.clear_cache(doctype=doctype)
