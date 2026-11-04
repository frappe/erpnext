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

	def test_company_filter_excludes_other_company_sales(self):
		from erpnext.selling.report.territory_target_variance_based_on_item_group.test_territory_target_variance_based_on_item_group import (
			check_company_filter,
		)

		check_company_filter(self, "Territory", "territory_name", execute)

	def test_duplicate_target_inputs_count_actuals_once(self):
		from erpnext.selling.report.territory_target_variance_based_on_item_group.test_territory_target_variance_based_on_item_group import (
			check_duplicate_targets,
		)

		check_duplicate_targets(self, "Territory", "territory_name", execute)

	def test_group_target_includes_descendant_sales(self):
		check_group_target(self, "Territory", "territory_name", execute)


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


def check_company_filter(test, doctype, name_field, execute_report):
	from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
		create_sales_target_doc,
	)
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	distribution = create_target_distribution(test.fiscal_year)
	holder = create_sales_target_doc(
		doctype, name_field, frappe.generate_hash(length=10), test.fiscal_year, distribution.name
	)
	order = make_sales_order(
		company="_Test Company 2",
		currency=frappe.get_cached_value("Company", "_Test Company 2", "default_currency"),
		warehouse=create_warehouse("_Test Target Report Warehouse", company="_Test Company 2"),
		rate=800,
		qty=1,
		do_not_submit=True,
	)
	field = frappe.scrub(doctype)
	if doctype == "Sales Person":
		order.set("sales_team", [{"sales_person": holder.name, "allocated_percentage": 100}])
	else:
		order.set(field, holder.name)
		if doctype == "Sales Partner":
			order.commission_rate = 5
	order.submit()
	filters = frappe._dict(
		fiscal_year=test.fiscal_year, doctype="Sales Order", period="Yearly", target_on="Amount"
	)

	def achieved():
		return next(r["total_achieved"] for r in execute_report(filters)[1] if r[field] == holder.name)

	test.assertEqual(flt(achieved(), 2), flt(order.base_net_total, 2))
	filters.company = "_Test Company"
	test.assertEqual(flt(achieved(), 2), 0)


def check_duplicate_targets(test, doctype, name_field, execute_report):
	from frappe.utils import add_months, getdate

	from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
		create_sales_target_doc,
	)

	distribution = create_target_distribution(test.fiscal_year)
	month = getdate(nowdate()).strftime("%B")
	for percentage in distribution.percentages:
		percentage.percentage_allocation = 100 if percentage.month == month else 0
	distribution.save()
	other_distribution = frappe.copy_doc(distribution)
	other_distribution.distribution_id = frappe.generate_hash(length=10)
	other_month = getdate(add_months(nowdate(), 1)).strftime("%B")
	for percentage in other_distribution.percentages:
		percentage.percentage_allocation = 100 if percentage.month == other_month else 0
	other_distribution.insert()
	holder = create_sales_target_doc(
		doctype, name_field, frappe.generate_hash(length=10), test.fiscal_year, distribution.name
	)
	holder.targets[0].target_amount = 1000
	holder.save()
	holder.append(
		"targets", dict(holder.targets[0].as_dict(), name=None, distribution_id=other_distribution.name)
	)
	order = make_sales_order(rate=600, qty=1, do_not_submit=True)
	field = frappe.scrub(doctype)
	if doctype == "Sales Person":
		order.set("sales_team", [{"sales_person": holder.name, "allocated_percentage": 100}])
	else:
		order.set(field, holder.name)
		if doctype == "Sales Partner":
			order.commission_rate = 5
	order.submit()
	filters = frappe._dict(
		company=order.company,
		fiscal_year=test.fiscal_year,
		doctype="Sales Order",
		period="Yearly",
		target_on="Amount",
	)
	from erpnext.accounts.report.financial_statements import get_period_list
	from erpnext.selling.report.sales_partner_target_variance_based_on_item_group.item_group_wise_sales_target_variance import (
		get_actual_data,
		prepare_data,
	)

	def report_row():
		periods = get_period_list(
			test.fiscal_year, test.fiscal_year, "", "", "Fiscal Year", filters.period, company=order.company
		)
		rows = prepare_data(
			filters,
			holder.targets,
			{holder.name: []},
			get_actual_data(filters, [holder.name], "transaction_date", field),
			"transaction_date",
			periods,
			field,
		)
		return rows[(holder.name, None)]

	# Feed historical duplicate inputs to the report without writing invalid records.
	row = report_row()
	test.assertEqual(
		[flt(row[k], 2) for k in ("total_target", "total_achieved", "total_variance")], [2000, 600, -1400]
	)
	filters.period = "Monthly"
	row = report_row()
	test.assertEqual(
		[flt(row[k], 2) for k in ("total_target", "total_achieved", "total_variance")], [2000, 600, -1400]
	)
	test.assertEqual(
		sorted(flt(v, 2) for k, v in row.items() if k.startswith("target_")), [0] * 10 + [1000, 1000]
	)


def check_group_target(test, doctype, name_field, execute_report):
	from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
		create_sales_target_doc,
	)

	distribution = create_target_distribution(test.fiscal_year)
	group = create_sales_target_doc(
		doctype, name_field, frappe.generate_hash(length=10), test.fiscal_year, distribution.name
	)
	group.is_group = 1
	group.save()
	parent_field = "parent_" + frappe.scrub(doctype)
	middle = frappe.get_doc(
		dict(
			doctype=doctype,
			is_group=1,
			**{name_field: frappe.generate_hash(length=10), parent_field: group.name},
		)
	).insert()
	leaf = frappe.get_doc(
		dict(doctype=doctype, **{name_field: frappe.generate_hash(length=10), parent_field: middle.name})
	).insert()
	order = make_sales_order(rate=700, qty=1, do_not_submit=True)
	field = frappe.scrub(doctype)
	if doctype == "Sales Person":
		order.set("sales_team", [{"sales_person": leaf.name, "allocated_percentage": 100}])
	else:
		order.set(field, leaf.name)
	order.submit()
	filters = frappe._dict(
		company=order.company,
		fiscal_year=test.fiscal_year,
		doctype="Sales Order",
		period="Yearly",
		target_on="Amount",
	)
	row = next(row for row in execute_report(filters)[1] if row[field] == group.name)
	test.assertEqual(flt(row["total_achieved"], 2), 700)
