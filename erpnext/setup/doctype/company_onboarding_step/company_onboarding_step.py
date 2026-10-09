# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompanyOnboardingStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		last_checked: DF.Datetime | None
		message: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal["Not Started", "Done", "Skipped"]
		step: DF.Data
		step_key: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Company Onboarding Step"
