# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SlabRepairRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		colour: DF.Color | None
		colour_indicator: DF.Data | None
		contamination: DF.Data | None
		crack_back: DF.Data | None
		crack_front: DF.Data | None
		epoxy_applied: DF.Check
		filler_spot: DF.Data | None
		film_contamination: DF.Check
		is_contamination: DF.Check
		job_card: DF.Link | None
		paper_deep_back: DF.Data | None
		paper_deep_front: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pinholes: DF.Check
		porasity: DF.Check
		remarks: DF.SmallText | None
		repair: DF.Data | None
		repair_reason: DF.Data | None
		repair_req_date: DF.Datetime | None
		repaired_date: DF.Datetime | None
		slab_thickness: DF.Float
	# end: auto-generated types
