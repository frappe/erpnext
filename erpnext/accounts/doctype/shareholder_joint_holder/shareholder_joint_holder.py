# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ShareholderJointHolder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		legal_name: DF.Data
		tax_id: DF.Data
		tax_id_country: DF.Link
		tax_id_type: DF.Data
	# end: auto-generated types

	pass
