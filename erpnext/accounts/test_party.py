from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.party import (
	get_address_tax_category,
	get_default_price_list,
	get_party_account,
	get_party_details,
	set_price_list,
)
from erpnext.selling.doctype.customer.test_customer import get_customer_dict
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class PartyTestCase(ERPNextTestSuite):
	def test_party_account_lookup_refreshes_after_changes(self):
		group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": frappe.generate_hash(length=10),
				"parent_customer_group": "All Customer Groups",
			}
		).insert()
		customer = frappe.get_doc(get_customer_dict(frappe.generate_hash(length=10)))
		customer.customer_group = group.name
		customer.insert()
		company = "_Test Company"
		default_account = frappe.get_cached_value("Company", company, "default_receivable_account")
		account = create_account(
			account_name=frappe.generate_hash(length=10),
			parent_account="Accounts Receivable - _TC",
			account_type="Receivable",
		)
		self.assertEqual(get_party_account("Customer", customer.name, company), default_account)
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as queries:
			self.assertEqual(get_party_account("Customer", customer.name, company), default_account)
			self.assertFalse(any("tabParty Account" in str(call.args[0]) for call in queries.call_args_list))

		group.append("accounts", {"company": company, "account": account})
		group.save()
		self.assertEqual(get_party_account("Customer", customer.name, company), account)
		frappe.db.savepoint("party_accounts")
		customer.append("accounts", {"company": company, "account": default_account})
		customer.save()
		self.assertEqual(get_party_account("Customer", customer.name, company), default_account)
		frappe.db.rollback(save_point="party_accounts")
		self.assertEqual(get_party_account("Customer", customer.name, company), account)
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_party_account("Customer", customer.name, company)
		group.accounts = []
		group.save()
		self.assertEqual(get_party_account("Customer", customer.name, company), default_account)

	def test_get_default_price_list_should_return_none_for_invalid_group(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "test customer",
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)
		customer.customer_group = None
		customer.save()
		price_list = get_default_price_list(customer)
		assert price_list is None

	def test_disabled_party_default_should_fall_back_to_given_price_list(self):
		customer = self.create_customer(default_price_list=self.create_price_list(enabled=0))
		given_price_list = self.create_price_list(enabled=1)

		party_details = frappe._dict()
		set_price_list(party_details, customer, "Customer", given_price_list)

		self.assertEqual(party_details.selling_price_list, given_price_list)

	def test_disabled_given_price_list_should_not_be_set(self):
		customer = self.create_customer()

		party_details = frappe._dict()
		set_price_list(party_details, customer, "Customer", self.create_price_list(enabled=0))

		self.assertIsNone(party_details.selling_price_list)

	def test_fallback_should_not_pick_an_unpermitted_price_list(self):
		permitted_default = self.create_price_list(enabled=1)
		permitted_other = self.create_price_list(enabled=1)
		user = self.create_user_with_price_list_permissions([permitted_default, permitted_other])
		customer = self.create_customer()

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(
				party_details, customer, "Customer", self.create_price_list(enabled=1), doctype="Sales Order"
			)

		self.assertEqual(party_details.selling_price_list, permitted_default)

	def test_permitted_given_price_list_should_be_kept(self):
		permitted_default = self.create_price_list(enabled=1)
		permitted_other = self.create_price_list(enabled=1)
		user = self.create_user_with_price_list_permissions([permitted_default, permitted_other])
		customer = self.create_customer()

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(party_details, customer, "Customer", permitted_other, doctype="Sales Order")

		self.assertEqual(party_details.selling_price_list, permitted_other)

	def test_permission_for_another_doctype_should_not_apply(self):
		permitted = [self.create_price_list(enabled=1), self.create_price_list(enabled=1)]
		user = self.create_user_with_price_list_permissions(permitted, applicable_for="Quotation")
		customer = self.create_customer()
		given_price_list = self.create_price_list(enabled=1)

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(party_details, customer, "Customer", given_price_list, doctype="Sales Order")

		self.assertEqual(party_details.selling_price_list, given_price_list)

	def test_a_single_permitted_price_list_should_fit_the_transaction(self):
		buying_price_list = self.create_price_list(enabled=1, selling=0, buying=1)
		user = self.create_user_with_price_list_permissions([buying_price_list])
		customer = self.create_customer()
		given_price_list = self.create_price_list(enabled=1)

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(party_details, customer, "Customer", given_price_list, doctype="Sales Order")

		self.assertIsNone(party_details.selling_price_list)

	def test_buying_transaction_should_not_take_a_selling_price_list(self):
		permitted = [self.create_price_list(enabled=1) for _ in range(2)]
		user = self.create_user_with_price_list_permissions(permitted)
		supplier_price_list = self.create_price_list(enabled=1, selling=0, buying=1)
		supplier = self.create_supplier(default_price_list=supplier_price_list)

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(party_details, supplier, "Supplier", None, doctype="Purchase Order")

		self.assertIsNone(party_details.buying_price_list)

	def test_permission_for_another_doctype_should_not_apply_without_a_doctype(self):
		permitted = [self.create_price_list(enabled=1), self.create_price_list(enabled=1)]
		user = self.create_user_with_price_list_permissions(permitted, applicable_for="Quotation")
		customer = self.create_customer()
		given_price_list = self.create_price_list(enabled=1)

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(party_details, customer, "Customer", given_price_list)

		self.assertEqual(party_details.selling_price_list, given_price_list)

	def test_pos_price_list_should_be_kept(self):
		permitted = [self.create_price_list(enabled=1), self.create_price_list(enabled=1)]
		user = self.create_user_with_price_list_permissions(permitted)
		pos_price_list = self.create_price_list(enabled=1)
		pos_profile = make_pos_profile(selling_price_list=pos_price_list)
		customer = self.create_customer()

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(
				party_details, customer, "Customer", None, pos=pos_profile.name, doctype="POS Invoice"
			)

		self.assertEqual(party_details.selling_price_list, pos_price_list)

	def test_disabled_permitted_price_lists_should_clear_the_price_list(self):
		permitted = [self.create_price_list(enabled=0), self.create_price_list(enabled=0)]
		user = self.create_user_with_price_list_permissions(permitted)
		customer = self.create_customer()
		given_price_list = self.create_price_list(enabled=1)

		party_details = frappe._dict()
		with self.set_user(user):
			set_price_list(party_details, customer, "Customer", given_price_list, doctype="Sales Order")

		self.assertIsNone(party_details.selling_price_list)

	def test_billing_address_outside_the_company_needs_address_read(self):
		other_address = self.create_billing_address()
		own_address = self.create_billing_address(
			links=[{"link_doctype": "Company", "link_name": "_Test Company"}]
		)
		# no supplier address, so only the billing address is rendered
		supplier = self.create_supplier().name
		stock_user = make_fenced_user("party-details-stock-user@example.com", ["Stock User"])
		purchase_user = make_fenced_user("party-details-purchase-user@example.com", ["Purchase User"])

		with self.set_user(stock_user):
			self.assertRaises(
				frappe.PermissionError, get_purchase_receipt_party_details, supplier, other_address
			)
			# the company's own address renders as before
			details = get_purchase_receipt_party_details(supplier, own_address)
			self.assertIn("1 Billing Street", details.billing_address_display)

		with self.set_user(purchase_user):
			details = get_purchase_receipt_party_details(supplier, other_address)
		self.assertEqual(details.billing_address, other_address)
		self.assertIn("1 Billing Street", details.billing_address_display)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"determine_address_tax_category_from": "Billing Address"}
	)
	def test_address_without_tax_category_should_fall_back_to_the_party(self):
		customer = self.create_customer(tax_category="_Test Tax Category 1")
		address_with_category = self.create_billing_address()
		frappe.db.set_value("Address", address_with_category, "tax_category", "_Test Tax Category 2")
		address_without_category = self.create_billing_address()
		pos_profile = make_pos_profile()
		pos_profile.db_set("tax_category", "_Test Tax Category 3")

		def tax_category(address, customer_name, pos_profile=None):
			return get_address_tax_category(
				billing_address=address, party_type="Customer", party=customer_name, pos_profile=pos_profile
			)

		self.assertEqual(tax_category(address_with_category, customer.name), "_Test Tax Category 2")
		self.assertEqual(tax_category(address_without_category, customer.name), "_Test Tax Category 1")
		self.assertEqual(
			tax_category(address_without_category, self.create_customer().name, pos_profile.name),
			"_Test Tax Category 3",
		)

	def create_user_with_price_list_permissions(self, price_lists, applicable_for=None):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"{frappe.generate_hash(length=10)}@example.com",
				"first_name": "Price List Test",
				"send_welcome_email": 0,
				"roles": [{"role": "Sales User"}],
			}
		).insert(ignore_permissions=True)

		for idx, price_list in enumerate(price_lists):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user.name,
					"allow": "Price List",
					"for_value": price_list,
					"is_default": int(idx == 0),
					"apply_to_all_doctypes": int(not applicable_for),
					"applicable_for": applicable_for,
				}
			).insert(ignore_permissions=True)

		frappe.clear_cache(user=user.name)
		self.addCleanup(frappe.clear_cache, user=user.name)

		return user.name

	def create_price_list(self, enabled, selling=1, buying=0):
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": frappe.generate_hash(length=10),
				"currency": "INR",
				"selling": selling,
				"buying": buying,
				"enabled": enabled,
			}
		).insert(ignore_permissions=True)

		return price_list.name

	def create_supplier(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": frappe.generate_hash(length=10),
				**values,
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)

	def create_customer(self, **values):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": frappe.generate_hash(length=10),
				**values,
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)
		customer.customer_group = None
		customer.save()

		return customer

	def create_billing_address(self, links=None):
		return (
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": frappe.generate_hash(length=10),
					"address_type": "Billing",
					"address_line1": "1 Billing Street",
					"city": "Pune",
					"country": "India",
					"links": links or [],
				}
			)
			.insert()
			.name
		)


def get_purchase_receipt_party_details(supplier, company_address):
	return get_party_details(
		party=supplier,
		party_type="Supplier",
		company="_Test Company",
		doctype="Purchase Receipt",
		company_address=company_address,
	)
