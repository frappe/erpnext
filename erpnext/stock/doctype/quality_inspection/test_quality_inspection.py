# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.controllers.stock_controller import (
	QualityInspectionNotSubmittedError,
	QualityInspectionRejectedError,
	QualityInspectionRequiredError,
	make_quality_inspections,
)
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityInspection(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		create_item("_Test Item with QA")
		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_delivery", 1)

	def test_qa_for_delivery(self):
		make_stock_entry(
			item_code="_Test Item with QA", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)

		self.assertRaises(QualityInspectionRequiredError, dn.submit)

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, status="Rejected"
		)
		dn.reload()
		self.assertRaises(QualityInspectionRejectedError, dn.submit)

		frappe.db.set_value("Quality Inspection", qa.name, "status", "Accepted")
		dn.reload()
		dn.submit()

		qa.reload()
		qa.cancel()
		dn.reload()
		dn.cancel()

	def test_qa_not_submit(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, do_not_submit=True
		)
		dn.items[0].quality_inspection = qa.name
		self.assertRaises(QualityInspectionNotSubmittedError, dn.submit)

		qa.delete()
		dn.delete()

	def test_value_based_qi_readings(self):
		# Test QI based on acceptance values (Non formula)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [
			{
				"specification": "Iron Content",  # numeric reading
				"min_value": 0.1,
				"max_value": 0.9,
				"reading_1": "0.4",
			},
			{
				"specification": "Particle Inspection Needed",  # non-numeric reading
				"numeric": 0,
				"value": "Yes",
				"reading_value": "Yes",
			},
		]

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, readings=readings, do_not_save=True
		)

		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Accepted")

		qa.delete()
		dn.delete()

	def test_formula_based_qi_readings(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [
			{
				"specification": "Iron Content",  # numeric reading
				"formula_based_criteria": 1,
				"acceptance_formula": "reading_1 > 0.35 and reading_1 < 0.50",
				"reading_1": "0.4",
			},
			{
				"specification": "Calcium Content",  # numeric reading
				"formula_based_criteria": 1,
				"acceptance_formula": "reading_1 > 0.20 and reading_1 < 0.50",
				"reading_1": "0.7",
			},
			{
				"specification": "Mg Content",  # numeric reading
				"formula_based_criteria": 1,
				"acceptance_formula": "mean < 0.9",
				"reading_1": "0.5",
				"reading_2": "0.7",
				"reading_3": "random text",  # check if random string input causes issues
			},
			{
				"specification": "Calcium Content",  # non-numeric reading
				"formula_based_criteria": 1,
				"numeric": 0,
				"acceptance_formula": "reading_value in ('Grade A', 'Grade B', 'Grade C')",
				"reading_value": "Grade B",
			},
		]

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, readings=readings, do_not_save=True
		)

		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Rejected")
		self.assertEqual(qa.readings[2].status, "Accepted")
		self.assertEqual(qa.readings[3].status, "Accepted")

		qa.delete()
		dn.delete()

	def test_make_quality_inspections_from_linked_document(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		if dn.doctype in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
			inspection_type = "Incoming"
		else:
			inspection_type = "Outgoing"
		for item in dn.items:
			item.sample_size = item.qty
		quality_inspections = make_quality_inspections(
			dn.company, dn.doctype, dn.name, dn.items, inspection_type
		)
		self.assertEqual(len(dn.items), len(quality_inspections))

		# cleanup
		for qi in quality_inspections:
			frappe.delete_doc("Quality Inspection", qi)
		dn.delete()

	def test_rejected_qi_validation(self):
		"""Test if rejected QI blocks Stock Entry as per Stock Settings."""
		se = make_stock_entry(
			item_code="_Test Item with QA",
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=100,
			inspection_required=True,
			do_not_submit=True,
		)

		readings = [{"specification": "Iron Content", "min_value": 0.1, "max_value": 0.9, "reading_1": "1.0"}]

		qa = create_quality_inspection(
			reference_type="Stock Entry", reference_name=se.name, readings=readings, status="Rejected"
		)

		frappe.db.set_single_value("Stock Settings", "action_if_quality_inspection_is_rejected", "Stop")
		se.reload()
		self.assertRaises(
			QualityInspectionRejectedError, se.submit
		)  # when blocked in Stock settings, block rejected QI

		frappe.db.set_single_value("Stock Settings", "action_if_quality_inspection_is_rejected", "Warn")
		se.reload()
		se.submit()  # when allowed in Stock settings, allow rejected QI

		# teardown
		qa.reload()
		qa.cancel()
		se.reload()
		se.cancel()
		frappe.db.set_single_value("Stock Settings", "action_if_quality_inspection_is_rejected", "Stop")

	def test_qi_status(self):
		make_stock_entry(
			item_code="_Test Item with QA", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, status="Accepted", do_not_save=True
		)
		qa.readings[0].manual_inspection = 1
		qa.save()

		# Case - 1: When there are one or more readings with rejected status and parent manual inspection is unchecked, then parent status should be set to rejected.
		qa.status = "Accepted"
		qa.manual_inspection = 0
		qa.readings[0].status = "Rejected"
		qa.save()
		self.assertEqual(qa.status, "Rejected")

		# Case - 2: When all readings have accepted status and parent manual inspection is unchecked, then parent status should be set to accepted.
		qa.status = "Rejected"
		qa.manual_inspection = 0
		qa.readings[0].status = "Accepted"
		qa.save()
		self.assertEqual(qa.status, "Accepted")

		# Case - 3: When parent manual inspection is checked, then parent status should not be changed.
		qa.status = "Accepted"
		qa.manual_inspection = 1
		qa.readings[0].status = "Rejected"
		qa.save()
		self.assertEqual(qa.status, "Accepted")

	@ERPNextTestSuite.change_settings("System Settings", {"number_format": "#.###,##"})
	def test_diff_number_format(self):
		self.assertEqual(frappe.db.get_default("number_format"), "#.###,##")  # sanity check

		# Test QI based on acceptance values (Non formula)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [
			{
				"specification": "Iron Content",  # numeric reading
				"min_value": 60,
				"max_value": 100,
				"reading_1": "70,000",
			},
			{
				"specification": "Iron Content",  # numeric reading
				"min_value": 60,
				"max_value": 100,
				"reading_1": "1.100,00",
			},
		]

		qa = create_quality_inspection(
			reference_type="Delivery Note", reference_name=dn.name, readings=readings, do_not_save=True
		)

		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Rejected")

		qa.delete()
		dn.delete()

	def test_delete_quality_inspection_linked_with_stock_entry(self):
		item_code = create_item("_Test Cicuular Dependecy Item with QA").name

		se = make_stock_entry(
			item_code=item_code, target="_Test Warehouse - _TC", qty=1, basic_rate=100, do_not_submit=True
		)

		se.inspection_required = 1
		se.save()

		qa = create_quality_inspection(
			item_code=item_code, reference_type="Stock Entry", reference_name=se.name, do_not_submit=True
		)

		se.reload()
		se.items[0].quality_inspection = qa.name
		se.save()

		qa.delete()

		se.reload()

		qc = se.items[0].quality_inspection
		self.assertFalse(qc)

		se.delete()

	def test_qi_updates_job_card_reference(self):
		"""Submitting a QI with reference_type 'Job Card' writes its name onto the
		Job Card's quality_inspection field (the Job Card branch of
		QualityInspection.update_qc_reference)."""
		create_item("_Test Item")

		# Job Card whose production_item matches the QI item_code -> must be updated.
		matching_jc = make_minimal_job_card(production_item="_Test Item")
		# Job Card with a different production_item -> the production_item filter must
		# keep it untouched.
		other_item = create_item("_Test Item for QC " + frappe.utils.random_string(6)).name
		non_matching_jc = make_minimal_job_card(production_item=other_item)

		qa = create_quality_inspection(
			item_code="_Test Item",
			reference_type="Job Card",
			reference_name=matching_jc,
		)

		# The converted UPDATE wrote the QI name onto the matching Job Card.
		self.assertEqual(
			frappe.db.get_value("Job Card", matching_jc, "quality_inspection"),
			qa.name,
		)
		# The production_item filter excluded the Job Card with a different item.
		self.assertFalse(frappe.db.get_value("Job Card", non_matching_jc, "quality_inspection"))

	def test_qi_job_card_reference_respects_production_item(self):
		"""A QI referencing a Job Card by name but whose item_code does not match the
		Job Card's production_item must NOT update that Job Card."""
		create_item("_Test Item")
		mismatch_item = create_item("_Test Item Mismatch QC " + frappe.utils.random_string(6)).name

		# Job Card produces a different item than the QI's item_code.
		jc = make_minimal_job_card(production_item=mismatch_item)

		create_quality_inspection(
			item_code="_Test Item",
			reference_type="Job Card",
			reference_name=jc,
		)

		# name matches but production_item != item_code, so the row is left untouched.
		self.assertFalse(frappe.db.get_value("Job Card", jc, "quality_inspection"))


