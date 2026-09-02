# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The `Default Company` navigation item kind: ERPNext's own, and the first one an app has
contributed (frappe/frappe#42424).

A kind is two files and, optionally, a hook. The record at
`setup/navigation_item_type/default_company/default_company.json` arrives at `bench migrate`;
the renderer beside it at `frontend/item.js` arrives at `bench build`; and because the record
declares the `Custom` permission rule, `hooks.py` points the framework at a `can_see` in the
same folder. Those are three independent channels, and the failure they share is quiet: a kind
missing its renderer is skipped with a console line, and a kind declaring `Custom` with no
`can_see` fails closed. Both read as an item that is simply not there.

So the pairing is asserted as much as the behaviour.
"""

import os
from unittest.mock import patch

import frappe
from frappe.shell.navigation import resolve_navigation
from frappe.tests import IntegrationTestCase

from erpnext.setup.navigation_item_type.default_company import default_company as kind

TYPE_NAME = "Default Company"
FOLDER = os.path.join(frappe.get_app_path("erpnext"), "setup", "navigation_item_type", "default_company")

# Where the item is authored: ERPNext's Setup sidebar, beside the `Company` list.
SIDEBAR = "module_def_setup"
KEY = "default-company"

# Any name will do where the permission call is stubbed: `can_see` passes the string through
# and never reads the document itself.
COMPANY = "A Company This Site May Or May Not Have"


class TestDefaultCompanyKind(IntegrationTestCase):
	"""What the app ships, and whether the three halves agree with each other."""

	def test_the_type_record_arrives_at_migrate(self):
		row = frappe.db.get_value(
			"Navigation Item Type", TYPE_NAME, ["permission_rule", "target_doctype", "module"], as_dict=True
		)

		self.assertIsNotNone(row, "the type record did not arrive; `bench migrate` imports it")
		self.assertEqual(row.permission_rule, "Custom")
		self.assertEqual(row.target_doctype, "Company")
		self.assertEqual(row.module, "Setup")

	def test_the_renderer_ships_beside_the_record(self):
		"""The pair is the kind. Ship one without the other and the item vanishes quietly --
		with no renderer it is skipped and logged to the console, which nobody is reading."""
		self.assertTrue(os.path.isfile(os.path.join(FOLDER, "default_company.json")))
		self.assertTrue(os.path.isfile(os.path.join(FOLDER, "frontend", "item.js")))

	def test_the_hook_names_a_can_see_that_imports(self):
		"""A `Custom` type whose hook points at nothing fails closed: every item of the kind is
		dropped and one line goes to the Error Log. This is the same lookup the framework does."""
		paths = frappe.get_hooks("navigation_item_resolvers", default={}).get(TYPE_NAME)

		self.assertTrue(paths, "hooks.py contributes no resolver for the kind")
		self.assertTrue(callable(frappe.get_attr(f"{paths[-1]}.can_see")))

	def test_the_shipped_row_carries_no_label(self):
		"""Deliberate: the renderer's fallback names the item after the company, which is not
		knowable when the row is authored. An authored label would win over it."""
		row = frappe.db.get_value(
			"Navigation Item",
			{"parenttype": "Sidebar", "parent": SIDEBAR, "key": KEY},
			["item_type", "label", "parent_key"],
			as_dict=True,
		)

		self.assertIsNotNone(row, f"{SIDEBAR} does not ship the {KEY} row")
		self.assertEqual(row.item_type, TYPE_NAME)
		self.assertFalse(row.label)
		self.assertEqual(row.parent_key, "section-organization")

	def test_the_type_is_code_owned(self):
		"""Charter point 5: a type row is app content, so nobody may mint one on a site.

		Read off the permission rows rather than by asking `has_permission`, which answers True
		for Administrator whatever the rows say -- the account most likely to be running this.
		"""
		grants = frappe.get_meta("Navigation Item Type").permissions

		self.assertTrue(grants, "the table grants nothing at all, which is a different bug")
		for grant in grants:
			self.assertFalse(grant.create, grant.role)
			self.assertFalse(grant.write, grant.role)


class TestDefaultCompanyVisibility(IntegrationTestCase):
	"""`can_see`, which is the whole reason the kind declares `Custom` rather than a bucket."""

	def setUp(self):
		self.items = [{"key": KEY, "item_type": TYPE_NAME}]
		self.context = _Context(frappe.session.user)

	def test_a_site_with_no_default_company_ships_nothing(self):
		"""A site still in the setup wizard. The item has nothing to point at, and it is dropped
		here rather than sent and then declined by the renderer."""
		with patch.object(kind, "default_company", return_value=None):
			self.assertEqual(kind.can_see(self.items, self.context), [])

	def test_the_check_is_on_the_document_and_not_the_doctype(self):
		"""The difference the kind exists for. `Readable DocType` asks whether this user may read
		`Company` at all; the honest question is whether they may open *this* company, which is
		what a `User Permission` decides on an ordinary ERPNext site."""
		with patch.object(kind, "default_company", return_value=COMPANY):
			with patch.object(frappe, "has_permission", return_value=True) as allowed:
				self.assertEqual(kind.can_see(self.items, self.context), self.items)

			self.assertEqual(allowed.call_args.args, ("Company",))
			self.assertEqual(allowed.call_args.kwargs["doc"], COMPANY)

			with patch.object(frappe, "has_permission", return_value=False):
				self.assertEqual(kind.can_see(self.items, self.context), [])

	def test_a_default_company_that_no_longer_exists_ships_nothing(self):
		"""Global Defaults naming a deleted company. Left to raise, this would fail the kind
		closed *and* write an Error Log on every boot of every session, since the cause is the
		site's data rather than a passing fault.

		As somebody other than Administrator, who never reaches the document: the permission
		system answers True for them before it looks anything up, so this leak is invisible to
		the account most likely to be testing it.
		"""
		context = _Context(_make_user("default.company.kind@example.com"))

		with patch.object(kind, "default_company", return_value="A Company Nobody Has"):
			self.assertEqual(kind.can_see(self.items, context), [])

	def test_one_permission_call_however_many_items(self):
		"""Batched by contract (frappe/frappe#42231): every item of this kind shares one
		destination, so there is one question to ask. A loop here is what the 3,594 ms
		measurement was made on."""
		many = [{"key": f"{KEY}-{n}", "item_type": TYPE_NAME} for n in range(20)]

		with patch.object(kind, "default_company", return_value=COMPANY):
			with patch.object(frappe, "has_permission", return_value=True) as allowed:
				self.assertEqual(kind.can_see(many, self.context), many)

		self.assertEqual(allowed.call_count, 1)

	def test_a_restricted_user_loses_the_item_from_the_resolved_sidebar(self):
		"""End to end, through the framework rather than by calling `can_see`: the same person
		keeps or loses the row on nothing but a `User Permission` naming another company.

		Run against the companies the site already has rather than ERPNext's `Company` test
		records, which cannot be created on a site that already keeps books -- their fiscal years
		collide with the real ones. So this is the one case that needs a second company and skips
		without one.
		"""
		companies = frappe.get_all("Company", pluck="name", limit=2)
		if len(companies) < 2:
			self.skipTest("needs two companies: one to be the default, one to be restricted to")

		default, other = companies
		user = _make_user("default.company.kind@example.com")

		with patch.object(kind, "default_company", return_value=default):
			self.assertIn(KEY, _sidebar_keys(user))

			_restrict(user, other)
			self.assertNotIn(KEY, _sidebar_keys(user))


class _Context:
	"""Stands in for `NavigationContext`, of which `can_see` reads one attribute.

	A real one would resolve the whole permission pass for a user this test does not otherwise
	need, and the narrowness is the point: a resolver that reached for more would be a resolver
	recomputing what the framework already paid for.
	"""

	def __init__(self, user: str):
		self.user = user


def _sidebar_keys(user: str) -> list[str]:
	frappe.set_user(user)
	try:
		frappe.clear_cache(user=user)
		rows = resolve_navigation("erpnext")["sidebars"].get(SIDEBAR, [])
		return [row["key"] for row in rows]
	finally:
		frappe.set_user("Administrator")


def _restrict(user: str, company: str):
	"""Pin somebody to one company, which is how an ERPNext site says it."""
	frappe.set_user("Administrator")
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "Company",
			"for_value": company,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(user=user)


def _make_user(email: str) -> str:
	if frappe.db.exists("User", email):
		return email

	return (
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Default Company Kind",
				"user_type": "System User",
				"roles": [{"role": "System Manager"}],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
