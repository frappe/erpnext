# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_user_permission
from frappe.utils import add_days, nowdate

from erpnext.tests.utils import ERPNextTestSuite


class TestContract(ERPNextTestSuite):
	def setUp(self):
		self.contract_doc = get_contract()

	def test_validate_start_date_before_end_date(self):
		self.contract_doc.start_date = nowdate()
		self.contract_doc.end_date = add_days(nowdate(), -1)

		self.assertRaises(frappe.ValidationError, self.contract_doc.insert)

	def test_unsigned_contract_status(self):
		self.contract_doc.insert()
		self.assertEqual(self.contract_doc.status, "Unsigned")

	def test_active_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), -1)
		self.contract_doc.end_date = add_days(nowdate(), 1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Active")

	def test_past_inactive_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), -2)
		self.contract_doc.end_date = add_days(nowdate(), -1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_future_inactive_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), 1)
		self.contract_doc.end_date = add_days(nowdate(), 2)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_contract_status_with_no_fulfilment_terms(self):
		self.contract_doc.contract_term = "_Test Customer Contract"
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.fulfilment_status, "N/A")

	def test_unfulfilled_contract_status(self):
		self.contract_doc.contract_term = "_Test Customer Contract with Requirements"
		self.contract_doc.requires_fulfilment = 1
		self.contract_doc.save()
		self.assertEqual(self.contract_doc.fulfilment_status, "Unfulfilled")

	def test_fulfilled_contract_status(self):
		self.contract_doc.contract_terms = "_Test Customer Contract with Requirements"

		# Mark all the terms as fulfilled
		self.contract_doc.requires_fulfilment = 1
		fulfilment_terms = []
		fulfilment_terms.append({"requirement": "This is a test requirement.", "fulfilled": 0})
		self.contract_doc.set("fulfilment_terms", fulfilment_terms)

		for term in self.contract_doc.fulfilment_terms:
			term.fulfilled = 1

		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Fulfilled")

	def test_partially_fulfilled_contract_status(self):
		self.contract_doc.contract_terms = "_Test Customer Contract with Requirements"
		self.contract_doc.requires_fulfilment = 1

		# Mark only the first term as fulfilled
		self.contract_doc.save()
		fulfilment_terms = []
		fulfilment_terms.append({"requirement": "This is a test requirement.", "fulfilled": 0})
		fulfilment_terms.append({"requirement": "This is another test requirement.", "fulfilled": 0})

		self.contract_doc.set("fulfilment_terms", fulfilment_terms)
		self.contract_doc.fulfilment_terms[0].fulfilled = 1
		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Partially Fulfilled")

	def test_lapsed_contract_status(self):
		self.contract_doc.contract_term = "_Test Customer Contract with Requirements"
		self.contract_doc.start_date = add_days(nowdate(), -2)
		self.contract_doc.end_date = add_days(nowdate(), 1)
		self.contract_doc.requires_fulfilment = 1
		self.contract_doc.fulfilment_deadline = add_days(nowdate(), -1)
		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Lapsed")

	def test_party_managers_reach_only_contracts_of_their_party_type(self):
		contracts = self.make_party_contracts()
		purchase_manager = create_user("contract-purchase-manager@example.com", "Purchase Manager")
		sales_manager = create_user("contract-sales-manager@example.com", "Sales Manager")

		self.assertEqual(
			self.get_visible_contracts(purchase_manager.name, contracts), {contracts["supplier"]}
		)
		self.assertEqual(
			self.get_visible_contracts(sales_manager.name, contracts),
			{contracts["customer"], contracts["other_customer"]},
		)
		self.assertFalse(
			frappe.has_permission("Contract", "write", doc=contracts["customer"], user=purchase_manager.name)
		)
		self.assertTrue(
			frappe.has_permission("Contract", "write", doc=contracts["supplier"], user=purchase_manager.name)
		)

	def test_user_permissions_on_the_party_restrict_contracts(self):
		contracts = self.make_party_contracts()
		user = create_user(
			"contract-restricted-sales-manager@example.com", "Sales Manager", "Purchase Manager"
		)
		add_user_permission("Customer", "_Test Customer", user.name)

		self.assertEqual(
			self.get_visible_contracts(user.name, contracts), {contracts["customer"], contracts["supplier"]}
		)
		self.assertTrue(frappe.has_permission("Contract", "read", doc=contracts["customer"], user=user.name))
		self.assertFalse(
			frappe.has_permission("Contract", "read", doc=contracts["other_customer"], user=user.name)
		)

	def test_no_contracts_when_none_of_the_party_types_exist(self):
		contract = get_contract()
		employee = frappe.db.get_value("Employee", {"first_name": "_Test Employee"})
		contract.update({"party_type": "Employee", "party_name": employee})
		contract.insert()

		make_property_setter("Contract", "party_type", "options", "Customer\nSupplier", "Text")
		self.addCleanup(frappe.clear_cache, doctype="Contract")
		user = create_user("contract-hr-manager@example.com", "HR Manager")

		self.assertEqual(self.get_visible_contracts(user.name, {"employee": contract.name}), set())
		self.assertFalse(frappe.has_permission("Contract", "read", doc=contract, user=user.name))

	def make_party_contracts(self) -> dict[str, str]:
		parties = {
			"customer": ("Customer", "_Test Customer"),
			"other_customer": ("Customer", "_Test Customer 1"),
			"supplier": ("Supplier", "_Test Supplier"),
		}
		contracts = {}
		for key, (party_type, party_name) in parties.items():
			contract = get_contract()
			contract.update({"party_type": party_type, "party_name": party_name})
			contracts[key] = contract.insert().name

		return contracts

	def get_visible_contracts(self, user: str, contracts: dict[str, str]) -> set[str]:
		with self.set_user(user):
			names = frappe.get_list(
				"Contract", filters={"name": ("in", list(contracts.values()))}, pluck="name"
			)

		return set(names)


def get_contract():
	doc = frappe.new_doc("Contract")
	doc.party_type = "Customer"
	doc.party_name = "_Test Customer"
	doc.contract_terms = "This is a test customer contract."
	return doc
