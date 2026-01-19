# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

EXTRA_TEST_RECORD_DEPENDENCIES = ["Supplier Group", "Customer Group"]


class TestTaxWithholdingCategory(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# create relevant supplier, etc
		create_records()
		create_tax_withholding_category_records()
		make_pan_no_field()

	def tearDown(self):
		frappe.db.rollback()

	def validate_tax_withholding_entries(self, doctype, docname, expected_entries):
		"""Validate tax withholding entries for a document"""
		entries = frappe.get_all(
			"Tax Withholding Entry",
			filters={"parenttype": doctype, "parent": docname},
			fields=[
				"tax_withholding_category",
				"party_type",
				"party",
				"tax_rate",
				"withholding_amount",
				"taxable_amount",
				"status",
				"taxable_doctype",
				"taxable_name",
				"withholding_doctype",
				"withholding_name",
				"under_withheld_reason",
				"lower_deduction_certificate",
			],
		)

		self.assertEqual(len(entries), len(expected_entries), "Number of entries mismatch")

		# Sort both actual and expected entries for consistent comparison
		def sort_key(entry):
			return (
				entry.get("taxable_doctype", ""),
				entry.get("taxable_name", ""),
				entry.get("withholding_doctype", ""),
				entry.get("withholding_name", ""),
				entry.get("tax_withholding_category", ""),
				entry.get("taxable_amount", 0),
				entry.get("withholding_amount", 0),
				entry.get("under_withheld_reason", "") or "",
				entry.get("lower_deduction_certificate", "") or "",
			)

		sorted_entries = sorted(entries, key=sort_key)
		sorted_expected = sorted(expected_entries, key=sort_key)

		# Normalize empty strings and None values for comparison
		def normalize_entry(entry):
			normalized = entry.copy()
			# Convert None to empty string and empty string to None for consistent comparison
			for field in ["under_withheld_reason", "lower_deduction_certificate"]:
				if field in normalized:
					if normalized[field] == "" or normalized[field] is None:
						normalized[field] = None
			return normalized

		normalized_entries = [normalize_entry(entry) for entry in sorted_entries]
		normalized_expected = [normalize_entry(entry) for entry in sorted_expected]

		self.assertEqual(
			normalized_entries, normalized_expected, "Tax withholding entries do not match expected values"
		)

	def get_tax_withholding_entry(self, **kwargs):
		"""
		Create a tax withholding entry with consistent field ordering
		"""
		entry = {
			"tax_withholding_category": kwargs.get("tax_withholding_category"),
			"party_type": kwargs.get("party_type"),
			"party": kwargs.get("party"),
			"tax_rate": kwargs.get("tax_rate") or 0.0,
			"withholding_amount": kwargs.get("withholding_amount") or 0.0,
			"taxable_amount": kwargs.get("taxable_amount") or 0.0,
			"status": kwargs.get("status"),
			"taxable_doctype": kwargs.get("taxable_doctype") or "",
			"taxable_name": kwargs.get("taxable_name") or "",
			"withholding_doctype": kwargs.get("withholding_doctype") or "",
			"withholding_name": kwargs.get("withholding_name") or "",
			"under_withheld_reason": kwargs.get("under_withheld_reason"),
			"lower_deduction_certificate": kwargs.get("lower_deduction_certificate"),
		}
		return entry

	def setup_party_with_category(self, party_type, party_name, category_name):
		"""Setup party with tax withholding category"""
		frappe.db.set_value(
			party_type,
			party_name,
			"tax_withholding_category",
			category_name,
		)

	def validate_tax_deduction(self, invoice, expected_amount):
		"""Validate invoice tax deduction and grand total"""
		actual_amount = sum([d.base_tax_amount for d in invoice.taxes if d.is_tax_withholding_account])
		self.assertEqual(
			actual_amount, expected_amount, f"Expected TCS charged: {expected_amount}, got: {actual_amount}"
		)

	def cleanup_invoices(self, invoice_list):
		"""Clean up invoices in reverse order to avoid dependency issues"""
		for invoice in reversed(invoice_list):
			invoice.reload()
			if invoice.docstatus == 1:
				invoice.cancel()

	def test_cumulative_threshold_tds(self):
		"Tax withholding entries for cumulative threshold TDS with Tax on excess without single threshold"
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")
		invoices = []

		# First invoice - should be under withheld
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier")
		pi1.submit()

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=0.0,
				status="Under Withheld",
				withholding_doctype=None,
				withholding_name=None,
				under_withheld_reason=None,
			)
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi1.name, expected_entries)

		# Second invoice - should also be under withheld
		pi2 = create_purchase_invoice(supplier="Test TDS Supplier")
		pi2.submit()

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=0.0,
				status="Under Withheld",
				withholding_doctype=None,
				withholding_name=None,
				under_withheld_reason=None,
			)
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi2.name, expected_entries)

		# Third invoice - surpasses cumulative threshold, all should be settled
		pi3 = create_purchase_invoice(supplier="Test TDS Supplier")
		pi3.submit()

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_amount=1000.0,
				tax_rate=10.0,
				taxable_amount=10000.0,
				status="Settled",
				withholding_doctype="Purchase Invoice",
				withholding_name=pi3.name,
				under_withheld_reason=None,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_amount=1000.0,
				tax_rate=10.0,
				taxable_amount=10000.0,
				status="Settled",
				withholding_doctype="Purchase Invoice",
				withholding_name=pi3.name,
				under_withheld_reason=None,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi3.name,
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=1000.0,
				status="Settled",
				withholding_doctype="Purchase Invoice",
				withholding_name=pi3.name,
				under_withheld_reason=None,
			),
		]

		# Validate invoice totals and tax withholding entries
		self.validate_tax_deduction(pi3, 3000)
		self.validate_tax_withholding_entries("Purchase Invoice", pi3.name, expected_entries)
		invoices.append(pi3)

		# Fourth invoice - TDS deducted on every invoice from now on
		pi4 = create_purchase_invoice(supplier="Test TDS Supplier", rate=5000)
		pi4.submit()

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi4.name,
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Settled",
				withholding_doctype="Purchase Invoice",
				withholding_name=pi4.name,
				under_withheld_reason=None,
			)
		]

		# Validate invoice totals and tax withholding entries
		self.validate_tax_deduction(pi4, 500)
		self.validate_tax_withholding_entries("Purchase Invoice", pi4.name, expected_entries)
		invoices.append(pi4)

	def test_cumulative_threshold_tds_with_account_change(self):
		"Cumulative threshold TDS without tax_on_excess, with account change in the middle of the year"
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Multi Account TDS Category")
		invoices = []

		# create invoices for lower than single threshold tax rate
		for _ in range(2):
			pi = create_purchase_invoice(supplier="Test TDS Supplier")
			pi.submit()
			invoices.append(pi)

		# create another invoice whose total when added to previously created invoice,
		# surpasses cumulative threshold
		pi = create_purchase_invoice(supplier="Test TDS Supplier")
		pi.submit()

		# assert equal tax deduction on total invoice amount until now
		self.assertEqual(pi.taxes_and_charges_deducted, 3000)
		self.assertEqual(pi.grand_total, 7000)
		invoices.append(pi)

		# Change account in the middle of the year
		frappe.db.set_value(
			"Tax Withholding Account",
			{"parent": "Multi Account TDS Category"},
			"account",
			"_Test Account VAT - _TC",
		)

		# TDS should be on invoice only even though account is changed
		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=5000)
		pi.submit()

		# assert equal tax deduction on total invoice amount until now
		self.assertEqual(pi.taxes_and_charges_deducted, 500)
		invoices.append(pi)

		# Clean up invoices to avoid clashing
		self.cleanup_invoices(invoices)

	def test_single_threshold_tds(self):
		invoices = []
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier1", "tax_withholding_category", "Single Threshold TDS"
		)
		pi = create_purchase_invoice(supplier="Test TDS Supplier1", rate=20000)
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes_and_charges_deducted, 2000)
		self.assertEqual(pi.grand_total, 18000)

		# check gl entry for the purchase invoice
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pi.name},
			fields=["account", {"SUM": "debit", "as": "debit"}, {"SUM": "credit", "as": "credit"}],
			group_by="account",
		)
		self.assertEqual(len(gl_entries), 3)
		for d in gl_entries:
			if d.account == pi.credit_to:
				self.assertEqual(d.credit, 20000)
				self.assertEqual(d.debit, 2000)
			elif d.account == pi.items[0].get("expense_account"):
				self.assertEqual(d.debit, 20000)
			elif d.account == pi.taxes[0].get("account_head"):
				self.assertEqual(d.credit, 2000)
			else:
				raise ValueError("Account head does not match.")

		pi = create_purchase_invoice(supplier="Test TDS Supplier1")
		pi.submit()
		invoices.append(pi)

		# TDS amount is 1000 because in previous invoices it's already deducted
		self.assertEqual(pi.taxes_and_charges_deducted, 1000)

		self.cleanup_invoices(invoices)

	def test_tax_withholding_category_checks(self):
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier3", "New TDS Category")

		# First Invoice with no tds check
		pi = create_purchase_invoice(supplier="Test TDS Supplier3", rate=20000, do_not_save=True)
		pi.apply_tds = 0
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Second Invoice will apply TDS checked
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier3", rate=20000)
		pi1.submit()
		invoices.append(pi1)

		# Cumulative threshold is 30000
		# Threshold calculation should be only on the Second invoice
		# Second didn't breach, no TDS should be applied
		self.assertEqual(pi1.taxes, [])

		self.cleanup_invoices(invoices)

	def test_cumulative_threshold_with_party_ledger_amount_on_net_total(self):
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier3", "Advance TDS Category")

		# Invoice with tax and without exceeding single and cumulative thresholds
		for _ in range(2):
			pi = create_purchase_invoice(supplier="Test TDS Supplier3", rate=1000, do_not_save=True)
			pi.apply_tds = 1
			pi.append(
				"taxes",
				{
					"category": "Total",
					"charge_type": "Actual",
					"account_head": "_Test Account VAT - _TC",
					"cost_center": "Main - _TC",
					"tax_amount": 500,
					"description": "Test",
					"add_deduct_tax": "Add",
				},
			)
			pi.save()
			pi.submit()
			invoices.append(pi)

		# Third Invoice exceeds single threshold and not exceeding cumulative threshold
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier3", rate=6000)
		pi1.apply_tds = 1
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		# Cumulative threshold is 10,000
		# Threshold calculation should be only on the third invoice
		self.assertEqual(pi1.taxes[0].tax_amount, 800)

		self.cleanup_invoices(invoices)

	def test_cumulative_threshold_with_tax_on_excess_amount(self):
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier3", "New TDS Category")

		# Invoice with tax and without exceeding single and cumulative thresholds
		for _ in range(2):
			pi = create_purchase_invoice(supplier="Test TDS Supplier3", rate=10000, do_not_save=True)
			pi.apply_tds = 1
			pi.append(
				"taxes",
				{
					"category": "Total",
					"charge_type": "Actual",
					"account_head": "_Test Account VAT - _TC",
					"cost_center": "Main - _TC",
					"tax_amount": 500,
					"description": "Test",
				},
			)
			pi.save()
			pi.submit()
			invoices.append(pi)

			# Validate tax withholding entry for each invoice (should be settled with exemption reason)
			expected_entries = [
				self.get_tax_withholding_entry(
					tax_withholding_category="New TDS Category",
					party_type="Supplier",
					party="Test TDS Supplier3",
					tax_rate=10.0,
					taxable_amount=10000.0,
					withholding_amount=0.0,
					status="Settled",
					taxable_doctype="Purchase Invoice",
					taxable_name=pi.name,
					withholding_doctype="Purchase Invoice",
					withholding_name=pi.name,
					under_withheld_reason="Threshold Exemption",
				)
			]
			self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)

		# Third Invoice breaches cumulative threshold
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier3", rate=20000)
		pi1.apply_tds = 1
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		# Validate tax withholding entries for current invoice only
		# For amount before threshold (first 10000): TDS entry with amount zero
		# For amount above threshold (next 10000): TDS entry with TDS applied
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=0.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi1.name,
				under_withheld_reason="Threshold Exemption",
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=1000.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi1.name,
				under_withheld_reason=None,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi1.name, expected_entries)

		# Cumulative threshold is 10,000
		# Threshold calculation should be only on the third invoice
		self.assertTrue(len(pi1.taxes) > 0)
		self.assertEqual(pi1.taxes[0].tax_amount, 1000)

		self.cleanup_invoices(invoices)

	def test_cumulative_threshold_tcs_on_gross_amount(self):
		self.setup_party_with_category("Customer", "Test TCS Customer", "Cumulative Threshold TCS")
		invoices = []

		# First two invoices - below threshold, should be settled with zero TCS
		for _ in range(2):
			si = create_sales_invoice(customer="Test TCS Customer")
			si.append(
				"taxes",
				{
					"category": "Total",
					"charge_type": "Actual",
					"account_head": "TCS - _TC",
					"cost_center": "Main - _TC",
					"tax_amount": 200,
					"description": "Test Gross Tax",
				},
			)
			si.save()
			si.submit()
			invoices.append(si)
			expected_entries = [
				self.get_tax_withholding_entry(
					tax_withholding_category="Cumulative Threshold TCS",
					party_type="Customer",
					party="Test TCS Customer",
					tax_rate=10.0,
					taxable_amount=10200.0,  # including vat amount
					withholding_amount=0.0,
					status="Settled",
					taxable_doctype="Sales Invoice",
					taxable_name=si.name,
					withholding_doctype="Sales Invoice",
					withholding_name=si.name,
					under_withheld_reason="Threshold Exemption",
				)
			]
			self.validate_tax_withholding_entries("Sales Invoice", si.name, expected_entries)

		# Third invoice - breaches threshold, TCS applied only on excess
		si = create_sales_invoice(customer="Test TCS Customer", rate=12000)
		si.append(
			"taxes",
			{
				"category": "Total",
				"charge_type": "Actual",
				"account_head": "TCS - _TC",
				"cost_center": "Main - _TC",
				"tax_amount": 400,
				"description": "Test Gross Tax",
			},
		)
		si.save()
		si.reload()
		si.submit()
		invoices.append(si)
		# For amount before threshold (first 8000 + VAT): TCS entry with amount zero
		# For amount above threshold (next 4000): TCS entry with TCS applied
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=9600.0,
				withholding_amount=0.0,
				status="Settled",
				taxable_doctype="Sales Invoice",
				taxable_name=si.name,
				withholding_doctype="Sales Invoice",
				withholding_name=si.name,
				under_withheld_reason="Threshold Exemption",
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=2800.0,
				withholding_amount=280.0,
				status="Settled",
				taxable_doctype="Sales Invoice",
				taxable_name=si.name,
				withholding_doctype="Sales Invoice",
				withholding_name=si.name,
				under_withheld_reason=None,
			),
		]
		self.validate_tax_withholding_entries("Sales Invoice", si.name, expected_entries)
		self.validate_tax_deduction(si, 280)
		self.assertEqual(si.grand_total, 12680)

		# Fourth invoice - TCS applied on full amount
		si = create_sales_invoice(customer="Test TCS Customer", rate=5000)
		si.append(
			"taxes",
			{
				"category": "Total",
				"charge_type": "Actual",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "Main - _TC",
				"tax_amount": 500,
				"description": "VAT added to test TDS calculation on gross amount",
			},
		)
		si.save()
		si.submit()
		invoices.append(si)
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=5500.0,
				withholding_amount=550.0,
				status="Settled",
				taxable_doctype="Sales Invoice",
				taxable_name=si.name,
				withholding_doctype="Sales Invoice",
				withholding_name=si.name,
				under_withheld_reason=None,
			)
		]
		self.validate_tax_withholding_entries("Sales Invoice", si.name, expected_entries)
		self.validate_tax_deduction(si, 550)
		self.assertEqual(si.grand_total, 6050)

		# cancel invoices to avoid clashing
		self.cleanup_invoices(invoices)

	def test_tcs_on_allocated_advance_payments(self):
		self.setup_party_with_category("Customer", "Test TCS Customer", "Cumulative Threshold TCS")

		vouchers = []

		# create advance payment
		pe = create_payment_entry(
			payment_type="Receive", party_type="Customer", party="Test TCS Customer", paid_amount=30000
		)
		pe.paid_from = "Debtors - _TC"
		pe.paid_to = "Cash - _TC"
		pe.apply_tds = 1
		pe.tax_withholding_category = "Cumulative Threshold TCS"
		pe.submit()
		vouchers.append(pe)

		# Validate payment entry tax withholding entries
		payment_expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=30000.0,
				withholding_amount=3000.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, payment_expected_entries)

		si = create_sales_invoice(customer="Test TCS Customer", rate=50000)
		advances = si.get_advance_entries()
		si.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 30000,
			},
		)
		si.submit()
		vouchers.append(si)

		# Validate TCS charged on Sales Invoice
		# Since PE already collected 3000 TCS (over-withheld), and total required is 5000,
		# the remaining 2000 is settled from PE's over-withheld amount.
		# No new TCS is deducted on SI - the taxes row should be 0.
		tcs_charged = sum([d.base_tax_amount for d in si.taxes if d.account_head == "TCS - _TC"])
		self.assertEqual(tcs_charged, 0)

		# Validate invoice tax withholding entries
		invoice_expected_entries = [
			# Main invoice entry
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=30000,  # Net amount after advance adjustment (50000-30000)
				withholding_amount=0,  # Tax on net amount: 30000 * 10%
				status="Settled",
				taxable_doctype="Sales Invoice",
				taxable_name=si.name,
				withholding_doctype="Sales Invoice",
				withholding_name=si.name,
				under_withheld_reason="Threshold Exemption",
			),
			# Advance allocation adjustment entry
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=20000.0,  # Positive amount that's allocated
				withholding_amount=2000.0,  # No tax on allocated advance
				status="Settled",
				taxable_doctype="Sales Invoice",
				taxable_name=si.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Sales Invoice", si.name, invoice_expected_entries)

		self.cleanup_invoices(vouchers)

	def test_tds_multiple_payments_adjust_only_linked(self):
		"""
		Test that when multiple advance payment entries exist for the same supplier,
		only the payment entry that is linked/allocated to the invoice is adjusted.
		"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")

		vouchers = []

		pe1 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier", paid_amount=5000
		)
		pe1.apply_tds = 1
		pe1.tax_withholding_category = "Cumulative Threshold TDS"
		pe1.save()
		pe1.submit()
		vouchers.append(pe1)

		pe1_expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe1.name, pe1_expected_entries)

		pe2 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier", paid_amount=3000
		)
		pe2.apply_tds = 1
		pe2.tax_withholding_category = "Cumulative Threshold TDS"
		pe2.save()
		pe2.submit()
		vouchers.append(pe2)

		pe2_expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe2.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe2.name, pe2_expected_entries)

		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=40000)
		pi.append(
			"advances",
			{
				"reference_type": pe1.doctype,
				"reference_name": pe1.name,
				"advance_amount": 5000,
				"allocated_amount": 5000,
			},
		)
		pi.submit()
		vouchers.append(pi)

		invoice_expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=35000.0,
				withholding_amount=3500.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, invoice_expected_entries)
		self.cleanup_invoices(vouchers)

	def test_tds_multiple_payments_with_unused_threshold(self):
		"""
		Test multiple payment entries with unused threshold (tax_on_excess_amount enabled).
		Only the linked payment entry should be adjusted, and threshold exemption should apply.
		"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier3", "New TDS Category")

		vouchers = []

		pe1 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier3", paid_amount=5000
		)
		pe1.apply_tds = 1
		pe1.tax_withholding_category = "New TDS Category"
		pe1.save()
		pe1.submit()
		vouchers.append(pe1)

		pe1_expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe1.name, pe1_expected_entries)

		pe2 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier3", paid_amount=3000
		)
		pe2.apply_tds = 1
		pe2.tax_withholding_category = "New TDS Category"
		pe2.save()
		pe2.submit()
		vouchers.append(pe2)

		pe2_expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe2.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe2.name, pe2_expected_entries)

		pi = create_purchase_invoice(supplier="Test TDS Supplier3", rate=40000)
		pi.append(
			"advances",
			{
				"reference_type": pe1.doctype,
				"reference_name": pe1.name,
				"advance_amount": 5000,
				"allocated_amount": 5000,
			},
		)
		pi.submit()
		vouchers.append(pi)

		# Expected entries:
		# 1. Threshold Exemption for first 30000 (no TDS)
		# 2. Remaining 5000 (40000-30000-5000 from PE1) from invoice
		# 3. PE1's 5000 adjusted
		invoice_expected_entries = [
			# Threshold exemption for first 30000
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=30000.0,
				withholding_amount=0.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason="Threshold Exemption",
			),
			# Remaining 5000 from invoice (40000 - 30000 threshold - 5000 PE1)
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
			# PE1's over-withheld adjustment (5000)
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier3",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, invoice_expected_entries)
		self.cleanup_invoices(vouchers)

	def test_tds_withholding_group_different_rates(self):
		"""
		Test that Tax Withholding Group applies different rates for different groups
		within the same Tax Withholding Category.
		"""
		for group_name in ["Individual", "Company"]:
			if not frappe.db.exists("Tax Withholding Group", group_name):
				frappe.get_doc({"doctype": "Tax Withholding Group", "group_name": group_name}).insert()

		fiscal_year = get_fiscal_year(today(), company="_Test Company")
		from_date = fiscal_year[1]
		to_date = fiscal_year[2]

		# Single category with BOTH groups at different rates
		if not frappe.db.exists("Tax Withholding Category", "TDS Group Rate Category"):
			frappe.get_doc(
				{
					"doctype": "Tax Withholding Category",
					"name": "TDS Group Rate Category",
					"category_name": "TDS Group Rate Category",
					"tax_deduction_basis": "Net Total",
					"rates": [
						{
							"from_date": from_date,
							"to_date": to_date,
							"tax_withholding_group": "Individual",
							"tax_withholding_rate": 1,  # 1% for Individual
							"single_threshold": 0,
							"cumulative_threshold": 0,
						},
						{
							"from_date": from_date,
							"to_date": to_date,
							"tax_withholding_group": "Company",
							"tax_withholding_rate": 2,  # 2% for Company
							"single_threshold": 0,
							"cumulative_threshold": 0,
						},
					],
					"accounts": [{"company": "_Test Company", "account": "TDS - _TC"}],
				}
			).insert()

		invoices = []

		self.setup_party_with_category("Supplier", "Test TDS Supplier5", "TDS Group Rate Category")
		frappe.db.set_value("Supplier", "Test TDS Supplier5", "tax_withholding_group", "Individual")
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier5", rate=100000)
		pi1.submit()
		invoices.append(pi1)

		total = sum([d.base_tax_amount for d in pi1.taxes if d.account_head == "TDS - _TC"])
		self.assertEqual(abs(total), 1000, "Individual rate should be 1% (1000 on 100000)")

		self.setup_party_with_category("Supplier", "Test TDS Supplier6", "TDS Group Rate Category")
		frappe.db.set_value("Supplier", "Test TDS Supplier6", "tax_withholding_group", "Company")
		pi2 = create_purchase_invoice(supplier="Test TDS Supplier6", rate=100000)
		pi2.submit()
		invoices.append(pi2)

		total = sum([d.base_tax_amount for d in pi2.taxes if d.account_head == "TDS - _TC"])
		self.assertEqual(abs(total), 2000, "Company rate should be 2% (2000 on 100000)")

		self.cleanup_invoices(invoices)

	def test_tds_calculation_on_net_total(self):
		self.setup_party_with_category("Supplier", "Test TDS Supplier4", "Cumulative Threshold TDS")
		invoices = []

		pi = create_purchase_invoice(supplier="Test TDS Supplier4", rate=20000, do_not_save=True)
		pi.append(
			"taxes",
			{
				"category": "Total",
				"charge_type": "Actual",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "Main - _TC",
				"tax_amount": 1000,
				"description": "VAT added to test TDS calculation on gross amount",
			},
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Second Invoice will apply TDS checked
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier4", rate=20000)
		pi1.submit()
		invoices.append(pi1)

		self.assertEqual(pi1.taxes[0].tax_amount, 4000)

		self.cleanup_invoices(invoices)

	def test_tds_calculation_on_net_total_partial_tds(self):
		self.setup_party_with_category("Supplier", "Test TDS Supplier4", "Cumulative Threshold TDS")
		invoices = []

		# Create purchase invoice with 3 items:
		# 1. No TDS (apply_tds = 0)
		# 2. TDS with Test Service Category (rate 10%, single_threshold=2000, cumulative_threshold=2000, no tax on excess)
		# 3. TDS with New TDS Category (rate 10%, cumulative_threshold=30000, tax on excess enabled)
		item_code = frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name")
		pi = create_purchase_invoice(supplier="Test TDS Supplier4", rate=0, do_not_save=True)
		pi.items = []
		pi.extend(
			"items",
			[
				{
					"doctype": "Purchase Invoice Item",
					"item_code": item_code,
					"qty": 1,
					"rate": 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 0,  # No TDS for this item
				},
				{
					"doctype": "Purchase Invoice Item",
					"item_code": item_code,
					"qty": 1,
					"rate": 5000,  # Above single threshold of 2000 for Test Service Category
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 1,
					"tax_withholding_category": "Test Service Category",
				},
				{
					"doctype": "Purchase Invoice Item",
					"item_code": item_code,
					"qty": 1,
					"rate": 35000,  # Above cumulative threshold for New TDS Category with tax on excess
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 1,
					"tax_withholding_category": "New TDS Category",
				},
			],
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Expected behavior:
		# Item 1: No TDS - no tax withholding entry
		# Item 2: Test Service Category - TDS applies as amount (5000) > single threshold (2000)
		# Item 3: New TDS Category - TDS applies with tax on excess logic as amount (35000) > cumulative threshold (30000)

		# Validate tax withholding entries
		expected_entries = [
			# Item 2: Test Service Category - TDS deducted on full amount since it exceeds single threshold
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Service Category",
				party_type="Supplier",
				party="Test TDS Supplier4",  # Same supplier for all items
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,  # 10% of 5000
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason=None,
			),
			# Item 3: New TDS Category - TDS with tax on excess logic
			# First 30000 (threshold) - no TDS
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier4",
				tax_rate=10.0,
				taxable_amount=30000.0,
				withholding_amount=0.0,  # No TDS on threshold amount
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason="Threshold Exemption",
			),
			# Remaining 5000 (35000-30000) - TDS applies
			self.get_tax_withholding_entry(
				tax_withholding_category="New TDS Category",
				party_type="Supplier",
				party="Test TDS Supplier4",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,  # 10% of excess amount (5000)
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason=None,
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)

		self.validate_tax_deduction(pi, 1000)

		self.cleanup_invoices(invoices)

	def test_tds_deduction_for_po_via_payment_entry(self):
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Cumulative Threshold TDS")
		order = create_purchase_order(supplier="Test TDS Supplier8", rate=40000, do_not_save=True)
		order.append(
			"taxes",
			{
				"category": "Total",
				"charge_type": "Actual",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "Main - _TC",
				"tax_amount": 8000,
				"description": "Test",
			},
		)

		order.save()
		order.submit()
		self.assertEqual(order.taxes[0].tax_amount, 8000)

		payment = get_payment_entry(order.doctype, order.name)
		payment.apply_tds = 1
		payment.tax_withholding_category = "Cumulative Threshold TDS"
		payment.save().submit()
		self.assertEqual(payment.taxes[0].tax_amount, 4800)

	def test_multi_category_single_supplier(self):
		self.setup_party_with_category("Supplier", "Test TDS Supplier5", "Test Service Category")
		invoices = []

		pi = create_purchase_invoice(supplier="Test TDS Supplier5", rate=500, do_not_save=True)
		pi.save()
		pi.submit()
		invoices.append(pi)
		self.assertEqual(pi.items[0].tax_withholding_category, "Test Service Category")

		# Second Invoice will apply TDS checked
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier5", rate=2500, do_not_save=True)
		for item in pi1.items:
			item.apply_tds = 1
			item.tax_withholding_category = "Test Goods Category"
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		self.assertEqual(pi1.taxes[0].tax_amount, 250)

		self.cleanup_invoices(invoices)

	def test_tds_deductions_with_payment_entries(self):
		"""
		Test tax withholding entries across different voucher types and statuses:
		- Purchase Invoice: Regular invoice (Under Withheld - below threshold)
		- Return Invoice: Negative amount (Under Withheld - return, no TDS)
		- Payment Entry: Over Withheld (always)
		- Payment Entry2: Over Withheld (always)
		- Final Invoice: Settlement invoice that settles all previous entries (Settled status)
		"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier6", "Test Multi Invoice Category")
		invoices = []

		# First invoice - below threshold, should be under withheld
		pi = create_purchase_invoice(supplier="Test TDS Supplier6", rate=4000, do_not_save=True)
		pi.apply_tds = 1
		pi.submit()
		invoices.append(pi)

		# Validate tax withholding entry for first invoice
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=4000.0,
				withholding_amount=0.0,
				status="Under Withheld",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="",
				withholding_name="",
				under_withheld_reason=None,
			)
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)

		pe1 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier6", paid_amount=3000
		)
		pe1.apply_tds = 1
		pe1.tax_withholding_category = "Test Multi Invoice Category"
		pe1.save()
		pe1.submit()
		invoices.append(pe1)

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe1.name, expected_entries)

		pe2 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier6", paid_amount=6000
		)
		pe2.apply_tds = 1
		pe2.tax_withholding_category = "Test Multi Invoice Category"
		pe2.save()
		pe2.submit()
		invoices.append(pe2)

		# Validate tax withholding entry for larger payment entry (over withheld)
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=600.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe2.name,
				under_withheld_reason=None,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe2.name, expected_entries)

		# Final invoice - should breach cumulative threshold and settle all previous entries
		pi2 = create_purchase_invoice(supplier="Test TDS Supplier6", rate=12000, do_not_save=True)
		pi2.apply_tds = 1
		pi2.tax_withholding_category = "Test Multi Invoice Category"
		advances = pi2.get_advance_entries()
		pi2.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": advances[0].amount,
			},
		)
		pi2.append(
			"advances",
			{
				"reference_type": advances[1].reference_type,
				"reference_name": advances[1].reference_name,
				"advance_amount": advances[1].amount,
				"allocated_amount": advances[1].amount,
			},
		)
		pi2.save()
		pi2.submit()
		invoices.append(pi2)

		# Validate tax withholding entries for final invoice (should settle previous entries)
		# Based on actual system behavior, this creates 2 settlement entries:
		# 1. Settlement for first invoice (4000, status: Settled)
		# 2. Entry for final invoice itself (9000, status: Settled)
		expected_entries = [
			# Settlement for first invoice
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=4000.0,
				withholding_amount=400.0,  # 10% of 4000
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,  # First invoice
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,  # Final invoice settles it
				under_withheld_reason=None,
			),
			# against first payment entry
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=3000.0,  # Final invoice amount
				withholding_amount=300.0,  # TDS on final invoice
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Final invoice itself
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
				under_withheld_reason=None,
			),
			# against second payment entry
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,  # Final invoice amount
				withholding_amount=600.0,  # TDS on final invoice
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Final invoice itself
				withholding_doctype="Payment Entry",
				withholding_name=pe2.name,
				under_withheld_reason=None,
			),
			# against second payment entry
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=3000.0,  # Final invoice amount
				withholding_amount=300.0,  # TDS on final invoice
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Final invoice itself
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
				under_withheld_reason=None,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi2.name, expected_entries)

		# validate duplicate entries in Purchase Invoice 1
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=4000.0,
				withholding_amount=400.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
				under_withheld_reason=None,
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)
		# validate duplicate entries in payment entry 1
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=3000.0,  # Final invoice amount
				withholding_amount=300.0,  # TDS on final invoice
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Final invoice itself
				withholding_doctype="Payment Entry",
				withholding_name=pe1.name,
				under_withheld_reason=None,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe1.name, expected_entries)

		# Validate duplicate entries in payment entry 2
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,  # Final invoice amount
				withholding_amount=600.0,  # TDS on final invoice
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Final invoice itself
				withholding_doctype="Payment Entry",
				withholding_name=pe2.name,
				under_withheld_reason=None,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe2.name, expected_entries)

		self.cleanup_invoices(invoices)

	def test_tds_deduction_with_partial_payment_adjustment(self):
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier6", "Test Multi Invoice Category")

		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier6", paid_amount=6000
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = "Test Multi Invoice Category"
		pe.save()
		pe.submit()
		invoices.append(pe)

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=600.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)

		pi = create_purchase_invoice(supplier="Test TDS Supplier6", rate=12000, do_not_save=True)
		pi.apply_tds = 1
		advances = pi.get_advance_entries()
		pi.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 3600,
			},
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		expected_entries = [
			# against first payment entry
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=4000.0,
				withholding_amount=400.0,  # 600 * 6000/(6000-5400)
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,  # Final invoice itself
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason=None,
			),
			# against remaining invoice
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=8000.0,  # Final invoice amount
				withholding_amount=800.0,  # TDS on final invoice
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,  # Final invoice itself
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason=None,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)
		# validate duplicate entries
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=4000.0,
				withholding_amount=400.0,  # 600 * 6000/(6000-5400)
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,  # Final invoice itself
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason=None,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=2000.0,
				withholding_amount=200.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)
		self.cleanup_invoices(invoices)

	def test_lower_deduction_certificate_application(self):
		frappe.db.set_value(
			"Supplier",
			"Test LDC Supplier",
			{
				"tax_withholding_category": "Test Service Category",
				"pan": "ABCTY1234D",
			},
		)

		create_lower_deduction_certificate(
			supplier="Test LDC Supplier",
			certificate_no="1AE0423AAJ",
			tax_withholding_category="Test Service Category",
			tax_rate=2,
			limit=50000,
		)

		pi1 = create_purchase_invoice(supplier="Test LDC Supplier", rate=35000)
		pi1.submit()
		self.assertEqual(pi1.taxes[0].tax_amount, 700)

		pi2 = create_purchase_invoice(supplier="Test LDC Supplier", rate=35000)
		pi2.submit()
		self.assertEqual(pi2.taxes[0].tax_amount, 2300)

		pi3 = create_purchase_invoice(supplier="Test LDC Supplier", rate=35000)
		pi3.submit()
		self.assertEqual(pi3.taxes[0].tax_amount, 3500)

		self.cleanup_invoices([pi1, pi2, pi3])

	def test_ldc_at_0_rate(self):
		frappe.db.set_value(
			"Supplier",
			"Test LDC Supplier",
			{
				"tax_withholding_category": "Test Service Category",
				"pan": "ABCTY1234D",
			},
		)

		fiscal_year = get_fiscal_year(today(), company="_Test Company")
		valid_from = fiscal_year[1]
		valid_upto = add_months(valid_from, 1)
		create_lower_deduction_certificate(
			supplier="Test LDC Supplier",
			certificate_no="1AE0423AAJ",
			tax_withholding_category="Test Service Category",
			tax_rate=0,
			limit=50000,
			valid_from=valid_from,
			valid_upto=valid_upto,
		)

		pi1 = create_purchase_invoice(
			supplier="Test LDC Supplier", rate=35000, posting_date=valid_from, set_posting_time=True
		)
		pi1.submit()
		self.assertEqual(pi1.taxes, [])

		pi2 = create_purchase_invoice(
			supplier="Test LDC Supplier",
			rate=35000,
			posting_date=add_days(valid_upto, 1),
			set_posting_time=True,
		)
		pi2.submit()
		self.assertEqual(len(pi2.taxes), 1)
		# pi1 net total shouldn't be included as it lies within LDC at rate of '0'
		self.assertEqual(pi2.taxes[0].tax_amount, 3500)
		self.cleanup_invoices([pi1, pi2])

	def test_payment_entry_with_ldc_and_invoice_adjustment(self):
		"""
		Test: Payment Entry with LDC, then Invoice, with correct tax adjustment.
		- Payment Entry (advance) is made and tax is deducted at LDC rate
		- Purchase Invoice is created for a higher amount
		- For the portion of invoice covered by advance, tax is adjusted at LDC rate
		- For the remaining invoice amount, tax is deducted at normal rate
		"""

		invoices = []
		pan = "ABCTY1234D"
		supplier = "Test LDC Supplier"
		category = "Test Service Category"
		ldc_no = "TEST-1"

		frappe.db.set_value(
			"Supplier",
			supplier,
			{
				"tax_withholding_category": category,
				"pan": pan,
			},
		)

		create_lower_deduction_certificate(
			supplier=supplier,
			certificate_no=ldc_no,
			tax_withholding_category=category,
			tax_rate=0,
			limit=10000,
		)

		# Payment Entry (advance) with LDC
		advance_amount = 6000.0
		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party=supplier, paid_amount=advance_amount
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = category
		pe.save()
		pe.submit()
		invoices.append(pe)

		# Validate payment entry tax withholding entries (LDC rate)
		expected_pe_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=advance_amount,
				withholding_amount=0.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_pe_entries)

		# Now create and link the invoice (do not update PE after this point)
		invoice_amount = 15000
		pi = create_purchase_invoice(
			supplier=supplier,
			rate=invoice_amount,
		)

		advances = pi.get_advance_entries()
		pi.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": advance_amount,
			},
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Validate invoice tax withholding entries
		expected_pi_entries = [
			# LDC portion (settled)
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=advance_amount,
				withholding_amount=0.0,
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
				status="Settled",
			),
			# Balance LDC portion (settled)
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=4000.0,
				withholding_amount=0.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
			),
			# Balance LDC portion (settled)
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
				under_withheld_reason=None,
				lower_deduction_certificate=None,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_pi_entries)

		# validate duplicate entries in payment entry
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=advance_amount,
				withholding_amount=0.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
			)
		]

		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)

		self.cleanup_invoices(invoices)

	def test_payment_entry_with_ldc_and_partial_invoice_adjustment(self):
		"""
		Test: Payment Entry with LDC, then Invoice, with correct tax adjustment.
		- Payment Entry (advance) is made and tax is deducted at LDC rate
		- Purchase Invoice is created for a higher amount
		- For the portion of invoice covered by advance, tax is adjusted at LDC rate
		- For the remaining invoice amount, tax is deducted at normal rate
		"""

		invoices = []
		pan = "ABCTY1234D"
		supplier = "Test LDC Supplier"
		category = "Test Service Category"
		ldc_no = "TEST-1"

		frappe.db.set_value(
			"Supplier",
			supplier,
			{
				"tax_withholding_category": category,
				"pan": pan,
			},
		)

		create_lower_deduction_certificate(
			supplier=supplier,
			certificate_no=ldc_no,
			tax_withholding_category=category,
			tax_rate=0,
			limit=15000,
		)

		# Payment Entry (advance) with LDC
		advance_amount = 6000.0
		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party=supplier, paid_amount=advance_amount
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = category
		pe.save()
		pe.submit()
		invoices.append(pe)

		# Validate payment entry tax withholding entries (LDC rate)
		expected_pe_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=advance_amount,
				withholding_amount=0.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_pe_entries)

		# Now create and link the invoice (do not update PE after this point)
		invoice_amount = 3000.0
		pi = create_purchase_invoice(
			supplier=supplier,
			rate=invoice_amount,
		)

		advances = pi.get_advance_entries()
		pi.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": invoice_amount,
			},
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Validate invoice tax withholding entries
		expected_pi_entries = [
			# LDC portion (settled)
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=invoice_amount,
				withholding_amount=0.0,
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
				status="Settled",
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_pi_entries)

		# validate duplicate entries in payment entry
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=invoice_amount,  # 3000
				withholding_amount=0.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category=category,
				party_type="Supplier",
				party=supplier,
				tax_rate=0.0,
				taxable_amount=advance_amount - invoice_amount,  # 6000-3000 = 3000
				withholding_amount=0.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
				under_withheld_reason="Lower Deduction Certificate",
				lower_deduction_certificate=ldc_no,
			),
		]

		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)
		self.cleanup_invoices(invoices)

	def set_previous_fy_and_tax_category(self):
		test_company = "_Test Company"
		category = "Cumulative Threshold TDS"

		def add_company_to_fy(fy, company):
			if not [x.company for x in fy.companies if x.company == company]:
				fy.append("companies", {"company": company})
				fy.save()

		# setup previous fiscal year
		fiscal_year = get_fiscal_year(today(), company=test_company)
		if prev_fiscal_year := get_fiscal_year(add_days(fiscal_year[1], -10)):
			self.prev_fy = frappe.get_doc("Fiscal Year", prev_fiscal_year[0])
			add_company_to_fy(self.prev_fy, test_company)
		else:
			# make previous fiscal year
			start = datetime.date(fiscal_year[1].year - 1, fiscal_year[1].month, fiscal_year[1].day)
			end = datetime.date(fiscal_year[2].year - 1, fiscal_year[2].month, fiscal_year[2].day)
			self.prev_fy = frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year_start_date": start,
					"year_end_date": end,
					"companies": [{"company": test_company}],
				}
			)
			self.prev_fy.save()

		# setup tax withholding category for previous fiscal year
		cat = frappe.get_doc("Tax Withholding Category", category)
		cat.append(
			"rates",
			{
				"from_date": self.prev_fy.year_start_date,
				"to_date": self.prev_fy.year_end_date,
				"tax_withholding_rate": 10,
				"single_threshold": 0,
				"cumulative_threshold": 30000,
			},
		)
		cat.save()

	def test_tds_across_fiscal_year(self):
		"""
		Advance TDS on previous fiscal year should be properly allocated on Invoices in upcoming fiscal year
		--||-----FY 2023-----||-----FY 2024-----||--
		--||-----Advance-----||---Inv1---Inv2---||--
		"""
		self.set_previous_fy_and_tax_category()
		supplier = "Test TDS Supplier"
		# Cumulative threshold 30000 and tax rate 10%
		category = "Cumulative Threshold TDS"
		frappe.db.set_value(
			"Supplier",
			supplier,
			{
				"tax_withholding_category": category,
				"pan": "ABCTY1234D",
			},
		)
		po_and_advance_posting_date = add_days(self.prev_fy.year_end_date, -10)
		po = create_purchase_order(supplier=supplier, qty=10, rate=10000)
		po.transaction_date = po_and_advance_posting_date
		po.taxes = []
		po.save().submit()

		# Partial advance
		payment = get_payment_entry(po.doctype, po.name)
		payment.posting_date = po_and_advance_posting_date
		payment.paid_amount = 60000
		payment.apply_tds = 1
		payment.tax_withholding_category = category
		payment.references = []
		payment.taxes = []
		payment.save().submit()

		self.assertEqual(len(payment.taxes), 1)
		self.assertEqual(payment.taxes[0].tax_amount, 6000)

		# Multiple partial invoices
		payment.reload()
		pi1 = make_purchase_invoice(source_name=po.name)
		pi1.apply_tds = True
		pi1.tax_withholding_category = category
		pi1.items[0].qty = 3
		pi1.items[0].rate = 10000
		advances = pi1.get_advance_entries()
		pi1.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 30000,
			},
		)
		pi1.save().submit()
		pi1.reload()
		payment.reload()
		self.assertEqual(pi1.taxes, [])
		self.assertEqual(payment.taxes[0].tax_amount, 6000)

		pi2 = make_purchase_invoice(source_name=po.name)
		pi2.apply_tds = True
		pi2.tax_withholding_category = category
		pi2.items[0].qty = 3
		pi2.items[0].rate = 10000
		advances = pi2.get_advance_entries()
		pi2.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 30000,
			},
		)
		pi2.save().submit()
		pi2.reload()
		payment.reload()
		self.assertEqual(pi2.taxes, [])
		self.assertEqual(payment.taxes[0].tax_amount, 6000)

	@IntegrationTestCase.change_settings("Accounts Settings", {"delete_linked_ledger_entries": 1})
	def test_tds_payment_entry_cancellation(self):
		"""
		Test payment entry cancellation clears withholding references from matched entries
		"""
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier6", "Test Multi Invoice Category")

		# Create payment entry with tax withholding
		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier6", paid_amount=6000
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = "Test Multi Invoice Category"
		pe.save()
		pe.submit()
		invoices.append(pe)

		# Verify initial "Over Withheld" entry
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=600.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)

		# Create purchase invoice that settles the payment entry
		pi = create_purchase_invoice(supplier="Test TDS Supplier6", rate=8000, do_not_save=True)
		pi.apply_tds = 1
		advances = pi.get_advance_entries()
		pi.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 6000,
			},
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Verify entries after invoice creation (should have Settled and Duplicate statuses)
		expected_pi_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=600.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=2000.0,
				withholding_amount=200.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_pi_entries)

		# Verify duplicate entry in payment entry
		expected_pe_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=600.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_pe_entries)

		# Cancel the payment entry (reload first to avoid timestamp mismatch)
		pe.reload()
		pe.cancel()

		# After payment entry cancellation, the purchase invoice entries should have:
		# - Withholding references cleared (empty doctype and name)
		# - Status changed to "Under Withheld"
		# - Withholding amounts set to 0
		expected_pi_entries_after_cancel = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=0.0,  # Cleared
				status="Under Withheld",  # Changed
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="",  # Cleared
				withholding_name="",  # Cleared
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=2000.0,
				withholding_amount=200.0,  # Not cleared (same document)
				status="Settled",  # Unchanged (same document)
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_pi_entries_after_cancel)

		pi1 = create_purchase_invoice(supplier="Test TDS Supplier6", rate=8000, do_not_save=True)
		pi1.apply_tds = 1
		pi1.tax_withholding_category = "Test Multi Invoice Category"
		pi1.submit()
		invoices.append(pi1)

		expected_entries = [
			# Adjust previous purchase invoice
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=6000.0,
				withholding_amount=600,  # Cleared
				status="Settled",  # Changed
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi1.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier6",
				tax_rate=10.0,
				taxable_amount=8000.0,
				withholding_amount=800,  # Cleared
				status="Settled",  # Changed
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi1.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi1.name, expected_entries)
		self.cleanup_invoices(invoices)

	@IntegrationTestCase.change_settings("Accounts Settings", {"delete_linked_ledger_entries": 1})
	def test_tds_purchase_invoice_cancellation(self):
		"""
		Test that after cancellation, new documents get automatically adjusted against remaining entries
		"""
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Test Multi Invoice Category")

		# Create payment entry with tax withholding
		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier8", paid_amount=10000
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = "Test Multi Invoice Category"
		pe.save()
		pe.submit()
		invoices.append(pe)

		# Create first purchase invoice
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=10000, do_not_save=True)
		pi1.apply_tds = 1
		pi1.tax_withholding_category = "Test Multi Invoice Category"
		advances = pi1.get_advance_entries()
		pi1.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 4500,
			},
		)
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		# Verify entries after first invoice
		expected_pe_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_pe_entries)

		# Cancel the first purchase invoice
		pi1.cancel()

		# After cancellation, payment entry should be back to single "Over Withheld" entry
		expected_pe_entries_after_cancel = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_pe_entries_after_cancel)

		# Create new purchase invoice - should automatically adjust against "Over Withheld" entries
		pi2 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=7000, do_not_save=True)
		pi2.apply_tds = 1
		pi2.tax_withholding_category = "Test Multi Invoice Category"
		advances = pi2.get_advance_entries()
		pi2.append(
			"advances",
			{
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": advances[0].amount,
				"allocated_amount": 5500,
			},
		)
		pi2.save()
		pi2.submit()
		invoices.append(pi2)

		# Verify automatic adjustment works correctly
		expected_pi2_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=2000.0,
				withholding_amount=200.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi2.name, expected_pi2_entries)

		# Payment entry should now have the remaining amount as "Over Withheld"
		expected_pe_entries_after_pi2 = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=2000.0,
				withholding_amount=200.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,
				withholding_amount=500.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_pe_entries_after_pi2)

		self.cleanup_invoices(invoices)

	def test_tds_deduction_in_purchase_return(self):
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")

		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=40000)
		pi.submit()

		self.assertEqual(pi.taxes_and_charges_deducted, 4000)

		pi_return = create_purchase_invoice(supplier="Test TDS Supplier", is_return=1, qty=-1, rate=40000)
		pi_return.return_against = pi.name
		pi_return.save()
		pi_return.submit()

		self.assertEqual(pi_return.taxes_and_charges_deducted, -4000)
		self.cleanup_invoices([pi, pi_return])

	def test_tds_purchase_invoice_cancellation_and_adjustment(self):
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Test Multi Invoice Category")

		pi1 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=3000, do_not_save=True)
		pi1.apply_tds = 1
		pi1.tax_withholding_category = "Test Multi Invoice Category"
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		pi2 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=10000, do_not_save=True)
		pi2.apply_tds = 1
		pi2.tax_withholding_category = "Test Multi Invoice Category"
		pi2.save()
		pi2.submit()
		invoices.append(pi2)

		pi1.reload()
		pi1.cancel()

		pi3 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=3000, do_not_save=True)
		pi3.apply_tds = 1
		pi3.tax_withholding_category = "Test Multi Invoice Category"
		pi3.save()
		pi3.submit()
		invoices.append(pi3)

		# Over-Withheld amount in pi2 will get adjusted
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi3.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
			)
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi3.name, expected_entries)
		self.cleanup_invoices(invoices)

	def test_tds_for_return_invoices(self):
		"""Test TDS handling for return invoices with 3-entry cancellation approach"""
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Test Multi Invoice Category")

		# Create return invoice
		pi1 = create_purchase_invoice(
			supplier="Test TDS Supplier8", rate=3000, is_return=1, qty=-1, do_not_save=True
		)
		pi1.apply_tds = 1
		pi1.tax_withholding_category = "Test Multi Invoice Category"
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		# Create regular invoice that breaches threshold
		pi2 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=10000, do_not_save=True)
		pi2.apply_tds = 1
		pi2.tax_withholding_category = "Test Multi Invoice Category"
		pi2.save()
		pi2.submit()
		invoices.append(pi2)

		# Before cancellation: 2 entries (cross-referenced settlement)
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=-3000.0,
				withholding_amount=-300.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=1000.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,  # pi2 settles against itself after adjustment
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi2.name, expected_entries)

		# Duplicate Entries in P1 before cancellation
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=-3000.0,
				withholding_amount=-300.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi1.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
			)
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi1.name, expected_entries)

		pi1.reload()
		pi1.cancel()

		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=1000.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=-3000.0,
				withholding_amount=-300.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
				under_withheld_reason=None,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=0.0,
				status="Under Withheld",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Points to withholding document, not cancelled return
				withholding_doctype="",
				withholding_name="",
				under_withheld_reason="",
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi2.name, expected_entries)

		# Test future invoice adjustment against the under withheld credit
		pi3 = create_purchase_invoice(supplier="Test TDS Supplier8", rate=5000, do_not_save=True)
		pi3.apply_tds = 1
		pi3.tax_withholding_category = "Test Multi Invoice Category"
		pi3.save()
		pi3.submit()
		invoices.append(pi3)

		# pi3 should adjust against the under withheld entry from pi1 cancellation
		expected_entries = [
			# Settlement of the cancelled return invoice credit
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # References the source of under withheld
				withholding_doctype="Purchase Invoice",
				withholding_name=pi3.name,
			),
			# Remaining amount with normal tax
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=5000.0,  # 5000 - 3000 already adjusted
				withholding_amount=500.0,  # 2000 * 10%
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi3.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi3.name,
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi3.name, expected_entries)

		# expected entries in pi2
		expected_entries = [
			# Original pi2 entry (unchanged)
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=10000.0,
				withholding_amount=1000.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
			),
			# Entry 1: Original entry from pi1 made settled (self-settle)
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=-3000.0,
				withholding_amount=-300.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi2.name,
				under_withheld_reason=None,
			),
			# Entry 2: Under withheld entry for future adjustment (taxable fields point to pi2)
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=3000.0,
				withholding_amount=300.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi2.name,  # Points to withholding document, not cancelled return
				withholding_doctype="Purchase Invoice",
				withholding_name=pi3.name,
				under_withheld_reason="",
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi2.name, expected_entries)

		self.cleanup_invoices(invoices)

	def test_manual_tax_withholding_validation(self):
		"""Test validation when user manually overrides tax withholding entries with incorrect amounts"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier6", "Test Multi Invoice Category")

		# Create purchase invoice with manual override
		pi = create_purchase_invoice(supplier="Test TDS Supplier6", rate=20000, do_not_save=True)
		pi.apply_tds = 1
		pi.ignore_tax_withholding_threshold = 1
		pi.save()

		pi.override_tax_withholding_entries = 1  # Enable manual override
		pi.tax_withholding_entries[0].withholding_amount = 1500  # incorrect  tax withheld
		self.assertRaisesRegex(
			frappe.ValidationError,
			r"Row #\d+: Withholding Amount \d+(\.\d+)? does not match calculated amount \d+(\.\d+)?",
			pi.save,
		)

		pi.reload()
		pi.tax_withholding_entries[0].taxable_amount = 15000  # correct taxable amount
		pi.save()

	def test_manual_tax_adjustment_with_partial_adjustment_and_rate_change(self):
		"""Test manual tax adjustment where tax rate is changed during adjustment between payment and invoice"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Test Multi Invoice Category")

		# Step 1: Create a Payment Entry with over withheld amount at 10% rate
		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier8", paid_amount=150000
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = "Test Multi Invoice Category"
		pe.save().submit()

		# Step 2: Create Purchase Invoice with partial adjustment and manual rate change
		pi = create_purchase_invoice(supplier="Test TDS Supplier8", rate=80000, do_not_save=True)
		pi.override_tax_withholding_entries = 1  # Enable manual override
		pi.tax_withholding_entries = []

		# Entry 1: Partial adjustment with new tax rate (12% instead of 10%)
		pi.append(
			"tax_withholding_entries",
			{
				"tax_withholding_category": "Test Multi Invoice Category",
				"party_type": "Supplier",
				"party": "Test TDS Supplier8",
				"tax_rate": 12.0,  # Changed rate from 10% to 12%
				"taxable_amount": 50000.0,  # Partial taxable amount
				"withholding_amount": 6000.0,  # 50000 * 12% = 6000
				"taxable_doctype": "Purchase Invoice",
				"taxable_name": pi.name,
				"withholding_doctype": "Payment Entry",
				"withholding_name": pe.name,
				"conversion_rate": 1.0,
			},
		)

		# Entry 2: Remaining taxable amount under withheld
		pi.append(
			"tax_withholding_entries",
			{
				"tax_withholding_category": "Test Multi Invoice Category",
				"party_type": "Supplier",
				"party": "Test TDS Supplier8",
				"tax_rate": 12.0,  # Same new rate
				"taxable_amount": 30000.0,  # Remaining taxable amount (80000 - 50000)
				"withholding_amount": 3600.0,  # 30000 * 12% = 3600
				"taxable_doctype": "Purchase Invoice",
				"taxable_name": pi.name,
				"withholding_doctype": "Purchase Invoice",
				"withholding_name": pi.name,
				"conversion_rate": 1.0,
			},
		)

		pi.save()
		pi.reload()
		pi.submit()

		# Step 3: Verify the tax withholding entries
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=12.0,  # Updated rate
				taxable_amount=50000.0,
				withholding_amount=6000.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=12.0,  # Updated rate
				taxable_amount=30000.0,
				withholding_amount=3600.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)

		# expected_entries in pe
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=12.0,  # Updated rate
				taxable_amount=50000.0,
				withholding_amount=6000.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,  # Updated rate
				taxable_amount=90000.0,
				withholding_amount=9000.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]

		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)

	def test_manual_tax_adjustment_with_rate_change(self):
		"""Test manual tax adjustment where tax rate is changed during adjustment between payment and invoice"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Test Multi Invoice Category")

		# Step 1: Create a Payment Entry with over withheld amount at 10% rate
		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier8", paid_amount=150000
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = "Test Multi Invoice Category"
		pe.save().submit()

		# Step 2: Create Purchase Invoice with partial adjustment and manual rate change
		pi = create_purchase_invoice(supplier="Test TDS Supplier8", rate=80000, do_not_save=True)
		pi.override_tax_withholding_entries = 1  # Enable manual override
		pi.tax_withholding_entries = []

		# Entry 1: Partial adjustment with new tax rate (12% instead of 10%)
		pi.append(
			"tax_withholding_entries",
			{
				"tax_withholding_category": "Test Multi Invoice Category",
				"party_type": "Supplier",
				"party": "Test TDS Supplier8",
				"tax_rate": 30.0,  # Changed rate from 10% to 12%
				"taxable_amount": 50000.0,  # Partial taxable amount
				"withholding_amount": 15000.0,  # 50000 * 12% = 6000
				"taxable_doctype": "Purchase Invoice",
				"taxable_name": pi.name,
				"withholding_doctype": "Payment Entry",
				"withholding_name": pe.name,
				"conversion_rate": 1.0,
			},
		)

		# Entry 2: Remaining taxable amount under withheld
		pi.append(
			"tax_withholding_entries",
			{
				"tax_withholding_category": "Test Multi Invoice Category",
				"party_type": "Supplier",
				"party": "Test TDS Supplier8",
				"tax_rate": 12.0,  # Same new rate
				"taxable_amount": 30000.0,  # Remaining taxable amount (80000 - 50000)
				"withholding_amount": 3600.0,  # 30000 * 12% = 3600
				"taxable_doctype": "Purchase Invoice",
				"taxable_name": pi.name,
				"withholding_doctype": "Purchase Invoice",
				"withholding_name": pi.name,
				"conversion_rate": 1.0,
			},
		)

		pi.save()
		pi.reload()
		pi.submit()

		# Step 3: Verify the tax withholding entries
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=30.0,  # Updated rate
				taxable_amount=50000.0,
				withholding_amount=15000.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=12.0,  # Updated rate
				taxable_amount=30000.0,
				withholding_amount=3600.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
		]

		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, expected_entries)

		# expected_entries in pe
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=30.0,  # Updated rate
				taxable_amount=50000.0,
				withholding_amount=15000.0,
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]

		self.validate_tax_withholding_entries("Payment Entry", pe.name, expected_entries)

	def test_manual_tax_adjustment_with_zero_rate(self):
		"""Test manual tax adjustment where tax rate is changed to zero during adjustment"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier8", "Test Multi Invoice Category")

		pe = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier8", paid_amount=100000
		)
		pe.apply_tds = 1
		pe.tax_withholding_category = "Test Multi Invoice Category"
		pe.save().submit()

		pe_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,
				taxable_amount=100000.0,
				withholding_amount=10000.0,
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, pe_expected)

		pi = create_purchase_invoice(supplier="Test TDS Supplier8", rate=50000, do_not_save=True)
		pi.override_tax_withholding_entries = 1
		pi.tax_withholding_entries = []

		pi.append(
			"tax_withholding_entries",
			{
				"tax_withholding_category": "Test Multi Invoice Category",
				"party_type": "Supplier",
				"party": "Test TDS Supplier8",
				"tax_rate": 0.0,  # Zero rate
				"taxable_amount": 50000.0,
				"withholding_amount": 0.0,  # No withholding at zero rate
				"taxable_doctype": "Purchase Invoice",
				"taxable_name": pi.name,
				"withholding_doctype": "Payment Entry",
				"withholding_name": pe.name,
				"conversion_rate": 1.0,
			},
		)

		pi.save()
		pi.submit()

		# Step 3: Verify the tax withholding entries on invoice
		pi_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=0.0,
				taxable_amount=50000.0,
				withholding_amount=0.0,
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, pi_expected)

		# Verify Payment Entry entries after adjustment
		# PE should have:
		# 1. Duplicate entry (adjusted 50000 portion with zero rate)
		# 2. Over Withheld entry (remaining 50000 portion at 10%)
		pe_expected_after = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=0.0,  # Updated to zero rate
				taxable_amount=50000.0,  # Preserved from manual entry
				withholding_amount=0.0,  # Zero because rate is zero
				status="Duplicate",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Test Multi Invoice Category",
				party_type="Supplier",
				party="Test TDS Supplier8",
				tax_rate=10.0,  # Original rate
				taxable_amount=50000.0,  # Adjusted taxable
				withholding_amount=10000.0,  # Original amount (not split)
				status="Over Withheld",  # Still over withheld
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, pe_expected_after)

		self.cleanup_invoices([pe, pi])

	def test_tds_on_journal_entry_for_supplier(self):
		"""Test TDS deduction for Supplier in Debit Note"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")

		jv = make_journal_entry_with_tax_withholding(
			party_type="Supplier",
			party="Test TDS Supplier",
			voucher_type="Debit Note",
			amount=50000,
			save=False,
		)
		jv.apply_tds = 1
		jv.tax_withholding_category = "Cumulative Threshold TDS"
		jv.save()

		# Again saving should not change tds amount
		jv.user_remark = "Test TDS on Journal Entry for Supplier"
		jv.save()
		jv.submit()

		# TDS = 50000 * 10% = 5000
		self.assertEqual(len(jv.accounts), 3)

		# Find TDS account row
		tds_row = None
		supplier_row = None
		for row in jv.accounts:
			if row.get("is_tax_withholding_account"):
				tds_row = row
			elif row.party_type == "Supplier":
				supplier_row = row

		self.assertIsNotNone(tds_row, "TDS account row should be created")
		self.assertIsNotNone(supplier_row, "Supplier account row should exist")

		# TDS should be credited (liability to government)
		self.assertEqual(tds_row.credit, 5000)
		self.assertEqual(tds_row.debit, 0)

		# Supplier credit should be reduced by TDS amount
		self.assertEqual(supplier_row.credit, 45000)  # 50000 - 5000

		# Validate tax withholding entries
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=50000.0,
				withholding_amount=5000.0,
				status="Settled",
				taxable_doctype="Journal Entry",
				taxable_name=jv.name,
				withholding_doctype="Journal Entry",
				withholding_name=jv.name,
			)
		]
		self.validate_tax_withholding_entries("Journal Entry", jv.name, expected_entries)

	def test_tcs_on_journal_entry_for_customer(self):
		"""Test TCS collection for Customer in Credit Note"""
		self.setup_party_with_category("Customer", "Test TCS Customer", "Cumulative Threshold TCS")

		# Create Credit Note with amount exceeding threshold
		jv = make_journal_entry_with_tax_withholding(
			party_type="Customer",
			party="Test TCS Customer",
			voucher_type="Credit Note",
			amount=50000,
			save=False,
		)
		jv.apply_tds = 1
		jv.tax_withholding_category = "Cumulative Threshold TCS"
		jv.save()

		# Again saving should not change tds amount
		jv.user_remark = "Test TCS on Journal Entry for Customer"
		jv.save()
		jv.submit()

		# Assert TCS calculation (10% on amount above threshold of 30000)
		self.assertEqual(len(jv.accounts), 3)

		# Find TCS account row
		tcs_row = None
		customer_row = None
		for row in jv.accounts:
			if row.get("is_tax_withholding_account"):
				tcs_row = row
			elif row.party_type == "Customer":
				customer_row = row

		self.assertIsNotNone(tcs_row, "TCS account row should be created")
		self.assertIsNotNone(customer_row, "Customer account row should exist")

		# TCS should be credited (liability to government)
		self.assertEqual(tcs_row.credit, 2000)  # (50000 - 30000) * 10%
		self.assertEqual(tcs_row.debit, 0)

		# Customer debit should be increased by TCS amount
		self.assertEqual(customer_row.debit, 52000)  # 50000 + 2000

		# Validate tax withholding entries - system creates two entries for threshold processing
		expected_entries = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=20000.0,  # Excess amount above threshold (50000 - 30000)
				withholding_amount=2000.0,  # 10% of 20000
				status="Settled",
				taxable_doctype="Journal Entry",
				taxable_name=jv.name,
				withholding_doctype="Journal Entry",
				withholding_name=jv.name,
			),
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TCS",
				party_type="Customer",
				party="Test TCS Customer",
				tax_rate=10.0,
				taxable_amount=30000.0,  # Threshold exemption amount
				withholding_amount=0.0,  # No tax on threshold portion
				status="Settled",
				taxable_doctype="Journal Entry",
				taxable_name=jv.name,
				withholding_doctype="Journal Entry",
				withholding_name=jv.name,
				under_withheld_reason="Threshold Exemption",
			),
		]
		self.validate_tax_withholding_entries("Journal Entry", jv.name, expected_entries)

	def test_tds_with_multi_currency_invoice(self):
		"""Test TDS calculation with multi-currency purchase invoice and payment"""
		invoices = []

		self.setup_party_with_category("Supplier", "_Test Supplier USD", "Cumulative Threshold TDS")

		pe = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"posting_date": today(),
				"payment_type": "Pay",
				"party_type": "Supplier",
				"party": "_Test Supplier USD",
				"company": "_Test Company",
				"paid_from": "Cash - _TC",
				"paid_to": "_Test Payable USD - _TC",
				"paid_amount": 40000,  # INR
				"received_amount": 500,  # USD
				"source_exchange_rate": 1,
				"target_exchange_rate": 80,
				"reference_no": "USD-TDS-001",
				"reference_date": today(),
				"paid_from_account_currency": "INR",
				"paid_to_account_currency": "USD",
				"apply_tds": 1,
				"tax_withholding_category": "Cumulative Threshold TDS",
			}
		)
		pe.save()
		pe.submit()
		invoices.append(pe)

		pe_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="_Test Supplier USD",
				tax_rate=10.0,
				taxable_amount=40000.0,  # Base currency: 500 USD * 80 = 40000 INR
				withholding_amount=4000.0,  # 10% of 40000 INR
				status="Over Withheld",
				taxable_doctype="",
				taxable_name="",
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			)
		]
		self.validate_tax_withholding_entries("Payment Entry", pe.name, pe_expected)

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": "_Test Supplier USD",
				"company": "_Test Company",
				"apply_tds": 1,
				"currency": "USD",
				"conversion_rate": 80,
				"credit_to": "_Test Payable USD - _TC",
				"taxes": [],
				"items": [
					{
						"doctype": "Purchase Invoice Item",
						"item_code": frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name"),
						"qty": 1,
						"rate": 500,  # 500 USD = 40000 INR
						"cost_center": "Main - _TC",
						"expense_account": "_Test Account Cost for Goods Sold - _TC",
					}
				],
				"advances": [
					{
						"doctype": "Purchase Invoice Advance",
						"reference_type": "Payment Entry",
						"reference_name": pe.name,
						"advance_amount": 500,  # USD
						"allocated_amount": 500,  # USD (full allocation)
						"ref_exchange_rate": 80,
					}
				],
			}
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		pi_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="_Test Supplier USD",
				tax_rate=10.0,
				taxable_amount=40000.0,  # Base currency: 500 USD * 80 = 40000 INR
				withholding_amount=4000.0,  # 10% of 40000 INR (settled from PE)
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Payment Entry",
				withholding_name=pe.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, pi_expected)
		self.cleanup_invoices(invoices)
		frappe.db.set_value("Supplier", "_Test Supplier USD", "tax_withholding_category", "")

	def test_journal_entry_with_adjustment_in_invoice(self):
		"""Test Journal Entry with amount below threshold creates Under Withheld entry
		and gets settled when a new Purchase Invoice crosses the threshold"""
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")

		# Create Debit Note with amount below threshold (30000)
		jv = make_journal_entry_with_tax_withholding(
			party_type="Supplier",
			party="Test TDS Supplier",
			voucher_type="Debit Note",
			amount=20000,  # Below cumulative threshold of 30000
			save=False,
		)
		jv.apply_tds = 1
		jv.tax_withholding_category = "Cumulative Threshold TDS"
		jv.save()
		jv.submit()
		invoices.append(jv)

		# Validate tax withholding entries - should have Under Withheld status
		jv_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=20000.0,
				withholding_amount=0.0,  # No tax withheld
				status="Under Withheld",
				taxable_doctype="Journal Entry",
				taxable_name=jv.name,
				withholding_doctype="",
				withholding_name="",
			)
		]
		self.validate_tax_withholding_entries("Journal Entry", jv.name, jv_expected)

		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=20000)
		pi.submit()
		invoices.append(pi)

		pi_expected = [
			# Entry for JV's under-withheld amount (now settled via PI)
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=20000.0,  # JV's taxable amount
				withholding_amount=2000.0,  # TDS on JV's amount
				status="Settled",
				taxable_doctype="Journal Entry",
				taxable_name=jv.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
			# Entry for PI's own amount
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=20000.0,  # PI's taxable amount
				withholding_amount=2000.0,  # TDS on PI's amount
				status="Settled",
				taxable_doctype="Purchase Invoice",
				taxable_name=pi.name,
				withholding_doctype="Purchase Invoice",
				withholding_name=pi.name,
			),
		]
		self.validate_tax_withholding_entries("Purchase Invoice", pi.name, pi_expected)

		self.cleanup_invoices(invoices)

	def test_journal_entry_negative_amount_debit_note(self):
		"""Test Journal Entry with negative amount (reversal of Debit Note)"""
		invoices = []
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")

		# First create a regular Debit Note to cross threshold
		jv1 = make_journal_entry_with_tax_withholding(
			party_type="Supplier",
			party="Test TDS Supplier",
			voucher_type="Debit Note",
			amount=50000,
			save=False,
		)
		jv1.apply_tds = 1
		jv1.tax_withholding_category = "Cumulative Threshold TDS"
		jv1.save()
		jv1.submit()
		invoices.append(jv1)

		# Validate first JV entries
		jv1_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=50000.0,
				withholding_amount=5000.0,
				status="Settled",
				taxable_doctype="Journal Entry",
				taxable_name=jv1.name,
				withholding_doctype="Journal Entry",
				withholding_name=jv1.name,
			)
		]
		self.validate_tax_withholding_entries("Journal Entry", jv1.name, jv1_expected)

		jv2 = frappe.new_doc("Journal Entry")
		jv2.posting_date = today()
		jv2.company = "_Test Company"
		jv2.voucher_type = "Debit Note"
		jv2.multi_currency = 0
		jv2.apply_tds = 1
		jv2.tax_withholding_category = "Cumulative Threshold TDS"

		jv2.append(
			"accounts",
			{
				"account": "Stock Received But Not Billed - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"credit_in_account_currency": 50000,  # Credit (reversal of expense)
				"exchange_rate": 1,
			},
		)

		# Supplier account: Debit 50000 (instead of normal Credit)
		# This reduces supplier liability (refund/reversal)
		jv2.append(
			"accounts",
			{
				"account": "Creditors - _TC",
				"party_type": "Supplier",
				"party": "Test TDS Supplier",
				"cost_center": "_Test Cost Center - _TC",
				"debit_in_account_currency": 50000,  # Debit (reversal)
				"exchange_rate": 1,
			},
		)

		jv2.save()
		jv2.submit()
		invoices.append(jv2)

		jv2_expected = [
			self.get_tax_withholding_entry(
				tax_withholding_category="Cumulative Threshold TDS",
				party_type="Supplier",
				party="Test TDS Supplier",
				tax_rate=10.0,
				taxable_amount=-50000.0,  # Negative taxable amount
				withholding_amount=-5000.0,  # Negative withholding (reversal)
				status="Settled",
				taxable_doctype="Journal Entry",
				taxable_name=jv2.name,
				withholding_doctype="Journal Entry",
				withholding_name=jv2.name,
			)
		]
		self.validate_tax_withholding_entries("Journal Entry", jv2.name, jv2_expected)
		self.cleanup_invoices(invoices)

	def test_delete_draft_pi_with_tax_withholding_entries(self):
		"""
		Test that draft Purchase Invoice with Tax Withholding Entries can be deleted.
		"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")

		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=50000, do_not_save=True)
		pi.save()

		self.assertTrue(len(pi.tax_withholding_entries) > 0)
		pi.delete()

	def test_tds_rounding_with_decimal_amounts(self):
		"""Test TDS rounding when round_off_tax_amount is enabled in category"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier3", "New TDS Category")

		pi = create_purchase_invoice(supplier="Test TDS Supplier3", rate=35555)
		pi.submit()

		tds_row = next(e for e in pi.tax_withholding_entries if e.withholding_amount > 0)
		self.assertEqual(tds_row.withholding_amount, 556)

		self.cleanup_invoices([pi])

	def test_tax_withholding_entry_status_determination(self):
		"""Test that Tax Withholding Entry status is correctly determined"""
		from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import (
			TaxWithholdingEntry,
		)

		# Entry with only taxable fields (Under Withheld)
		entry = frappe._dict(
			docstatus=1,
			withholding_name="",
			under_withheld_reason="",
			taxable_name="PI-001",
		)
		self.assertEqual(TaxWithholdingEntry.get_status(entry), "Under Withheld")

		# Entry with withholding but no taxable (Over Withheld)
		entry = frappe._dict(
			docstatus=1,
			withholding_name="PE-001",
			under_withheld_reason="",
			taxable_name="",
		)
		self.assertEqual(TaxWithholdingEntry.get_status(entry), "Over Withheld")

		# Entry with both (Settled)
		entry = frappe._dict(
			docstatus=1,
			withholding_name="PE-001",
			under_withheld_reason="",
			taxable_name="PI-001",
		)
		self.assertEqual(TaxWithholdingEntry.get_status(entry), "Settled")

		# Entry with under withheld reason (considered matched/settled)
		entry = frappe._dict(
			docstatus=1,
			withholding_name="",
			under_withheld_reason="Threshold Exemption",
			taxable_name="PI-001",
		)
		self.assertEqual(TaxWithholdingEntry.get_status(entry), "Settled")

		# Cancelled entry
		entry = frappe._dict(docstatus=2, withholding_name="", under_withheld_reason="", taxable_name="")
		self.assertEqual(TaxWithholdingEntry.get_status(entry), "Cancelled")

	def test_invalid_withholding_amount_validation(self):
		"""Test that mismatched withholding amounts throw validation error on save"""
		self.setup_party_with_category("Supplier", "Test TDS Supplier", "Cumulative Threshold TDS")
		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=50000)

		self.assertTrue(len(pi.tax_withholding_entries) > 0)
		pi.override_tax_withholding_entries = 1

		entry = pi.tax_withholding_entries[0]
		entry.withholding_amount = 5001  # Should be 5000 (10% of 50000)
		self.assertRaisesRegex(frappe.ValidationError, "Withholding Amount.*does not match", pi.save)


