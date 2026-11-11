# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_item_tax_template
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
TAX_ACCOUNT = "_Test Account VAT - _TC"
RECEIVABLE_ACCOUNT = "Debtors - _TC"


class TestItemTaxTemplate(ERPNextTestSuite):
	"""Item Tax Template validates its tax rows: each account must belong to the
	company, be a tax-like account type, and appear only once."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_template(self, rows, title="_Test ITT"):
		doc = frappe.new_doc("Item Tax Template")
		doc.title = f"{title} {frappe.generate_hash(length=6)}"
		doc.company = COMPANY
		for account, rate, not_applicable in rows:
			doc.append(
				"taxes",
				{"tax_type": account, "tax_rate": rate, "not_applicable": not_applicable},
			)
		return doc

	def test_valid_template_saves_and_is_named_with_abbr(self):
		doc = self.make_template([(TAX_ACCOUNT, 9, 0)])
		doc.insert()
		self.assertTrue(doc.name.endswith(" - _TC"))
		self.assertTrue(doc.name.startswith(doc.title))

	def test_duplicate_tax_type_throws(self):
		doc = self.make_template([(TAX_ACCOUNT, 9, 0), (TAX_ACCOUNT, 5, 0)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_account_of_wrong_company_throws(self):
		other_account = frappe.db.get_value("Account", {"company": "_Test Company 1", "is_group": 0}, "name")
		self.assertTrue(other_account, "need a non-group account in _Test Company 1")
		doc = self.make_template([(other_account, 9, 0)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_disallowed_account_type_throws(self):
		# a Receivable account is not Tax/Chargeable/Income/Expense
		doc = self.make_template([(RECEIVABLE_ACCOUNT, 9, 0)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_not_applicable_row_has_rate_zeroed(self):
		doc = self.make_template([(TAX_ACCOUNT, 18, 1)])
		doc.insert()
		self.assertEqual(doc.taxes[0].tax_rate, 0)

	def test_negative_tax_rate_is_accepted(self):
		# SUSPECTED BUG: validate never bounds tax_rate, so a negative (or >100) rate
		# saves silently. Locking the current (wrong) behaviour.
		doc = self.make_template([(TAX_ACCOUNT, -5, 0)])
		doc.insert()
		self.assertEqual(doc.taxes[0].tax_rate, -5)

	def make_tax_template(self, rate):
		return self.make_template([(TAX_ACCOUNT, rate, 0)]).insert().name

	def make_item_with_taxes(self, taxes):
		return make_item(properties={"taxes": taxes}).name

	def get_template_for(self, item_code, **kwargs):
		ctx = {"item_code": item_code, "company": COMPANY, "posting_date": today(), "tax_category": None}
		ctx.update(kwargs)
		return get_item_tax_template(ctx)

	def make_tax_category(self, title):
		if not frappe.db.exists("Tax Category", title):
			frappe.get_doc({"doctype": "Tax Category", "title": title}).insert()
		return title

	def test_dated_and_rate_band_rows_together(self):
		template_18 = self.make_tax_template(18)
		template_5 = self.make_tax_template(5)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
				{"item_tax_template": template_5, "minimum_net_rate": 0, "maximum_net_rate": 1000},
			]
		)

		self.assertEqual(self.get_template_for(item_code, base_net_rate=500), template_18)

	def test_rate_band_without_valid_from_on_backdated_transaction(self):
		template_5 = self.make_tax_template(5)
		template_12 = self.make_tax_template(12)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_5, "minimum_net_rate": 0, "maximum_net_rate": 1000},
				{"item_tax_template": template_12, "minimum_net_rate": 1000.01, "maximum_net_rate": 1000000},
			]
		)

		yesterday = add_days(today(), -1)
		self.assertEqual(
			self.get_template_for(item_code, posting_date=yesterday, base_net_rate=500), template_5
		)
		self.assertEqual(
			self.get_template_for(item_code, posting_date=yesterday, base_net_rate=5000), template_12
		)

	def test_undated_row_is_kept_for_its_tax_category(self):
		in_state = self.make_tax_category("_Test In-State")
		out_state = self.make_tax_category("_Test Out-State")
		template_in_state = self.make_tax_template(5)
		template_out_state = self.make_tax_template(18)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_in_state, "tax_category": in_state},
				{
					"item_tax_template": template_out_state,
					"tax_category": out_state,
					"valid_from": add_days(today(), -10),
				},
			]
		)

		self.assertEqual(self.get_template_for(item_code, tax_category=in_state), template_in_state)
		self.assertEqual(self.get_template_for(item_code, tax_category=out_state), template_out_state)

	def test_template_of_old_tax_category_is_replaced(self):
		in_state = self.make_tax_category("_Test In-State")
		out_state = self.make_tax_category("_Test Out-State")
		template_in_state = self.make_tax_template(5)
		template_out_state = self.make_tax_template(18)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_in_state, "tax_category": in_state},
				{
					"item_tax_template": template_out_state,
					"tax_category": out_state,
					"valid_from": add_days(today(), -10),
				},
			]
		)

		self.assertEqual(
			self.get_template_for(item_code, tax_category=out_state, item_tax_template=template_in_state),
			template_out_state,
		)
		self.assertEqual(
			self.get_template_for(item_code, tax_category=None, item_tax_template=template_in_state),
			template_in_state,
		)

	def test_superseded_template_is_replaced_on_transaction(self):
		template_12 = self.make_tax_template(12)
		template_18 = self.make_tax_template(18)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_12, "valid_from": add_days(today(), -60)},
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
			]
		)

		self.assertEqual(self.get_template_for(item_code, item_tax_template=template_12), template_18)

		si = create_sales_invoice(item_code=item_code, rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template_12
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": TAX_ACCOUNT,
				"description": "VAT",
				"rate": 0,
			},
		)
		si.insert()

		self.assertEqual(si.items[0].item_tax_template, template_18)
		self.assertEqual(si.taxes[0].tax_amount, 180)

	def make_item_group_with_taxes(self, taxes):
		item_group = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": f"_Test ITT Group {frappe.generate_hash(length=6)}",
				"parent_item_group": "All Item Groups",
				"taxes": taxes,
			}
		)
		return item_group.insert().name

	def test_superseded_template_is_replaced_with_item_row_before_item_group_row(self):
		template_5 = self.make_tax_template(5)
		template_12 = self.make_tax_template(12)
		template_18 = self.make_tax_template(18)
		item_group = self.make_item_group_with_taxes(
			[
				{"item_tax_template": template_12, "valid_from": add_days(today(), -60)},
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
			]
		)
		item_code = make_item(
			properties={
				"item_group": item_group,
				"taxes": [{"item_tax_template": template_5, "valid_from": add_days(today(), -20)}],
			}
		).name

		si = create_sales_invoice(item_code=item_code, rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template_12
		si.insert()

		self.assertEqual(self.get_template_for(item_code), template_5)
		self.assertEqual(si.items[0].item_tax_template, template_5)

	def test_actual_charge_breakup_with_not_applicable_item(self):
		freight_account = "_Test Account Shipping Charges - _TC"
		not_applicable_template = self.make_template([(freight_account, 0, 1)]).insert().name
		exempt_item = self.make_item_with_taxes([{"item_tax_template": not_applicable_template}])
		normal_item = make_item(properties={"is_stock_item": 0}).name

		for first_item, second_item in ((exempt_item, normal_item), (normal_item, exempt_item)):
			si = create_sales_invoice(item_code=first_item, rate=500, do_not_save=True)
			si.append("items", {"item_code": second_item, "qty": 1, "rate": 500})
			si.append(
				"taxes",
				{
					"charge_type": "Actual",
					"account_head": freight_account,
					"description": "Freight",
					"tax_amount": 100,
				},
			)
			si.insert()

			normal_row = next(item.name for item in si.items if item.item_code == normal_item)
			breakup = {row.item_row: row.amount for row in si.item_wise_tax_details}
			self.assertEqual(si.taxes[0].tax_amount, 100)
			self.assertEqual(si.grand_total, 1100)
			self.assertEqual(breakup, {normal_row: 100})

	def test_actual_charge_goes_to_last_item_when_no_item_is_applicable(self):
		freight_account = "_Test Account Shipping Charges - _TC"
		not_applicable_template = self.make_template([(freight_account, 0, 1)]).insert().name
		exempt_item = self.make_item_with_taxes([{"item_tax_template": not_applicable_template}])

		si = create_sales_invoice(item_code=exempt_item, rate=500, do_not_save=True)
		si.append("items", {"item_code": exempt_item, "qty": 1, "rate": 500})
		si.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": freight_account,
				"description": "Freight",
				"tax_amount": 100,
			},
		)
		si.insert()

		self.assertEqual(si.taxes[0].tax_amount, 100)
		self.assertEqual(si.grand_total, 1100)

	def test_group_account_throws(self):
		doc = self.make_template([("Duties and Taxes - _TC", 7, 0)])
		self.assertRaisesRegex(frappe.ValidationError, "is a group account", doc.insert)

	def test_disabled_template_on_transaction_throws(self):
		template = self.make_template([(TAX_ACCOUNT, 28, 0)])
		template.disabled = 1
		template.insert()

		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template.name
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", si.insert)

	def test_draft_submits_after_its_template_is_disabled(self):
		template = self.make_tax_template(28)
		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template
		si.insert()

		frappe.db.set_value("Item Tax Template", template, "disabled", 1)
		si.reload()
		si.submit()
		self.assertEqual(si.docstatus, 1)

		draft = create_sales_invoice(rate=1000, do_not_submit=True)
		draft.append(
			"items", {"item_code": "_Test Item", "qty": 1, "rate": 1000, "item_tax_template": template}
		)
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", draft.save)

	def test_template_of_other_company_on_transaction_throws(self):
		other_company_template = frappe.db.get_value("Item Tax Template", {"company": "_Test Company 1"})
		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.items[0].item_tax_template = other_company_template
		self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company", si.insert)

	def test_inter_company_purchase_invoice_drops_seller_template(self):
		from erpnext.accounts.doctype.sales_invoice.mapper import make_inter_company_transaction
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_internal_parties

		create_internal_parties()
		seller_template = frappe.new_doc("Item Tax Template")
		seller_template.title = f"_Test ITT {frappe.generate_hash(length=6)}"
		seller_template.company = "Wind Power LLC"
		seller_template.append("taxes", {"tax_type": "ST 6% - WP", "tax_rate": 6})
		seller_template.insert()

		si = create_sales_invoice(
			company="Wind Power LLC",
			customer="_Test Internal Customer",
			debit_to="Debtors - WP",
			warehouse="Stores - WP",
			income_account="Sales - WP",
			expense_account="Cost of Goods Sold - WP",
			cost_center="Main - WP",
			currency="USD",
			do_not_save=1,
		)
		si.selling_price_list = "_Test Price List Rest of the World"
		si.items[0].item_tax_template = seller_template.name
		si.submit()

		pi = make_inter_company_transaction("Sales Invoice", si.name)
		pi.items[0].update(
			{
				"expense_account": "Cost of Goods Sold - _TC1",
				"cost_center": "Main - _TC1",
				"warehouse": "Stores - _TC1",
			}
		)
		pi.submit()

		self.assertEqual(pi.company, "_Test Company 1")
		self.assertNotEqual(pi.items[0].item_tax_template, seller_template.name)
