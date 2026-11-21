# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class Routing(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.bom_operation.bom_operation import BOMOperation

		disabled: DF.Check
		operations: DF.Table[BOMOperation]
		routing_name: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.calculate_operating_cost()
		self.set_routing_id()

	def on_update(self):
		self.calculate_operating_cost()

	def calculate_operating_cost(self):
		self.set_workstation_hour_rates()
		for operation in self.operations:
			operation.operating_cost = flt(
				flt(operation.hour_rate) * flt(operation.time_in_mins) / 60,
				operation.precision("operating_cost"),
			)

	def set_workstation_hour_rates(self):
		rows = self.get_rows_without_workstation_rate()
		workstations = list({row.workstation for row in rows if row.workstation})
		if not workstations:
			return

		hour_rates = dict(
			frappe.get_all(
				"Workstation",
				filters={"name": ["in", workstations]},
				fields=["name", "hour_rate"],
				as_list=True,
			)
		)
		for row in rows:
			if row.workstation in hour_rates:
				row.hour_rate = hour_rates[row.workstation]

	def get_rows_without_workstation_rate(self):
		previous = self.get_doc_before_save()
		previous_rows = {row.name: row for row in previous.operations} if previous else {}

		rows = []
		for row in self.operations:
			old = previous_rows.get(row.name)
			if not row.hour_rate or (
				old and old.workstation != row.workstation and flt(old.hour_rate) == flt(row.hour_rate)
			):
				rows.append(row)

		return rows

	def set_routing_id(self):
		sequence_id = 0
		for row in self.operations:
			if not row.sequence_id:
				row.sequence_id = sequence_id + 1
			elif sequence_id and row.sequence_id and cint(sequence_id) > cint(row.sequence_id):
				frappe.throw(
					_(
						"At row #{0}: the sequence id {1} cannot be less than previous row sequence id {2}"
					).format(row.idx, row.sequence_id, sequence_id)
				)

			sequence_id = row.sequence_id