def create_purchase_invoice(**args):
	# return sales invoice doc object
	item = frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name")

	args = frappe._dict(args)
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"set_posting_time": args.set_posting_time or False,
			"posting_date": args.posting_date or today(),
			"apply_tds": 0 if args.do_not_apply_tds else 1,
			"is_return": args.is_return or 0,
			"supplier": args.supplier,
			"company": "_Test Company",
			"taxes_and_charges": "",
			"currency": "INR",
			"credit_to": "Creditors - _TC",
			"taxes": [],
			"items": [
				{
					"doctype": "Purchase Invoice Item",
					"item_code": item,
					"qty": args.qty or 1,
					"rate": args.rate or 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
				}
			],
		}
	)

	pi.save()
	return pi


def create_purchase_order(**args):
	# return purchase order doc object
	item = frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name")

	args = frappe._dict(args)
	po = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"transaction_date": today(),
			"schedule_date": today(),
			"apply_tds": 0 if args.do_not_apply_tds else 1,
			"supplier": args.supplier,
			"company": "_Test Company",
			"taxes_and_charges": "",
			"currency": "INR",
			"taxes": [],
			"items": [
				{
					"doctype": "Purchase Order Item",
					"item_code": item,
					"qty": args.qty or 1,
					"rate": args.rate or 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
				}
			],
		}
	)

	po.save()
	return po


