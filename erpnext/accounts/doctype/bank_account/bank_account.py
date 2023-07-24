# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.document import Document


class BankAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		account_name: DF.Data
		account_subtype: DF.Link | None
		account_type: DF.Link | None
		bank: DF.Link
		bank_account_no: DF.Data | None
		branch_code: DF.Data | None
		company: DF.Link | None
		iban: DF.Data | None
		integration_id: DF.Data | None
		is_company_account: DF.Check
		is_default: DF.Check
		last_integration_date: DF.Date | None
		mask: DF.Data | None
		party: DF.DynamicLink | None
		party_type: DF.Link | None
	# end: auto-generated types
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)

	def autoname(self):
		self.name = self.account_name + " - " + self.bank

	def on_trash(self):
		delete_contact_and_address("BankAccount", self.name)

	def validate(self):
		self.validate_company()
		self.validate_iban()

	def validate_company(self):
		if self.is_company_account and not self.company:
			frappe.throw(_("Company is manadatory for company account"))

	def validate_iban(self):
		"""
		Algorithm: https://en.wikipedia.org/wiki/International_Bank_Account_Number#Validating_the_IBAN
		"""
		# IBAN field is optional
		if not self.iban:
			return

		def encode_char(c):
			# Position in the alphabet (A=1, B=2, ...) plus nine
			return str(9 + ord(c) - 64)

		# remove whitespaces, upper case to get the right number from ord()
		iban = "".join(self.iban.split(" ")).upper()

		# Move country code and checksum from the start to the end
		flipped = iban[4:] + iban[:4]

		# Encode characters as numbers
		encoded = [encode_char(c) if ord(c) >= 65 and ord(c) <= 90 else c for c in flipped]

		try:
			to_check = int("".join(encoded))
		except ValueError:
			frappe.throw(_("IBAN is not valid"))

		if to_check % 97 != 1:
			frappe.throw(_("IBAN is not valid"))


@frappe.whitelist()
def make_bank_account(doctype, docname):
	doc = frappe.new_doc("Bank Account")
	doc.party_type = doctype
	doc.party = docname
	doc.is_default = 1

	return doc


def get_party_bank_account(party_type, party):
	return frappe.db.get_value(party_type, party, "default_bank_account")


@frappe.whitelist()
def get_bank_account_details(bank_account):
	return frappe.get_cached_value(
		"Bank Account", bank_account, ["account", "bank", "bank_account_no"], as_dict=1
	)
