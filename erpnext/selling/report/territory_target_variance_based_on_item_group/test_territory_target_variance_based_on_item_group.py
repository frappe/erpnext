# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
	create_target_distribution,
)
from erpnext.selling.report.territory_target_variance_based_on_item_group.territory_target_variance_based_on_item_group import (
	execute,
)
from erpnext.stock.doctype.item.test_item import make_item


class TestTerritoryTargetVarianceBasedOnItemGroup(FrappeTestCase):
	def setUp(self):
		self.fiscal_year = get_fiscal_year(nowdate())[0]

	def tearDown(self):
		frappe.db.rollback()

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

	def test_overall_target_counts_all_item_groups(self):
		distribution = create_target_distribution(self.fiscal_year)
		item_a = make_item(properties={"item_group": "_Test Item Group A"}).name
		item_d = make_item(properties={"item_group": "_Test Item Group D"}).name

		territory = frappe.new_doc("Territory")
		territory.territory_name = "_Test Target Territory Mixed"
		territory.parent_territory = "All Territories"
		territory.is_group = 0
		# overall target leaves item_group unset; the second row targets one group
		territory.append(
			"targets",
			{
				"fiscal_year": self.fiscal_year,
				"target_amount": 20000,
				"distribution_id": distribution.name,
			},
		)
		territory.append(
			"targets",
			{
				"fiscal_year": self.fiscal_year,
				"item_group": "_Test Item Group A",
				"target_amount": 4000,
				"distribution_id": distribution.name,
			},
		)
		territory.insert()

		for item_code, qty in ((item_a, 5), (item_d, 3)):
			so = make_sales_order(item_code=item_code, rate=1000, qty=qty, do_not_submit=True)
			so.territory = territory.name
			so.submit()

		rows = [
			frappe._dict(r)
			for r in execute(
				frappe._dict(
					{
						"fiscal_year": self.fiscal_year,
						"doctype": "Sales Order",
						"period": "Yearly",
						"target_on": "Amount",
					}
				)
			)[1]
			if r.get("territory") == territory.name
		]

		# the item-group row counts only its own sales, the overall row counts every group
		group_a = next(r for r in rows if r.item_group == "_Test Item Group A")
		overall = next(r for r in rows if not r.item_group)
		self.assertEqual(flt(group_a.total_achieved, 2), 5000)
		self.assertEqual(flt(overall.total_achieved, 2), 8000)

	def test_achieved_respects_user_permissions(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user
		from frappe.permissions import add_user_permission, remove_user_permission

		distribution = create_target_distribution(self.fiscal_year)
		territory = create_territory_with_target(
			"_Test Target Territory Perm", self.fiscal_year, distribution.name
		)

		for customer, qty in (("_Test Customer", 5), ("_Test Customer 2", 3)):
			so = make_sales_order(customer=customer, rate=1000, qty=qty, do_not_submit=True)
			so.territory = territory.name
			so.submit()

		def achieved():
			return sum(
				flt(r.get("total_achieved"))
				for r in execute(
					frappe._dict(
						{
							"fiscal_year": self.fiscal_year,
							"doctype": "Sales Order",
							"period": "Yearly",
							"target_on": "Quantity",
						}
					)
				)[1]
				if r.get("territory") == territory.name
			)

		self.assertEqual(flt(achieved(), 2), 8)

		user = create_user("tgt_variance_restricted@example.com", "Sales Manager").name
		add_user_permission("Customer", "_Test Customer 2", user)
		try:
			with self.set_user(user):
				restricted = achieved()
		finally:
			remove_user_permission("Customer", "_Test Customer 2", user)
		self.assertEqual(flt(restricted, 2), 3)


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