def create_sales_invoice(**args):
	# return sales invoice doc object
	item = frappe.db.get_value("Item", {"item_name": "TCS Item"}, "name")

	args = frappe._dict(args)
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"posting_date": today(),
			"customer": args.customer,
			"company": "_Test Company",
			"apply_tds": 0 if args.do_not_apply_tds else 1,
			"taxes_and_charges": "",
			"currency": "INR",
			"debit_to": "Debtors - _TC",
			"taxes": [],
			"items": [
				{
					"doctype": "Sales Invoice Item",
					"item_code": item,
					"qty": args.qty or 1,
					"rate": args.rate or 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Cost of Goods Sold - _TC",
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
				}
			],
		}
	)

	si.save()
	return si


def create_payment_entry(**args):
	# return payment entry doc object
	args = frappe._dict(args)
	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"posting_date": today(),
			"payment_type": args.payment_type,
			"party_type": args.party_type,
			"party": args.party,
			"company": "_Test Company",
			"paid_from": "Cash - _TC",
			"paid_to": "Creditors - _TC",
			"paid_amount": args.paid_amount or 10000,
			"received_amount": args.paid_amount or 10000,
			"reference_no": args.reference_no or "12345",
			"reference_date": today(),
			"paid_from_account_currency": "INR",
			"paid_to_account_currency": "INR",
		}
	)

	pe.save()
	return pe


