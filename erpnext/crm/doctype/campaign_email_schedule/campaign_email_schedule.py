# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class CampaignEmailSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email_template: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		send_after_days: DF.Int
	# end: auto-generated types

	pass