def make_minimal_job_card(production_item):
	"""db_insert a minimal submitted Job Card row carrying only the columns the
	converted UPDATE reads (name, production_item, quality_inspection, modified)."""
	jc = frappe.new_doc("Job Card")
	jc.name = "_T-Job Card-" + frappe.utils.random_string(10)
	jc.flags.name_set = True
	jc.production_item = production_item
	jc.company = "_Test Company"
	jc.for_quantity = 1
	jc.docstatus = 1
	jc.db_insert()
	return jc.name


def create_quality_inspection(**args):
	args = frappe._dict(args)
	qa = frappe.new_doc("Quality Inspection")
	qa.report_date = nowdate()
	qa.inspection_type = args.inspection_type or "Outgoing"
	qa.reference_type = args.reference_type
	qa.reference_name = args.reference_name
	qa.item_code = args.item_code or "_Test Item with QA"
	qa.sample_size = 1
	qa.inspected_by = frappe.session.user
	qa.status = args.status or "Accepted"

	if not args.readings:
		create_quality_inspection_parameter("Size")
		readings = {"specification": "Size", "min_value": 0, "max_value": 10, "reading_1": "5"}
		if args.status == "Rejected":
			readings["reading_1"] = "12"  # status is auto set in child on save
	else:
		readings = args.readings

	if isinstance(readings, list):
		for entry in readings:
			create_quality_inspection_parameter(entry["specification"])
			qa.append("readings", entry)
	else:
		qa.append("readings", readings)

	if not args.do_not_save:
		qa.save()
		if not args.do_not_submit:
			qa.submit()

	return qa


def create_quality_inspection_parameter(parameter):
	if not frappe.db.exists("Quality Inspection Parameter", parameter):
		frappe.get_doc(
			{"doctype": "Quality Inspection Parameter", "parameter": parameter, "description": parameter}
		).insert()
