# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.templates.pages.partners import get_context, page_title
from erpnext.tests.utils import ERPNextTestSuite


class TestPartnersPage(ERPNextTestSuite):
	def _make_partner(self, name, show_in_website):
		if not frappe.db.exists("Sales Partner", name):
			frappe.get_doc(
				{
					"doctype": "Sales Partner",
					"partner_name": name,
					"territory": "_Test Territory",
					"commission_rate": 5,
					"show_in_website": show_in_website,
				}
			).insert(ignore_permissions=True)
		return name

	def test_get_context_lists_only_website_partners(self):
		"""partners.py builds the /partners list via
		frappe.get_all("Sales Partner", filters={"show_in_website": 1}, ...).
		Seed one website-visible partner and one hidden control partner, then assert the
		returned context contains the visible one and excludes the hidden one -- real
		membership of the converted query's result, not a tautology."""
		visible = self._make_partner("_Test Website Sales Partner", 1)
		hidden = self._make_partner("_Test Hidden Sales Partner", 0)

		result = get_context(frappe._dict())

		# context shape: {"partners": [...], "title": page_title}
		self.assertEqual(result["title"], page_title)
		partner_names = [p.name for p in result["partners"]]

		self.assertIn(
			visible,
			partner_names,
			"website-flagged Sales Partner missing from /partners context",
		)
		self.assertNotIn(
			hidden,
			partner_names,
			"Sales Partner with show_in_website=0 leaked into /partners context",
		)

		# every returned row really has show_in_website=1 (filter applied, not just appended)
		for partner in result["partners"]:
			self.assertEqual(
				partner.show_in_website,
				1,
				f"Sales Partner {partner.name} returned despite show_in_website != 1",
			)
