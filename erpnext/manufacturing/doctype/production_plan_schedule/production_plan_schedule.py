# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ProductionPlanSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		duration_mins: DF.Float
		from_time: DF.Datetime
		item_code: DF.Link | None
		item_name: DF.Data | None
		operation: DF.Link | None
		plan_row: DF.Data | None
		production_plan: DF.Link
		row_type: DF.Literal["Finished Good", "Sub Assembly"]
		subject: DF.Data | None
		task_key: DF.Data | None
		to_time: DF.Datetime
		workstation: DF.Link | None
	# end: auto-generated types

	pass


def on_doctype_update():
	import frappe

	frappe.db.add_index("Production Plan Schedule", ["production_plan"])
	frappe.db.add_index("Production Plan Schedule", ["workstation", "from_time"])
