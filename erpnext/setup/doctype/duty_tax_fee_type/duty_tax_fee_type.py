# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DutyTaxFeeType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		title: DF.Data | None
	# end: auto-generated types

	pass


def create_duty_tax_fee_types():
	from csv import DictReader
	from pathlib import Path

	path = Path(__file__).parent / "data.csv"
	with path.open() as file:
		for row in DictReader(file):
			doc = frappe.new_doc("Duty Tax Fee Type")
			doc.name = row["code"]
			doc.title = row["title"]
			doc.description = row["description"]
			doc.insert(ignore_if_duplicate=True)
