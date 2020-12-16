# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import nowdate
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.controllers.stock_controller import QualityInspectionRejectedError, QualityInspectionRequiredError, QualityInspectionNotSubmittedError

# test_records = frappe.get_test_records('Quality Inspection')

class TestQualityInspection(unittest.TestCase):
	def setUp(self):
		create_item("_Test Item with QA")
		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_delivery", 1)

	def test_qa_for_delivery(self):
		make_stock_entry(item_code="_Test Item with QA", target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)

		self.assertRaises(QualityInspectionRequiredError, dn.submit)

		qa = create_quality_inspection(reference_type="Delivery Note", reference_name=dn.name, status="Rejected")
		dn.reload()
		self.assertRaises(QualityInspectionRejectedError, dn.submit)

		frappe.db.set_value("Quality Inspection Reading", {"parent": qa.name}, "status", "Accepted")
		dn.reload()
		dn.submit()

		qa.cancel()
		dn.reload()
		dn.cancel()

	def test_qa_not_submit(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		qa = create_quality_inspection(reference_type="Delivery Note", reference_name=dn.name, do_not_submit=True)
		dn.items[0].quality_inspection = qa.name
		self.assertRaises(QualityInspectionNotSubmittedError, dn.submit)

		qa.delete()
		dn.delete()

	def test_formula_based_qi_readings(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		readings = [{
			"specification": "Iron Content",
			"acceptance_formula": "reading_1 > 0.35 and reading_1 < 0.50",
			"reading_1": 0.4
		},
		{
			"specification": "Calcium Content",
			"acceptance_formula": "reading_1 > 0.20 and reading_1 < 0.50",
			"reading_1": 0.7
		},
		{
			"specification": "Mg Content",
			"acceptance_formula": "(reading_1 + reading_2 + reading_3) / 3 < 0.9",
			"reading_1": 0.5,
			"reading_2": 0.7,
			"reading_3": "random text" # check if random string input causes issues
		}]

		qa = create_quality_inspection(reference_type="Delivery Note", reference_name=dn.name,
			readings=readings, do_not_save=True)
		qa.save()

		# status must be auto set as per formula
		self.assertEqual(qa.readings[0].status, "Accepted")
		self.assertEqual(qa.readings[1].status, "Rejected")
		self.assertEqual(qa.readings[2].status, "Accepted")

		qa.delete()
		dn.delete()

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

	readings = args.readings or {"specification": "Size", "status": args.status}

	if isinstance(readings, list):
		for entry in readings:
			qa.append("readings", entry)
	else:
		qa.append("readings", readings)

	if not args.do_not_save:
		qa.save()
		if not args.do_not_submit:
			qa.submit()

	return qa
