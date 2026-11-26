import frappe

from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.party import get_address_tax_category, get_default_price_list, set_price_list
from erpnext.tests.utils import ERPNextTestSuite


class PartyTestCase(ERPNextTestSuite):
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

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"determine_address_tax_category_from": "Billing Address"}
	)
	def test_address_without_tax_category_should_fall_back_to_the_party(self):
		customer = self.create_customer(tax_category="_Test Tax Category 1")
		address_with_category = self.create_address(tax_category="_Test Tax Category 2")
		address_without_category = self.create_address()
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

	def create_address(self, tax_category=None):
		address = frappe.new_doc("Address")
		address.address_title = frappe.generate_hash(length=10)
		address.address_line1 = "Line 1"
		address.city = "Mumbai"
		address.country = "India"
		address.tax_category = tax_category
		address.insert(ignore_permissions=True)

		return address.name

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
