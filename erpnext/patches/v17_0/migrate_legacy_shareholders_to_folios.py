# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Move legacy Shareholder identity and folio data into the Accounts model.

	The patch deliberately does not infer tax IDs, Share Class categories or
	transaction face values. Values that cannot be mapped safely are reported for
	manual review instead of being fabricated.
	"""
	if not frappe.db.exists("DocType", "Share Folio"):
		return
	if not frappe.db.table_exists("Shareholding Legacy Staging", cached=False):
		return

	legacy_shareholders = get_legacy_shareholders()
	issues = []
	for shareholder in legacy_shareholders:
		migrate_shareholder_identity(shareholder)
		if shareholder.is_company:
			# The old Share Transfer created this internal balancing record; it is
			# not a real member of the company's share register.
			continue
		migrate_shareholder_folio(shareholder, issues)

	legacy_share_types = (
		frappe.get_all("Share Type", pluck="name") if frappe.db.exists("DocType", "Share Type") else []
	)
	if legacy_share_types:
		issues.append(
			"Share Types require manual Ordinary/Preference classification before migration: "
			+ ", ".join(legacy_share_types)
		)

	if issues:
		message = "\n".join(f"- {issue}" for issue in issues)
		frappe.log_error(message=message, title="Shareholding Migration Review Required")
		print("Shareholding migration completed with items requiring review:\n" + message)


def get_legacy_shareholders():
	return frappe.db.sql(
		"""
			select s.name, l.title, l.folio_no, l.company, l.is_company,
				s.legal_name, s.shareholder_type
			from `tabShareholding Legacy Staging` l
			inner join `tabShareholder` s on s.name = l.name
			where l.company is not null and l.company != ''
		""",
		as_dict=True,
	)


def migrate_shareholder_identity(shareholder):
	values = {}
	if not shareholder.legal_name:
		values["legal_name"] = shareholder.title or shareholder.name
	if not shareholder.shareholder_type:
		values["shareholder_type"] = "Organization" if shareholder.is_company else "Individual"
	if values:
		frappe.db.set_value("Shareholder", shareholder.name, values, update_modified=False)


def migrate_shareholder_folio(shareholder, issues):
	existing_folio = frappe.db.get_value(
		"Share Folio",
		{"company": shareholder.company, "shareholder": shareholder.name, "is_treasury": 0},
		"name",
	)
	if existing_folio:
		return

	folio_number = shareholder.folio_no or None
	if folio_number and frappe.db.exists(
		"Share Folio", {"company": shareholder.company, "folio_number": folio_number}
	):
		issues.append(
			f"Shareholder {shareholder.name}: folio number {folio_number} already exists in {shareholder.company}"
		)
		return

	folio = frappe.get_doc(
		{
			"doctype": "Share Folio",
			"company": shareholder.company,
			"shareholder": shareholder.name,
			"folio_number": folio_number,
			"is_treasury": 0,
		}
	)
	folio.insert(ignore_permissions=True)

	if not shareholder.folio_no:
		issues.append(
			f"Shareholder {shareholder.name}: no legacy folio number was available; generated {folio.folio_number}"
		)
