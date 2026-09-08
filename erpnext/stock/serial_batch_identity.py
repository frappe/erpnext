"""Resolve physical numbers at input boundaries. Stock references always contain document IDs."""

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import cstr, now


class SerialBatchIdentity:
	def __init__(self, doctype):
		self.doctype = doctype
		self.item_field, self.number_field = {
			"Serial No": ("item_code", "serial_no"),
			"Batch": ("item", "batch_id"),
		}[doctype]

	def resolve(self, item_code, numbers, *, create=False, defaults=None):
		"""Return IDs in input order. A physical number is never looked up as a document ID."""
		if not isinstance(numbers, list | tuple) or any(not isinstance(number, str) for number in numbers):
			frappe.throw(_("Physical numbers must be a list of strings"))
		numbers = [number.strip() for number in numbers]
		if not numbers:
			return []
		if not isinstance(item_code, str) or not item_code or any(not number for number in numbers):
			frappe.throw(_("Item and physical number are required"))

		filters = {self.item_field: item_code, self.number_field: ("in", numbers)}
		records = frappe.get_all(self.doctype, filters=filters, fields=["name", self.number_field])
		ids = {row[self.number_field]: row.name for row in records}
		missing = []
		for number in dict.fromkeys(numbers):
			if number in ids:
				continue
			# Use the database comparison rules, including its collation, for exact lookups.
			name = (
				frappe.db.get_value(self.doctype, {self.item_field: item_code, self.number_field: number})
				if records
				else None
			)
			if not name and create:
				missing.append(number)
				continue
			if not name:
				frappe.throw(_("{0} {1} does not exist for Item {2}").format(self.doctype, number, item_code))
			ids[number] = name
		if missing:
			ids.update(self.create_many(item_code, missing, defaults))
		return [ids[number] for number in numbers]

	def create_many(self, item_code, numbers, defaults=None):
		if self.doctype == "Batch":
			return {number: self.create_batch(item_code, number, defaults) for number in numbers}

		# Inactive serials can be prepared before their first receipt assigns a company.
		item = frappe.get_cached_value(
			"Item", item_code, ["item_name", "description", "warranty_period", "has_serial_no"], as_dict=True
		)
		if not item.has_serial_no:
			frappe.throw(_("Item {0} does not have serial numbers enabled").format(item_code))
		common = {
			"item_code": item_code,
			"item_name": item.item_name,
			"description": item.description,
			"warranty_period": item.warranty_period or 0,
			"status": "Inactive",
			"creation": now(),
			"modified": now(),
			"owner": frappe.session.user,
			"modified_by": frappe.session.user,
			**(defaults or {}),
		}
		ids = {number: make_autoname("hash", "Serial No") for number in numbers}
		try:
			frappe.db.bulk_insert(
				"Serial No",
				fields=["name", "serial_no", *common],
				values=[(name, number, *common.values()) for number, name in ids.items()],
			)
		except Exception as error:
			if frappe.db.is_unique_key_violation(error) or frappe.db.is_primary_key_violation(error):
				frappe.throw(
					_("A serial number already exists for Item {0}. Refresh and try again.").format(
						item_code
					),
					frappe.DuplicateEntryError,
				)
			raise
		return ids

	def create_batch(self, item_code, number, defaults=None):
		doc = frappe.new_doc("Batch")
		doc.update(defaults or {})
		doc.item = item_code
		doc.batch_id = number
		doc.insert(ignore_permissions=True)
		return doc.name

	def labels(self, names):
		if not names:
			return {}
		return dict(
			frappe.get_all(
				self.doctype,
				filters={"name": ("in", list(set(names)))},
				fields=["name", self.number_field],
				as_list=True,
			)
		)

	def validate(self, doc):
		number = cstr(doc.get(self.number_field)).strip()
		doc.set(self.number_field, number)
		filters = {self.item_field: doc.get(self.item_field), self.number_field: number}
		if doc.name:
			filters["name"] = ("!=", doc.name)
		if number and frappe.db.exists(self.doctype, filters):
			frappe.throw(
				_("{0} {1} already exists for Item {2}").format(
					self.doctype, number, doc.get(self.item_field)
				),
				frappe.DuplicateEntryError,
			)

	def backfill_numbers(self):
		table = frappe.qb.DocType(self.doctype)
		frappe.qb.update(table).set(table[self.number_field], table.name).where(
			table[self.number_field].isnull() | (table[self.number_field] == "")
		).run()

	def sync_constraint(self):
		self.backfill_numbers()
		frappe.db.add_unique(self.doctype, [self.item_field, self.number_field])


