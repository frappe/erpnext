# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# WBS Monthly Distribution
import frappe
from frappe.model.document import Document
from frappe import _


class WBSMonthlyDistribution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:  # pragma: no cover
		from erpnext.budget.doctype.distribution_percentage.distribution_percentage import DistributionPercentage
		from frappe.types import DF

		action_if_accumulated_monthly_budget_exceeded_on_actual: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		applicable_on_booking_actual_expenses: DF.Check
		applicable_on_material_request: DF.Check
		applicable_on_purchase_order: DF.Check
		for_wbs: DF.Link | None
		linked_gl_account: DF.Link | None
		monthly_distribution: DF.Table[DistributionPercentage]
		wbs_available_budget: DF.Currency
		work_breakdown_structure_name: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.check_duplicate_for_wbs()
		self.update_linked_wbs()
		self.check_total_allocation()

	def check_duplicate_for_wbs(self):
		# Check if there are any existing records with the same for_wbs
		existing_record = frappe.db.exists(
			"WBS Monthly Distribution", 
			{
				"for_wbs": self.for_wbs,
				"name": ["!=", self.name]
			}
		)
		
		if existing_record:
			frappe.throw(_("A record with the same WBS already exists: {0}").format(existing_record))

	def update_linked_wbs(self):
		if self.for_wbs:
			frappe.db.set_value("Work Breakdown Structure", self.for_wbs, "linked_monthly_distribution", self.name)

	def on_trash(self):
		if self.for_wbs:
			frappe.db.set_value("Work Breakdown Structure", self.for_wbs, "linked_monthly_distribution", None)

	
	def check_total_allocation(self):
		total_percentage = 0.0
		if self.monthly_distribution:
			for i in self.monthly_distribution:
				total_percentage += i.get("allocation")
		if total_percentage > 100:
			frappe.throw(_("Total Monthly Distribution Allocation Percentage should not be more than 100%"))
			


	