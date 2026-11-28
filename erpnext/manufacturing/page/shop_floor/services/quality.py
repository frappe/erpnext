import frappe
from frappe import _
from frappe.utils import cint

from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)


def get_quality_inspection_checklist(job_card: str):
	"""Template parameters for the inline quality check an operator fills before submitting a
	job card. Returns the resolved template, its parameter rows, any already-linked inspection,
	and the item being inspected.
	"""
	frappe.has_permission("Job Card", "read", doc=job_card, throw=True)

	jc = frappe.db.get_value(
		"Job Card",
		job_card,
		[
			"quality_inspection",
			"quality_inspection_template",
			"operation",
			"production_item",
			"finished_good",
		],
		as_dict=True,
	)
	if not jc:
		frappe.throw(_("Job Card {0} not found").format(job_card))

	template = jc.quality_inspection_template
	if not template and jc.operation:
		template = frappe.get_cached_value("Operation", jc.operation, "quality_inspection_template")

	parameters = []
	for p in get_template_details(template):
		parameters.append(
			{
				"specification": p.specification,
				"value": p.value,
				"numeric": cint(p.numeric),
				"min_value": p.min_value,
				"max_value": p.max_value,
				"formula_based_criteria": cint(p.formula_based_criteria),
				"acceptance_formula": p.acceptance_formula,
			}
		)

	return {
		"template": template,
		"parameters": parameters,
		"existing": jc.quality_inspection,
		"item_code": jc.finished_good or jc.production_item,
	}


def submit_quality_inspection(job_card: str, readings: str | None = None):
	"""Create + submit an In-Process Quality Inspection for the job card and link it back, so the
	standard Job Card.validate_inspection() gate passes when the card is submitted.

	`readings` is a JSON list of {specification, status, reading_value} captured inline. For numeric
	/ formula parameters the measured value is stored and the Quality Inspection auto-evaluates
	pass/fail against min/max (or the formula); for qualitative parameters the operator's explicit
	Accepted/Rejected is taken as authoritative (manual_inspection). The QI's own validation then
	sets the overall Accepted/Rejected status.
	"""
	frappe.has_permission("Job Card", "write", throw=True)
	frappe.has_permission("Quality Inspection", "submit", throw=True)

	jc = frappe.get_doc("Job Card", job_card)
	jc.check_permission("write")
	if jc.docstatus != 0:
		frappe.throw(_("Quality Inspection can be added only to a draft Job Card"))

	# Idempotent: if a submitted inspection is already linked, don't create another.
	if jc.quality_inspection:
		existing = frappe.db.get_value(
			"Quality Inspection", jc.quality_inspection, ["status", "docstatus"], as_dict=True
		)
		if existing and existing.docstatus == 1:
			return {"name": jc.quality_inspection, "status": existing.status}

	template = jc.quality_inspection_template
	if not template and jc.operation:
		template = frappe.get_cached_value("Operation", jc.operation, "quality_inspection_template")
	if not template:
		frappe.throw(_("No Quality Inspection Template is configured for this operation."))

	reading_map = {r.get("specification"): r for r in (frappe.parse_json(readings) or [])}

	qi = frappe.new_doc("Quality Inspection")
	qi.inspection_type = "In Process"
	qi.reference_type = "Job Card"
	qi.reference_name = job_card
	qi.item_code = jc.finished_good or jc.production_item
	qi.bom_no = jc.bom_no
	qi.quality_inspection_template = template
	qi.sample_size = 1
	qi.inspected_by = frappe.session.user
	qi.get_item_specification_details()  # load readings from the template

	for reading in qi.readings:
		entry = reading_map.get(reading.specification)
		if not entry:
			continue
		value = entry.get("reading_value")
		if reading.numeric or reading.formula_based_criteria:
			# Measured value → let the Quality Inspection judge it against min/max or the formula.
			if value not in (None, ""):
				reading.reading_value = value
				reading.reading_1 = value
		else:
			# Qualitative check → the operator's explicit pass/fail wins.
			reading.manual_inspection = 1
			reading.status = entry.get("status") or "Accepted"
			if value not in (None, ""):
				reading.reading_value = value

	qi.insert()
	qi.submit()  # validate() → inspect_and_set_status() sets the overall Accepted/Rejected status

	# Link explicitly: the QI's own back-reference matches on production_item, which can differ
	# from the operation's finished_good, so we set it directly to be safe.
	jc.db_set("quality_inspection", qi.name)
	return {"name": qi.name, "status": qi.status}