def make_journal_entry_with_tax_withholding(
	party_type,
	party,
	voucher_type,
	amount,
	cost_center=None,
	posting_date=None,
	save=True,
	submit=False,
):
	"""Helper function to create Journal Entry for tax withholding"""
	if not cost_center:
		cost_center = "_Test Cost Center - _TC"

	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date or today()
	jv.company = "_Test Company"
	jv.voucher_type = voucher_type
	jv.multi_currency = 0

	if party_type == "Supplier":
		# Debit Note: Expense Dr, Supplier Cr
		expense_account = "Stock Received But Not Billed - _TC"
		party_account = "Creditors - _TC"

		jv.append(
			"accounts",
			{
				"account": expense_account,
				"cost_center": cost_center,
				"debit_in_account_currency": amount,
				"exchange_rate": 1,
			},
		)

		jv.append(
			"accounts",
			{
				"account": party_account,
				"party_type": party_type,
				"party": party,
				"cost_center": cost_center,
				"credit_in_account_currency": amount,
				"exchange_rate": 1,
			},
		)
	else:  # Customer
		# Credit Note: Customer Dr, Income Cr
		party_account = "Debtors - _TC"
		income_account = "Sales - _TC"

		jv.append(
			"accounts",
			{
				"account": party_account,
				"party_type": party_type,
				"party": party,
				"cost_center": cost_center,
				"debit_in_account_currency": amount,
				"exchange_rate": 1,
			},
		)

		jv.append(
			"accounts",
			{
				"account": income_account,
				"cost_center": cost_center,
				"credit_in_account_currency": amount,
				"exchange_rate": 1,
			},
		)

	if save or submit:
		jv.insert()

		if submit:
			jv.submit()

	return jv


