# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import create_bank_account


class TestAutoMatchParty(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		create_bank_account()
		frappe.db.set_single_value("Accounts Settings", "enable_party_matching", 1)
		frappe.db.set_single_value("Accounts Settings", "enable_fuzzy_matching", 1)
		return super().setUpClass()

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_single_value("Accounts Settings", "enable_party_matching", 0)
		frappe.db.set_single_value("Accounts Settings", "enable_fuzzy_matching", 0)

	def test_match_by_account_number(self):
		"""Test if transaction matches with existing (Bank Party Mapper) or new match."""
		create_supplier_for_match(account_no="000000003716541159")
		doc = create_bank_transaction(
			withdrawal=1200,
			transaction_id="562213b0ca1bf838dab8f2c6a39bbc3b",
			account_no="000000003716541159",
			iban="DE02000000003716541159",
		)

		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "John Doe & Co.")
		self.assertTrue(doc.bank_party_mapper)

		# Check if Bank Party Mapper is created to remember mapping
		bank_party_mapper = frappe.get_doc("Bank Party Mapper", doc.bank_party_mapper)
		self.assertEqual(bank_party_mapper.party, "John Doe & Co.")
		self.assertEqual(bank_party_mapper.bank_party_account_number, "000000003716541159")
		self.assertEqual(bank_party_mapper.bank_party_iban, "DE02000000003716541159")

		# Check if created mapping is used for quick match
		doc_2 = create_bank_transaction(
			withdrawal=500,
			transaction_id="602413b8ji8bf838fub8f2c6a39bah7y",
			account_no="000000003716541159",
		)
		self.assertEqual(doc_2.party, "John Doe & Co.")
		self.assertEqual(doc_2.bank_party_mapper, bank_party_mapper.name)

	def test_match_by_iban(self):
		create_supplier_for_match(iban="DE02000000003716541159")
		doc = create_bank_transaction(
			withdrawal=1200,
			transaction_id="c5455a224602afaa51592a9d9250600d",
			account_no="000000003716541159",
			iban="DE02000000003716541159",
		)

		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "John Doe & Co.")
		self.assertTrue(doc.bank_party_mapper)

		bank_party_mapper = frappe.get_doc("Bank Party Mapper", doc.bank_party_mapper)
		self.assertEqual(bank_party_mapper.party, "John Doe & Co.")
		self.assertEqual(bank_party_mapper.bank_party_account_number, "000000003716541159")
		self.assertEqual(bank_party_mapper.bank_party_iban, "DE02000000003716541159")

	def test_match_by_party_name(self):
		create_supplier_for_match(supplier_name="Jackson Ella W.")
		doc = create_bank_transaction(
			withdrawal=1200,
			transaction_id="1f6f661f347ff7b1ea588665f473adb1",
			party_name="Ella Jackson",
			iban="DE04000000003716545346",
		)
		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "Jackson Ella W.")
		self.assertTrue(doc.bank_party_mapper)

		bank_party_mapper = frappe.get_doc("Bank Party Mapper", doc.bank_party_mapper)
		self.assertEqual(bank_party_mapper.party, "Jackson Ella W.")
		self.assertEqual(bank_party_mapper.bank_party_name, "Ella Jackson")
		self.assertEqual(bank_party_mapper.bank_party_iban, None)

		# Check if created mapping is used for quick match
		doc_2 = create_bank_transaction(
			withdrawal=500,
			transaction_id="578313b8ji8bf838fub8f2c6a39bah7y",
			party_name="Ella Jackson",
			account_no="000000004316531152",
		)
		self.assertEqual(doc_2.party, "Jackson Ella W.")
		self.assertEqual(doc_2.bank_party_mapper, bank_party_mapper.name)

	def test_match_by_description(self):
		create_supplier_for_match(supplier_name="Microsoft")
		doc = create_bank_transaction(
			description="Auftraggeber: microsoft payments Buchungstext: msft ..e3006b5hdy. ref. j375979555927627/5536",
			withdrawal=1200,
			transaction_id="8df880a2d09c3bed3fea358ca5168c5a",
			party_name="",
		)
		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "Microsoft")
		self.assertFalse(doc.bank_party_mapper)

	def test_correct_match_after_submit(self):
		"""Correct wrong mapping after submit. Test impact."""
		# Similar named suppliers
		create_supplier_for_match(supplier_name="Amazon")
		create_supplier_for_match(supplier_name="Amazing Co.")

		# Bank Transactions actually from "Amazon" that match better with "Amazing Co."
		doc = create_bank_transaction(
			description="visa06323202 amzn.com/bill 7,88eur1,5324711959 90.22. 1,62 87861003",
			withdrawal=24.85,
			transaction_id="3a1da4ee2dc5a980138d36ef5297cbd9",
			party_name="Amazn Co.",
		)
		doc_2 = create_bank_transaction(
			description="visa61268005 amzn.com/bill 22,345eur1,7654711959 89.23. 1,64 61268005",
			withdrawal=80,
			transaction_id="584314e459b00f792bfd569267efba6e",
			party_name="Amazn Co.",
		)

		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "Amazing Co.")
		self.assertTrue(doc.bank_party_mapper)
		self.assertTrue(doc_2.bank_party_mapper, doc.bank_party_mapper)

		bank_party_mapper = frappe.get_doc("Bank Party Mapper", doc.bank_party_mapper)
		self.assertEqual(bank_party_mapper.party, "Amazing Co.")
		self.assertEqual(bank_party_mapper.bank_party_name, "Amazn Co.")

		# User corrects the value after submit to "Amazon"
		doc.party = "Amazon"
		doc.save()
		bank_party_mapper.reload()
		doc_2.reload()

		# Mapping is edited and all transactions with this mapping are updated
		self.assertEqual(bank_party_mapper.party, "Amazon")
		self.assertEqual(bank_party_mapper.bank_party_name, "Amazn Co.")
		self.assertEqual(doc_2.party, "Amazon")

	def test_skip_match_if_multiple_close_results(self):
		create_supplier_for_match(supplier_name="Adithya Medical & General Stores")
		create_supplier_for_match(supplier_name="Adithya Medical And General Stores")

		doc = create_bank_transaction(
			description="Paracetamol Consignment, SINV-0009",
			withdrawal=24.85,
			transaction_id="3a1da4ee2dc5a980138d56ef3460cbd9",
			party_name="Adithya Medical & General",
		)

		# Mapping is skipped as both Supplier names have the same match score
		self.assertEqual(doc.party_type, None)
		self.assertEqual(doc.party, None)
		self.assertFalse(doc.bank_party_mapper)


