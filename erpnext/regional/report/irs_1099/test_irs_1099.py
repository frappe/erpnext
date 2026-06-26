# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.regional.report.irs_1099.irs_1099 import get_street_address_html
from erpnext.tests.utils import ERPNextTestSuite


class TestIRS1099StreetAddress(ERPNextTestSuite):
	def test_street_address_prefers_postal(self):
		"""The original query cross-joined Address with no join predicate, so its
		`ORDER BY address_type='Postal' DESC` sorted on an arbitrary cross-joined row and never
		controlled which link.parent (Address) was returned. The conversion joins address.name ==
		link.parent so the Postal/Billing preference actually applies; a `link.parent` tie-break keeps
		the LIMIT-1 pick deterministic across engines when several addresses share the top type."""
		party = "_Test 1099 Address Supplier"
		if not frappe.db.exists("Supplier", party):
			frappe.get_doc(
				{"doctype": "Supplier", "supplier_name": party, "supplier_group": "_Test Supplier Group"}
			).insert(ignore_permissions=True)

		def mk_addr(title, address_type, line1):
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": title,
					"address_type": address_type,
					"address_line1": line1,
					"city": "Testville",
					"country": "United States",
					"links": [{"link_doctype": "Supplier", "link_name": party}],
				}
			).insert(ignore_permissions=True)

		mk_addr("_Test 1099 Billing", "Billing", "1 Billing St")
		mk_addr("_Test 1099 Postal", "Postal", "9 Postal Rd")

		street, _city_state = get_street_address_html("Supplier", party)
		# the Postal address must win over the Billing one (deterministically, on both engines)
		self.assertIn("9 Postal Rd", street)
		self.assertNotIn("1 Billing St", street)
