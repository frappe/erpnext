from contextlib import contextmanager

import frappe
from frappe.exceptions import FrappeTypeError

OTHER_COMPANY = "_Test Company 1"
MISSING_NAME = "_Test Missing UP Record"


def make_fenced_user(email, roles, user_permissions=None):
	if not frappe.db.exists("User", email):
		frappe.flags.in_import = True
		try:
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_import = False
	user = frappe.get_doc("User", email)
	user.set("roles", [])
	user.add_roles(*roles)
	frappe.db.delete("User Permission", {"user": email})
	for user_permission in user_permissions or []:
		hide_descendants = 0
		if len(user_permission) > 2:
			hide_descendants = user_permission[2]
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": email,
				"allow": user_permission[0],
				"for_value": user_permission[1],
				"apply_to_all_doctypes": 1,
				"hide_descendants": hide_descendants,
			}
		).insert(ignore_permissions=True)
	frappe.cache.hdel("user_permissions", email)
	frappe.clear_cache(user=email)
	return email


def make_company_fenced_user(email, roles, company):
	return make_fenced_user(email, roles, [("Company", company)])


def malformed_names():
	return [{"name": ["like", "%"]}, ["like", "%"], MISSING_NAME]


@contextmanager
def as_user(email):
	previous = frappe.session.user
	frappe.set_user(email)
	try:
		yield email
	finally:
		frappe.set_user(previous)
		frappe.clear_cache(user=email)


def refusal_message():
	return frappe._("Not permitted")


def assert_refused(test, fn, *args, **kwargs):
	frappe.clear_messages()
	with test.assertRaises(frappe.PermissionError) as refusal:
		fn(*args, **kwargs)
	frappe.flags.pop("disable_traceback", None)
	test.assertEqual(str(refusal.exception), refusal_message())
	for message in frappe.get_message_log():
		test.assertEqual(message.get("message"), refusal_message())


def assert_refused_without(test, values, fn, *args, **kwargs):
	assert_refused(test, fn, *args, **kwargs)
	response = frappe.as_json(frappe.get_message_log())
	for value in values:
		test.assertNotIn(str(value), response)


def assert_type_gated(test, fn, *args, **kwargs):
	with test.assertRaises(FrappeTypeError):
		fn(*args, **kwargs)


def assert_not_found(test, fn, *args, **kwargs):
	with test.assertRaises(frappe.DoesNotExistError):
		fn(*args, **kwargs)


def assert_refused_for_names(test, fn, build_kwargs, names, type_gated=False, caller_supplied=False):
	cases = list(names)
	for name in malformed_names():
		cases.append(name)
	for name in cases:
		if type_gated and not isinstance(name, str | int):
			assert_type_gated(test, fn, **build_kwargs(name))
		elif caller_supplied and name in malformed_names():
			assert_not_found(test, fn, **build_kwargs(name))
		else:
			assert_refused(test, fn, **build_kwargs(name))


def insert_test_record(doctype, values):
	record = frappe.new_doc(doctype)
	record.update(values)
	if not record.name:
		record.name = frappe.generate_hash(length=12)
	record.db_insert()
	return record.name


def disable_mandatory_accounting_dimensions():
	for name in frappe.get_all("Accounting Dimension Detail", pluck="name"):
		frappe.db.set_value(
			"Accounting Dimension Detail", name, {"mandatory_for_bs": 0, "mandatory_for_pl": 0}
		)
	frappe.flags.accounting_dimensions_details = None
