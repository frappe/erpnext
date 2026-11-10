import json

import frappe
from frappe.utils import cint

# `select` grants added to the shipped DocType JSON in this release. A DocType carrying any Custom
# DocPerm row stops reading the shipped rows, so mirror them -- for those DocTypes only.
GRANTS = {
	"Account": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Master Manager",
		"Quality Manager",
		"Sales Master Manager",
		"Stock Manager",
	],
	"Activity Type": [
		"Accounts User",
		"HR User",
		"Manufacturing User",
	],
	"Asset": [
		"Accounts Manager",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Manager",
		"Purchase User",
		"Stock Manager",
		"Stock User",
		"System Manager",
	],
	"Asset Category": [
		"Item Manager",
	],
	"Asset Maintenance Team": [
		"Quality Manager",
	],
	"Asset Shift Factor": [
		"Quality Manager",
	],
	"BOM": [
		"Maintenance User",
		"Sales Manager",
		"Sales User",
	],
	"Bank": [
		"Accounts Manager",
		"Accounts User",
	],
	"Bank Account": [
		"Purchase Manager",
		"Purchase Master Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Batch": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Master Manager",
		"Quality Manager",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Blanket Order": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
	],
	"Brand": [
		"Website Manager",
	],
	"Company": [
		"Desk User",
	],
	"Cost Center": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Projects Manager",
		"Projects User",
		"Purchase Master Manager",
		"Quality Manager",
		"Sales Master Manager",
		"Stock Manager",
	],
	"Coupon Code": [
		"Maintenance Manager",
		"Maintenance User",
	],
	"Customer": [
		"Delivery Manager",
		"Delivery User",
		"Employee",
		"Fulfillment User",
		"HR Manager",
		"HR User",
		"Maintenance Manager",
		"Maintenance User",
		"Projects Manager",
		"Projects User",
		"Purchase Master Manager",
		"Quality Manager",
		"Support Team",
		"Website Manager",
	],
	"Customer Group": [
		"Item Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Website Manager",
	],
	"Department": [
		"Accounts User",
		"Projects Manager",
		"Projects User",
		"Quality Manager",
	],
	"Driver": [
		"Fulfillment User",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Employee": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Fleet Manager",
		"Manufacturing Manager",
		"Manufacturing User",
		"Projects User",
		"Quality Manager",
		"Sales Master Manager",
		"Stock Manager",
	],
	"Finance Book": [
		"HR Manager",
		"Manufacturing Manager",
		"Quality Manager",
	],
	"Fiscal Year": [
		"Sales Master Manager",
	],
	"Holiday List": [
		"Accounts Manager",
		"Manufacturing User",
		"Projects Manager",
		"Projects User",
		"Sales Manager",
	],
	"Incoterm": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
	],
	"Issue": [
		"Projects User",
	],
	"Issue Priority": [
		"Support Team",
	],
	"Item Tax Template": [
		"Delivery Manager",
		"Delivery User",
		"Item Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Lead": [
		"Support Team",
	],
	"Location": [
		"Quality Manager",
	],
	"Loyalty Program": [
		"Sales Master Manager",
		"Sales User",
	],
	"Manufacturer": [
		"Accounts Manager",
		"Accounts User",
	],
	"Market Segment": [
		"Sales Master Manager",
	],
	"Material Request": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance User",
	],
	"Mode of Payment": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
	],
	"Monthly Distribution": [
		"Sales Master Manager",
	],
	"POS Invoice": [
		"Sales Manager",
		"Sales User",
	],
	"POS Profile": [
		"Sales Manager",
	],
	"Payment Term": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
	],
	"Plant Floor": [
		"Manufacturing User",
	],
	"Price List": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Stock Manager",
		"Website Manager",
	],
	"Product Bundle": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
	],
	"Project": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Manager",
		"Purchase Master Manager",
		"Purchase User",
		"Quality Manager",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
		"Support Team",
	],
	"Project Template": [
		"Projects Manager",
		"Projects User",
	],
	"Purchase Invoice": [
		"Manufacturing Manager",
		"Quality Manager",
		"Stock Manager",
	],
	"Purchase Receipt": [
		"Delivery Manager",
		"Delivery User",
		"Quality Manager",
	],
	"Purchase Taxes and Charges Template": [
		"Accounts Manager",
		"Accounts User",
		"Manufacturing Manager",
		"Stock Manager",
	],
	"Quality Inspection": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase User",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Sales Forecast": [
		"Stock Manager",
	],
	"Sales Order": [
		"Projects Manager",
		"Projects User",
	],
	"Sales Partner": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Stock Manager",
		"Website Manager",
	],
	"Sales Partner Type": [
		"Sales Master Manager",
	],
	"Sales Person": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Stock Manager",
	],
	"Sales Taxes and Charges Template": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Stock Manager",
	],
	"Serial No": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance User",
		"Quality Manager",
	],
	"Serial and Batch Bundle": [
		"Accounts Manager",
		"Accounts User",
		"Maintenance Manager",
		"Maintenance User",
		"Quality Manager",
	],
	"Shipment Parcel Template": [
		"Stock Manager",
	],
	"Shipping Rule": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Purchase Manager",
		"Purchase User",
		"Stock Manager",
	],
	"Supplier": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance User",
		"Quality Manager",
		"Sales Master Manager",
		"Website Manager",
	],
	"Supplier Group": [
		"Sales Manager",
		"Website Manager",
	],
	"Supplier Quotation": [
		"Maintenance Manager",
		"Maintenance User",
	],
	"Task": [
		"Accounts User",
		"Employee",
		"Manufacturing User",
	],
	"Tax Category": [
		"Delivery Manager",
		"Delivery User",
		"Item Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Purchase Manager",
		"Purchase Master Manager",
		"Purchase User",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Tax Withholding Category": [
		"Item Manager",
		"Purchase Manager",
		"Purchase Master Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Tax Withholding Group": [
		"Accounts Manager",
		"Accounts User",
		"Purchase Manager",
		"Purchase Master Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Terms and Conditions": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
	],
	"Territory": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Website Manager",
	],
	"UOM": [
		"Desk User",
	],
	"Vehicle": [
		"Fulfillment User",
		"Stock User",
	],
	"Warehouse": [
		"Delivery Manager",
		"Delivery User",
		"HR Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Quality Manager",
		"Website Manager",
	],
}


