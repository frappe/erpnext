# Copyright (c) 2019, Hash Include Solutions FZC and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class QualityFeedbackTemplateParameter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parameter: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
