# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from jinja2.sandbox import SandboxedEnvironment

from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions


class TestTermsAndConditions(UnitTestCase):
	def test_literal_terms_with_file_extensions(self):
		for extension in ("html", "txt", "md"):
			with self.subTest(extension=extension):
				terms = "Full terms for {{ customer }} at https://example.com/terms." + extension
				with (
					patch("frappe.get_cached_doc") as get_doc,
					patch(
						"erpnext.setup.doctype.terms_and_conditions.terms_and_conditions.get_terms_environment",
						return_value=SandboxedEnvironment(),
					),
				):
					get_doc.return_value.terms = terms
					get_doc.return_value.disabled = 0
					self.assertEqual(
						get_terms_and_conditions("Test", {"customer": "Acme"}),
						"Full terms for Acme at https://example.com/terms." + extension,
					)

	def test_applicable_modules_without_hrms(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import TermsandConditions

		doc = TermsandConditions.__new__(TermsandConditions)
		doc.__dict__.update(terms=None, buying=0, selling=0, disabled=0)
		with self.assertRaises(frappe.ValidationError):
			doc.validate()
		doc.disabled = 1
		doc.validate()
		doc.disabled = 0
		doc.hr = 1
		doc.validate()

	def test_template_cannot_use_unchecked_data_helpers(self):
		from jinja2 import UndefinedError

		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_environment

		for expression in (
			"frappe.db.sql('select sentinel')",
			"frappe.get_all('User')",
			"frappe.qb.DocType('User')",
			"frappe.get_doc('User', 'Administrator')",
			"frappe.render_template('x')",
			"frappe.session.csrf_token",
			"frappe.utils.image_to_base64('/tmp/sentinel')",
		):
			with self.subTest(expression=expression), self.assertRaises(UndefinedError):
				get_terms_environment("editor@example.com").from_string("{{ " + expression + " }}").render({})

	def test_template_preserves_formatting_and_context(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_environment

		self.assertEqual(
			get_terms_environment("editor@example.com")
			.from_string("{{ customer }} {{ frappe.format(days, 'Int') }} {{ frappe.bold('Terms') }}")
			.render(customer="Acme", days="30"),
			"Acme 30 <strong>Terms</strong>",
		)

	def test_template_rejects_permission_overrides(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_environment

		for override in ("ignore_permissions=True", "user='Administrator'"):
			with self.subTest(override=override), self.assertRaises(TypeError):
				get_terms_environment("editor@example.com").from_string(
					"{{ frappe.get_list('ToDo', " + override + ") }}"
				).render({})

	def test_template_cannot_rebind_query_author(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_environment

		self.assertEqual(
			get_terms_environment("editor@example.com")
			.from_string("{{ frappe.get_list.func is defined }}")
			.render({}),
			"False",
		)


class TestTermsPermissions(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.db.rollback)
		self.author = "terms-editor@example.com"
		if not frappe.db.exists("User", self.author):
			frappe.get_doc(
				doctype="User",
				email=self.author,
				first_name="Terms Editor",
				send_welcome_email=0,
				roles=[{"role": "Sales Master Manager"}],
			).insert()
		self.todo = frappe.get_doc(doctype="ToDo", description="Terms sentinel").insert()

	def test_editor_cannot_borrow_renderer_permissions(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		# The current renderer is Administrator, but the template editor cannot read Purchase Invoice.
		with self.assertRaises(frappe.PermissionError):
			get_terms_list(self.author, "Purchase Invoice", fields=["name"])

	def test_get_list_checks_editor_record_permissions(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		self.assertEqual(
			get_terms_list(self.author, "ToDo", filters={"name": self.todo.name}, fields=["description"]), []
		)
		self.todo.allocated_to = self.author
		self.todo.save()
		self.assertEqual(
			get_terms_list(self.author, "ToDo", filters={"name": self.todo.name}, fields=["description"]),
			[{"description": "Terms sentinel"}],
		)

	def test_masked_fields_are_excluded_for_administrator_renderer(self):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter
		from frappe.model import get_permitted_fields

		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		self.todo.color = "#123456"
		self.todo.allocated_to = self.author
		self.todo.save()
		make_property_setter("ToDo", "color", "mask", 1, "Check")
		self.addCleanup(frappe.clear_cache, doctype="ToDo")
		frappe.set_user(self.author)
		self.assertIn("color", get_permitted_fields("ToDo", permission_type="read"))
		self.assertIn("color", [df.fieldname for df in frappe.get_meta("ToDo").get_masked_fields()])
		frappe.set_user("Administrator")
		for kwargs in (
			{"fields": ["color"]},
			{"filters": {"color": "#123456"}},
			{"order_by": "color desc"},
		):
			with self.subTest(kwargs=kwargs), self.assertRaises(frappe.PermissionError):
				get_terms_list(self.author, "ToDo", **kwargs)
		rows = get_terms_list(self.author, "ToDo", filters={"name": self.todo.name}, fields=["*"])
		self.assertEqual(len(rows), 1)
		self.assertNotIn("color", rows[0])

	def test_editor_record_permissions_are_applied_before_limit(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		visible = frappe.get_doc(
			doctype="ToDo", description="B visible terms", allocated_to=self.author
		).insert()
		self.todo.description = "A hidden terms"
		self.todo.save()
		self.assertEqual(
			get_terms_list(
				self.author,
				"ToDo",
				filters={"name": ["in", [self.todo.name, visible.name]]},
				fields=["description"],
				order_by="description asc",
				limit_page_length=1,
			),
			[{"description": "B visible terms"}],
		)

	def test_get_list_checks_caller_permissions(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		frappe.set_user(self.author)
		with self.assertRaises(frappe.PermissionError):
			get_terms_list("Administrator", "Purchase Invoice", fields=["name"])

	def test_get_list_blocks_field_and_query_bypasses(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		for kwargs in (
			{"fields": ["password"]},
			{"fields": ["name as password"]},
			{"fields": ["count(name)"]},
			{"filters": {"password": "sentinel"}},
			{"order_by": "password desc"},
			{"filters": [["password", "=", "sentinel"]]},
		):
			with self.subTest(kwargs=kwargs), self.assertRaises(frappe.PermissionError):
				get_terms_list("Administrator", "User", **kwargs)

	def test_get_list_checks_editor_field_permissions(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_list

		with self.assertRaises(frappe.PermissionError):
			get_terms_list(self.author, "User", fields=["reset_password_key"])

	def test_formatting_cannot_read_unchecked_document_fields(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_environment

		record = frappe._dict(doctype="ToDo", name=self.todo.name, owner="Administrator")
		for formatter in ("format", "format_value"):
			with self.subTest(formatter=formatter), patch(
				"frappe.get_cached_value", return_value="terms-formatting-secret-sentinel"
			) as get_value:
				result = (
					get_terms_environment(self.author)
					.from_string(
						"{{ frappe."
						+ formatter
						+ "(1, {'fieldtype': 'Currency', 'options': 'User:owner:email'}, record) }}"
					)
					.render(record=record)
				)
				get_value.assert_not_called()
				self.assertNotIn("terms-formatting-secret-sentinel", result)

	def test_renderer_uses_last_editor_permissions(self):
		frappe.set_user(self.author)
		terms = frappe.get_doc(
			doctype="Terms and Conditions",
			title="Editor permission sentinel",
			selling=1,
			terms="{{ frappe.get_list('Purchase Invoice', fields=['name']) }}",
		).insert()
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			get_terms_and_conditions(terms.name, {})


class TestTermsApplicability(UnitTestCase):
	def test_transaction_validation_rejects_wrong_side_with_prefilled_terms(self):
		from erpnext.controllers.buying_controller import BuyingController
		from erpnext.controllers.selling_controller import SellingController

		for controller, side in ((SellingController, "buying"), (BuyingController, "selling")):
			with self.subTest(controller=controller.__name__), patch("frappe.get_cached_doc") as get_doc:
				get_doc.return_value = frappe._dict(name="Wrong side", disabled=0, selling=0, buying=0)
				get_doc.return_value[side] = 1
				doc = controller.__new__(controller)
				doc.__dict__.update(tc_name="Wrong side", terms="Already filled")
				with self.assertRaises(frappe.ValidationError):
					doc.validate()

	def test_company_defaults_validate_both_sides(self):
		from erpnext.setup.doctype.company.company import Company

		for field in ("default_selling_terms", "default_buying_terms"):
			with self.subTest(field=field), patch("frappe.get_cached_doc") as get_doc:
				get_doc.return_value = frappe._dict(name="Disabled", disabled=1, selling=1, buying=1)
				doc = Company.__new__(Company)
				doc.__dict__[field] = "Disabled"
				with self.assertRaises(frappe.ValidationError):
					doc.validate()

	def test_pos_profile_and_blanket_order_validate_terms(self):
		from erpnext.accounts.doctype.pos_profile.pos_profile import POSProfile
		from erpnext.manufacturing.doctype.blanket_order.blanket_order import BlanketOrder

		for controller in (POSProfile, BlanketOrder):
			with self.subTest(controller=controller.__name__), patch("frappe.get_cached_doc") as get_doc:
				get_doc.return_value = frappe._dict(name="Disabled", disabled=1, selling=1, buying=1)
				doc = controller.__new__(controller)
				doc.__dict__.update(tc_name="Disabled", blanket_order_type="Selling")
				with self.assertRaises(frappe.ValidationError):
					doc.validate()

	def test_render_rejects_disabled_and_wrong_side_terms(self):
		for flags, doctype in (
			({"disabled": 1, "selling": 1, "buying": 1}, "Sales Order"),
			({"disabled": 0, "selling": 0, "buying": 1}, "Sales Order"),
			({"disabled": 0, "selling": 1, "buying": 0}, "Purchase Order"),
		):
			with self.subTest(flags=flags, doctype=doctype), patch("frappe.get_cached_doc") as get_doc:
				get_doc.return_value.terms = "Plain terms"
				get_doc.return_value.disabled = flags["disabled"]
				get_doc.return_value.get.side_effect = flags.get
				with self.assertRaises(frappe.ValidationError):
					get_terms_and_conditions("Test", {"doctype": doctype})

	def test_enabled_terms_validate_for_both_modules(self):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import (
			validate_terms_and_conditions,
		)

		with patch("frappe.get_cached_doc", return_value=frappe._dict(disabled=0, selling=1, buying=1)):
			validate_terms_and_conditions("Both", "selling")
			validate_terms_and_conditions("Both", "buying")
			validate_terms_and_conditions(None, "selling")


class TestTermsTransactionValidation(IntegrationTestCase):
	def test_prefilled_terms_cannot_bypass_transaction_save(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		terms = frappe.get_doc(
			doctype="Terms and Conditions",
			title="Buying-only terms sentinel",
			buying=1,
			selling=0,
			terms="Buying terms",
		).insert()
		self.addCleanup(frappe.db.rollback)
		doc = make_sales_order(do_not_save=True)
		doc.tc_name = terms.name
		doc.terms = "Already filled"
		with self.assertRaisesRegex(frappe.ValidationError, "not applicable"):
			doc.insert()

	def test_render_cannot_bypass_flags_with_client_docstatus(self):
		terms = frappe.get_doc(
			doctype="Terms and Conditions",
			title="Disabled terms sentinel",
			disabled=1,
			terms="Disabled terms",
		).insert()
		self.addCleanup(frappe.db.rollback)
		with self.assertRaisesRegex(frappe.ValidationError, "disabled"):
			get_terms_and_conditions(terms.name, {"doctype": "Sales Order", "docstatus": 1})

	def test_submitted_onload_does_not_render_terms_again(self):
		from frappe.model.docstatus import DocStatus

		from erpnext.controllers.selling_controller import SellingController
		from erpnext.controllers.stock_controller import StockController

		doc = SellingController.__new__(SellingController)
		doc.__dict__.update(
			doctype="Sales Order",
			docstatus=DocStatus(1),
			company="_Test Company",
			terms=None,
			tc_name="Disabled",
		)
		with (
			patch.object(StockController, "onload"),
			patch.object(
				SellingController,
				"set_missing_terms",
				side_effect=AssertionError("Historical terms rendered"),
			),
		):
			doc.onload()

	def test_draft_onload_keeps_invalid_terms_editable(self):
		from frappe.model.docstatus import DocStatus

		from erpnext.controllers.buying_controller import BuyingController
		from erpnext.controllers.selling_controller import SellingController
		from erpnext.controllers.stock_controller import StockController
		from erpnext.controllers.subcontracting_controller import SubcontractingController

		for controller, parent, module, doctype in (
			(SellingController, StockController, "selling", "Other"),
			(BuyingController, SubcontractingController, "buying", "Purchase Order"),
		):
			for disabled, applicable in ((1, 1), (0, 0), (0, 1)):
				with self.subTest(module=module, disabled=disabled, applicable=applicable):
					doc = controller.__new__(controller)
					doc.__dict__.update(
						doctype=doctype, docstatus=DocStatus(0), company="Company", terms=None, tc_name="Old"
					)
					tnc = frappe._dict(disabled=disabled, **{module: applicable})
					with (
						patch.object(parent, "onload"),
						patch("frappe.get_cached_doc", return_value=tnc),
						patch.object(controller, "set_missing_terms") as render,
					):
						doc.onload()
						self.assertEqual(render.call_count, int(not disabled and applicable))

	def test_company_save_retains_disabled_existing_default(self):
		self.addCleanup(frappe.db.rollback)
		terms = frappe.get_doc(
			doctype="Terms and Conditions",
			title=f"Company default sentinel {frappe.generate_hash(length=8)}",
			selling=1,
			terms="Terms",
		).insert()
		company = frappe.get_doc("Company", "_Test Company")
		company.default_selling_terms = terms.name
		company.save()
		terms.disabled = 1
		terms.save()
		company.reload()
		company.save()
		self.assertEqual(company.default_selling_terms, terms.name)

	def test_draft_with_disabled_terms_can_be_opened_and_corrected(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		self.addCleanup(frappe.db.rollback)
		for module, factory in (("selling", make_sales_order), ("buying", create_purchase_order)):
			with self.subTest(module=module):
				terms = frappe.get_doc(
					doctype="Terms and Conditions",
					title=f"Draft terms {frappe.generate_hash(length=8)}",
					**{module: 1},
				).insert()
				doc = factory(do_not_save=True)
				doc.tc_name = terms.name
				doc.terms = None
				doc.insert()
				terms.disabled = 1
				terms.save()
				doc.reload()
				doc.run_method("onload")
				self.assertEqual(doc.tc_name, terms.name)
				doc.tc_name = None
				doc.save()
				self.assertFalse(doc.tc_name)
