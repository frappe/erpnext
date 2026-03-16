# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from erpnext.setup.doctype.sales_invoice_series.sales_invoice_series import SalesInvoiceSeries


class MahiGranitesSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.manufacturing.doctype.quarantine_label.quarantine_label import QuarantineLabel
		from erpnext.manufacturing.doctype.slab_quality_grade.slab_quality_grade import SlabQualityGrade
		from erpnext.manufacturing.doctype.slab_seed.slab_seed import SlabSeed
		from erpnext.setup.doctype.sales_invoice_series.sales_invoice_series import SalesInvoiceSeries
		from frappe.types import DF

		grades: DF.Table[SlabQualityGrade]
		max_heating_minutes: DF.Float
		max_pay_line_amount: DF.Currency
		mfg_unit: DF.Link
		min_quarantine_hours: DF.Float
		quarantine_labels: DF.Table[QuarantineLabel]
		sales_invoice_patterns: DF.Table[SalesInvoiceSeries]
		show_job_card_queue_to_mixer_operators: DF.Check
		slab_seeds: DF.Table[SlabSeed]
	# end: auto-generated types
	pass

	def onload(self):
		print(self)
		pass
