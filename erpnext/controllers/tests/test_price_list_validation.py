import frappe

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite


class TestPriceListValidation(ERPNextTestSuite):
	def create_price_list(self, selling=0, buying=0, enabled=1):
		return (
			frappe.get_doc(
				{
					"doctype": "Price List",
					"price_list_name": frappe.generate_hash(length=10),
					"currency": "INR",
					"selling": selling,
					"buying": buying,
					"enabled": enabled,
				}
			)
			.insert()
			.name
		)

	def test_selling_transaction_should_reject_a_buying_price_list(self):
		invoice = create_sales_invoice(do_not_save=1)
		invoice.selling_price_list = self.create_price_list(buying=1)

		with self.assertRaisesRegex(frappe.ValidationError, "selling transaction"):
			invoice.save()

	def test_buying_transaction_should_reject_a_selling_price_list(self):
		invoice = make_purchase_invoice(do_not_save=1)
		invoice.buying_price_list = self.create_price_list(selling=1)

		with self.assertRaisesRegex(frappe.ValidationError, "buying transaction"):
			invoice.save()

	def test_a_price_list_for_both_sides_should_be_accepted(self):
		price_list = self.create_price_list(selling=1, buying=1)

		invoice = create_sales_invoice(do_not_save=1)
		invoice.selling_price_list = price_list
		invoice.save()

		self.assertEqual(invoice.selling_price_list, price_list)

	def test_disabled_price_list_should_still_report_as_disabled(self):
		invoice = create_sales_invoice(do_not_save=1)
		invoice.selling_price_list = self.create_price_list(selling=1, enabled=0)

		with self.assertRaisesRegex(frappe.ValidationError, "is disabled"):
			invoice.save()
