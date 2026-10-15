import frappe
from frappe.permissions import get_doctypes_with_custom_docperms
from frappe.utils import cint

from erpnext.patches.v16_0.mirror_release_perms_to_custom_docperm import mirror_rules
from erpnext.patches.v16_0.remove_all_role_from_payment_terms_template import remove_rule
from erpnext.setup.install import get_role_rules

DOCTYPE = "Voice Call Settings"
DESK_USER_PTYPES = ("read", "write", "create", "report", "export", "print", "email")


def execute():
	"""Keep each user's Voice Call Settings to that user and move customised sites to `Desk User`."""
	remove_shares()
	if DOCTYPE in get_doctypes_with_custom_docperms():
		move_customised_rules()


def remove_shares():
	# Shares grant access past the per-user permission hooks; the settings are personal.
	frappe.db.delete("DocShare", {"share_doctype": DOCTYPE})


def move_customised_rules():
	mirror_rules({DOCTYPE: {"Desk User": DESK_USER_PTYPES}})
	removed = False
	for rule in get_role_rules(DOCTYPE, "All"):
		if not cint(rule.permlevel) and remove_rule(DOCTYPE, rule.name):
			removed = True
	if removed:
		frappe.clear_cache(doctype=DOCTYPE)