@frappe.whitelist(methods=["POST"])
def resolve_serial_batch_numbers(
	item_code: str,
	serial_numbers: list | str | None = None,
	batch_numbers: list | str | None = None,
	create: bool = False,
):
	"""Resolve physical input to Link values. Existing ID-based APIs keep their meaning."""
	frappe.has_permission("Item", "read", doc=item_code, throw=True)
	result = {}
	for doctype, values, key in (
		("Serial No", serial_numbers, "serial_nos"),
		("Batch", batch_numbers, "batch_nos"),
	):
		values = frappe.parse_json(values) or []
		if values:
			permission = "create" if create else "select" if frappe.only_has_select_perm(doctype) else "read"
			frappe.has_permission(doctype, permission, throw=True)
		result[key] = SerialBatchIdentity(doctype).resolve(item_code, values, create=create)
		if values and not create:
			allowed = frappe.get_list(
				doctype, filters={"name": ("in", result[key])}, pluck="name", limit_page_length=0
			)
			if set(result[key]) - set(allowed):
				frappe.throw(
					_("Not permitted to select these serial or batch records"), frappe.PermissionError
				)
	return result


@frappe.whitelist(methods=["GET", "POST"])
def get_serial_batch_labels(doctype: str, names: list | str):
	if doctype not in ("Serial No", "Batch"):
		frappe.throw(_("Only Serial No and Batch labels are supported"))
	names = frappe.parse_json(names)
	if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
		frappe.throw(_("Document IDs must be a list of strings"))
	identity = SerialBatchIdentity(doctype)
	return dict(
		frappe.get_list(
			doctype,
			filters={"name": ("in", names)},
			fields=["name", identity.number_field],
			as_list=True,
			limit_page_length=0,
		)
	)


@frappe.whitelist(methods=["POST"])
def resolve_transaction_serial_numbers(parent: dict | str, row: dict | str, numbers: list | str):
	from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import SUPPORTED_VOUCHER_TYPES
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_type_of_transaction

	parent, row = frappe._dict(frappe.parse_json(parent)), frappe._dict(frappe.parse_json(row))
	frappe.has_permission(
		parent.doctype, "write", doc=parent.name if not parent.__islocal else None, throw=True
	)
	frappe.has_permission("Item", "read", doc=row.item_code or row.rm_item_code, throw=True)
	frappe.has_permission("Serial No", "read", throw=True)
	create = parent.doctype in SUPPORTED_VOUCHER_TYPES and get_type_of_transaction(parent, row) == "Inward"
	return SerialBatchIdentity("Serial No").resolve(
		row.item_code or row.rm_item_code,
		frappe.parse_json(numbers),
		create=create,
		defaults={"company": parent.company},
	)


def add_number_labels(entries):
	"""Attach display values without changing the references or their field names."""
	for field, doctype, label in (
		("serial_no", "Serial No", "serial_number"),
		("batch_no", "Batch", "batch_number"),
	):
		labels = SerialBatchIdentity(doctype).labels([row.get(field) for row in entries if row.get(field)])
		for row in entries:
			row[label] = labels.get(row.get(field), row.get(field))
	return entries


def resolve_number_entries(item_code, entries, *, create=False):
	"""Only explicit physical-number fields are resolved. Link fields already contain IDs."""
	for field, doctype, number_field in (
		("batch_no", "Batch", "batch_number"),
		("serial_no", "Serial No", "serial_number"),
	):
		rows = [row for row in entries if row.get(number_field) and not row.get(field)]
		ids = SerialBatchIdentity(doctype).resolve(
			item_code, [row[number_field] for row in rows], create=create
		)
		for row, name in zip(rows, ids, strict=True):
			row[field] = name
	return entries


def validate_item_merge(old, new):
	for doctype in ("Serial No", "Batch"):
		identity = SerialBatchIdentity(doctype)
		source = frappe.qb.DocType(doctype).as_("source")
		target = frappe.qb.DocType(doctype).as_("target")
		conflict = (
			frappe.qb.from_(source)
			.join(target)
			.on(source[identity.number_field] == target[identity.number_field])
			.select(source[identity.number_field])
			.where((source[identity.item_field] == old) & (target[identity.item_field] == new))
			.limit(1)
		).run()
		if conflict:
			frappe.throw(_("Cannot merge items with the same {0}: {1}").format(doctype, conflict[0][0]))