# Custom DocPerm defaults `read` and `export` to 1, so every ptype is written explicitly: these
# rows grant `select` and nothing else, exactly like the shipped rows they stand in for.
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

# `read` grants added to the shipped DocType JSON in this release, mirrored for the same reason.
# They apply only where the pair has no Custom DocPerm row; an existing row is left as it is.
READ_GRANTS = {
	# `read`, not `select`: get_bom_items() checks `read`, and the fallback only runs the other way --
	# a `select` row does not satisfy a `read` check.
	"BOM": {
		"Purchase Manager": ("read",),
		"Purchase User": ("read",),
		"Stock Manager": ("read",),
		"Stock User": ("read",),
	},
	"Company": {"Sales Manager": ("read",)},
	"Material Request": {"Manufacturing Manager": ("read", "report")},
}


def grant_map():
	"""(DocType, role) -> the ptypes this release granted, from both tables above."""
	combined = {}
	for doctype, roles in GRANTS.items():
		for role in roles:
			combined.setdefault(doctype, {}).setdefault(role, set()).add("select")

	for doctype, roles in READ_GRANTS.items():
		for role, ptypes in roles.items():
			combined.setdefault(doctype, {}).setdefault(role, set()).update(ptypes)

	return combined


SAVEPOINT = "mirror_select_perms_to_custom_docperm"


def removed_roles(doctype):
	"""Return roles whose rule on `doctype` this site created and then deleted.

	A pair in GRANTS never shipped a DocPerm row, so copy_perms() cannot have produced a
	Custom DocPerm row for it and it was never on screen in Role Permission Manager to be
	removed. The one way it can be absent by choice is that an administrator added the rule
	themselves and later deleted it, and that leaves a trail: hooks.py registers
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


def log_added(doctype, row):
	"""Record an inserted row in Permission Log by hand.

	insert_perm_log() returns early on frappe.flags.in_migrate, so nothing this patch writes
	would otherwise reach the log an administrator reads. Shape matches what that function
	would have written for an insert.
	"""
	after = {field: row.get(field) for field in ("role", "permlevel", "if_owner", "select", *PTYPES)}

	frappe.get_doc(
		{
			"doctype": "Permission Log",
			"owner": frappe.session.user,
			"changed_by": frappe.session.user,
			"reference_type": "Custom DocPerm",
			"reference": row.name,
			"for_doctype": "DocType",
			"for_document": doctype,
			"status": "Added",
			"changes": frappe.as_json({"from": dict.fromkeys(after, ""), "to": after}, indent=0),
		}
	).db_insert()


def execute():
	# Permission Log is the only thing that distinguishes a rule the site deleted from one that never
	# existed. It arrived after v15, so without it this test cannot be evaluated at all.
	if not frappe.db.exists("DocType", "Permission Log"):
		print(
			"mirror_select_perms_to_custom_docperm: Permission Log is not installed on this site, "
			"so a rule that was created and later deleted cannot be told apart from one that never "
			"existed. Skipping rather than re-granting a rule the site may have removed."
		)
		return

	for doctype, roles in grant_map().items():
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

			# leave any existing rule for this role and level as the site configured it
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
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
				log_added(doctype, row)
				added = True
			except Exception:
				# Roll back before logging. A failed statement leaves the transaction
				# unusable on Postgres, so log_error() would fail too and the migration
				# would stop with only part of the rows written.
				frappe.db.rollback(save_point=SAVEPOINT)
				frappe.log_error(
					title="Could not add select permission",
					message=f"{doctype} / {role}\n\n{frappe.get_traceback()}",
				)

		if added:
			frappe.clear_cache(doctype=doctype)
