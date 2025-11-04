# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class QualityAction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.quality_management.doctype.quality_action_resolution.quality_action_resolution import (
			QualityActionResolution,
		)

		corrective_preventive: DF.Literal["Corrective", "Preventive"]
		date: DF.Date | None
		feedback: DF.Link | None
		goal: DF.Link | None
		procedure: DF.Link | None
		resolutions: DF.Table[QualityActionResolution]
		review: DF.Link | None
		status: DF.Literal["Open", "Completed"]
	# end: auto-generated types

	def validate(self):
		self.status = "Open" if any([d.status == "Open" for d in self.resolutions]) else "Completed"