def create_records():
	# create a new suppliers
	for name in [
		"Test TDS Supplier",
		"Test TDS Supplier1",
		"Test TDS Supplier2",
		"Test TDS Supplier3",
		"Test TDS Supplier4",
		"Test TDS Supplier5",
		"Test TDS Supplier6",
		"Test TDS Supplier7",
		"Test TDS Supplier8",
		"Test LDC Supplier",
	]:
		if frappe.db.exists("Supplier", name):
			continue

		frappe.get_doc(
			{
				"supplier_group": "_Test Supplier Group",
				"supplier_name": name,
				"doctype": "Supplier",
			}
		).insert()

	for name in ["Test TCS Customer"]:
		if frappe.db.exists("Customer", name):
			continue

		frappe.get_doc(
			{"customer_group": "_Test Customer Group", "customer_name": name, "doctype": "Customer"}
		).insert()

	# create item
	if not frappe.db.exists("Item", "TDS Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "TDS Item",
				"item_name": "TDS Item",
				"item_group": "All Item Groups",
				"is_stock_item": 0,
			}
		).insert()

	if not frappe.db.exists("Item", "TCS Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "TCS Item",
				"item_name": "TCS Item",
				"item_group": "All Item Groups",
				"is_stock_item": 1,
			}
		).insert()

	# create tds account
	if not frappe.db.exists("Account", "TDS - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": "_Test Company",
				"account_name": "TDS",
				"parent_account": "Tax Assets - _TC",
				"report_type": "Balance Sheet",
				"root_type": "Asset",
			}
		).insert()

	# create tcs account
	if not frappe.db.exists("Account", "TCS - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": "_Test Company",
				"account_name": "TCS",
				"parent_account": "Duties and Taxes - _TC",
				"report_type": "Balance Sheet",
				"root_type": "Liability",
			}
		).insert()


