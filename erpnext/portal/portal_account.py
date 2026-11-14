# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The signed-in portal user's own account: their name and phone numbers, and their password.
Every endpoint acts on the session user only, and reads or writes only the fields below."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, validate_phone_number

# what the account page shows and may change; never roles, email, user type or anything else on User
EDITABLE_FIELDS = ("first_name", "last_name", "phone", "mobile_no")

# a User's name fields are Data fields
NAME_LENGTH = 140


@frappe.whitelist()
def get_account() -> dict:
	"""The signed-in user's own name, email and phone numbers."""
	user = _signed_in_user()
	values = frappe.db.get_value("User", user, ["email", *EDITABLE_FIELDS], as_dict=True)
	return {**values, "user": user}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60, user_based=True, ip_based=False)
def update_account(
	first_name: str, last_name: str | None = None, phone: str | None = None, mobile_no: str | None = None
) -> dict:
	"""Change the signed-in user's own name and phone numbers."""
	user = _signed_in_user()
	values = {
		"first_name": (first_name or "").strip(),
		"last_name": (last_name or "").strip(),
		"phone": (phone or "").strip(),
		"mobile_no": (mobile_no or "").strip(),
	}
	if not values["first_name"]:
		frappe.throw(_("Enter your first name."))
	for field in ("first_name", "last_name"):
		if len(values[field]) > NAME_LENGTH:
			frappe.throw(_("Your name is too long."))
	for field, label in (("phone", _("Phone")), ("mobile_no", _("Mobile"))):
		if values[field] and not validate_phone_number(values[field]):
			frappe.throw(_("{0} is not a valid phone number.").format(label))

	doc = frappe.get_doc("User", user)
	doc.update(values)
	# a user may change their own name and phone in Desk too; this saves only the fields above
	doc.save(ignore_permissions=True)
	return get_account()


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60, user_based=True, ip_based=False)
def change_password(old_password: str, new_password: str, logout_other_sessions: int = 0) -> None:
	"""Change the signed-in user's password. Frappe's own update checks the current password as a
	login does (failed attempts count), enforces the site's password policy, refuses the current
	password, and can sign the user out everywhere else."""
	from frappe.core.doctype.user.user import update_password

	_signed_in_user()
	if not old_password:
		frappe.throw(_("Enter your current password."))
	update_password(new_password, logout_all_sessions=cint(logout_other_sessions), old_password=old_password)


def _signed_in_user() -> str:
	user = frappe.session.user
	if user in (None, "", "Guest"):
		raise frappe.PermissionError
	return user
