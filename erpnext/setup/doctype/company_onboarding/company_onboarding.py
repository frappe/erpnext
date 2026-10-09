# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from erpnext.setup.doctype.company_onboarding.company_onboarding_steps import get_step_paths

# Company fields the Edit dialog fills; the setup wizard does not ask for them
COMPANY_FIELDS = (
	"company_logo",
	"tax_id",
	"phone_no",
	"email",
	"website",
	"date_of_incorporation",
	"registration_details",
)
ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "state", "pincode", "country")


class CompanyOnboarding(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.company_onboarding_opening_balance.company_onboarding_opening_balance import (
			CompanyOnboardingOpeningBalance,
		)
		from erpnext.setup.doctype.company_onboarding_step.company_onboarding_step import (
			CompanyOnboardingStep,
		)

		chart_of_accounts_source: DF.Literal["", "Existing", "Imported"]
		company: DF.Link
		opening_balances: DF.Table[CompanyOnboardingOpeningBalance]
		status: DF.Literal["In Progress", "Live"]
		steps: DF.Table[CompanyOnboardingStep]
	# end: auto-generated types

	_DOCTYPE_NAME = "Company Onboarding"

	def onload(self):
		self.set_onload("company_details", get_company_details(self.company))
		self.set_onload(
			"steps",
			{
				key: {"title": step["title"], "description": step["description"]}
				for key, step in get_steps(self).items()
			},
		)

	def validate(self):
		self.update_steps()

	def update_steps(self):
		"""Put the registered steps in order and set each one's status from the data."""
		rows = {row.step_key: row for row in self.steps}
		self.steps = []
		for key, step in get_steps(self).items():
			row = rows.get(key)
			if row is None:
				row = frappe._dict(step_key=key)
			if step["done"]:
				status = "Done"
			elif row.status == "Skipped":
				status = "Skipped"
			else:
				status = "Not Started"

			if row.status != status:
				row.last_checked = now_datetime()
			row.status = status
			row.step = step["title"]
			self.append("steps", row)

		for idx, row in enumerate(self.steps, 1):
			row.idx = idx

	@frappe.whitelist()
	def check_steps(self) -> bool:
		"""Save when a step's status changed. The form calls this each time it opens."""
		before = [(row.step_key, row.status) for row in self.steps]
		self.update_steps()
		changed = before != [(row.step_key, row.status) for row in self.steps]
		if changed and self.has_permission("write"):
			self.save()
		return changed

	@frappe.whitelist()
	def skip_step(self, step_key: str, skip: int = 1):
		"""Skip a step, or bring a skipped step back. A step that is done stays done."""
		row = next((row for row in self.steps if row.step_key == step_key), None)
		if not row:
			frappe.throw(_("Step {0} not found").format(step_key))
		row.status = "Skipped" if cint(skip) else "Not Started"
		self.save()

	@frappe.whitelist()
	def use_existing_chart(self):
		"""Keep the chart of accounts made during setup."""
		self.chart_of_accounts_source = "Existing"
		self.save()

	@frappe.whitelist()
	def change_chart_choice(self):
		"""Undo the chart choice, so the step asks again."""
		self.chart_of_accounts_source = ""
		self.save()

	@frappe.whitelist()
	def update_company_details(self, values: dict | str):
		"""Save the company details and address from the Edit dialog."""
		values = frappe.parse_json(values)
		company = frappe.get_doc("Company", self.company)
		company.update({field: values.get(field) for field in COMPANY_FIELDS})
		company.save()
		save_company_address(self.company, values)


def get_steps(onboarding) -> dict[str, dict]:
	"""Every step in order, keyed by its path, with title, description and done."""
	return {path: frappe.get_attr(path)(onboarding) for path in get_step_paths()}


def get_company_details(company: str) -> dict:
	"""What the Company card shows."""
	details = frappe.db.get_value(
		"Company",
		company,
		["company_name", "abbr", "country", "default_currency", *COMPANY_FIELDS],
		as_dict=True,
	)
	if not details:
		return {}

	address = get_default_address("Company", company)
	if address:
		details.update(frappe.db.get_value("Address", address, ADDRESS_FIELDS, as_dict=True))
	return details


def save_company_address(company: str, values: dict):
	"""Update the company's own address, or add one when a first line is given."""
	name = get_default_address("Company", company)
	if not name and not values.get("address_line1"):
		return

	address = frappe.get_doc("Address", name) if name else frappe.new_doc("Address")
	address.update({field: values.get(field) for field in ADDRESS_FIELDS})
	if address.is_new():
		address.address_title = company
		address.address_type = "Billing"
		address.is_your_company_address = 1
		address.append("links", {"link_doctype": "Company", "link_name": company})
	address.save()


def create_company_onboarding(company: str):
	"""Start the onboarding of a new company."""
	if frappe.db.exists("Company Onboarding", company):
		return
	doc = frappe.new_doc("Company Onboarding")
	doc.company = company
	doc.insert()
