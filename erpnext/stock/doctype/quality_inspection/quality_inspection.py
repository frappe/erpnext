# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from math import isfinite
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, get_link_to_form
from frappe.utils.number_format import NUMBER_FORMAT_MAP, NumberFormat

from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)
from erpnext.stock.services.quality_inspection_service import (
	QI_INCOMING_PURPOSES,
	QI_OUTGOING_PURPOSES,
)


class QualityInspection(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.quality_inspection_reading.quality_inspection_reading import (
			QualityInspectionReading,
		)

		amended_from: DF.Link | None
		batch_no: DF.Link | None
		bom_no: DF.Link | None
		child_row_reference: DF.Data | None
		company: DF.Link | None
		description: DF.SmallText | None
		inspected_by: DF.Link
		inspection_type: DF.Literal["", "Incoming", "Outgoing", "In Process"]
		item_code: DF.Link
		item_name: DF.Data | None
		item_serial_no: DF.Link | None
		letter_head: DF.Link | None
		manual_inspection: DF.Check
		naming_series: DF.Literal["MAT-QA-.YYYY.-"]
		quality_inspection_template: DF.Link | None
		readings: DF.Table[QualityInspectionReading]
		reference_name: DF.DynamicLink
		reference_type: DF.Literal[
			"",
			"Purchase Receipt",
			"Purchase Invoice",
			"Subcontracting Receipt",
			"Delivery Note",
			"Sales Invoice",
			"Stock Entry",
			"Job Card",
		]
		remarks: DF.Text | None
		report_date: DF.Date
		sample_size: DF.Float
		status: DF.Literal["", "Accepted", "Rejected", "Cancelled"]
		verified_by: DF.Data | None

	# end: auto-generated types
	def on_discard(self):
		self.update_qc_reference()
		self.db_set("status", "Cancelled")

	def validate(self):
		if not self.readings and self.item_code:
			self.get_item_specification_details()

		if self.inspection_type == "In Process" and self.reference_type == "Job Card":
			item_qi_template = frappe.db.get_value("Item", self.item_code, "quality_inspection_template")
			parameters = get_template_details(item_qi_template)
			for reading in self.readings:
				for d in parameters:
					if reading.specification == d.specification:
						reading.update(d)
						reading.status = "Accepted"

		if self.readings:
			self.validate_reading_number_format()
			self.inspect_and_set_status()

		self.validate_inspection_required()
		self.set_child_row_reference()
		self.set_company()

	def set_company(self):
		if self.reference_type and self.reference_name:
			company = frappe.get_cached_value(self.reference_type, self.reference_name, "company")
			if company != self.company:
				self.company = company

	def set_child_row_reference(self):
		if self.child_row_reference:
			return

		if not (self.reference_type and self.reference_name):
			return

		doctype = self.reference_type + " Item"
		if self.reference_type == "Stock Entry":
			doctype = "Stock Entry Detail"

		child_doc = frappe.qb.DocType(doctype)
		qi_doc = frappe.qb.DocType("Quality Inspection")

		child_row_references = (
			frappe.qb.from_(child_doc)
			.left_join(qi_doc)
			.on(child_doc.name == qi_doc.child_row_reference)
			.select(child_doc.name)
			.where(
				(child_doc.item_code == self.item_code)
				& (child_doc.parent == self.reference_name)
				& (child_doc.docstatus < 2)
				& (qi_doc.name.isnull())
			)
			.orderby(child_doc.idx)
		).run(pluck=True)

		if len(child_row_references):
			self.child_row_reference = child_row_references[0]

	def validate_inspection_required(self):
		if frappe.db.get_single_value(
			"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
		):
			return

		if self.reference_type in ["Purchase Receipt", "Purchase Invoice"] and not frappe.get_cached_value(
			"Item", self.item_code, "inspection_required_before_purchase"
		):
			frappe.throw(
				_(
					"'Inspection Required before Purchase' is disabled for the item {0}, no need to create the QI"
				).format(get_link_to_form("Item", self.item_code))
			)

		if self.reference_type in ["Delivery Note", "Sales Invoice"] and not frappe.get_cached_value(
			"Item", self.item_code, "inspection_required_before_delivery"
		):
			frappe.throw(
				_(
					"'Inspection Required before Delivery' is disabled for the item {0}, no need to create the QI"
				).format(get_link_to_form("Item", self.item_code))
			)

	def before_submit(self):
		self.validate_readings_status_mandatory()

	@frappe.whitelist()
	def get_item_specification_details(self):
		if not self.quality_inspection_template:
			self.quality_inspection_template = frappe.db.get_value(
				"Item", self.item_code, "quality_inspection_template"
			)

		if not self.quality_inspection_template:
			return

		self.set("readings", [])
		parameters = get_template_details(self.quality_inspection_template)
		for d in parameters:
			child = self.append("readings", {})
			child.update(d)
			child.status = "Accepted"
			child.parameter_group = frappe.get_value(
				"Quality Inspection Parameter", d.specification, "parameter_group"
			)

	@frappe.whitelist()
	def get_quality_inspection_template(self):
		template = ""
		if self.bom_no:
			template = frappe.db.get_value("BOM", self.bom_no, "quality_inspection_template")

		if not template:
			template = frappe.db.get_value("BOM", self.item_code, "quality_inspection_template")

		self.quality_inspection_template = template
		self.get_item_specification_details()

	def on_update(self):
		action_if_qi_in_draft = frappe.db.get_single_value(
			"Stock Settings", "action_if_quality_inspection_is_not_submitted"
		)

		if not action_if_qi_in_draft or action_if_qi_in_draft == "Warn":
			self.update_qc_reference()

	def on_submit(self):
		if (
			frappe.db.get_single_value("Stock Settings", "action_if_quality_inspection_is_not_submitted")
			== "Stop"
		):
			self.update_qc_reference()

	def on_cancel(self):
		self.ignore_linked_doctypes = "Serial and Batch Bundle"

		self.update_qc_reference()

	def on_trash(self):
		self.update_qc_reference(remove_reference=True)

	def validate_readings_status_mandatory(self):
		for reading in self.readings:
			if not reading.status:
				frappe.throw(_("Row #{0}: Status is mandatory").format(reading.idx))

	def update_qc_reference(self, remove_reference=False):
		quality_inspection = self.name if self.docstatus < 2 and not remove_reference else ""

		if self.reference_type == "Job Card":
			if self.reference_name:
				ref = frappe.qb.DocType(self.reference_type)
				(
					frappe.qb.update(ref)
					.set(ref.quality_inspection, quality_inspection)
					.set(ref.modified, self.modified)
					.where((ref.name == self.reference_name) & (ref.production_item == self.item_code))
				).run()

		else:
			doctype = self.reference_type + " Item"

			if self.reference_type == "Stock Entry":
				doctype = "Stock Entry Detail"

			if doctype and self.reference_name:
				child_doc = frappe.qb.DocType(doctype)

				query = (
					frappe.qb.update(child_doc)
					.set(child_doc.quality_inspection, quality_inspection)
					.where(
						(child_doc.parent == self.reference_name) & (child_doc.item_code == self.item_code)
					)
				)

				if self.batch_no and self.docstatus < 2:
					query = query.where(child_doc.batch_no == self.batch_no)

				if self.docstatus == 2:  # if cancel, then remove qi link wherever same name
					query = query.where(child_doc.quality_inspection == self.name)

				if self.child_row_reference:
					query = query.where(child_doc.name == self.child_row_reference)

				query.run()

				frappe.db.set_value(
					self.reference_type,
					self.reference_name,
					"modified",
					self.modified,
				)

		if self.reference_type and self.reference_name:
			frappe.get_lazy_doc(self.reference_type, self.reference_name).notify_update()

	def inspect_and_set_status(self):
		for reading in self.readings:
			if not reading.manual_inspection:  # dont auto set status if manual
				if reading.formula_based_criteria:
					self.set_status_based_on_acceptance_formula(reading)
				else:
					# if not formula based check acceptance values set
					self.set_status_based_on_acceptance_values(reading)

		if not self.manual_inspection:
			self.status = "Accepted"
			for reading in self.readings:
				if reading.status == "Rejected":
					self.status = "Rejected"
					frappe.msgprint(
						_("Status set to rejected as there are one or more rejected readings."), alert=True
					)
					break

	def validate_reading_number_format(self):
		"""Reject newly entered readings that are not numbers in the user's format.

		They would otherwise be misread rather than refused, silently rejecting an
		inspection whose readings are in fact within the acceptance range. Readings
		already stored are left alone, so a document entered by a user in one locale
		stays saveable and submittable by a user in another."""
		number_format = get_reading_number_format()
		decimal_str, comma_str = get_reading_separators(number_format)
		before_save = self.get_doc_before_save()

		for reading in self.readings:
			if not cint(reading.numeric) or cint(reading.manual_inspection):
				continue

			stored = before_save and before_save.get("readings", {"name": reading.name})
			stored = stored[0] if stored else None

			for i in range(1, 11):
				field = "reading_" + str(i)
				value = reading.get(field)
				if value is None or not value.strip():
					continue

				if stored and stored.get(field) == value:
					continue

				if parse_reading(value, decimal_str, comma_str) is None:
					frappe.throw(
						_(
							"Row #{0}: Reading {1} {2} is not a valid number in the {3} number format. Use {4} as the decimal separator."
						).format(
							reading.idx,
							i,
							frappe.bold(value),
							frappe.bold(number_format.string),
							frappe.bold(decimal_str),
						),
						title=_("Invalid Reading"),
					)

	def set_status_based_on_acceptance_values(self, reading):
		if not cint(reading.numeric):
			reading_value = reading.get("reading_value") or ""
			value = reading.get("value") or ""
			result = reading_value == value
		else:
			# numeric readings
			result = self.min_max_criteria_passed(reading)

		reading.status = "Accepted" if result else "Rejected"

	def min_max_criteria_passed(self, reading):
		"""Determine whether all readings fall in the acceptable range."""
		has_reading = False
		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				has_reading = True
				result = (
					flt(reading.get("min_value"))
					<= parse_float(reading_value)
					<= flt(reading.get("max_value"))
				)
				if not result:
					return False
		return has_reading

	def set_status_based_on_acceptance_formula(self, reading):
		if not reading.acceptance_formula:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is required.").format(reading.idx),
				title=_("Missing Formula"),
			)

		condition = reading.acceptance_formula
		data = self.get_formula_evaluation_data(reading)

		try:
			result = frappe.safe_eval(condition, None, data)
			reading.status = "Accepted" if result else "Rejected"
		except NameError as e:
			field = frappe.bold(e.args[0].split()[1])
			frappe.throw(
				_(
					"Row #{0}: {1} is not a valid reading field. Please refer to the field description."
				).format(reading.idx, field),
				title=_("Invalid Formula"),
			)
		except Exception:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is incorrect.").format(reading.idx),
				title=_("Invalid Formula"),
			)

	def get_formula_evaluation_data(self, reading):
		data = {}
		if not cint(reading.numeric):
			data = {"reading_value": reading.get("reading_value")}
		else:
			# numeric readings
			for i in range(1, 11):
				field = "reading_" + str(i)
				if reading.get(field) is None:
					data[field] = 0.0
					continue

				data[field] = parse_float(reading.get(field))
			data["mean"] = self.calculate_mean(reading)

		return data

	def calculate_mean(self, reading):
		"""Calculate mean of all non-empty readings."""
		from statistics import mean

		readings_list = []

		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				readings_list.append(parse_float(reading_value))

		actual_mean = mean(readings_list) if readings_list else 0
		return actual_mean


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype: Any, txt: str | None, searchfield: Any, start: int, page_len: int, filters: dict):
	reference_doctype = filters.get("reference_doctype")

	if not reference_doctype:
		return []
	elif reference_doctype == "Job Card":
		production_item, item_name = frappe.get_value(
			"Job Card", filters.get("reference_name"), ["production_item", "item_name"]
		)
		return ((production_item, item_name),)
	else:
		my_filters = [
			["items.parent", "=", filters.get("reference_name")],
			"and",
			["items.item_code", "like", f"%{txt}%"],
			"and",
			["docstatus", "<", 2],
			"and",
			["items.quality_inspection", "is", "not set"],
		]

		require_distinct_warehouse = False

		if reference_doctype == "Stock Entry":
			purpose = frappe.get_cached_value("Stock Entry", filters.get("reference_name"), "purpose")
			my_filters.extend(
				[
					"and",
					["items.secondary_item_type", "is", "not set"],
					"and",
					["items.is_legacy_scrap_item", "=", 0],
				]
			)
			if purpose == "Manufacture":
				my_filters.extend(
					[
						"and",
						["items.is_finished_item", "=", 1],
					]
				)
			elif purpose in QI_INCOMING_PURPOSES:
				my_filters.extend(
					[
						"and",
						["items.t_warehouse", "is", "set"],
					]
				)
			elif purpose in QI_OUTGOING_PURPOSES:
				my_filters.extend(
					[
						"and",
						["items.s_warehouse", "is", "set"],
					]
				)
				require_distinct_warehouse = True
			else:
				# purpose requires no quality inspection
				return []
		elif filters.get("inspection_type") != "In Process":
			my_filters.extend(
				[
					"and",
					[
						"items.item_code",
						"in",
						frappe.get_list(
							"Item",
							filters={
								"inspection_required_before_purchase"
								if filters.get("inspection_type") == "Incoming"
								else "inspection_required_before_delivery": 1
							},
							pluck="name",
						),
					],
				]
			)

		query = frappe.get_query(
			reference_doctype,
			fields=["items.item_code, items.item_name"],
			filters=my_filters,
			offset=start,
			limit=page_len,
			ignore_permissions=False,
			distinct=True,
		)
		# frappe's db_query drops ORDER BY for a distinct query on Postgres, which (with offset/limit)
		# changes both the order and the page contents vs MariaDB. Appending the order to the built
		# query instead keeps it -- item_code is in the DISTINCT select, so it is valid on Postgres.
		items_field = frappe.get_meta(reference_doctype).get_field("items")
		if items_field:
			child = frappe.qb.DocType(items_field.options)
			if require_distinct_warehouse:
				query = query.where(child.t_warehouse.isnull() | (child.s_warehouse != child.t_warehouse))
			query = query.orderby(child.item_code)
		return query.run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def quality_inspection_query(
	doctype: Any, txt: str | None, searchfield: Any, start: int, page_len: int, filters: dict
):
	return frappe.get_all(
		"Quality Inspection",
		limit_start=start,
		limit_page_length=page_len,
		filters={
			"docstatus": ("<", 2),
			"name": ("like", "%%%s%%" % txt),
			"item_code": filters.get("item_code"),
			"reference_name": ("in", [filters.get("reference_name", ""), ""]),
			"child_row_reference": ("in", [filters.get("child_row_reference", ""), ""]),
		},
		as_list=1,
	)


