# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class QCLot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accepted_qty: DF.Float
		batch_no: DF.Link | None
		company: DF.Link | None
		inspection_basis: DF.Literal["Sample", "Each Quantity"]
		inspection_template: DF.Link | None
		item_code: DF.Link
		naming_series: DF.Literal["QCLOT-.YYYY.-"]
		pending_qty: DF.Float
		quality_warehouse: DF.Link
		received_qty: DF.Float
		rejected_qty: DF.Float
		source_document: DF.DynamicLink | None
		source_document_type: DF.Link | None
		status: DF.Literal["Under Inspection", "Partially Released", "Released", "Rejected"]
	# end: auto-generated types

	def validate(self):
		self.set_pending_qty_and_status()

	def set_pending_qty_and_status(self):
		self.pending_qty = flt(self.received_qty) - flt(self.accepted_qty) - flt(self.rejected_qty)

		resolved = flt(self.accepted_qty) + flt(self.rejected_qty)
		if resolved <= 0:
			self.status = "Under Inspection"
		elif self.pending_qty > 0:
			self.status = "Partially Released"
		elif flt(self.accepted_qty) <= 0:
			self.status = "Rejected"
		else:
			self.status = "Released"
