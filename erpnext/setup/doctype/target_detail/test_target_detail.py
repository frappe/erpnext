# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
	create_sales_target_doc,
	create_target_distribution,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestTargetDetail(ERPNextTestSuite):
	def test_duplicate_target_rows_are_rejected(self):
		fiscal_year = get_fiscal_year(nowdate())[0]
		distribution = create_target_distribution(fiscal_year)
		for doctype, name_field in (
			("Territory", "territory_name"),
			("Sales Person", "sales_person_name"),
			("Sales Partner", "partner_name"),
		):
			holder = create_sales_target_doc(
				doctype, name_field, frappe.generate_hash(length=10), fiscal_year, distribution.name
			)
			for item_group in (None, "_Test Item Group A"):
				with self.subTest(doctype=doctype, item_group=item_group):
					holder.reload()
					holder.targets[0].item_group = item_group
					holder.append(
						"targets", dict(holder.targets[0].as_dict(), name=None, item_group=item_group or "")
					)
					with self.assertRaisesRegex(frappe.ValidationError, "target already exists"):
						holder.save()

			# Overall and specific item groups are separate targets.
			holder.reload()
			holder.targets[0].item_group = None
			holder.append(
				"targets", dict(holder.targets[0].as_dict(), name=None, item_group="_Test Item Group A")
			)
			holder.save()
