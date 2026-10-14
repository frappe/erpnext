# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import to_timedelta


class CommunicationMedium(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.communication.doctype.communication_medium_timeslot.communication_medium_timeslot import (
			CommunicationMediumTimeslot,
		)

		catch_all: DF.Link | None
		communication_channel: DF.Literal
		communication_medium_type: DF.Literal["Voice", "Email", "Chat"]
		disabled: DF.Check
		provider: DF.Link | None
		timeslots: DF.Table[CommunicationMediumTimeslot]
	# end: auto-generated types

	def validate(self):
		self.validate_timeslots()

	def validate_timeslots(self):
		for slot in self.timeslots:
			if to_timedelta(slot.from_time) >= to_timedelta(slot.to_time):
				frappe.throw(
					_("Row {0}: To Time must be later than From Time. Split overnight slots by day.").format(
						slot.idx
					)
				)
