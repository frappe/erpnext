# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
	create_target_distribution,
)
from erpnext.selling.report.territory_target_variance_based_on_item_group.territory_target_variance_based_on_item_group import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestTerritoryTargetVarianceBasedOnItemGroup(ERPNextTestSuite):
	def setUp(self):
		self.fiscal_year = get_fiscal_year(nowdate())[0]

	def test_achieved_target_and_variance(self):
		distribution = create_target_distribution(self.fiscal_year)
		territory = create_territory_with_target(
			"_Test Target Territory", self.fiscal_year, distribution.name, target_qty=50
		)

		# a Sales Order in that territory contributes to the achieved quantity
		so = make_sales_order(rate=1000, qty=20, do_not_submit=True)
		so.territory = territory.name
		so.submit()

		result = execute(
			frappe._dict(
				{
					"fiscal_year": self.fiscal_year,
					"doctype": "Sales Order",
					"period": "Yearly",
					"target_on": "Quantity",
				}
			)
		)[1]

		# no item_group is set on the target, so the report emits exactly one row per
		# territory -- assert all three figures against that single row
		rows = [frappe._dict(r) for r in result if r.get("territory") == territory.name]
		self.assertEqual(len(rows), 1, "expected exactly one row for the target territory")
		row = rows[0]
		self.assertEqual(flt(row.total_target, 2), 50)
		self.assertEqual(flt(row.total_achieved, 2), 20)
		self.assertEqual(flt(row.total_variance, 2), -30)


def create_territory_with_target(name, fiscal_year, distribution_id, target_qty=50):
	doc = frappe.new_doc("Territory")
	doc.territory_name = name
	doc.parent_territory = "All Territories"
	doc.is_group = 0
	doc.append(
		"targets",
		{
			"fiscal_year": fiscal_year,
			"target_qty": target_qty,
			"target_amount": 30000,
			"distribution_id": distribution_id,
		},
	)
	return doc.insert()
