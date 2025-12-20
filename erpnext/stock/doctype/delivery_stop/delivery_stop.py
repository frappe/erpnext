# Copyright (c) 2017, newmatik.io / ESO Electronic Service Ottenbreit and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class DeliveryStop(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.Link
		contact: DF.Link | None
		customer: DF.Link | None
		customer_address: DF.SmallText | None
		customer_contact: DF.SmallText | None
		delivery_note: DF.Link | None
		details: DF.TextEditor | None
		distance: DF.Float
		email_sent_to: DF.Data | None
		estimated_arrival: DF.Datetime | None
		grand_total: DF.Currency
		lat: DF.Float
		lng: DF.Float
		locked: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		uom: DF.Link | None
		visited: DF.Check
	# end: auto-generated types

	pass
