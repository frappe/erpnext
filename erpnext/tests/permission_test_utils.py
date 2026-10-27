from contextlib import contextmanager

import frappe
from frappe.exceptions import FrappeTypeError
from frappe.utils import today

OTHER_COMPANY = "_Test Company 3"
MISSING_NAME = "_Test Missing UP Record"
TEST_BANK = "_Test UP Bank"


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
	try:
		frappe.throw_permission_error()
	except frappe.PermissionError as refusal:
		return str(refusal)
	finally:
		frappe.flags.pop("disable_traceback", None)


def assert_refused(test, fn, *args, **kwargs):
	frappe.local.message_log = []
	with test.assertRaises(frappe.PermissionError) as refusal:
		fn(*args, **kwargs)
	frappe.flags.pop("disable_traceback", None)
	constant = refusal_message()
	test.assertEqual(str(refusal.exception), constant)
	for message in frappe.local.message_log:
		test.assertEqual(message.get("message"), constant)


def assert_refused_without(test, values, fn, *args, **kwargs):
	assert_refused(test, fn, *args, **kwargs)
	logged = ""
	for message in frappe.local.message_log:
		logged += str(message)
	for value in values:
		test.assertNotIn(str(value), logged)


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
		elif caller_supplied and (name == MISSING_NAME or not isinstance(name, str | int)):
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


def make_bank(bank_name=TEST_BANK):
	if not frappe.db.exists("Bank", bank_name):
		frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert()
	return bank_name


def make_other_company_bank_gl():
	account = "_Test UP Bank - _TC3"
	if not frappe.db.exists("Account", account):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test UP Bank",
				"company": OTHER_COMPANY,
				"parent_account": "Bank Accounts - _TC3",
				"account_type": "Bank",
				"account_currency": "INR",
			}
		).insert()
	return account


def make_bank_account(account_name, company, account):
	existing = frappe.db.get_value("Bank Account", {"account": account})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": account_name,
				"bank": make_bank(),
				"is_company_account": 1,
				"company": company,
				"account": account,
			}
		)
		.insert()
		.name
	)


def make_other_company_bank_account():
	return make_bank_account("_Test UP Other", OTHER_COMPANY, make_other_company_bank_gl())


def make_bank_transaction(bank_account, deposit=0, withdrawal=0, reference_number=None):
	return (
		frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"date": today(),
				"deposit": deposit,
				"withdrawal": withdrawal,
				"bank_account": bank_account,
				"currency": "INR",
				"reference_number": reference_number or frappe.generate_hash(length=10),
			}
		)
		.save()
		.submit()
	)
