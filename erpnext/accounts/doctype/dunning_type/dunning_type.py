# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import comma_and
from frappe.utils.jinja import validate_template


class DunningType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.dunning_letter_text.dunning_letter_text import DunningLetterText

		company: DF.Link
		cost_center: DF.Link | None
		dunning_fee: DF.Currency
		dunning_letter_text: DF.Table[DunningLetterText]
		dunning_type: DF.Data
		income_account: DF.Link | None
		is_default: DF.Check
		rate_of_interest: DF.Float
	# end: auto-generated types

	def autoname(self):
		company_abbr = frappe.get_value("Company", self.company, "abbr")
		self.name = f"{self.dunning_type} - {company_abbr}"

	def validate(self):
		self.validate_dunning_letter_text()
		self.validate_income_account()
		self.validate_cost_center()
		self.set_default_dunning_type()

	def validate_dunning_letter_text(self):
		self.validate_languages()
		self.validate_is_default_language()
		self.validate_dunning_letter_text_templates()

	def validate_income_account(self):
		if not self.income_account:
			return

		account = frappe.get_cached_doc("Account", self.income_account)

		msg = []
		if account.company != self.company:
			msg.append(
				_(
					"{0} doesn't belong to Company {1}. Please select an Income Account that belongs to Company {1}."
				).format(frappe.bold(self.income_account), frappe.bold(self.company))
			)

		if account.disabled:
			msg.append(
				_("{0} is disabled. Please select a valid Income Account.").format(
					frappe.bold(self.income_account)
				)
			)

		if account.root_type != "Income":
			msg.append(
				_("{0} is not an Income Account. Please select a valid Income Account.").format(
					frappe.bold(self.income_account)
				)
			)

		if account.is_group:
			msg.append(
				_("{0} is a group account. Please select a non-group Income Account.").format(
					frappe.bold(self.income_account)
				)
			)

		if msg:
			frappe.msgprint(
				msg,
				title=_("Income Account Validation Error"),
				as_list=True,
				raise_exception=frappe.ValidationError,
			)

	def validate_cost_center(self):
		if not self.cost_center:
			return

		cost_center = frappe.get_cached_doc("Cost Center", self.cost_center)

		msg = []
		if cost_center.company != self.company:
			msg.append(
				_(
					"{0} doesn't belong to Company {1}. Please select a Cost Center that belongs to Company {1}."
				).format(frappe.bold(self.cost_center), frappe.bold(self.company))
			)

		if cost_center.disabled:
			msg.append(
				_("{0} is disabled. Please select an enabled Cost Center.").format(
					frappe.bold(self.cost_center)
				)
			)

		if cost_center.is_group:
			msg.append(
				_("{0} is a group Cost Center. Please select a non-group Cost Center.").format(
					frappe.bold(self.cost_center)
				)
			)

		if msg:
			frappe.msgprint(
				msg,
				title=_("Cost Center Validation Error"),
				as_list=True,
				raise_exception=frappe.ValidationError,
			)

	def validate_languages(self):
		languages = [d.language for d in self.dunning_letter_text]

		if len(languages) == len(set(languages)):
			return

		frappe.throw(_("Duplicate languages found on Dunning Letter Text. Keep only one of them."))

	def validate_is_default_language(self):
		is_default_language_list = [
			d.language for d in self.dunning_letter_text if d.is_default_language == 1
		]

		if len(is_default_language_list) <= 1:
			return

		frappe.throw(
			_("{0} languages are marked as default languages. Please select only one of them.").format(
				comma_and(is_default_language_list, add_quotes=True)
			)
		)

	def validate_dunning_letter_text_templates(self):
		for d in self.dunning_letter_text:
			if d.body_text:
				validate_template(d.body_text, restrict_globals=True)

			if d.closing_text:
				validate_template(d.closing_text, restrict_globals=True)

	def set_default_dunning_type(self):
		if self.is_default != 1:
			return

		frappe.db.set_value(
			"Dunning Type",
			{"company": self.company, "is_default": 1, "name": ["!=", self.name]},
			"is_default",
			0,
		)
