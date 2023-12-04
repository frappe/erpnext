# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class DeliverySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dispatch_attachment: DF.Link | None
		dispatch_template: DF.Link | None
		send_with_attachment: DF.Check
		stop_delay: DF.Int
	# end: auto-generated types

	pass
