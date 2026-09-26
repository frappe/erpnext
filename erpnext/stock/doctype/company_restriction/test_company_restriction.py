# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.accounts.party import get_party_details
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.controllers.queries import party_query
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.stock.doctype.company_restriction.company_restriction import CompanyRestrictionError
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.tests.utils import ERPNextTestSuite


class TestCompanyRestriction(ERPNextTestSuite):
	def restrict_to_companies(self, doctype, name, companies):
		doc = frappe.get_doc(doctype, name)
		doc.restrict_to_companies = 1
		doc.set("allowed_companies", [])
		for company in companies:
			doc.append("allowed_companies", {"company": company})
		doc.save()

	def test_restricted_item_blocks_transaction_in_other_company(self):
		item = make_item()
		self.restrict_to_companies("Item", item.name, ["_Test Company 1"])

		self.assertRaises(CompanyRestrictionError, make_material_request, item_code=item.name)

		self.restrict_to_companies("Item", item.name, ["_Test Company 1", "_Test Company"])
		make_material_request(item_code=item.name)

	def test_restricted_customer_blocks_transaction_in_other_company(self):
		customer = make_customer("_Test Company Restricted Customer")
		self.restrict_to_companies("Customer", customer, ["_Test Company 1"])

		self.assertRaises(CompanyRestrictionError, make_quotation, party_name=customer, do_not_submit=1)

		self.restrict_to_companies("Customer", customer, ["_Test Company"])
		make_quotation(party_name=customer, do_not_submit=1)

	def test_restricted_supplier_blocks_transaction_in_other_company(self):
		supplier = create_supplier(supplier_name="_Test Company Restricted Supplier")
		self.restrict_to_companies("Supplier", supplier.name, ["_Test Company 1"])

		self.assertRaises(
			CompanyRestrictionError, create_purchase_order, supplier=supplier.name, do_not_submit=1
		)

		self.restrict_to_companies("Supplier", supplier.name, ["_Test Company"])
		create_purchase_order(supplier=supplier.name, do_not_submit=1)

	def test_party_query_filters_customer_and_supplier_by_transaction_company(self):
		customer = make_customer("_Test Company Query Restricted Customer")
		supplier = create_supplier(supplier_name="_Test Company Query Restricted Supplier")

		for doctype, party in (("Customer", customer), ("Supplier", supplier.name)):
			self.restrict_to_companies(doctype, party, ["_Test Company 1"])

			results = party_query(
				doctype,
				party,
				"name",
				0,
				20,
				filters={"disabled": 0, "company": "_Test Company"},
			)
			self.assertNotIn(party, [row[0] for row in results])

			results = party_query(
				doctype,
				party,
				"name",
				0,
				20,
				filters={"disabled": 0, "company": "_Test Company 1"},
			)
			self.assertIn(party, [row[0] for row in results])

	def test_get_party_details_checks_transaction_company_restriction(self):
		customer = make_customer("_Test Party Details Restricted Customer")
		supplier = create_supplier(supplier_name="_Test Party Details Restricted Supplier")

		for doctype, party in (("Customer", customer), ("Supplier", supplier.name)):
			self.restrict_to_companies(doctype, party, ["_Test Company 1"])

			self.assertRaises(
				CompanyRestrictionError,
				get_party_details,
				party=party,
				party_type=doctype,
				company="_Test Company",
			)

	def test_unrestricted_party_ignores_company_permission(self):
		customer = make_customer("_Test Party Details Company Permission Customer")
		user = self.make_user_with_roles("test_party_details_company@example.com", ["Sales User"])
		self.allow_company(user, "_Test Company 1")

		with self.set_user(user):
			results = party_query(
				"Customer",
				customer,
				"name",
				0,
				20,
				filters={"disabled": 0, "company": "_Test Company"},
			)
			self.assertIn(customer, [row[0] for row in results])

			details = get_party_details(
				party=customer,
				party_type="Customer",
				company="_Test Company",
			)
			self.assertEqual(details.customer, customer)

	def test_unrestricted_item_is_not_blocked(self):
		item = make_item()
		make_material_request(item_code=item.name)

	def test_allowed_companies_is_mandatory_when_restricted(self):
		item = make_item()
		item.restrict_to_companies = 1
		self.assertRaises(frappe.MandatoryError, item.save)

	def test_exempt_doctypes_exist(self):
		from erpnext.stock.doctype.company_restriction.company_restriction import (
			COMPANY_RESTRICTION_EXEMPT_DOCTYPES,
		)

		for doctype in COMPANY_RESTRICTION_EXEMPT_DOCTYPES:
			self.assertTrue(frappe.db.exists("DocType", doctype), f"{doctype} is not a DocType")

	def test_cancel_works_after_restriction_change(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item()
		stock_entry = make_stock_entry(
			item_code=item.name, qty=5, to_warehouse="_Test Warehouse - _TC", rate=100
		)

		self.restrict_to_companies("Item", item.name, ["_Test Company 1"])
		stock_entry.reload()
		stock_entry.cancel()

	def allow_company(self, user, company):
		permission = {
			"user": user,
			"allow": "Company",
			"for_value": company,
			"apply_to_all_doctypes": 1,
		}
		if not frappe.db.exists("User Permission", permission):
			frappe.get_doc({"doctype": "User Permission", **permission}).insert(ignore_permissions=True)
		frappe.clear_cache(user=user)

	def make_item_price(self, item_code):
		return (
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "_Test Price List",
					"item_code": item_code,
					"price_list_rate": 100,
				}
			)
			.insert()
			.name
		)

	def test_item_price_inherits_item_company_restriction(self):
		restricted = make_item()
		allowed = make_item()
		self.restrict_to_companies("Item", restricted.name, ["_Test Company 1"])
		prices = {item.name: self.make_item_price(item.name) for item in (restricted, allowed)}

		user = self.make_user_with_roles("test_item_price_restriction@example.com", ["Sales Master Manager"])
		self.allow_company(user, "_Test Company")

		with self.set_user(user):
			visible = frappe.get_list(
				"Item Price",
				filters={"item_code": ("in", [restricted.name, allowed.name])},
				pluck="item_code",
			)
			self.assertEqual(visible, [allowed.name])

			self.assertFalse(frappe.has_permission("Item Price", doc=prices[restricted.name]))
			self.assertTrue(frappe.has_permission("Item Price", doc=prices[allowed.name]))

	def test_item_price_is_visible_without_company_permission(self):
		restricted = make_item()
		self.restrict_to_companies("Item", restricted.name, ["_Test Company 1"])
		price = self.make_item_price(restricted.name)

		user = self.make_user_with_roles("test_item_price_unrestricted@example.com", ["Sales Master Manager"])

		with self.set_user(user):
			self.assertTrue(frappe.has_permission("Item Price", doc=price))

	def make_user_with_roles(self, email, roles):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"roles": [{"role": role} for role in roles],
				}
			).insert(ignore_permissions=True)
		return email

	def test_restriction_fields_require_permlevel_access(self):
		customer = make_customer("_Test Permlevel Restricted Customer")
		self.restrict_to_companies("Customer", customer, ["_Test Company"])

		sales_user = self.make_user_with_roles("test_company_restriction_sales@example.com", ["Sales User"])
		manager = self.make_user_with_roles(
			"test_company_restriction_manager@example.com", ["Sales User", "Sales Master Manager"]
		)

		permitted = frappe.get_meta("Customer").get_permitted_fieldnames(user=sales_user)
		self.assertNotIn("restrict_to_companies", permitted)

		permitted = frappe.get_meta("Customer").get_permitted_fieldnames(user=manager)
		self.assertIn("restrict_to_companies", permitted)

		with self.set_user(sales_user):
			doc = frappe.get_doc("Customer", customer)
			doc.restrict_to_companies = 0
			doc.set("allowed_companies", [])
			doc.save()

			doc.reload()
			self.assertEqual(doc.restrict_to_companies, 1)
			self.assertEqual([row.company for row in doc.allowed_companies], ["_Test Company"])

	def make_report_user(self):
		user = self.make_user_with_roles(
			"test_company_restriction_reports@example.com", ["Stock User", "Sales User", "Accounts User"]
		)
		self.allow_company(user, "_Test Company")
		return user

	def run_report(self, module, report, filters):
		execute = frappe.get_attr(f"erpnext.{module}.report.{report}.{report}.execute")
		return execute(frappe._dict(filters))[1]

	def test_item_prices_report_hides_restricted_items(self):
		restricted, allowed = make_item(), make_item()
		self.restrict_to_companies("Item", restricted.name, ["_Test Company 1"])

		items = {row[0] for row in self.run_report("stock", "item_prices", {})}
		self.assertTrue({restricted.name, allowed.name} <= items)

		with self.set_user(self.make_report_user()):
			items = {row[0] for row in self.run_report("stock", "item_prices", {})}
			self.assertIn(allowed.name, items)
			self.assertNotIn(restricted.name, items)

	def test_variant_reports_hide_restricted_variants(self):
		from erpnext.controllers.item_variant import create_variant

		template = make_item(properties={"has_variants": 1, "attributes": [{"attribute": "Test Size"}]})
		restricted = create_variant(template.name, {"Test Size": "Small"}).insert()
		allowed = create_variant(template.name, {"Test Size": "Large"}).insert()
		self.restrict_to_companies("Item", restricted.name, ["_Test Company 1"])

		with self.set_user(self.make_report_user()):
			rows = self.run_report("stock", "item_variant_details", {"item": template.name})
			self.assertEqual([row["variant_name"] for row in rows], [allowed.name])

			rows = self.run_report("stock", "item_where_used", {"item": template.name})
			self.assertEqual([row.related_item for row in rows], [allowed.name])

	def test_bom_search_hides_restricted_product_bundles(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle

		component = make_item()
		restricted = make_product_bundle(make_item(properties={"is_stock_item": 0}).name, [component.name])
		allowed = make_product_bundle(make_item(properties={"is_stock_item": 0}).name, [component.name])
		self.restrict_to_companies("Item", restricted.new_item_code, ["_Test Company 1"])

		with self.set_user(self.make_report_user()):
			rows = self.run_report(
				"stock", "bom_search", {"search_sub_assemblies": 0, "item1": component.name}
			)
			self.assertEqual([row[0] for row in rows], [allowed.name])

	def test_trial_balance_for_party_hides_restricted_customers(self):
		from erpnext.accounts.utils import get_fiscal_year

		restricted = make_customer("_Test Trial Balance Restricted Customer")
		allowed = make_customer("_Test Trial Balance Allowed Customer")
		self.restrict_to_companies("Customer", restricted, ["_Test Company 1"])
		filters = {
			"company": "_Test Company",
			"fiscal_year": get_fiscal_year(frappe.utils.nowdate(), company="_Test Company")[0],
			"party_type": "Customer",
			"show_zero_values": 1,
			"exclude_zero_balance_parties": 0,
		}

		with self.set_user(self.make_report_user()):
			rows = self.run_report("accounts", "trial_balance_for_party", filters)
			parties = {row.get("party") for row in rows}
			self.assertIn(allowed, parties)
			self.assertNotIn(restricted, parties)

	def test_converted_query_reports_hide_restricted_masters(self):
		restricted_item, allowed_item = make_item(), make_item()
		restricted_customer = make_customer("_Test Query Report Restricted Customer")
		allowed_customer = make_customer("_Test Query Report Allowed Customer")
		self.restrict_to_companies("Item", restricted_item.name, ["_Test Company 1"])
		self.restrict_to_companies("Customer", restricted_customer, ["_Test Company 1"])

		with self.set_user(self.make_report_user()):
			items = {row.item_code for row in self.run_report("stock", "item_balance", {})}
			self.assertIn(allowed_item.name, items)
			self.assertNotIn(restricted_item.name, items)

			rows = self.run_report("selling", "customers_without_any_sales_transactions", {})
			customers = {row.customer for row in rows}
			self.assertIn(allowed_customer, customers)
			self.assertNotIn(restricted_customer, customers)
