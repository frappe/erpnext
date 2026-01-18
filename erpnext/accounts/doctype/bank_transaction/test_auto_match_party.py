# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import create_bank_account

IBAN_1 = "DE02000000003716541159"
IBAN_2 = "DE02500105170137075030"


class TestAutoMatchParty(IntegrationTestCase):
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
		create_supplier_for_match(account_no=IBAN_1[11:])
		doc = create_bank_transaction(
			withdrawal=1200,
			transaction_id="562213b0ca1bf838dab8f2c6a39bbc3b",
			account_no=IBAN_1[11:],
			iban=IBAN_1,
		)

		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "John Doe & Co.")

	def test_match_by_iban(self):
		create_supplier_for_match(iban=IBAN_1)
		doc = create_bank_transaction(
			withdrawal=1200,
			transaction_id="c5455a224602afaa51592a9d9250600d",
			account_no=IBAN_1[11:],
			iban=IBAN_1,
		)

		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "John Doe & Co.")

	def test_match_by_party_name(self):
		create_supplier_for_match(supplier_name="Jackson Ella W.")
		doc = create_bank_transaction(
			withdrawal=1200,
			transaction_id="1f6f661f347ff7b1ea588665f473adb1",
			party_name="Ella Jackson",
			iban=IBAN_2,
		)
		self.assertEqual(doc.party_type, "Supplier")
		self.assertEqual(doc.party, "Jackson Ella W.")

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
	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = supplier_name
	supplier.supplier_group = "Services"
	supplier.supplier_type = "Company"
	supplier.insert()

	if not frappe.db.exists("Bank", "TestBank"):
		bank = frappe.new_doc("Bank")
		bank.bank_name = "TestBank"
		bank.insert(ignore_if_duplicate=True)

	if not frappe.db.exists("Bank Account", supplier.name + " - " + "TestBank"):
		bank_account = frappe.new_doc("Bank Account")
		bank_account.account_name = supplier.name
		bank_account.bank = "TestBank"
		bank_account.iban = iban
		bank_account.bank_account_no = account_no
		bank_account.party_type = "Supplier"
		bank_account.party = supplier.name
		bank_account.insert()


def create_bank_transaction(
	description=None,
	withdrawal=0,
	deposit=0,
	transaction_id=None,
	party_name=None,
	account_no=None,
	iban=None,
):
	doc = frappe.new_doc("Bank Transaction")
	doc.update(
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
	)
	doc.insert()
	doc.submit()
	doc.reload()

	return doc
