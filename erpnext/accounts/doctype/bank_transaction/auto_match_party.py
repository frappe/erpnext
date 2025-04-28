import frappe
from frappe.utils import flt
from rapidfuzz import fuzz, process
<<<<<<< HEAD
from rapidfuzz.utils import default_process
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)


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

	def match(self) -> tuple | None:
		result = None
		result = AutoMatchbyAccountIBAN(
			bank_party_account_number=self.bank_party_account_number,
			bank_party_iban=self.bank_party_iban,
			deposit=self.deposit,
		).match()

<<<<<<< HEAD
		fuzzy_matching_enabled = frappe.get_single_value("Accounts Settings", "enable_fuzzy_matching")
=======
		fuzzy_matching_enabled = frappe.db.get_single_value("Accounts Settings", "enable_fuzzy_matching")
>>>>>>> 7c4cf3e834 (Favicon.svg)
		if not result and fuzzy_matching_enabled:
			result = AutoMatchbyPartyNameDescription(
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

<<<<<<< HEAD
		return self.match_account_in_party()

	def match_account_in_party(self) -> tuple | None:
		"""
		Returns (Party Type, Party) if a matching account is found in Bank Account or Employee:
		1. Get party from a matching (iban/account no) Bank Account
		2. If not found, get party from Employee with matching bank account details (iban/account no)
		"""
		if not (self.bank_party_account_number or self.bank_party_iban):
			# Nothing to match
			return None

		# Search for a matching Bank Account that has party set
		party_result = frappe.db.get_all(
			"Bank Account",
			or_filters=self.get_or_filters(),
			filters={"party_type": ("is", "set"), "party": ("is", "set")},
			fields=["party", "party_type"],
			limit_page_length=1,
		)
		if result := party_result[0] if party_result else None:
			return (result["party_type"], result["party"])

		# If no party is found, search in Employee (since it has bank account details)
		if employee_result := frappe.db.get_all(
			"Employee", or_filters=self.get_or_filters("Employee"), pluck="name", limit_page_length=1
		):
			return ("Employee", employee_result[0])

	def get_or_filters(self, party: str | None = None) -> dict:
		"""Return OR filters for Bank Account and IBAN"""
		or_filters = {}
		if self.bank_party_account_number:
			bank_ac_field = "bank_ac_no" if party == "Employee" else "bank_account_no"
			or_filters[bank_ac_field] = self.bank_party_account_number
=======
		result = self.match_account_in_party()
		return result

	def match_account_in_party(self) -> tuple | None:
		"""Check if there is a IBAN/Account No. match in Customer/Supplier/Employee"""
		result = None
		parties = get_parties_in_order(self.deposit)
		or_filters = self.get_or_filters()

		for party in parties:
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

				if "bank_ac_no" in or_filters:
					or_filters["bank_account_no"] = or_filters.pop("bank_ac_no")

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
>>>>>>> 7c4cf3e834 (Favicon.svg)

		if self.bank_party_iban:
			or_filters["iban"] = self.bank_party_iban

		return or_filters


class AutoMatchbyPartyNameDescription:
	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self) -> tuple | None:
		# fuzzy search by customer/supplier & employee
		if not (self.bank_party_name or self.description):
			return None

<<<<<<< HEAD
		return self.match_party_name_desc_in_party()
=======
		result = self.match_party_name_desc_in_party()
		return result
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def match_party_name_desc_in_party(self) -> tuple | None:
		"""Fuzzy search party name and/or description against parties in the system"""
		result = None
		parties = get_parties_in_order(self.deposit)

		for party in parties:
			filters = {"status": "Active"} if party == "Employee" else {"disabled": 0}
<<<<<<< HEAD
			field = f"{party.lower()}_name"
=======
			field = party.lower() + "_name"
>>>>>>> 7c4cf3e834 (Favicon.svg)
			names = frappe.get_all(party, filters=filters, fields=[f"{field} as party_name", "name"])

			for field in ["bank_party_name", "description"]:
				if not self.get(field):
					continue

				result, skip = self.fuzzy_search_and_return_result(party, names, field)
				if result or skip:
					break

			if result or skip:
				# Skip If: It was hard to distinguish between close matches and so match is None
				# OR if the right match was found
				break

		return result

	def fuzzy_search_and_return_result(self, party, names, field) -> tuple | None:
		skip = False
		result = process.extract(
			query=self.get(field),
			choices={row.get("name"): row.get("party_name") for row in names},
			scorer=fuzz.token_set_ratio,
<<<<<<< HEAD
			processor=default_process,
		)
		party_name, skip = self.process_fuzzy_result(result)

		return ((party, party_name), skip) if party_name else (None, skip)
=======
		)
		party_name, skip = self.process_fuzzy_result(result)

		if not party_name:
			return None, skip

		return (
			party,
			party_name,
		), skip
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def process_fuzzy_result(self, result: list | None):
		"""
		If there are multiple valid close matches return None as result may be faulty.
		Return the result only if one accurate match stands out.

		Returns: Result, Skip (whether or not to discontinue matching)
		"""
		SCORE, PARTY_ID, CUTOFF = 1, 2, 80

		if not result or not len(result):
			return None, False

		first_result = result[0]
		if len(result) == 1:
			return (first_result[PARTY_ID] if first_result[SCORE] > CUTOFF else None), True

<<<<<<< HEAD
		if first_result[SCORE] > CUTOFF:
			second_result = result[1]
=======
		second_result = result[1]
		if first_result[SCORE] > CUTOFF:
>>>>>>> 7c4cf3e834 (Favicon.svg)
			# If multiple matches with the same score, return None but discontinue matching
			# Matches were found but were too close to distinguish between
			if first_result[SCORE] == second_result[SCORE]:
				return None, True

			return first_result[PARTY_ID], True
		else:
			return None, False


def get_parties_in_order(deposit: float) -> list:
<<<<<<< HEAD
	return (
		["Customer", "Supplier", "Employee"]  # most -> least likely to pay us
		if flt(deposit) > 0
		else ["Supplier", "Employee", "Customer"]  # most -> least likely to receive from us
	)
=======
	parties = ["Supplier", "Employee", "Customer"]  # most -> least likely to receive
	if flt(deposit) > 0:
		parties = ["Customer", "Supplier", "Employee"]  # most -> least likely to pay

	return parties
>>>>>>> 7c4cf3e834 (Favicon.svg)
