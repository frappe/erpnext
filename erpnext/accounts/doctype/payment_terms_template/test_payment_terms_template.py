# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate

from erpnext.controllers.accounts_controller import get_payment_term_details
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused_for_names,
	make_fenced_user,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentTermsTemplate(ERPNextTestSuite):
	def test_create_template(self):
		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template For Test",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 30,
					}
				],
			}
		)

		self.assertRaises(frappe.ValidationError, template.insert)

		template.append(
			"terms",
			{
				"doctype": "Payment Terms Template Detail",
				"invoice_portion": 50.00,
				"credit_days_based_on": "Day(s) after invoice date",
				"credit_days": 0,
			},
		)

		template.insert()

	def test_credit_days(self):
		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template For Test",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 100.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": -30,
					}
				],
			}
		)

		self.assertRaises(frappe.ValidationError, template.insert)

	def test_no_discount_date_without_discount(self):
		posting_date = "2026-05-29"
		term = frappe._dict(
			{
				"payment_term": "_Test No Discount Term",
				"invoice_portion": 100.0,
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": 0,
				"credit_months": 0,
				"discount_type": "Percentage",
				"discount": 0,
				"discount_validity_based_on": "Day(s) after invoice date",
				"discount_validity": 0,
			}
		)

		details = get_payment_term_details(
			term, posting_date=posting_date, grand_total=100, base_grand_total=100
		)

		self.assertEqual(getdate(details.due_date), getdate(posting_date))
		self.assertIsNone(details.discount_date)

	def test_discount_date_generated_with_discount(self):
		posting_date = "2026-05-29"
		term = frappe._dict(
			{
				"payment_term": "_Test Discount Term",
				"invoice_portion": 100.0,
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": 30,
				"credit_months": 0,
				"discount_type": "Percentage",
				"discount": 5,
				"discount_validity_based_on": "Day(s) after invoice date",
				"discount_validity": 10,
			}
		)

		details = get_payment_term_details(
			term, posting_date=posting_date, grand_total=100, base_grand_total=100
		)

		self.assertEqual(getdate(details.due_date), getdate(add_days(posting_date, 30)))
		self.assertEqual(getdate(details.discount_date), getdate(add_days(posting_date, 10)))

	def test_duplicate_terms(self):
		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template For Test",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 30,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 30,
					},
				],
			}
		)

		self.assertRaises(frappe.ValidationError, template.insert)

	def test_get_payment_terms_fences_the_template(self):
		from erpnext.accounts.services.payment_schedule import get_payment_terms

		template = "_Test Payment Term Template"
		other = frappe.db.get_value("Payment Terms Template", {"name": ["!=", template]})

		def payment_terms_kwargs(name):
			return {"terms_template": name, "grand_total": 100}

		outside = make_fenced_user(
			"ptt-fenced@example.com", ["Accounts User"], [("Payment Terms Template", other)]
		)
		with as_user(outside):
			assert_refused_for_names(
				self,
				get_payment_terms,
				payment_terms_kwargs,
				[template],
				type_gated=True,
				caller_supplied=True,
			)
		inside = make_fenced_user(
			"ptt-fenced@example.com", ["Accounts User"], [("Payment Terms Template", template)]
		)
		with as_user(inside):
			schedule = get_payment_terms(template, grand_total=100)
		total = 0
		for row in schedule:
			total += row.payment_amount
		self.assertEqual(total, 100)

	def test_get_payment_term_details_fences_the_term(self):
		from erpnext.accounts.services.payment_schedule import get_payment_term_details

		def term_kwargs(name):
			return {"term": name, "grand_total": 100}

		outside = make_fenced_user(
			"pt-fenced@example.com", ["Accounts User"], [("Payment Term", "_Test COD")]
		)
		with as_user(outside):
			assert_refused_for_names(
				self,
				get_payment_term_details,
				term_kwargs,
				["_Test N30"],
				type_gated=True,
				caller_supplied=True,
			)
		inside = make_fenced_user("pt-fenced@example.com", ["Accounts User"], [("Payment Term", "_Test N30")])
		with as_user(inside):
			details = get_payment_term_details("_Test N30", grand_total=100)
		self.assertEqual(
			details.payment_amount, frappe.db.get_value("Payment Term", "_Test N30", "invoice_portion")
		)

	def make_term(self, name, **values):
		if not frappe.db.exists("Payment Term", name):
			frappe.get_doc({"doctype": "Payment Term", "payment_term_name": name, **values}).insert()
		return name

	def make_template(self, terms, allocate=0):
		return frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": f"_Test Template {frappe.generate_hash(length=6)}",
				"allocate_payment_based_on_payment_terms": allocate,
				"terms": terms,
			}
		)

	def make_invoice(self, template, posting_date, rate=1000):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		invoice = create_sales_invoice(posting_date=posting_date, rate=rate, do_not_save=1)
		invoice.payment_terms_template = template
		invoice.payment_schedule = []
		return invoice

	def test_schedule_rows_add_up_to_total(self):
		template = self.make_template(
			[
				{"payment_term": self.make_term("_Test Third 1"), "invoice_portion": 33.33, "credit_days": 0},
				{
					"payment_term": self.make_term("_Test Third 2"),
					"invoice_portion": 33.33,
					"credit_days": 30,
				},
				{
					"payment_term": self.make_term("_Test Third 3"),
					"invoice_portion": 33.34,
					"credit_days": 60,
				},
			],
			allocate=1,
		).insert()

		invoice = self.make_invoice(template.name, "2026-10-02", rate=1001)
		invoice.insert()

		amounts = [row.payment_amount for row in invoice.payment_schedule]
		self.assertEqual(amounts, [333.63, 333.63, 333.74])
		self.assertEqual(sum(amounts), invoice.grand_total)
		self.assertEqual(invoice.payment_schedule[-1].outstanding, 333.74)

	def test_template_due_date_counts_from_invoice_date(self):
		from erpnext.accounts.party import get_due_date_from_template

		template = self.make_template(
			[
				{"invoice_portion": 50, "due_date_based_on": "Day(s) after invoice date", "credit_days": 30},
				{"invoice_portion": 50, "due_date_based_on": "Day(s) after invoice date", "credit_days": 60},
			]
		).insert()

		due_date = get_due_date_from_template(template.name, "2026-10-02", None)
		self.assertEqual(getdate(due_date), getdate("2026-12-01"))

	def test_terms_on_the_same_date_can_be_submitted(self):
		template = self.make_template(
			[
				{
					"payment_term": self.make_term("_Test On Invoice Date"),
					"invoice_portion": 50,
					"due_date_based_on": "Day(s) after invoice date",
				},
				{
					"payment_term": self.make_term("_Test Month End"),
					"invoice_portion": 50,
					"due_date_based_on": "Day(s) after the end of the invoice month",
				},
			]
		).insert()

		# a string posting date, as server scripts pass it
		invoice = self.make_invoice(template.name, "2026-08-31")
		invoice.insert()
		invoice.submit()

		self.assertEqual(
			[getdate(row.due_date) for row in invoice.payment_schedule], [getdate("2026-08-31")] * 2
		)

	def test_same_term_twice_is_refused_when_allocating_by_terms(self):
		term = self.make_term("_Test Instalment")
		rows = [
			{"payment_term": term, "invoice_portion": 50, "credit_days": 30},
			{"payment_term": term, "invoice_portion": 50, "credit_days": 60},
		]
		self.assertRaisesRegex(
			frappe.ValidationError, "used more than once", self.make_template(rows, allocate=1).insert
		)

		self.make_template(rows).insert()

	def test_negative_portion_is_refused(self):
		template = self.make_template(
			[
				{"invoice_portion": 150, "credit_days": 0},
				{"invoice_portion": -50, "credit_days": 30},
			]
		)
		self.assertRaisesRegex(frappe.ValidationError, "must be more than 0", template.insert)

	@ERPNextTestSuite.change_settings("Accounts Settings", {"automatically_fetch_payment_terms": 1})
	def test_amount_discount_is_fetched_from_order(self):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		term = self.make_term("_Test Amount Discount")
		template = self.make_template(
			[
				{
					"payment_term": term,
					"invoice_portion": 100,
					"credit_days": 30,
					"discount_type": "Amount",
					"discount": 50,
					"discount_validity_based_on": "Day(s) after invoice date",
					"discount_validity": 10,
				}
			],
			allocate=1,
		).insert()

		order = make_sales_order(qty=1, rate=1000, do_not_save=1)
		order.payment_terms_template = template.name
		order.payment_schedule = []
		order.save()
		order.submit()

		invoice = make_sales_invoice(order.name)
		invoice.insert()
		self.assertEqual(invoice.payment_schedule[0].discount_type, "Amount")
		self.assertEqual(invoice.payment_schedule[0].discount, 50)
