# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""ERPNext's shipped desk v2 navigation: one Rail record and eighteen module Sidebars.

These are fixture tests. The rows arrive as JSON at `bench migrate` and the framework resolves
them, so what there is to get wrong is the content of those rows: a rail item naming a sidebar
nobody ships, a row pointing at a doctype this site does not have, or two rows claiming one key.
Each of those resolves to a quietly shorter list rather than to an error, which is why they are
asserted here.

This is the module-primary half of charter point 2 (frappe/frappe#42226): the same table, the
same resolver and the same item kinds that give CRM a doctype-primary rail, giving ERPNext one
made of modules. The rail is a `Sidebar` item per module that has an authored sidebar and a
`Module` item per module that does not.

The one piece of ERPNext navigation code lives elsewhere: `test_navigation_kind.py` covers the
`Default Company` item kind, which is the app contributing a kind rather than authoring rows.

Every test runs as somebody other than Administrator. The permission filter short-circuits for
an administrator (`frappe/shell/navigation_filter.py`), so an Administrator suite would pass
against a rail that is not being filtered at all.
"""

import frappe
from frappe.shell.navigation import resolve_navigation
from frappe.tests import IntegrationTestCase

APP = "erpnext"

# The rail, in the order it is authored -- which is the order ERPNext already curated for desk
# v1's dock, since that list is what a person using ERPNext expects to see.
RAIL = (
	"accounts",
	"crm",
	"buying",
	"projects",
	"selling",
	"setup",
	"manufacturing",
	"stock",
	"support",
	"utilities",
	"assets",
	"maintenance",
	"regional",
	"erpnext-integrations",
	"quality-management",
	"communication",
	"telephony",
	"bulk-transaction",
	"subcontracting",
	"edi",
)

# The two modules whose authored sidebar would hold one row or none, so none is shipped. Their
# rail item is a `Module`, which lands on the module page -- a list derived from the module's
# contents, which is a different list on purpose (frappe/frappe#42357).
#
# `Portal` is on desk v1's dock and is deliberately not here: it holds no doctypes at all, so
# it has neither a sidebar to open nor a module page to land on, and the renderer would find no
# address and skip the row.
INDEPENDENT = ("erpnext-integrations", "communication")

# Every other module ships a sidebar, addressed at its `Module Def`. The scrubbed address is
# both the standard record's name and the key boot files it under, and it is the string the
# rail item of type `Sidebar` carries in `link_to`.
LINKED = tuple(key for key in RAIL if key not in INDEPENDENT)


def rail_of(user: str) -> list[dict]:
	frappe.set_user(user)
	try:
		return resolve_navigation(APP)["rail"]
	finally:
		frappe.set_user("Administrator")


class TestERPNextNavigation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = make_erpnext_user("erpnext.navigation.test@example.com")

	def setUp(self):
		frappe.set_user(self.user)
		self.addCleanup(frappe.set_user, "Administrator")
		# `IntegrationTestCase` rolls back once per CLASS, so a `Block Module` row written by one
		# test is still there for the next -- and three tests below block the same module, so the
		# one that asserts what the rail looks like *before* the block would depend on running
		# first. Cleared here rather than in a cleanup, so it holds however the tests are ordered.
		self.unblock()
		self.addCleanup(self.unblock)

	def unblock(self):
		"""Give every module back, and clear the cache the block is read through."""
		frappe.set_user("Administrator")
		doc = frappe.get_doc("User", self.user)
		if doc.block_modules:
			doc.set("block_modules", [])
			doc.save(ignore_permissions=True)
		frappe.clear_cache(user=self.user)
		frappe.set_user(self.user)

	def test_the_rail_is_the_twenty_authored_items(self):
		"""As Administrator, who is filtered by nothing, so this is the shipped list itself."""
		frappe.set_user("Administrator")

		self.assertEqual(tuple(item["key"] for item in resolve_navigation(APP)["rail"]), RAIL)

	def test_a_linked_item_names_a_sidebar_this_app_ships(self):
		"""A typo in `link_to` costs the item its panel and nothing else, so nothing reports it.

		Read off the **shipped rows**, not the resolved payload. `Sidebar` declares the
		`Derived From Children` permission rule, so an item naming an address that resolves to no
		rows is dropped by the server's own cascade -- silently, and correctly, because that is
		also what an emptied sidebar has to do. Asserting against the resolved list would
		therefore be asserting that the cascade works, which is frappe's test and not this one.
		"""
		linked = [row for row in shipped("Rail", "erpnext") if row.item_type == "Sidebar"]
		addresses = set(frappe.get_all("Sidebar", filters={"app": APP, "standard": 1}, pluck="name"))

		self.assertEqual(tuple(row.key for row in linked), LINKED)
		for row in linked:
			self.assertIn(row.link_to, addresses, row.key)

	def test_an_independent_item_is_a_module_and_opens_nothing(self):
		"""Charter point 1 makes independent a first-class state, and needs no field to say so:
		a `Module` item lands on the module page and has no sidebar to open."""
		frappe.set_user("Administrator")
		navigation = resolve_navigation(APP)
		rail = {item["key"]: item for item in navigation["rail"]}

		for key in INDEPENDENT:
			self.assertEqual(rail[key]["item_type"], "Module")
			self.assertNotIn(frappe.scrub(f"Module Def {rail[key]['link_to']}"), navigation["sidebars"])

	def test_every_sidebar_is_addressed_at_a_module_that_exists(self):
		"""The address is the module, not the desk v1 sidebar the rows were curated for -- and
		those two differ: v1's `Quality` sidebar belongs to the `Quality Management` module."""
		for name in frappe.get_all(
			"Sidebar", filters={"app": APP, "standard": 1, "link_doctype": "Module Def"}, pluck="name"
		):
			module = frappe.db.get_value("Sidebar", name, "link_to")
			self.assertTrue(frappe.db.exists("Module Def", module), name)
			self.assertEqual(name, frappe.scrub(f"Module Def {module}"))

	def test_every_destination_is_a_doctype_this_site_has(self):
		"""Read off the shipped rows rather than the resolved payload, which has already dropped
		any row it could not place.

		A typo cannot get this far: `link_to` is a Dynamic Link, so `_validate_links` refuses the
		row at import with `Could not find Row #N: Link To` -- checked, not assumed. What is left
		for this to catch is a doctype removed *after* the rows were imported, which arrives as a
		quietly shorter sidebar and nothing else.
		"""
		for container, address in every_container():
			for row in shipped(container, address):
				if row.item_type == "DocType":
					self.assertTrue(frappe.db.exists("DocType", row.link_to), f"{address}/{row.key}")

	def test_keys_are_unique_within_each_container(self):
		"""Every site and user edit is filed against a key, so two rows sharing one collide."""
		for container, address in every_container():
			keys = [row.key for row in shipped(container, address)]
			self.assertEqual(len(keys), len(set(keys)), address)

	def test_no_section_is_shipped_over_nothing(self):
		"""A heading with no rows under it is dropped by the cascade at read time, so shipping one
		would mean shipping a row that can never render. Left out at authoring instead -- and read
		here off the shipped rows, since the cascade would have hidden it either way."""
		for container, address in every_container():
			rows = shipped(container, address)
			parents = {row.parent_key for row in rows}
			for row in rows:
				if row.item_type == "Section":
					self.assertIn(row.key, parents, f"{address}/{row.key}")

	def test_every_parent_key_names_a_section_beside_it(self):
		"""A row filed under a heading that is not there loses its nesting silently: the resolver
		promotes an orphan to the top level rather than dropping it."""
		for container, address in every_container():
			rows = shipped(container, address)
			sections = {row.key for row in rows if row.item_type == "Section"}
			for row in rows:
				if row.parent_key:
					self.assertIn(row.parent_key, sections, f"{address}/{row.key}")

	def test_a_real_user_sees_fewer_modules_than_administrator(self):
		"""The filter is doing something, which is the one thing an Administrator suite cannot
		show. An `Accounts User` has no reason to be offered `Regional` or `Telephony`."""
		frappe.set_user("Administrator")
		everything = len(resolve_navigation(APP)["rail"])

		self.assertLess(len(rail_of(self.user)), everything)

	def test_a_blocked_module_ships_nothing(self):
		"""The veto on a module-primary rail, which is what this rail is here to exercise.

		`block_modules` gates module-derived items, and a module-primary rail reaches a module
		through a `Sidebar` item holding `DocType` rows -- so before frappe/frappe#42423 blocking
		Accounts left all 73 rows and the rail item standing. The block now names the sidebar's
		*address*, and the rail item goes with it through the cascade it already ran under.
		"""
		before = [item["key"] for item in rail_of(self.user)]
		self.assertIn("accounts", before)

		block("Accounts", self.user)
		after = rail_of(self.user)

		self.assertEqual([item["key"] for item in after], [key for key in before if key != "accounts"])

	def test_a_blocked_module_takes_its_sidebar_with_it(self):
		block("Accounts", self.user)
		frappe.set_user(self.user)

		self.assertNotIn("module_def_accounts", resolve_navigation(APP)["sidebars"])

	def test_a_doctype_in_a_blocked_module_is_still_reachable(self):
		"""Hiding a module hides the way to a document, never the document. `Sales Invoice` is
		an Accounts doctype and ERPNext's Selling sidebar links it, which is one of the 101 rows
		that point outside their own module."""
		block("Accounts", self.user)
		frappe.set_user(self.user)
		sidebars = resolve_navigation(APP)["sidebars"]

		self.assertTrue(
			any(
				row.get("link_to") == "Sales Invoice"
				for address, rows in sidebars.items()
				if address != "module_def_accounts"
				for row in rows
			)
		)


def every_container() -> list[tuple[str, str]]:
	"""Every standard record ERPNext ships, as `(doctype, name)`."""
	return [("Rail", "erpnext")] + [
		("Sidebar", name)
		for name in frappe.get_all("Sidebar", filters={"app": APP, "standard": 1}, pluck="name")
	]


def shipped(container: str, address: str) -> list:
	"""The rows as authored, before the resolver has filtered or cascaded anything away.

	The distinction matters for every fixture assertion below: `resolve_navigation` drops a row
	naming a doctype that is gone, a heading over nothing and a linked item whose sidebar
	emptied. Read against its output, a test for those is asserting that the resolver works.
	"""
	return frappe.get_all(
		"Navigation Item",
		filters={
			"parenttype": container,
			"parent": address,
			"parentfield": "items" if container == "Rail" else "navigation_items",
		},
		fields=["key", "parent_key", "item_type", "link_doctype", "link_to"],
		order_by="idx asc",
	)


def block(module: str, user: str):
	"""Withdraw a module from one person, the way an administrator does on the User form.

	`tabBlock Module` holds no rows on either bench site, so the veto cannot be observed without
	seeding one -- which is why it had never been watched on a real rail.
	"""
	frappe.set_user("Administrator")
	doc = frappe.get_doc("User", user)
	doc.append("block_modules", {"module": module})
	doc.save(ignore_permissions=True)
	frappe.clear_cache(user=user)
	frappe.set_user(user)


def make_erpnext_user(email: str) -> str:
	"""Somebody who works in a few of ERPNext's modules and not in the rest of them."""
	if frappe.db.exists("User", email):
		return email

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "ERPNext Navigation",
			"user_type": "System User",
			"roles": [{"role": "Accounts User"}, {"role": "Stock User"}, {"role": "Sales User"}],
		}
	).insert(ignore_permissions=True)

	return user.name
