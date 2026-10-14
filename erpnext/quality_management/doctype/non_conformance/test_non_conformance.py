# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.quality_management.doctype.quality_procedure.test_quality_procedure import create_procedure
from erpnext.tests.permission_test_utils import as_user, make_fenced_user


class TestNonConformance(FrappeTestCase):
	def test_quality_manager_can_raise_non_conformance(self):
		procedure = create_procedure()
		quality_manager = make_fenced_user("non-conformance-manager@example.com", ["Quality Manager"])

		with as_user(quality_manager):
			non_conformance = frappe.get_doc(
				doctype="Non Conformance",
				subject="_Test Non Conformance",
				procedure=procedure.name,
				status="Open",
			).insert()

		self.assertEqual(non_conformance.owner, quality_manager)
