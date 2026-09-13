import re

import frappe
from frappe import _
from frappe.query_builder.functions import Lower
from frappe.query_builder.terms import ParameterizedValueWrapper
from frappe.utils import escape_html
from pypika.analytics import Min


class SerialBatchIdentity:
	def __init__(self, doctype):
		self.doctype = doctype
		self.item_field, self.number_field = {
			"Serial No": ("item_code", "serial_no"),
			"Batch": ("item", "batch_id"),
		}[doctype]
		self.constraint_name = f"unique_{self.item_field}_{self.number_field}"

	def add_unique_constraint(self):
		if frappe.db.has_index(f"tab{self.doctype}", self.constraint_name):
			return
		if frappe.db.db_type == "postgres":
			# Frappe's add_unique accepts columns, not expressions.
			frappe.db.sql_ddl(
				f'CREATE UNIQUE INDEX "{self.constraint_name}" ON "tab{self.doctype}" '
				f'(lower("{self.number_field}"), "{self.item_field}")'
			)
		else:
			frappe.db.add_unique(self.doctype, [self.item_field, self.number_field], self.constraint_name)

	def raise_duplicate(self, error, item_code, number=None, *, message=None):
		if not frappe.db.is_unique_key_violation(error):
			return
		constraint = getattr(getattr(error, "diag", None), "constraint_name", None)
		if frappe.db.db_type == "mariadb":
			matches = re.findall(r"for key ['`](?:[^'`]+\.)?([^'`]+)['`]", str(error))
			constraint = matches[-1] if matches else None
		if constraint == self.constraint_name:
			if message is None:
				message = _("{0} {1} already exists for Item {2}").format(
					_(self.doctype), escape_html(number), escape_html(item_code)
				)
			frappe.throw(message, frappe.UniqueValidationError)

	def resolve(self, item_code, numbers, *, create=False, defaults=None, ignore_permissions=False):
		"""Resolve physical numbers to IDs. Creation is opt-in for authorized saves."""
		if not isinstance(item_code, str) or not item_code:
			frappe.throw(_("Item is required"))
		if not isinstance(numbers, list | tuple) or any(not isinstance(number, str) for number in numbers):
			frappe.throw(_("Physical numbers must be a list of strings"))
		numbers = [number.strip() for number in numbers]
		if any(not number for number in numbers):
			frappe.throw(_("Physical numbers cannot be empty"))
		if not numbers:
			return []

		if not ignore_permissions:
			frappe.has_permission("Item", "read", doc=item_code, throw=True)
			permission = "select" if frappe.only_has_select_perm(self.doctype) else "read"
			frappe.has_permission(self.doctype, permission, throw=True)

		names = [None] * len(numbers)
		created = {}
		for index, name, first_index in self._match_numbers(item_code, numbers):
			if not name:
				if not create:
					frappe.throw(
						_("{0} {1} does not exist for Item {2}").format(
							_(self.doctype), escape_html(numbers[index]), escape_html(item_code)
						)
					)
				if first_index not in created:
					created[first_index] = self._create_record(
						item_code, numbers[first_index], defaults, ignore_permissions
					)
				name = created[first_index]
			if names[index]:
				frappe.throw(
					_("{0} {1} matches multiple records for Item {2}").format(
						_(self.doctype), escape_html(numbers[index]), escape_html(item_code)
					)
				)
			names[index] = name

		if not ignore_permissions:
			allowed = frappe.get_list(self.doctype, filters={"name": ("in", names)}, pluck="name")
			if set(names) - set(allowed):
				frappe.throw(
					_("Not permitted to select these serial or batch records"), frappe.PermissionError
				)
		return names

	def get_records(self, item_code, numbers, fields, *, ignore_permissions=True):
		if not numbers:
			return []
		table = frappe.qb.DocType(self.doctype)
		return (
			frappe.qb.get_query(
				self.doctype,
				fields=fields,
				filters={self.item_field: item_code} if item_code is not None else {},
				ignore_permissions=ignore_permissions,
			)
			.where(
				self._number_key(table[self.number_field]).isin(
					[self._number_key(number) for number in numbers]
				)
			)
			.run(as_dict=True)
		)

	def _create_record(self, item_code, number, defaults, ignore_permissions):
		values = {
			**(defaults or {}),
			"doctype": self.doctype,
			self.item_field: item_code,
			self.number_field: number,
		}
		if self.doctype == "Serial No":
			if not frappe.get_cached_value("Item", item_code, "has_serial_no"):
				frappe.throw(
					_("Item {0} does not have serial numbers enabled").format(escape_html(item_code))
				)
			values["status"] = "Inactive"
		return frappe.get_doc(values).insert(ignore_permissions=ignore_permissions).name

	def _match_numbers(self, item_code, numbers):
		table = frappe.qb.DocType(self.doctype)
		# Retain the physical column's collation when comparing input on MariaDB.
		inputs = (
			frappe.qb.from_(table)
			.select(table[self.number_field].as_("number"), ParameterizedValueWrapper(-1).as_("ordinal"))
			.where(table.name.isnull())
		)
		for index, number in enumerate(numbers):
			inputs = inputs.union_all(
				frappe.qb.select(
					ParameterizedValueWrapper(number).as_("number"),
					ParameterizedValueWrapper(index).as_("ordinal"),
				)
			)
		inputs = inputs.as_("numbers")
		return (
			frappe.qb.from_(inputs)
			.left_join(table)
			.on(
				(table[self.item_field] == item_code)
				& (self._number_key(table[self.number_field]) == self._number_key(inputs.number))
			)
			.select(inputs.ordinal, table.name, Min(inputs.ordinal).over(self._number_key(inputs.number)))
		).run()

	def _number_key(self, value):
		return Lower(value) if frappe.db.db_type == "postgres" else value