@frappe.whitelist()
def make_quality_inspection(source_name: str, target_doc: str | dict | Document | None = None):
	def postprocess(source, doc):
		doc.inspected_by = frappe.session.user
		doc.get_quality_inspection_template()

	doc = get_mapped_doc(
		"BOM",
		source_name,
		{
			"BOM": {
				"doctype": "Quality Inspection",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {"name": "bom_no", "item": "item_code", "stock_uom": "uom", "stock_qty": "qty"},
			}
		},
		target_doc,
		postprocess,
	)

	return doc


def get_reading_number_format() -> NumberFormat:
	"""Number format the user enters readings in.

	User defaults fall back to the global default, so this is the same format the
	user's desk formats numbers with."""
	number_format = frappe.defaults.get_user_default("number_format")
	if number_format not in NUMBER_FORMAT_MAP:
		number_format = "#,###.##"

	return NumberFormat.from_string(number_format)


def get_reading_separators(number_format: NumberFormat) -> tuple[str, str]:
	"""Decimal and thousands separator a reading may be written with.

	A format with no decimal separator still has to accept decimal readings, so it
	falls back to a dot and gives up any grouping that would collide with it."""
	decimal_str = number_format.decimal_separator or "."
	comma_str = number_format.thousands_separator

	return decimal_str, "" if comma_str == decimal_str else comma_str


def parse_reading(value: str, decimal_str: str, comma_str: str) -> float | None:
	"""Reading as a float, or None when it is not a number in that format."""
	value = value.strip()
	integer_part = value.partition(decimal_str)[0]

	if comma_str and comma_str in integer_part:
		groups = integer_part.split(comma_str)
		lead = groups[0][1:] if groups[0][:1] in ("+", "-") else groups[0]
		if not 1 <= len(lead) <= 3 or len(groups[-1]) != 3:
			return None

		if any(len(group) not in (2, 3) for group in groups[1:-1]):
			return None

		value = value.replace(comma_str, "")

	if decimal_str != ".":
		value = value.replace(decimal_str, ".")

	try:
		number = float(value)
	except ValueError:
		return None

	return number if isfinite(number) else None


def parse_float(num: str) -> float:
	"""Since reading_# fields are `Data` field they might contain number which
	is representation in user's prefered number format instead of machine
	readable format. This function converts them to machine readable format."""

	decimal_str, comma_str = get_reading_separators(get_reading_number_format())

	return flt(parse_reading(num, decimal_str, comma_str))
