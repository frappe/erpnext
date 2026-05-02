# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SlabRecoveryReport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.manufacturing.doctype.slab_quality_observation.slab_quality_observation import SlabQualityObservation
		from frappe.types import DF

		amended_from: DF.Link | None
		contamination: DF.Check
		epoxy_applied: DF.Check
		film_contamination: DF.Check
		observations: DF.Table[SlabQualityObservation]
		pinholes: DF.Check
		porasity: DF.Check
		quality_report: DF.Link
		slab: DF.Link
		slab_template: DF.Link
	# end: auto-generated types
	pass
