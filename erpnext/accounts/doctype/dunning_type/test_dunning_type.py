# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


def make_dunning_type(dunning_type, company="_Test Company", **kwargs):
	doc = frappe.new_doc("Dunning Type")
	doc.dunning_type = dunning_type
	doc.company = company
	doc.dunning_fee = kwargs.get("dunning_fee", 100)
	doc.rate_of_interest = kwargs.get("rate_of_interest", 5)
	doc.is_default = kwargs.get("is_default", 0)

	if "income_account" in kwargs:
		doc.income_account = kwargs["income_account"]
	elif kwargs.get("income_account") is not False:
		doc.income_account = "Sales - _TC" if company == "_Test Company" else "Sales - _TC1"

	if "cost_center" in kwargs:
		doc.cost_center = kwargs["cost_center"]
	elif kwargs.get("cost_center") is not False:
		doc.cost_center = "Main - _TC" if company == "_Test Company" else "Main - _TC1"

	for row in kwargs.get("dunning_letter_text", [{"language": "en", "body_text": "Test body"}]):
		doc.append("dunning_letter_text", row)

	return doc


class TestDunningType(ERPNextTestSuite):
	def test_income_account_must_belong_to_company(self):
		doc = make_dunning_type("_Test Dunning Wrong Company Account", income_account="Sales - _TC1")
		self.assertRaisesRegex(frappe.ValidationError, "doesn't belong to Company", doc.insert)

	def test_income_account_must_not_be_disabled(self):
		disabled_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test Disabled Income Account",
				"parent_account": "Direct Income - _TC",
				"company": "_Test Company",
				"account_type": "Income Account",
				"disabled": 1,
			}
		).insert()

		doc = make_dunning_type("_Test Dunning Disabled Account", income_account=disabled_account.name)
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", doc.insert)

	def test_income_account_must_be_income_type(self):
		doc = make_dunning_type("_Test Dunning Non Income Account", income_account="Debtors - _TC")
		self.assertRaisesRegex(frappe.ValidationError, "is not an Income Account", doc.insert)

	def test_income_account_must_not_be_group(self):
		doc = make_dunning_type("_Test Dunning Group Account", income_account="Income - _TC")
		self.assertRaisesRegex(frappe.ValidationError, "is a group account", doc.insert)

	def test_income_account_is_optional(self):
		doc = make_dunning_type("_Test Dunning No Income Account", income_account=False)
		doc.insert()
		self.assertFalse(doc.income_account)

	def test_valid_income_account_passes(self):
		doc = make_dunning_type("_Test Dunning Valid Income Account", income_account="Sales - _TC")
		doc.insert()
		self.assertEqual(doc.income_account, "Sales - _TC")

	def test_cost_center_must_belong_to_company(self):
		doc = make_dunning_type("_Test Dunning Wrong Company CC", cost_center="Main - _TC1")
		self.assertRaisesRegex(frappe.ValidationError, "doesn't belong to Company", doc.insert)

	def test_cost_center_must_not_be_disabled(self):
		disabled_cc = frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "_Test Disabled Cost Center",
				"parent_cost_center": "_Test Company - _TC",
				"company": "_Test Company",
				"disabled": 1,
			}
		).insert()

		doc = make_dunning_type("_Test Dunning Disabled CC", cost_center=disabled_cc.name)
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", doc.insert)

	def test_cost_center_must_not_be_group(self):
		doc = make_dunning_type("_Test Dunning Group CC", cost_center="_Test Company - _TC")
		self.assertRaisesRegex(frappe.ValidationError, "is a group Cost Center", doc.insert)

	def test_cost_center_is_optional(self):
		doc = make_dunning_type("_Test Dunning No CC", cost_center=False)
		doc.insert()
		self.assertFalse(doc.cost_center)

	def test_valid_cost_center_passes(self):
		doc = make_dunning_type("_Test Dunning Valid CC", cost_center="Main - _TC")
		doc.insert()
		self.assertEqual(doc.cost_center, "Main - _TC")

	def test_duplicate_languages_not_allowed(self):
		doc = make_dunning_type(
			"_Test Dunning Duplicate Language",
			dunning_letter_text=[
				{"language": "en", "body_text": "Body one"},
				{"language": "en", "body_text": "Body two"},
			],
		)
		self.assertRaisesRegex(frappe.ValidationError, "Duplicate languages found", doc.insert)

	def test_unique_languages_allowed(self):
		doc = make_dunning_type(
			"_Test Dunning Unique Languages",
			dunning_letter_text=[
				{"language": "en", "body_text": "Body one"},
				{"language": "de", "body_text": "Body two"},
			],
		)
		doc.insert()
		self.assertEqual(len(doc.dunning_letter_text), 2)

	def test_only_one_default_language_allowed(self):
		doc = make_dunning_type(
			"_Test Dunning Multiple Default Language",
			dunning_letter_text=[
				{"language": "en", "body_text": "Body one", "is_default_language": 1},
				{"language": "de", "body_text": "Body two", "is_default_language": 1},
			],
		)
		self.assertRaisesRegex(
			frappe.ValidationError, "languages are marked as default languages", doc.insert
		)

	def test_single_default_language_allowed(self):
		doc = make_dunning_type(
			"_Test Dunning Single Default Language",
			dunning_letter_text=[
				{"language": "en", "body_text": "Body one", "is_default_language": 1},
				{"language": "de", "body_text": "Body two", "is_default_language": 0},
			],
		)
		doc.insert()
		self.assertEqual(doc.dunning_letter_text[0].is_default_language, 1)

	def test_invalid_jinja_template_in_body_text_raises(self):
		doc = make_dunning_type(
			"_Test Dunning Invalid Body Template",
			dunning_letter_text=[{"language": "en", "body_text": "{{ unclosed"}],
		)
		self.assertRaisesRegex(frappe.ValidationError, "Syntax error in template", doc.insert)

	def test_invalid_jinja_template_in_closing_text_raises(self):
		doc = make_dunning_type(
			"_Test Dunning Invalid Closing Template",
			dunning_letter_text=[
				{"language": "en", "body_text": "Valid body", "closing_text": "{{ unclosed"}
			],
		)
		self.assertRaisesRegex(frappe.ValidationError, "Syntax error in template", doc.insert)

	def test_valid_jinja_template_passes(self):
		doc = make_dunning_type(
			"_Test Dunning Valid Template",
			dunning_letter_text=[
				{
					"language": "en",
					"body_text": "Outstanding amount is {{ outstanding_amount }}",
					"closing_text": "Regards, {{ company }}",
				}
			],
		)
		doc.insert()
		self.assertTrue(doc.name)

	def test_set_default_dunning_type_unsets_previous_default(self):
		first = make_dunning_type("_Test Dunning Default One", is_default=1)
		first.insert()
		self.assertEqual(frappe.db.get_value("Dunning Type", first.name, "is_default"), 1)

		second = make_dunning_type("_Test Dunning Default Two", is_default=1)
		second.insert()

		self.assertEqual(frappe.db.get_value("Dunning Type", first.name, "is_default"), 0)
		self.assertEqual(frappe.db.get_value("Dunning Type", second.name, "is_default"), 1)

	def test_set_default_dunning_type_scoped_per_company(self):
		company_1 = make_dunning_type("_Test Dunning Default Co1", is_default=1)
		company_1.insert()

		company_2 = make_dunning_type(
			"_Test Dunning Default Co2",
			company="_Test Company 1",
			is_default=1,
		)
		company_2.insert()

		self.assertEqual(frappe.db.get_value("Dunning Type", company_1.name, "is_default"), 1)
		self.assertEqual(frappe.db.get_value("Dunning Type", company_2.name, "is_default"), 1)
