# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SerialandBatchBundle(Document):
	def validate(self):
		self.validate_serial_and_batch_no()

	def validate_serial_and_batch_no(self):
		if self.item_code and not self.has_serial_no and not self.has_batch_no:
			msg = f"The Item {self.item_code} does not have Serial No or Batch No"
			frappe.throw(_(msg))

	def before_cancel(self):
		self.delink_serial_and_batch_bundle()
		self.clear_table()

	def delink_serial_and_batch_bundle(self):
		self.voucher_no = None

		sles = frappe.get_all("Stock Ledger Entry", filters={"serial_and_batch_bundle": self.name})

		for sle in sles:
			frappe.db.set_value("Stock Ledger Entry", sle.name, "serial_and_batch_bundle", None)

	def clear_table(self):
		self.set("ledgers", [])


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	item_filters = {"disabled": 0}
	if txt:
		item_filters["name"] = ("like", f"%{txt}%")

	return frappe.get_all(
		"Item",
		filters=item_filters,
		or_filters={"has_serial_no": 1, "has_batch_no": 1},
		fields=["name", "item_name"],
		as_list=1,
	)


@frappe.whitelist()
def get_serial_batch_ledgers(item_code, voucher_no, name=None):
	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=[
			"`tabSerial and Batch Ledger`.`name`",
			"`tabSerial and Batch Ledger`.`qty`",
			"`tabSerial and Batch Ledger`.`warehouse`",
			"`tabSerial and Batch Ledger`.`batch_no`",
			"`tabSerial and Batch Ledger`.`serial_no`",
		],
		filters=[
			["Serial and Batch Bundle", "item_code", "=", item_code],
			["Serial and Batch Ledger", "parent", "=", name],
			["Serial and Batch Bundle", "voucher_no", "=", voucher_no],
			["Serial and Batch Bundle", "docstatus", "!=", 2],
		],
	)


@frappe.whitelist()
def add_serial_batch_ledgers(ledgers, child_row) -> object:
	if isinstance(child_row, str):
		child_row = frappe._dict(frappe.parse_json(child_row))

	if isinstance(ledgers, str):
		ledgers = frappe.parse_json(ledgers)

	if frappe.db.exists("Serial and Batch Bundle", child_row.serial_and_batch_bundle):
		doc = update_serial_batch_no_ledgers(ledgers, child_row)
	else:
		doc = create_serial_batch_no_ledgers(ledgers, child_row)

	return doc


def create_serial_batch_no_ledgers(ledgers, child_row) -> object:
	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"voucher_no": child_row.parent,
			"item_code": child_row.item_code,
			"voucher_detail_no": child_row.name,
		}
	)

	for row in ledgers:
		row = frappe._dict(row)
		doc.append(
			"ledgers",
			{
				"qty": row.qty or 1.0,
				"warehouse": child_row.warehouse,
				"batch_no": row.batch_no,
				"serial_no": row.serial_no,
			},
		)

	doc.save()

	frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc


def update_serial_batch_no_ledgers(ledgers, child_row) -> object:
	doc = frappe.get_doc("Serial and Batch Bundle", child_row.serial_and_batch_bundle)
	doc.voucher_detail_no = child_row.name
	doc.set("ledgers", [])
	doc.set("ledgers", ledgers)
	doc.save()

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc
