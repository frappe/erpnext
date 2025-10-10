# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime
from frappe.utils.scheduler import is_scheduler_inactive


class ProcessPeriodClosingVoucher(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.process_period_closing_voucher_detail.process_period_closing_voucher_detail import (
			ProcessPeriodClosingVoucherDetail,
		)

		amended_from: DF.Link | None
		dates_to_process: DF.Table[ProcessPeriodClosingVoucherDetail]
		parent_pcv: DF.Link
		status: DF.Literal["Queued", "Running", "Completed"]
	# end: auto-generated types

	def validate(self):
		self.status = "Queued"
		self.populate_processing_table()

	def populate_processing_table(self):
		self.dates_to_process = []
		pcv = frappe.get_doc("Period Closing Voucher", self.parent_pcv)
		start = get_datetime(pcv.period_start_date)
		end = get_datetime(pcv.period_end_date)
		dates = [start + timedelta(days=x) for x in range((end - start).days + 1)]
		for x in dates:
			self.append("dates_to_process", {"processing_date": x, "status": "Queued"})


@frappe.whitelist()
def start_pcv_processing(docname: str):
	if frappe.db.get_value("Process Period Closing Voucher", docname, "status") in ["Queued", "Paused"]:
		frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Running")
		if dates_to_process := frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": docname, "status": "Queued"},
			fields=["processing_date"],
			order_by="processing_date",
			limit=4,
		):
			if not is_scheduler_inactive():
				for x in dates_to_process:
					frappe.enqueue(
						method="erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.process_individual_date",
						queue="long",
						is_async=True,
						enqueue_after_commit=True,
						docname=docname,
						date=x.processing_date,
					)
		else:
			frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")


@frappe.whitelist()
def pause_pcv_processing(docname: str):
	frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Paused")


def process_individual_date(docname: str, date: str):
	if frappe.db.get_value("Process Period Closing Voucher", docname, "status") == "Running":
		frappe.db.set_value(
			"Process Period Closing Voucher Detail", {"processing_date": date}, "status", "Completed"
		)
		if next_date_to_process := frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": docname, "status": "Queued"},
			fields=["processing_date"],
			order_by="processing_date",
			limit=1,
		):
			if not is_scheduler_inactive():
				frappe.enqueue(
					method="erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.process_individual_date",
					queue="long",
					is_async=True,
					enqueue_after_commit=True,
					docname=docname,
					date=next_date_to_process[0].processing_date,
				)
		else:
			frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")
