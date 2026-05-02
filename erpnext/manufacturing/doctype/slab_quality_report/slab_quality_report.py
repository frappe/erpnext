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
		from erpnext.manufacturing.doctype.slab_recalibration_reason_map.slab_recalibration_reason_map import (
			SlabRecalibrationReasonMap,
		)
		from erpnext.manufacturing.doctype.slab_recovery_reason_map.slab_recovery_reason_map import (
			SlabRecoveryReasonMap,
		)
		from erpnext.manufacturing.doctype.slab_repair_record.slab_repair_record import SlabRepairRecord
		from erpnext.manufacturing.doctype.slab_repolish_reason_map.slab_repolish_reason_map import (
			SlabRepolishReasonMap,
		)

		amended_from: DF.Link | None
		bend: DF.Float
		colour: DF.Literal["#007BFF", "#33CC33", "#A020F0", "#FF8C00", "#00CED1", "#FFD700", "#E6194B", "#800000", "#008080", "#F032E6", "#808000", "#9E2A3A"]
		contamination: DF.Data | None
		crack_back: DF.Data | None
		crack_front: DF.Data | None
		date: DF.Date
		filler_spot: DF.Data | None
		grade: DF.Link | None
		job_card: DF.Link
		observations: DF.Table[SlabQualityObservation]
		paper_deep_back: DF.Data | None
		paper_deep_front: DF.Data | None
		recalibration_type: DF.TableMultiSelect[SlabRecalibrationReasonMap]
		recovery_type: DF.TableMultiSelect[SlabRecoveryReasonMap]
		remarks: DF.SmallText | None
		repair: DF.Literal["", "None", "Recovery", "Repolish", "Recalibration"]
		repair_history: DF.Table[SlabRepairRecord]
		repolish_type: DF.TableMultiSelect[SlabRepolishReasonMap]
		shade: DF.Literal["", "Shade 1", "Shade 2", "Shade 3"]
		shift: DF.Link
		slab: DF.Link
		slab_length: DF.Float
		slab_template: DF.Link
		slab_thickness: DF.Float
		slab_width: DF.Float
	# end: auto-generated types

	@property
	def recovery_count(self):
		return len([r for r in self.repair_history if r.repair == "Recovery"])

	@property
	def repolish_count(self):
		return len([r for r in self.repair_history if r.repair == "Repolish"])

	@property
	def recalibration_count(self):
		return len([r for r in self.repair_history if r.repair == "Recalibration"])

	def to_json(self):
		data = self.as_dict().copy()
		data['recovery_count'] = self.recovery_count
		data['repolish_count'] = self.repolish_count
		data['recalibration_count'] = self.recalibration_count
		return data
