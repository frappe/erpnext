import frappe
from frappe import _

from erpnext.stock.serial_batch_fields import NUMBER_INPUT_DOCTYPES
from erpnext.stock.serial_batch_identity import SerialBatchIdentity, resolve_serial_batch_numbers


def resolve_transaction_numbers(doc, method=None):
	if doc.docstatus == 2:
		return
	for row in [doc, *doc.get_all_children()]:
		if row.doctype in NUMBER_INPUT_DOCTYPES:
			TransactionNumberInput(doc, row).resolve()


class TransactionNumberInput:
	def __init__(self, doc, row):
		self.doc = doc
		self.row = row
		self.item_code = row.get("item_code") or row.get("rm_item_code")

	def resolve(self):
		for field in ("batch_no", "serial_no", "rejected_serial_no", "current_serial_no"):
			number_field = field.replace("_no", "_number")
			value = self.row.get(number_field)
			if value is None:
				continue
			if not isinstance(value, str):
				frappe.throw(_("Physical numbers must be text"))
			numbers = (
				[value.strip()]
				if field == "batch_no" and value.strip()
				else [number.strip() for number in value.replace(",", "\n").splitlines() if number.strip()]
			)
			if field == "batch_no" and len(numbers) > 1:
				frappe.throw(_("Enter one physical batch number per row"))
			if self.row.get(field):
				frappe.throw(_("Provide either {0} or {1}, not both").format(field, number_field))
			names = self.resolve_numbers(field, numbers) if numbers else []
			self.row.set(field, "\n".join(names))
			self.row.set(number_field, None)
			if names and self.row.meta.has_field("use_serial_batch_fields"):
				self.row.use_serial_batch_fields = 1

	def resolve_numbers(self, field, numbers):
		doctype = "Batch" if field == "batch_no" else "Serial No"
		identity = SerialBatchIdentity(doctype)
		if not self.item_code:
			frappe.throw(_("Item is required"))
		frappe.has_permission("Item", "read", doc=self.item_code, throw=True)
		existing = {
			record[identity.number_field]
			for record in identity.get_query(numbers, self.item_code).run(as_dict=True)
		}
		missing = any(
			number not in existing and not identity.exists(number, self.item_code) for number in numbers
		)
		if missing and self.can_create(field):
			frappe.has_permission(doctype, "create", throw=True)
			identity.resolve(
				self.item_code, numbers, create=True, defaults={"company": self.doc.get("company")}
			)
		key = "batch_numbers" if field == "batch_no" else "serial_numbers"
		names = resolve_serial_batch_numbers(self.item_code, **{key: numbers})[
			"batch_nos" if field == "batch_no" else "serial_nos"
		]
		if doctype == "Serial No" and len(set(names)) != len(names):
			frappe.throw(_("A serial number cannot appear twice in the same row"))
		return names

	def can_create(self, field):
		from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import SUPPORTED_VOUCHER_TYPES
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			get_type_of_transaction,
		)

		row = frappe._dict(self.row.as_dict())
		row.pop("type_of_transaction", None)
		return (
			field != "current_serial_no"
			and self.doc.doctype in SUPPORTED_VOUCHER_TYPES
			and get_type_of_transaction(self.doc, row) == "Inward"
		)
