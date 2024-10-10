import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.report.sales_partner_target_variance_based_on_item_group.sales_partner_target_variance_based_on_item_group import (
	execute,
)
from erpnext.selling.report.sales_person_target_variance_based_on_item_group.test_sales_person_target_variance_based_on_item_group import (
	create_sales_target_doc,
	create_target_distribution,
)


class TestSalesPartnerTargetVarianceBasedOnItemGroup(IntegrationTestCase):
	def setUp(self):
		self.fiscal_year = get_fiscal_year(nowdate())[0]

	def tearDown(self):
		frappe.db.rollback()

	def test_achieved_target_and_variance_for_partner(self):
		# Create a Target Distribution
		distribution = create_target_distribution(self.fiscal_year)

		# Create Sales Partner with targets for the current fiscal year
		sales_partner = create_sales_target_doc(
			"Sales Partner", "partner_name", "Sales Partner 1", self.fiscal_year, distribution.name
		)

		# Create a Sales Invoice for the Partner
		si = create_sales_invoice(
			rate=1000,
			qty=20,
			do_not_submit=True,
		)
		si.sales_partner = sales_partner
		si.commission_rate = 5
		si.submit()

		# Check Achieved Target and Variance for the Sales Partner
		result = execute(
			frappe._dict(
				{
					"fiscal_year": self.fiscal_year,
					"doctype": "Sales Invoice",
					"period": "Yearly",
					"target_on": "Quantity",
				}
			)
		)[1]
		row = frappe._dict(result[0])
		self.assertSequenceEqual(
			[flt(value, 2) for value in (row.total_target, row.total_achieved, row.total_variance)],
			[50, 20, -30],
		)
