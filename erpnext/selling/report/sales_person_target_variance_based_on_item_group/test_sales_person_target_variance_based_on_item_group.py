import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_person_target_variance_based_on_item_group.sales_person_target_variance_based_on_item_group import (
	execute,
)


class TestSalesPersonTargetVarianceBasedOnItemGroup(IntegrationTestCase):
	def setUp(self):
		self.fiscal_year = get_fiscal_year(nowdate())[0]

	def tearDown(self):
		frappe.db.rollback()

	def test_achieved_target_and_variance(self):
		# Create a Target Distribution
		distribution = create_target_distribution(self.fiscal_year)

		# Create sales people with targets for the current fiscal year
		person_1 = create_sales_target_doc(
			"Sales Person", "sales_person_name", "Sales Person 1", self.fiscal_year, distribution.name
		)
		person_2 = create_sales_target_doc(
			"Sales Person", "sales_person_name", "Sales Person 2", self.fiscal_year, distribution.name
		)

		# Create a Sales Order with 50-50 contribution between both Sales people
		so = make_sales_order(
			rate=1000,
			qty=20,
			do_not_submit=True,
		)
		so.set(
			"sales_team",
			[
				{
					"sales_person": person_1.name,
					"allocated_percentage": 50,
					"allocated_amount": 10000,
				},
				{
					"sales_person": person_2.name,
					"allocated_percentage": 50,
					"allocated_amount": 10000,
				},
			],
		)
		so.submit()

		# Check Achieved Target and Variance
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
		row = frappe._dict(result[0])
		self.assertSequenceEqual(
			[flt(value, 2) for value in (row.total_target, row.total_achieved, row.total_variance)],
			[50, 10, -40],
		)


def create_target_distribution(fiscal_year):
	distribution = frappe.new_doc("Monthly Distribution")
	distribution.distribution_id = "Target Report Distribution"
	distribution.fiscal_year = fiscal_year
	distribution.get_months()
	return distribution.insert()


def create_sales_target_doc(
	sales_field_dt, sales_field_name, sales_field_value, fiscal_year, distribution_id
):
	sales_target_doc = frappe.new_doc(sales_field_dt)
	sales_target_doc.set(sales_field_name, sales_field_value)
	sales_target_doc.append(
		"targets",
		{
			"fiscal_year": fiscal_year,
			"target_qty": 50,
			"target_amount": 30000,
			"distribution_id": distribution_id,
		},
	)
	if sales_field_dt == "Sales Partner":
		sales_target_doc.commission_rate = 5
	return sales_target_doc.insert()
