import frappe

from erpnext.accounts.party import get_default_price_list, set_price_list
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

	def test_set_price_list_uses_default_user_permission(self):
		# multiple permitted price lists, one Is Default -> use the Is Default one
		for pl in ("_Test PL A", "_Test PL B"):
			if not frappe.db.exists("Price List", pl):
				frappe.get_doc(
					{"doctype": "Price List", "price_list_name": pl, "selling": 1, "currency": "INR"}
				).insert(ignore_permissions=True)

		user = "test_pl_perm@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "PL", "roles": [{"role": "Sales User"}]}
			).insert(ignore_permissions=True)

		for pl, is_default in (("_Test PL A", 0), ("_Test PL B", 1)):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": "Price List",
					"for_value": pl,
					"is_default": is_default,
				}
			).insert(ignore_permissions=True)

		customer = frappe.get_doc({"doctype": "Customer", "customer_name": "test pl perm customer"}).insert(
			ignore_permissions=True, ignore_mandatory=True
		)

		party_details = frappe._dict()
		frappe.set_user(user)
		try:
			set_price_list(party_details, customer, "Customer", None)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(party_details.selling_price_list, "_Test PL B")

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

	def create_price_list(self, enabled):
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": frappe.generate_hash(length=10),
				"currency": "INR",
				"selling": 1,
				"enabled": enabled,
			}
		).insert(ignore_permissions=True)

		return price_list.name

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