def create_supplier_for_match(supplier_name="John Doe & Co.", iban=None, account_no=None):
	if frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
		# Update related Bank Account details
		if not (iban or account_no):
			return

		frappe.db.set_value(
			dt="Bank Account",
			dn={"party": supplier_name},
			field={"iban": iban, "bank_account_no": account_no},
		)
		return

	# Create Supplier and Bank Account for the same
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"supplier_group": "Services",
			"supplier_type": "Company",
		}
	).insert()

	if not frappe.db.exists("Bank", "TestBank"):
		frappe.get_doc(
			{
				"doctype": "Bank",
				"bank_name": "TestBank",
			}
		).insert(ignore_if_duplicate=True)

	if not frappe.db.exists("Bank Account", supplier.name + " - " + "TestBank"):
		frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": supplier.name,
				"bank": "TestBank",
				"iban": iban,
				"bank_account_no": account_no,
				"party_type": "Supplier",
				"party": supplier.name,
			}
		).insert()


def create_bank_transaction(
	description=None,
	withdrawal=0,
	deposit=0,
	transaction_id=None,
	party_name=None,
	account_no=None,
	iban=None,
):
	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"description": description or "1512567 BG/000002918 OPSKATTUZWXXX AT776000000098709837 Herr G",
			"date": nowdate(),
			"withdrawal": withdrawal,
			"deposit": deposit,
			"currency": "INR",
			"bank_account": "Checking Account - Citi Bank",
			"transaction_id": transaction_id,
			"bank_party_name": party_name,
			"bank_party_account_number": account_no,
			"bank_party_iban": iban,
		}
	).insert()
	doc.submit()
	doc.reload()

	return doc
