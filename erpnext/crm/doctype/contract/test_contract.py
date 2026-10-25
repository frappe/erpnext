# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_days, nowdate

from erpnext.crm.doctype.contract.contract import update_status_for_contracts
from erpnext.tests.utils import ERPNextTestSuite


class TestContract(ERPNextTestSuite):
	def setUp(self):
		self.contract_doc = get_contract()

	def test_validate_start_date_before_end_date(self):
		self.contract_doc.start_date = nowdate()
		self.contract_doc.end_date = add_days(nowdate(), -1)

		self.assertRaises(frappe.ValidationError, self.contract_doc.insert)

		self.contract_doc.start_date = None
		self.contract_doc.insert()

	def test_unsigned_contract_status(self):
		self.contract_doc.insert()
		self.assertEqual(self.contract_doc.status, "Unsigned")

	def test_active_signed_contract_status(self):
		sign(self.contract_doc)
		self.contract_doc.start_date = add_days(nowdate(), -1)
		self.contract_doc.end_date = add_days(nowdate(), 1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Active")

	def test_past_inactive_signed_contract_status(self):
		sign(self.contract_doc)
		self.contract_doc.start_date = add_days(nowdate(), -2)
		self.contract_doc.end_date = add_days(nowdate(), -1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_future_inactive_signed_contract_status(self):
		sign(self.contract_doc)
		self.contract_doc.start_date = add_days(nowdate(), 1)
		self.contract_doc.end_date = add_days(nowdate(), 2)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_open_ended_contract_starting_later_is_inactive(self):
		sign(self.contract_doc)
		self.contract_doc.start_date = add_days(nowdate(), 30)
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

	def test_daily_job_lapses_fulfilment_after_the_deadline(self):
		contract = self.make_signed_contract(fulfilment_deadline=nowdate())
		self.assertEqual(contract.fulfilment_status, "Unfulfilled")

		with patch("erpnext.crm.doctype.contract.contract.nowdate", return_value=add_days(nowdate(), 1)):
			update_status_for_contracts()
		self.assertEqual(frappe.db.get_value("Contract", contract.name, "fulfilment_status"), "Lapsed")

	def test_fulfilment_terms_cannot_be_replaced_after_submit(self):
		contract = self.make_signed_contract()
		contract.fulfilment_terms = []
		contract.append("fulfilment_terms", {"requirement": "Nothing", "fulfilled": 1})
		self.assertRaises(frappe.UpdateAfterSubmitError, contract.save)

		contract.reload()
		contract.fulfilment_terms[0].fulfilled = 1
		contract.save()
		self.assertEqual(contract.fulfilment_status, "Fulfilled")

	def test_signature_is_required_and_kept_after_submit(self):
		self.contract_doc.is_signed = 1
		self.assertRaises(frappe.ValidationError, self.contract_doc.insert)

		contract = self.make_signed_contract()
		contract.is_signed = 0
		contract.signee = "Someone else"
		self.assertRaises(frappe.UpdateAfterSubmitError, contract.save)

	def test_missing_signature_details_can_be_filled_after_submit(self):
		contract = self.make_signed_contract()
		frappe.db.set_value("Contract", contract.name, {"signee": None, "signed_on": None})
		contract.reload()

		sign(contract)
		contract.fulfilment_terms[0].fulfilled = 1
		contract.save()
		self.assertEqual(frappe.db.get_value("Contract", contract.name, "signee"), "Test Signee")

		contract.signee = "Someone else"
		self.assertRaises(frappe.UpdateAfterSubmitError, contract.save)

	def test_cancelled_contract_status(self):
		contract = self.make_signed_contract()
		contract.cancel()
		self.assertEqual(frappe.db.get_value("Contract", contract.name, "status"), "Cancelled")

	def test_party_full_name_follows_the_party(self):
		self.contract_doc.insert()
		self.contract_doc.party_name = "_Test Customer 1"
		self.contract_doc.save()

		customer_name = frappe.db.get_value("Customer", "_Test Customer 1", "customer_name")
		self.assertEqual(self.contract_doc.party_full_name, customer_name)

	def test_linked_document_must_belong_to_the_party(self):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test Contract Project",
				"customer": "_Test Customer 1",
				"company": "_Test Company",
			}
		).insert()
		self.contract_doc.document_type = "Project"
		self.contract_doc.document_name = project.name
		self.assertRaises(frappe.ValidationError, self.contract_doc.insert)

		self.contract_doc.party_name = "_Test Customer 1"
		self.contract_doc.insert()

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

	def make_signed_contract(self, **fields):
		sign(self.contract_doc)
		self.contract_doc.update(
			{
				"start_date": nowdate(),
				"requires_fulfilment": 1,
				**fields,
			}
		)
		self.contract_doc.append("fulfilment_terms", {"requirement": "Deliver 10 tables"})
		self.contract_doc.insert()
		self.contract_doc.submit()
		return self.contract_doc


def sign(contract):
	contract.update({"is_signed": 1, "signee": "Test Signee", "signed_on": frappe.utils.now_datetime()})


def get_contract():
	doc = frappe.new_doc("Contract")
	doc.party_type = "Customer"
	doc.party_name = "_Test Customer"
	doc.contract_terms = "This is a test customer contract."
	return doc
