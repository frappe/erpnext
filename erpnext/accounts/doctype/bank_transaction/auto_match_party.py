from typing import Tuple, Union

import frappe
from frappe.utils import flt
from rapidfuzz import fuzz, process


class AutoMatchParty:
	"""
	Matches by Account/IBAN and then by Party Name/Description sequentially.
	Returns when a result is obtained.

<<<<<<< HEAD
	Result (if present) is of the form: (Party Type, Party,)
=======
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
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)
	"""

	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self) -> Union[Tuple, None]:
<<<<<<< HEAD
		result = None
=======
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)
		result = AutoMatchbyAccountIBAN(
			bank_party_account_number=self.bank_party_account_number,
			bank_party_iban=self.bank_party_iban,
			deposit=self.deposit,
		).match()

		fuzzy_matching_enabled = frappe.db.get_single_value("Accounts Settings", "enable_fuzzy_matching")
		if not result and fuzzy_matching_enabled:
<<<<<<< HEAD
			result = AutoMatchbyPartyNameDescription(
=======
			result = AutoMatchbyPartyDescription(
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)
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

		result = self.match_account_in_party()
		return result

<<<<<<< HEAD
=======
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

>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)
	def match_account_in_party(self) -> Union[Tuple, None]:
		"""Check if there is a IBAN/Account No. match in Customer/Supplier/Employee"""
		result = None
		parties = get_parties_in_order(self.deposit)
		or_filters = self.get_or_filters()

		for party in parties:
<<<<<<< HEAD
<<<<<<< HEAD
			party_result = frappe.db.get_all(
				"Bank Account", or_filters=or_filters, pluck="party", limit_page_length=1
=======
			or_filters = {}
			if self.bank_party_account_number:
				or_filters["bank_account_no"] = self.bank_party_account_number
=======
			or_filters = {}
			if self.bank_party_account_number:
				acc_no_field = "bank_ac_no" if party == "Employee" else "bank_account_no"
				or_filters[acc_no_field] = self.bank_party_account_number
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)

			if self.bank_party_iban:
				or_filters["iban"] = self.bank_party_iban

			party_result = frappe.db.get_all(
<<<<<<< HEAD
<<<<<<< HEAD
				"Bank Account", or_filters=or_filters, pluck="name", limit_page_length=1
>>>>>>> dbf7a479b6 (fix: Use existing bank fields to match by bank account no/IBAN)
=======
				"Bank Account", or_filters=or_filters, pluck="party", limit_page_length=1
>>>>>>> 4a14e9ea4e (fix: Tests)
			)

			if party == "Employee" and not party_result:
				# Search in Bank Accounts first for Employee, and then Employee record
				if "bank_account_no" in or_filters:
					or_filters["bank_ac_no"] = or_filters.pop("bank_account_no")

				party_result = frappe.db.get_all(
					party, or_filters=or_filters, pluck="name", limit_page_length=1
				)

=======
				party, or_filters=or_filters, pluck="name", limit_page_length=1
			)
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)
			if party_result:
				result = (
					party,
					party_result[0],
<<<<<<< HEAD
=======
					{
						"bank_party_account_number": self.get("bank_party_account_number"),
						"bank_party_iban": self.get("bank_party_iban"),
					},
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)
				)
				break

		return result

	def get_or_filters(self) -> dict:
		or_filters = {}
		if self.bank_party_account_number:
			or_filters["bank_account_no"] = self.bank_party_account_number

		if self.bank_party_iban:
			or_filters["iban"] = self.bank_party_iban

		return or_filters


class AutoMatchbyPartyNameDescription:
	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self) -> Union[Tuple, None]:
<<<<<<< HEAD
=======
		# Match  by Customer, Supplier or Employee Name
		# search bank party mapper by party
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)
		# fuzzy search by customer/supplier & employee
		if not (self.bank_party_name or self.description):
			return None

		result = self.match_party_name_desc_in_party()
		return result

<<<<<<< HEAD
	def match_party_name_desc_in_party(self) -> Union[Tuple, None]:
		"""Fuzzy search party name and/or description against parties in the system"""
		result = None
		parties = get_parties_in_order(self.deposit)
=======
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
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)

		for party in parties:
			filters = {"status": "Active"} if party == "Employee" else {"disabled": 0}
<<<<<<< HEAD
			names = frappe.get_all(party, filters=filters, pluck=party.lower() + "_name")
=======
			names = frappe.get_all(party, filters=filters, pluck=name_field)
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)

			for field in ["bank_party_name", "description"]:
				if not self.get(field):
					continue

				result, skip = self.fuzzy_search_and_return_result(party, names, field)
				if result or skip:
					break

			if result or skip:
<<<<<<< HEAD
				# Skip If: It was hard to distinguish between close matches and so match is None
=======
				# We skip if:
				# If it was hard to distinguish between close matches and so match is None
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)
				# OR if the right match was found
				break

		return result

	def fuzzy_search_and_return_result(self, party, names, field) -> Union[Tuple, None]:
<<<<<<< HEAD
		skip = False
<<<<<<< HEAD
		result = process.extract(query=self.get(field), choices=names, scorer=fuzz.token_set_ratio)
		party_name, skip = self.process_fuzzy_result(result)
=======
		result = process.extractOne(query=self.get(field), choices=names, scorer=fuzz.token_set_ratio)
>>>>>>> d7bc192804 (fix: Match by both Account No and IBAN & other cleanups)

		if not party_name:
			return None, skip

		return (
			party,
			party_name,
=======

		result = process.extract(query=self.get(field), choices=names, scorer=fuzz.token_set_ratio)
		party_name, skip = self.process_fuzzy_result(result)

		if not party_name:
			return None, skip

		# Dont set description as a key in Bank Party Mapper due to its volatility
		mapper = {"bank_party_name": self.get(field)} if field == "bank_party_name" else None
		return (
			party,
			party_name,
			mapper,
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)
		), skip

	def process_fuzzy_result(self, result: Union[list, None]):
		"""
		If there are multiple valid close matches return None as result may be faulty.
		Return the result only if one accurate match stands out.

<<<<<<< HEAD
		Returns: Result, Skip (whether or not to discontinue matching)
=======
		Returns: Result, Skip (whether or not to continue matching)
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)
		"""
		PARTY, SCORE, CUTOFF = 0, 1, 80

		if not result or not len(result):
			return None, False

		first_result = result[0]
<<<<<<< HEAD
		if len(result) == 1:
			return (first_result[PARTY] if first_result[SCORE] > CUTOFF else None), True

		second_result = result[1]
		if first_result[SCORE] > CUTOFF:
			# If multiple matches with the same score, return None but discontinue matching
			# Matches were found but were too close to distinguish between
=======

		if len(result) == 1:
			return (result[0][PARTY] if first_result[SCORE] > CUTOFF else None), True

		second_result = result[1]

		if first_result[SCORE] > CUTOFF:
			# If multiple matches with the same score, return None but discontinue matching
			# Matches were found but were too closes to distinguish between
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)
			if first_result[SCORE] == second_result[SCORE]:
				return None, True

			return first_result[PARTY], True
		else:
			return None, False
<<<<<<< HEAD


def get_parties_in_order(deposit: float) -> list:
	parties = ["Supplier", "Employee", "Customer"]  # most -> least likely to receive
	if flt(deposit) > 0:
		parties = ["Customer", "Supplier", "Employee"]  # most -> least likely to pay

	return parties
=======
>>>>>>> 4364fb9628 (feat: Optional Fuzzy Matching & Skip Matches for multiple similar matches)
