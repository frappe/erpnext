from typing import Tuple, Union

import frappe
from frappe.utils import flt
from rapidfuzz import fuzz, process


class AutoMatchParty:
	"""
	Matches by Account/IBAN and then by Party Name/Description sequentially.
	Returns when a result is obtained.

	Result (if present) is of the form: (Party Type, Party, Mapper,)

	Mapper(if present) is one of the forms:
	        1. {"mapper_name": <docname>}: Indicates that an existing Bank Party Mapper matched against
	                the transaction and the same must be linked in the Bank Transaction.

	        2. {"bank_party_account_number": <ACC No.>, "bank_party_iban": <IBAN>} : Indicates that a match was
	                found in Customer/Supplier/Employee by account details. A Bank Party Mapper is now created
	                mapping the Party to the Account No./IBAN

	        3. {"bank_party_name": <Counter Party Name>}: Indicates that a match was found in
	                Customer/Supplier/Employee by party name. A Bank Party Mapper is now created mapping the Party
	                to the Party Name (Bank Statement). If matched by Description, no mapper is created as
	                description is not a static key.

	Mapper data is used either to create a new Bank Party Mapper or link an existing mapper to a transaction.
	"""

	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self) -> Union[Tuple, None]:
		result = AutoMatchbyAccountIBAN(
			bank_party_account_number=self.bank_party_account_number,
			bank_party_iban=self.bank_party_iban,
			deposit=self.deposit,
		).match()

		if not result:
			result = AutoMatchbyPartyDescription(
				bank_party_name=self.bank_party_name, description=self.description, deposit=self.deposit
			).match()

		return result


class AutoMatchbyAccountIBAN:
	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self):
		if not (self.bank_party_account_number or self.bank_party_iban):
			return None

		result = self.match_account_in_bank_party_mapper()
		if not result:
			result = self.match_account_in_party()

		return result

	def match_account_in_bank_party_mapper(self) -> Union[Tuple, None]:
		"""Check for a IBAN/Account No. match in Bank Party Mapper"""
		result = None
		or_filters = {}
		if self.bank_party_account_number:
			or_filters["bank_party_account_number"] = self.bank_party_account_number

		if self.bank_party_iban:
			or_filters["bank_party_iban"] = self.bank_party_iban

		mapper = frappe.db.get_all(
			"Bank Party Mapper",
			or_filters=or_filters,
			fields=["party_type", "party", "name"],
			limit_page_length=1,
		)
		if mapper:
			data = mapper[0]
			return (data["party_type"], data["party"], {"mapper_name": data["name"]})

		return result

	def match_account_in_party(self) -> Union[Tuple, None]:
		"""Check if there is a IBAN/Account No. match in Customer/Supplier/Employee"""
		result = None

		parties = ["Supplier", "Employee", "Customer"]  # most -> least likely to receive
		if flt(self.deposit) > 0:
			parties = ["Customer", "Supplier", "Employee"]  # most -> least likely to pay

		for party in parties:
			or_filters = {}
			if self.bank_party_account_number:
				or_filters["bank_account_no"] = self.bank_party_account_number

			if self.bank_party_iban:
				or_filters["iban"] = self.bank_party_iban

			party_result = frappe.db.get_all(
				"Bank Account", or_filters=or_filters, pluck="party", limit_page_length=1
			)

			if party == "Employee" and not party_result:
				# Search in Bank Accounts first for Employee, and then Employee record
				if "bank_account_no" in or_filters:
					or_filters["bank_ac_no"] = or_filters.pop("bank_account_no")

				party_result = frappe.db.get_all(
					party, or_filters=or_filters, pluck="name", limit_page_length=1
				)

			if party_result:
				result = (
					party,
					party_result[0],
					{
						"bank_party_account_number": self.get("bank_party_account_number"),
						"bank_party_iban": self.get("bank_party_iban"),
					},
				)
				break

		return result


class AutoMatchbyPartyDescription:
	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self) -> Union[Tuple, None]:
		# Match  by Customer, Supplier or Employee Name
		# search bank party mapper by party
		# fuzzy search by customer/supplier & employee
		if not (self.bank_party_name or self.description):
			return None

		result = self.match_party_name_in_bank_party_mapper()

		if not result:
			result = self.match_party_name_desc_in_party()

		return result

	def match_party_name_in_bank_party_mapper(self) -> Union[Tuple, None]:
		"""Check if match exists for party name in Bank Party Mapper"""
		result = None
		if not self.bank_party_name:
			return

		mapper_res = frappe.get_all(
			"Bank Party Mapper",
			filters={"bank_party_name": self.bank_party_name},
			fields=["party_type", "party", "name"],
			limit_page_length=1,
		)
		if mapper_res:
			mapper_res = mapper_res[0]
			return (
				mapper_res["party_type"],
				mapper_res["party"],
				{"mapper_name": mapper_res["name"]},
			)

		return result

	def match_party_name_desc_in_party(self) -> Union[Tuple, None]:
		"""Fuzzy search party name and/or description against parties in the system"""
		result = None
		parties = ["Supplier", "Employee", "Customer"]  # most-least likely to receive
		if flt(self.deposit) > 0.0:
			parties = ["Customer", "Supplier", "Employee"]  # most-least likely to pay

		for party in parties:
			name_field = party.lower() + "_name"
			filters = {"status": "Active"} if party == "Employee" else {"disabled": 0}

			names = frappe.get_all(party, filters=filters, pluck=name_field)

			for field in ["bank_party_name", "description"]:
				if not result and self.get(field):
					result = self.fuzzy_search_and_return_result(party, names, field)
					if result:
						break

		return result

	def fuzzy_search_and_return_result(self, party, names, field) -> Union[Tuple, None]:
		result = process.extractOne(query=self.get(field), choices=names, scorer=fuzz.token_set_ratio)

		if result:
			party_name, score, index = result
			if score > 75:
				# Dont set description as a key in Bank Party Mapper due to its volatility
				mapper = {"bank_party_name": self.get(field)} if field == "bank_party_name" else None
				return (
					party,
					party_name,
					mapper,
				)
			else:
				return None

		return result
