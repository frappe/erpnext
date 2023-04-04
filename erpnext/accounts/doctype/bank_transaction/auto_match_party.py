import frappe
from frappe.utils import flt
from rapidfuzz import fuzz, process


class AutoMatchParty:
	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self):
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

	def match_account_in_bank_party_mapper(self):
		filter_field = (
			"bank_party_account_number" if self.bank_party_account_number else "bank_party_iban"
		)
		result = frappe.db.get_value(
			"Bank Party Mapper",
			filters={filter_field: self.get(filter_field)},
			fieldname=["party_type", "party", "name"],
		)
		if result:
			party_type, party, mapper_name = result
			return (party_type, party, {"mapper_name": mapper_name})

		return result

	def match_account_in_party(self):
		# If not check if there is a match in Customer/Supplier/Employee
		filter_field = "bank_account_no" if self.bank_party_account_number else "iban"
		transaction_field = (
			"bank_party_account_number" if self.bank_party_account_number else "bank_party_iban"
		)
		result = None

		parties = ["Supplier", "Employee", "Customer"]  # most -> least likely to receive
		if flt(self.deposit) > 0:
			parties = ["Customer", "Supplier", "Employee"]  # most -> least likely to pay

		for party in parties:
			party_name = frappe.db.get_value(
				party, filters={filter_field: self.get(transaction_field)}, fieldname=["name"]
			)
			if party_name:
				result = (party, party_name, {transaction_field: self.get(transaction_field)})
				break

		return result


class AutoMatchbyPartyDescription:
	def __init__(self, **kwargs) -> None:
		self.__dict__.update(kwargs)

	def get(self, key):
		return self.__dict__.get(key, None)

	def match(self):
		# Match  by Customer, Supplier or Employee Name
		# search bank party mapper by party
		# fuzzy search by customer/supplier & employee
		if not (self.bank_party_name or self.description):
			return None

		result = self.match_party_name_in_bank_party_mapper()

		if not result:
			result = self.match_party_name_desc_in_party()

		return result

	def match_party_name_in_bank_party_mapper(self):
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
			result = (
				mapper_res["party_type"],
				mapper_res["party"],
				{"mapper_name": mapper_res["name"]},
			)

		return result

	def match_party_name_desc_in_party(self):
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

	def fuzzy_search_and_return_result(self, party, names, field):
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
