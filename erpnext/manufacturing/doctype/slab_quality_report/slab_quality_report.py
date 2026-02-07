# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SlabQualityReport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		bend: DF.Float
		con: DF.Data | None
		crack_back: DF.Data | None
		crack_front: DF.Data | None
		date: DF.Date
		fs: DF.Data | None
		grade: DF.Link
		job_card: DF.Link
		paper_deep_back: DF.Data | None
		paper_deep_front: DF.Data | None
		remarks: DF.Text | None
		shift: DF.Link
		slab: DF.Link
		slab_length: DF.Float
		slab_template: DF.Link
		slab_thickness: DF.Float
		slab_width: DF.Float
	# end: auto-generated types
	pass
