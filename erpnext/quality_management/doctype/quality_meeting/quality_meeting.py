# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class QualityMeeting(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.quality_management.doctype.quality_meeting_agenda.quality_meeting_agenda import (
			QualityMeetingAgenda,
		)
		from erpnext.quality_management.doctype.quality_meeting_minutes.quality_meeting_minutes import (
			QualityMeetingMinutes,
		)

		agenda: DF.Table[QualityMeetingAgenda]
		minutes: DF.Table[QualityMeetingMinutes]
		status: DF.Literal["Open", "Closed"]
	# end: auto-generated types

	pass