def create_tax_withholding_category_records():
	fiscal_year = get_fiscal_year(today(), company="_Test Company")
	from_date = fiscal_year[1]
	to_date = fiscal_year[2]

	# Cumulative threshold
	create_tax_withholding_category(
		category_name="Cumulative Threshold TDS",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=0,
		cumulative_threshold=30000.00,
		disable_transaction_threshold=1,
	)

	# Category for TCS
	create_tax_withholding_category(
		category_name="Cumulative Threshold TCS",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TCS - _TC",
		single_threshold=0,
		cumulative_threshold=30000.00,
		disable_transaction_threshold=1,
		tax_deduction_basis="Gross Total",
		tax_on_excess_amount=1,
	)

	# Single threshold
	create_tax_withholding_category(
		category_name="Single Threshold TDS",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=20000,
		cumulative_threshold=0,
	)

	create_tax_withholding_category(
		category_name="New TDS Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=0,
		cumulative_threshold=30000,
		round_off_tax_amount=1,
		tax_on_excess_amount=1,
	)

	create_tax_withholding_category(
		category_name="Test Service Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=2000,
		cumulative_threshold=2000,
	)

	create_tax_withholding_category(
		category_name="Test Goods Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=2000,
		cumulative_threshold=2000,
	)

	create_tax_withholding_category(
		category_name="Test Multi Invoice Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=5000,
		cumulative_threshold=10000,
	)

	create_tax_withholding_category(
		category_name="Advance TDS Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=5000,
		cumulative_threshold=10000,
	)

	create_tax_withholding_category(
		category_name="Multi Account TDS Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=0,
		cumulative_threshold=30000,
		disable_transaction_threshold=1,
	)


