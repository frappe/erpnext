# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.core.doctype.prepared_report.prepared_report import create_json_gz_file
from frappe.desk.form.load import get_attachments
from frappe.model.document import Document
from frappe.utils import get_link_to_form, gzip_decompress, parse_json
from frappe.utils.background_jobs import enqueue

from erpnext.stock.report.stock_balance.stock_balance import execute


class ClosingStockBalance(Document):
	def before_save(self):
		self.set_status()

	def set_status(self, save=False):
		self.status = "Queued"
		if self.docstatus == 2:
			self.status = "Canceled"

		if self.docstatus == 0:
			self.status = "Draft"

		if save:
			self.db_set("status", self.status)

	def validate(self):
		self.validate_duplicate()

	def validate_duplicate(self):
		table = frappe.qb.DocType("Closing Stock Balance")

		query = (
			frappe.qb.from_(table)
			.select(table.name)
			.where(
				(table.docstatus == 1)
				& (table.company == self.company)
				& (
					(table.from_date.between(self.from_date, self.to_date))
					| (table.to_date.between(self.from_date, self.to_date))
					| (table.from_date >= self.from_date and table.to_date <= self.to_date)
				)
			)
		)

		for fieldname in ["warehouse", "item_code", "item_group", "warehouse_type"]:
			if self.get(fieldname):
				query = query.where(table[fieldname] == self.get(fieldname))

		query = query.run(as_dict=True)

		if query and query[0].name:
			name = get_link_to_form("Closing Stock Balance", query[0].name)
			msg = f"Closing Stock Balance {name} already exists for the selected date range"
			frappe.throw(_(msg), title=_("Duplicate Closing Stock Balance"))

	def on_submit(self):
		self.set_status(save=True)
		self.enqueue_job()

	def on_cancel(self):
		self.set_status(save=True)
		self.clear_attachment()

	@frappe.whitelist()
	def enqueue_job(self):
		self.db_set("status", "In Progress")
		self.clear_attachment()
		enqueue(prepare_closing_stock_balance, name=self.name, queue="long", timeout=1500)

	@frappe.whitelist()
	def regenerate_closing_balance(self):
		self.enqueue_job()

	def clear_attachment(self):
		if attachments := get_attachments(self.doctype, self.name):
			attachment = attachments[0]
			frappe.delete_doc("File", attachment.name)

	def create_closing_stock_balance_entries(self):
		columns, data = execute(
			filters=frappe._dict(
				{
					"company": self.company,
					"from_date": self.from_date,
					"to_date": self.to_date,
					"warehouse": self.warehouse,
					"item_code": self.item_code,
					"item_group": self.item_group,
					"warehouse_type": self.warehouse_type,
					"include_uom": self.include_uom,
					"ignore_closing_balance": 1,
					"show_variant_attributes": 1,
					"show_stock_ageing_data": 1,
				}
			)
		)

		create_json_gz_file({"columns": columns, "data": data}, self.doctype, self.name)

	def get_prepared_data(self):
		if attachments := get_attachments(self.doctype, self.name):
			attachment = attachments[0]
			attached_file = frappe.get_doc("File", attachment.name)

			data = gzip_decompress(attached_file.get_content())
			if data := json.loads(data.decode("utf-8")):
				data = data

			return parse_json(data)

		return frappe._dict({})


def prepare_closing_stock_balance(name):
	doc = frappe.get_doc("Closing Stock Balance", name)

	doc.db_set("status", "In Progress")

	try:
		doc.create_closing_stock_balance_entries()
		doc.db_set("status", "Completed")
	except Exception as e:
		doc.db_set("status", "Failed")
		traceback = frappe.get_traceback()

		frappe.log_error("Closing Stock Balance Failed", traceback, doc.doctype, doc.name)
