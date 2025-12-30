# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CRMQuestionMaster(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		lead_stage: DF.Literal["Stage 0 - Welcome", "Stage 1 - Data Gathering", "Stage 2 - Event Demo", "Stage 3 - One to One Demo", "Stage 4 - Short Offering", "Stage 5 - Formal Offering", "Stage 6 - Oral Closing", "Stage 7 - Signed Closing / Onboarding", "Stage 8 - Users Experiencing", "Stage 9 - Potential Order Scale Up", "Stage 10 - Engaged Promoter"]
		question: DF.Data | None
		status: DF.Literal["Lead Capture", "Lead Qualification", "Engagement / Nurturing", "Evaluation / proposal", "Conversion / Purchase", "Onboarding / Ownership experience", "Retention"]
		type: DF.Literal["", "Individual buyer", "Fleet operator / delivery company", "Corporate mobility buyer", "Media / investor"]
	# end: auto-generated types
	pass