def create_tax_withholding_category(
	category_name,
	rate,
	from_date,
	to_date,
	account,
	single_threshold=0,
	cumulative_threshold=0,
	round_off_tax_amount=0,
	tax_on_excess_amount=0,
	disable_transaction_threshold=0,
	tax_deduction_basis="Net Total",
):
	if not frappe.db.exists("Tax Withholding Category", category_name):
		frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"name": category_name,
				"category_name": category_name,
				"round_off_tax_amount": round_off_tax_amount,
				"tax_on_excess_amount": tax_on_excess_amount,
				"disable_transaction_threshold": disable_transaction_threshold,
				"tax_deduction_basis": tax_deduction_basis,
				"rates": [
					{
						"from_date": from_date,
						"to_date": to_date,
						"tax_withholding_rate": rate,
						"single_threshold": single_threshold,
						"cumulative_threshold": cumulative_threshold,
					}
				],
				"accounts": [{"company": "_Test Company", "account": account}],
			}
		).insert()


def create_lower_deduction_certificate(
	supplier, tax_withholding_category, tax_rate, certificate_no, limit, valid_from=None, valid_upto=None
):
	fiscal_year = get_fiscal_year(today(), company="_Test Company")
	if not frappe.db.exists("Lower Deduction Certificate", certificate_no):
		frappe.get_doc(
			{
				"doctype": "Lower Deduction Certificate",
				"company": "_Test Company",
				"supplier": supplier,
				"certificate_no": certificate_no,
				"tax_withholding_category": tax_withholding_category,
				"fiscal_year": fiscal_year[0],
				"valid_from": valid_from or fiscal_year[1],
				"valid_upto": valid_upto or fiscal_year[2],
				"rate": tax_rate,
				"certificate_limit": limit,
			}
		).insert()


def make_pan_no_field():
	pan_field = {
		"Supplier": [
			{
				"fieldname": "pan",
				"label": "PAN",
				"fieldtype": "Data",
				"translatable": 0,
			}
		]
	}

	create_custom_fields(pan_field, update=1)
