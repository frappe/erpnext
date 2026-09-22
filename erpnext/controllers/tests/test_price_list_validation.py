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

	def test_a_missing_price_list_should_report_rather_than_crash(self):
		invoice = create_sales_invoice(do_not_save=1)
		invoice.selling_price_list = frappe.generate_hash(length=10)

		with self.assertRaises(frappe.ValidationError):
			invoice.validate_price_list()

	def test_internal_transfer_should_keep_the_outward_price_list(self):
		"""The inward document of an internal transfer takes the price list of the outward one, which
		is flagged for the opposite side."""
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
			prepare_data_for_internal_transfer,
		)
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		prepare_data_for_internal_transfer()
		company = "_Test Company with perpetual inventory"
		selling_only = self.create_price_list(selling=1)

		delivery_note = create_delivery_note(
			company=company,
			customer="_Test Internal Customer 2",
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			warehouse="Stores - TCP1",
			target_warehouse=create_warehouse("_Test Transit For Price List", company=company),
			do_not_submit=1,
		)
		delivery_note.selling_price_list = selling_only
		delivery_note.save()
		delivery_note.submit()

		receipt = make_inter_company_purchase_receipt(delivery_note.name)
		receipt.items[0].warehouse = "Stores - TCP1"
		receipt.save()

		self.assertEqual(receipt.buying_price_list, selling_only)

	def test_disabled_price_list_should_still_report_as_disabled(self):
		invoice = create_sales_invoice(do_not_save=1)
		invoice.selling_price_list = self.create_price_list(selling=1, enabled=0)

		with self.assertRaisesRegex(frappe.ValidationError, "is disabled"):
			invoice.save()
