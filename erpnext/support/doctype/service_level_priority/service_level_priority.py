# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class ServiceLevelPriority(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default_priority: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		priority: DF.Link
		resolution_time: DF.Duration | None
		response_time: DF.Duration
	# end: auto-generated types

	pass
