# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr, flt

from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)


class QualityInspection(Document):
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
			self.inspect_and_set_status()

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

	@frappe.whitelist()
	def get_quality_inspection_template(self):
		template = ""
		if self.bom_no:
			template = frappe.db.get_value("BOM", self.bom_no, "quality_inspection_template")

		if not template:
			template = frappe.db.get_value("BOM", self.item_code, "quality_inspection_template")

		self.quality_inspection_template = template
		self.get_item_specification_details()

	def on_submit(self):
		self.update_qc_reference()

	def on_cancel(self):
		self.update_qc_reference()

	def validate_readings_status_mandatory(self):
		for reading in self.readings:
			if not reading.status:
				frappe.throw(_("Row #{0}: Status is mandatory").format(reading.idx))

	def update_qc_reference(self):
		quality_inspection = self.name if self.docstatus == 1 else ""

		if self.reference_type == "Job Card":
			if self.reference_name:
				frappe.db.sql(
					"""
					UPDATE `tab{doctype}`
					SET quality_inspection = %s, modified = %s
					WHERE name = %s and production_item = %s
				""".format(
						doctype=self.reference_type
					),
					(quality_inspection, self.modified, self.reference_name, self.item_code),
				)

		else:
			args = [quality_inspection, self.modified, self.reference_name, self.item_code]
			doctype = self.reference_type + " Item"

			if self.reference_type == "Stock Entry":
				doctype = "Stock Entry Detail"

			if self.reference_type and self.reference_name:
				conditions = ""
				if self.batch_no and self.docstatus == 1:
					conditions += " and t1.batch_no = %s"
					args.append(self.batch_no)

				if self.docstatus == 2:  # if cancel, then remove qi link wherever same name
					conditions += " and t1.quality_inspection = %s"
					args.append(self.name)

				frappe.db.sql(
					"""
					UPDATE
						`tab{child_doc}` t1, `tab{parent_doc}` t2
					SET
						t1.quality_inspection = %s, t2.modified = %s
					WHERE
						t1.parent = %s
						and t1.item_code = %s
						and t1.parent = t2.name
						{conditions}
				""".format(
						parent_doc=self.reference_type, child_doc=doctype, conditions=conditions
					),
					args,
				)

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

	def set_status_based_on_acceptance_values(self, reading):
		if not cint(reading.numeric):
			result = reading.get("reading_value") == reading.get("value")
		else:
			# numeric readings
			result = self.min_max_criteria_passed(reading)

		reading.status = "Accepted" if result else "Rejected"

	def min_max_criteria_passed(self, reading):
		"""Determine whether all readings fall in the acceptable range."""
		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				result = flt(reading.get("min_value")) <= flt(reading_value) <= flt(reading.get("max_value"))
				if not result:
					return False
		return True

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
				_("Row #{0}: {1} is not a valid reading field. Please refer to the field description.").format(
					reading.idx, field
				),
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
				data[field] = flt(reading.get(field))
			data["mean"] = self.calculate_mean(reading)

		return data

	def calculate_mean(self, reading):
		"""Calculate mean of all non-empty readings."""
		from statistics import mean

		readings_list = []

		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				readings_list.append(flt(reading_value))

		actual_mean = mean(readings_list) if readings_list else 0
		return actual_mean


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters):
	from frappe.desk.reportview import get_match_cond

	from_doctype = cstr(filters.get("from"))
	if not from_doctype or not frappe.db.exists("DocType", from_doctype):
		return []

	mcond = get_match_cond(from_doctype)
	cond, qi_condition = "", "and (quality_inspection is null or quality_inspection = '')"

	if filters.get("parent"):
		if (
			from_doctype in ["Purchase Invoice Item", "Purchase Receipt Item"]
			and filters.get("inspection_type") != "In Process"
		):
			cond = """and item_code in (select name from `tabItem` where
				inspection_required_before_purchase = 1)"""
		elif (
			from_doctype in ["Sales Invoice Item", "Delivery Note Item"]
			and filters.get("inspection_type") != "In Process"
		):
			cond = """and item_code in (select name from `tabItem` where
				inspection_required_before_delivery = 1)"""
		elif from_doctype == "Stock Entry Detail":
			cond = """and s_warehouse is null"""

		if from_doctype in ["Supplier Quotation Item"]:
			qi_condition = ""

		return frappe.db.sql(
			"""
				SELECT item_code
				FROM `tab{doc}`
				WHERE parent=%(parent)s and docstatus < 2 and item_code like %(txt)s
				{qi_condition} {cond} {mcond}
				ORDER BY item_code limit {page_len} offset {start}
			""".format(
				doc=from_doctype,
				cond=cond,
				mcond=mcond,
				start=cint(start),
				page_len=cint(page_len),
				qi_condition=qi_condition,
			),
			{"parent": filters.get("parent"), "txt": "%%%s%%" % txt},
		)

	elif filters.get("reference_name"):
		return frappe.db.sql(
			"""
				SELECT production_item
				FROM `tab{doc}`
				WHERE name = %(reference_name)s and docstatus < 2 and production_item like %(txt)s
				{qi_condition} {cond} {mcond}
				ORDER BY production_item
				limit {page_len} offset {start}
			""".format(
				doc=from_doctype,
				cond=cond,
				mcond=mcond,
				start=cint(start),
				page_len=cint(page_len),
				qi_condition=qi_condition,
			),
			{"reference_name": filters.get("reference_name"), "txt": "%%%s%%" % txt},
		)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def quality_inspection_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.get_all(
		"Quality Inspection",
		limit_start=start,
		limit_page_length=page_len,
		filters={
			"docstatus": 1,
			"name": ("like", "%%%s%%" % txt),
			"item_code": filters.get("item_code"),
			"reference_name": ("in", [filters.get("reference_name", ""), ""]),
		},
		as_list=1,
	)


@frappe.whitelist()
def make_quality_inspection(source_name, target_doc=None):
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
