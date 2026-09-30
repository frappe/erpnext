import frappe
from frappe import _

STANDARD_TRANSACTION_ROLES = [
	"Sales User",
	"Sales Manager",
	"Purchase User",
	"Purchase Manager",
	"Stock User",
	"Stock Manager",
	"Accounts User",
	"Accounts Manager",
]


def execute():
	"""Seed SMS Settings.allowed_roles with ERPNext's standard transaction roles."""
	frappe.reload_doctype("SMS Settings")

	if not frappe.get_meta("SMS Settings").has_field("allowed_roles"):
		frappe.throw(
			_(
				"SMS Settings.allowed_roles not found. Update the Frappe Framework app to a "
				"version that includes this field, then re-run bench migrate."
			)
		)

	sms_settings = frappe.get_single("SMS Settings")
	existing_roles = {d.role for d in sms_settings.get("allowed_roles")}

	added = False
	for role in STANDARD_TRANSACTION_ROLES:
		if role not in existing_roles and frappe.db.exists("Role", role):
			sms_settings.append("allowed_roles", {"role": role})
			added = True

	if added:
		sms_settings.flags.ignore_mandatory = True
		sms_settings.save()
