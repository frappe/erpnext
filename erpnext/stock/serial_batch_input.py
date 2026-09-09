import frappe
from frappe import _

from erpnext.stock.serial_batch_fields import NUMBER_INPUT_DOCTYPES
from erpnext.stock.serial_batch_identity import SerialBatchIdentity

NUMBER_FIELDS = ("batch_no", "serial_no", "rejected_serial_no", "current_serial_no")


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
		fields = self.row.get("__serial_batch_input")
		if fields is None:
			return
		if not isinstance(fields, list) or any(field not in NUMBER_FIELDS for field in fields):
			frappe.throw(_("Physical input must identify serial or batch fields"))
		for field in NUMBER_FIELDS:
			if field not in fields:
				continue
			value = self.row.get(field)
			if value is None:
				value = ""
			if not isinstance(value, str):
				frappe.throw(_("Physical numbers must be text"))
			numbers = (
				[value.strip()]
				if field == "batch_no" and value.strip()
				else [number.strip() for number in value.replace(",", "\n").splitlines() if number.strip()]
			)
			if field == "batch_no" and len(numbers) > 1:
				frappe.throw(_("Enter one physical batch number per row"))
			names = self.resolve_numbers(field, numbers) if numbers else []
			self.row.set(field, "\n".join(names))
			fields.remove(field)
			if names and self.row.meta.has_field("use_serial_batch_fields"):
				self.row.use_serial_batch_fields = 1
		self.row.__dict__.pop("__serial_batch_input", None)

	def resolve_numbers(self, field, numbers):
		doctype = "Batch" if field == "batch_no" else "Serial No"
		identity = SerialBatchIdentity(doctype)
		if not self.item_code:
			frappe.throw(_("Item is required"))
		frappe.has_permission("Item", "read", doc=self.item_code, throw=True)
		names = identity.resolve(
			self.item_code,
			numbers,
			create=self.can_create(field),
			defaults={"company": self.doc.get("company")},
			check_permissions=True,
		)
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
