from typing import Tuple, Union

import frappe
from frappe.utils import flt
from rapidfuzz import fuzz, process


class AutoMatchParty:
	"""
	Matches by Account/IBAN and then by Party Name/Description sequentially.
	Returns when a result is obtained.

	Result (if present) is of the form: (Party Type, Party,)
	"""

	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self) -> Union[Tuple, None]:
		result = None
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

	def match_account_in_party(self) -> Union[Tuple, None]:
		"""Check if there is a IBAN/Account No. match in Customer/Supplier/Employee"""
		result = None
		parties = get_parties_in_order(self.deposit)
		or_filters = self.get_or_filters()

		for party in parties:
<<<<<<< HEAD
			party_result = frappe.db.get_all(
				"Bank Account", or_filters=or_filters, pluck="party", limit_page_length=1
=======
			or_filters = {}
			if self.bank_party_account_number:
				or_filters["bank_account_no"] = self.bank_party_account_number

			if self.bank_party_iban:
				or_filters["iban"] = self.bank_party_iban

			party_result = frappe.db.get_all(
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

			if party_result:
				result = (
					party,
					party_result[0],
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
		# fuzzy search by customer/supplier & employee
		if not (self.bank_party_name or self.description):
			return None

		result = self.match_party_name_desc_in_party()
		return result

	def match_party_name_desc_in_party(self) -> Union[Tuple, None]:
		"""Fuzzy search party name and/or description against parties in the system"""
		result = None
		parties = get_parties_in_order(self.deposit)

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
		skip = False
<<<<<<< HEAD
		result = process.extract(query=self.get(field), choices=names, scorer=fuzz.token_set_ratio)
		party_name, skip = self.process_fuzzy_result(result)

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
