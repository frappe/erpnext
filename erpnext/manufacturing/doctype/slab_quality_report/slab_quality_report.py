# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.manufacturing.doctype.slab.slab import Slab


class SlabQualityReport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.slab_quality_observation.slab_quality_observation import (
			SlabQualityObservation,
		)

		amended_from: DF.Link | None
		bend: DF.Float
		contamination: DF.Data | None
		crack_back: DF.Data | None
		crack_front: DF.Data | None
		date: DF.Date
		filler_spot: DF.Data | None
		grade: DF.Link
		job_card: DF.Link
		observations: DF.Table[SlabQualityObservation]
		paper_deep_back: DF.Data | None
		paper_deep_front: DF.Data | None
		remarks: DF.Text | None
		repair: DF.Literal["None", "Recovery", "Repolish", "3cm to 2cm"]
		shift: DF.Link
		slab: DF.Link
		slab_length: DF.Float
		slab_template: DF.Link
		slab_thickness: DF.Float
		slab_width: DF.Float
	# end: auto-generated types
	pass


	def before_save(self):
		self.update_shipping_details_on_slab()


	def before_update_after_submit(self):
		self.update_shipping_details_on_slab()


	def update_shipping_details_on_slab(self):
		slab: Slab = frappe.get_doc("Slab", self.slab)  # pyright: ignore[reportAssignmentType]
		slab.save(ignore_permissions=True)
