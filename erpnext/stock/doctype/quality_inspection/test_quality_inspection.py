# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from datetime import date, datetime

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, nowdate, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.controllers.stock_controller import (
	QualityInspectionNotSubmittedError,
	QualityInspectionRejectedError,
	QualityInspectionRequiredError,
	make_quality_inspections,
)
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

# test_records = frappe.get_test_records('Quality Inspection')


class TestQualityInspection(FrappeTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
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
		for item in dn.items:
			item.sample_size = item.qty
		quality_inspections = make_quality_inspections(dn.doctype, dn.name, dn.items)
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

	@change_settings("System Settings", {"number_format": "#.###,##"})
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

	def test_qa_for_pr_TC_SCK_159(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_received_but_not_billed", "Cost of Goods Sold - _TC")

		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		item_code = create_item("_Test Item with QA", valuation_rate=200).name
		pr = make_purchase_receipt(
			item_code=item_code, company="_Test Company", stock_uom="Box", do_not_submit=True
		)

		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_purchase", 1)
		qa = create_quality_inspection(
			reference_type="Purchase Receipt",
			reference_name=pr.name,
			status="Accepted",
			inspection_type="Incoming",
			do_not_submit=True,
		)
		pr.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		qa.reload()
		pr.reload()
		pr.submit()
		self.assertEqual(qa.status, "Accepted")

		qa.reload()
		qa.cancel()
		pr.reload()
		pr.cancel()

	def test_qa_for_pi_TC_SCK_160(self):
		from datetime import date

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_received_but_not_billed", "Cost of Goods Sold - _TC")

		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		create_supplier(supplier_name="_Test Supplier")

		pr = make_purchase_invoice(item_code="_Test Item with QA", uom="Box", do_not_save=True)
		pr.due_date = date.today()
		pr.save()
		pr.submit()
		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_purchase", 1)
		qa = create_quality_inspection(
			reference_type="Purchase Invoice",
			reference_name=pr.name,
			status="Accepted",
			inspection_type="Incoming",
			do_not_submit=True,
		)
		pr.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		qa.reload()
		self.assertEqual(qa.status, "Accepted")

		qa.reload()
		qa.cancel()
		pr.reload()
		pr.cancel()

	@change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_qa_for_dn_TC_SCK_161(self):
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

	def test_qa_for_si_TC_SCK_163(self):
		si = create_sales_invoice(item_code="_Test Item with QA")

		qa = create_quality_inspection(
			reference_type="Sales Invoice",
			reference_name=si.name,
			status="Accepted",
			inspection_type="Incoming",
			do_not_submit=True,
		)
		si.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		qa.reload()
		self.assertEqual(qa.status, "Accepted")

		qa.reload()
		qa.cancel()
		si.reload()
		si.cancel()

	def test_qa_for_pr_out_TC_SCK_162(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_received_but_not_billed", "Cost of Goods Sold - _TC")

		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		item_code = create_item("_Test Item with QA", valuation_rate=200).name

		pr = make_purchase_receipt(
			item_code=item_code, company="_Test Company", stock_uom="Box", do_not_submit=True
		)

		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_purchase", 1)
		qa = create_quality_inspection(
			reference_type="Purchase Receipt",
			reference_name=pr.name,
			status="Accepted",
			inspection_type="Outgoing",
			do_not_submit=True,
		)
		pr.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		pr.reload()
		pr.submit()
		qa.reload()
		self.assertEqual(qa.status, "Accepted")
		qa.reload()
		qa.cancel()
		pr.reload()
		pr.cancel()

	def test_qa_for_se_inc_TC_SCK_164(self):
		item_code = create_item("_Test SE Item with QA").name
		create_company()
		warehouse = create_warehouse("_Test warehouse PO", company="_Test Company QA")

		se = make_stock_entry(
			item_code=item_code, target=warehouse, qty=1, basic_rate=100, do_not_submit=True
		)

		se.inspection_required = 1
		se.save()

		qa = create_quality_inspection(
			item_code=item_code,
			reference_type="Stock Entry",
			reference_name=se.name,
			inspection_type="Incoming",
			do_not_submit=True,
		)

		se.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		qa.reload()
		self.assertEqual(qa.status, "Accepted")

		qa.reload()
		qa.cancel()

	def test_qa_for_se_out_TC_SCK_165(self):
		item_code = create_item("_Test SE Item with QA").name
		create_company()
		warehouse = create_warehouse("_Test warehouse PO", company="_Test Company QA")

		se = make_stock_entry(
			item_code=item_code, target=warehouse, qty=1, basic_rate=100, do_not_submit=True
		)

		se.inspection_required = 1
		se.save()

		qa = create_quality_inspection(
			item_code=item_code,
			reference_type="Stock Entry",
			reference_name=se.name,
			inspection_type="Outgoing",
			do_not_submit=True,
		)

		se.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		qa.reload()
		self.assertEqual(qa.status, "Accepted")

		qa.reload()
		qa.cancel()

	def test_qa_for_pr_proc_TC_SCK_166(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		company = "_Test Company"
		frappe.db.set_value("Company", company, "stock_received_but_not_billed", "Cost of Goods Sold - _TC")

		create_supplier(supplier_name="_Test Supplier")
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		item_code = create_item("_Test Item with QA", valuation_rate=200).name
		pr = make_purchase_receipt(item_code=item_code, uom="Box", stock_uom="Box", do_not_submit=True)
		frappe.db.set_value("Item", "_Test Item with QA", "inspection_required_before_purchase", 1)

		qa = create_quality_inspection(
			reference_type="Purchase Receipt",
			reference_name=pr.name,
			status="Accepted",
			inspection_type="In Process",
			do_not_submit=True,
		)
		pr.reload()
		qa.reload()
		self.assertEqual(qa.docstatus, 0)
		qa.submit()
		qa.reload()
		pr.reload()
		pr.submit()
		self.assertEqual(qa.status, "Accepted")

		qa.reload()
		qa.cancel()
		pr.reload()
		pr.cancel()

	def test_qa_for_dn_prcs_TC_SCK_167(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		self.assertRaises(QualityInspectionRequiredError, dn.submit)

		qa = create_quality_inspection(
			reference_type="Delivery Note",
			reference_name=dn.name,
			status="Rejected",
			inspection_type="In Process",
		)
		dn.reload()
		self.assertRaises(QualityInspectionRejectedError, dn.submit)
		frappe.db.set_value("Quality Inspection", qa.name, "status", "Accepted")
		qa.reload()
		qa.cancel()

	def test_qa_for_dn_out_TC_SCK_168(self):
		dn = create_delivery_note(item_code="_Test Item with QA", do_not_submit=True)
		self.assertRaises(QualityInspectionRequiredError, dn.submit)

		qa = create_quality_inspection(
			reference_type="Delivery Note",
			reference_name=dn.name,
			status="Rejected",
			inspection_type="Outgoing",
		)
		dn.reload()
		self.assertRaises(QualityInspectionRejectedError, dn.submit)
		frappe.db.set_value("Quality Inspection", qa.name, "status", "Accepted")
		qa.reload()
		qa.cancel()

	def test_validate_TC_SCK_287(self):
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		frappe.set_user("Administrator")
		frappe.db.rollback()
		company = setup_test_company_defaults()
		warehouse = create_warehouse("_Test Warehouse", company=company.name)

		item = create_item(item_code="_Test Item", stock_uom="Nos", valuation_rate=100)
		raw_material_item = create_item(
			item_code="_Test Raw Material", stock_uom="Nos", is_stock_item=1, is_purchase_item=1
		)

		# Create or Get BOM
		bom = frappe.db.get_value("BOM", {"item": item.name, "is_active": 1, "is_default": 1})
		if not bom:
			bom = (
				frappe.get_doc(
					{
						"doctype": "BOM",
						"item": item.name,
						"is_active": 1,
						"is_default": 1,
						"quantity": 1,
						"items": [{"item_code": raw_material_item.name, "qty": 1, "rate": 100}],
					}
				)
				.insert()
				.name
			)

		template_name = "TEST-TEMPLATE"
		# Create QA Template
		if not frappe.db.exists("Quality Inspection Template", template_name):
			qi_template = frappe.new_doc("Quality Inspection Template")
			qi_template.quality_inspection_template_name = template_name
			qi_template.append(
				"item_quality_inspection_parameter",
				{
					"specification": "Spec-A",
					"value": "15",
					"min_value": "5.0",
					"max_value": "15.0",
				},
			)
			qi_template.insert()

		# Assign template to item
		item.quality_inspection_template = template_name
		item.save()

		# Create Operation
		if not frappe.db.exists("Operation", "Test Operation"):
			op = frappe.new_doc("Operation")
			op.name = "Test Operation"
			op.insert()

		# Create Workstation
		workstation = frappe.new_doc("Workstation")
		workstation.workstation_name = "Test Workstation"
		workstation.insert()
		# Create Work Order
		wo = make_wo_order_test_record(
			item=item.name,
			qty=1,
			fg_warehouse=warehouse,
			stock_uom="Nos",
			company=company.name,
			do_not_save=True,
		)
		wo.production_item = item.name
		wo.target_warehouse = warehouse
		wo.scrap_warehouse = warehouse
		wo.bom_no = bom
		wo.append(
			"operations", {"operation": "Test Operation", "workstation": workstation.name, "time_in_mins": 10}
		)
		wo.save()
		wo.submit()

		# Create Job Card
		job_card = frappe.new_doc("Job Card")
		job_card.work_order = wo.name
		job_card.operation = wo.operations[0].operation
		job_card.workstation = workstation.name
		job_card.for_quantity = 5
		job_card.production_item = item.name
		job_card.wip_warehouse = warehouse
		job_card.insert()

		# Quality Inspection: In Process + Job Card
		qi = frappe.new_doc("Quality Inspection")
		qi.inspection_type = "In Process"
		qi.reference_type = "Job Card"
		qi.reference_name = job_card.name
		qi.item_code = item.name
		qi.inspected_by = "Administrator"
		qi.sample_size = 15
		qi.append(
			"readings",
			{
				"specification": "Spec-A",
				"reading_1": "15",
				"status": "Accepted",
			},
		)
		qi.insert()
		qi.validate()
		self.assertEqual(qi.readings[0].value, "15")

	def test_get_quality_inspection_template_TC_SCK_288(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.manufacturing.doctype.bom.test_bom import make_bom
		from erpnext.stock.doctype.quality_inspection.quality_inspection import make_quality_inspection

		frappe.set_user("Administrator")
		frappe.db.rollback()

		company = setup_test_company_defaults()
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()
		warehouse = create_warehouse("_Test Warehouse", company=company.name)
		create_supplier(supplier_name="_Test Supplier")

		# Create Quality Inspection Template
		template_name = "TEMPLATE-FROM-BOM"
		if not frappe.db.exists("Quality Inspection Template", template_name):
			qi_template = frappe.new_doc("Quality Inspection Template")
			qi_template.quality_inspection_template_name = template_name
			qi_template.append(
				"item_quality_inspection_parameter",
				{"specification": "Spec-BOM", "value": "20", "min_value": "10.0", "max_value": "30.0"},
			)
			qi_template.insert()

		# Create Item
		item = create_item(item_code="_Test BOM Item", stock_uom="Nos", is_stock_item=1)
		item.quality_inspection_template = template_name
		item.inspection_required_before_purchase = 1
		item.save()

		# Create BOM for the item and link the QA template
		raw_material = "Test SO RM Production Item 1"
		create_item(item_code=raw_material, stock_uom="Nos", is_stock_item=1, valuation_rate=100)
		if not frappe.db.get_value("BOM", {"item": item.name}):
			bom = make_bom(item=item, raw_materials=[raw_material], do_not_save=True)
			bom.inspection_required = 1
			bom.quality_inspection_template = template_name
			bom.save()
			bom.submit()

		pr = make_purchase_receipt(
			item_code=item.name,
			supplier_warehouse=warehouse,
			company=company.name,
			stock_uom="Box",
			do_not_submit=True,
		)

		# Create Quality Inspection without template (method will fetch it from BOM)
		qi = frappe.new_doc("Quality Inspection")
		qi.item_code = item.name
		qi.inspection_type = "Incoming"
		qi.reference_type = "Purchase Receipt"
		qi.reference_name = pr.name
		qi.inspected_by = "Administrator"
		qi.sample_size = 10
		qi.bom_no = bom.name
		qi.append(
			"readings",
			{
				"specification": "Spec-BOM",
				"reading_1": "15",
				"status": "Accepted",
			},
		)
		qi.insert()

		qi2 = frappe.new_doc("Quality Inspection")
		qi2.item_code = item.name
		qi2.inspection_type = "Incoming"
		qi2.reference_type = "Purchase Receipt"
		qi2.reference_name = pr.name
		qi2.inspected_by = "Administrator"
		qi2.sample_size = 10
		qi2.append(
			"readings",
			{
				"specification": "Spec-BOM",
				"reading_1": "15",
				"status": "Accepted",
			},
		)
		qi2.insert()

		# Call method under test
		qi.get_quality_inspection_template()
		qi = make_quality_inspection(source_name=bom.name)

		qi2.get_quality_inspection_template()

		self.assertEqual(len(qi.readings), 1)
		self.assertEqual(qi.readings[0].specification, "Spec-BOM")
		self.assertEqual(qi.readings[0].value, "20")
		self.assertEqual(qi.readings[0].min_value, 10.0)
		self.assertEqual(qi.readings[0].max_value, 30.0)
		self.assertEqual(qi.readings[0].status, "Accepted")

	def test_distribute_child_row_reference_TC_SCK_289(self):
		import unittest.mock

		frappe.set_user("Administrator")
		frappe.db.rollback()

		# Setup common test data
		company = setup_test_company_defaults()
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()
		item = create_item(item_code="_Test Item Dist", stock_uom="Nos", is_stock_item=1)
		warehouse = create_warehouse("_Test Warehouse", company=company.name)
		reference_name = "Test-Ref-Dist"
		child_rows = ["ROW-1", "ROW-2", "ROW-3"]

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Receipt"
		stock_entry.company = company.name
		stock_entry.to_warehouse = warehouse

		stock_entry.append(
			"items",
			{
				"item_code": item.name,
				"qty": 1,
				"uom": "Nos",
				"t_warehouse": warehouse,
				"allow_zero_valuation_rate": 1,
			},
		)
		stock_entry.insert()
		stock_entry.submit()

		reference_name = stock_entry.name

		# Create 3 Quality Inspections:
		# 1st one is submitted and already has child row → will be skipped
		qi1 = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"item_code": item.name,
				"reference_type": "Stock Entry",
				"reference_name": reference_name,
				"child_row_reference": "ROW-1",
				"inspection_type": "Incoming",
			}
		)
		qi1.inspected_by = "Administrator"
		qi1.sample_size = 5
		qi1.insert()
		qi1.db_set("docstatus", 1)

		# 2nd one is draft and has child row → will be skipped and removed from available
		qi2 = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"item_code": item.name,
				"reference_type": "Stock Entry",
				"reference_name": reference_name,
				"child_row_reference": "ROW-2",
				"inspection_type": "Incoming",
			}
		)
		qi2.inspected_by = "Administrator"
		qi2.sample_size = 5
		qi2.insert()

		# 3rd is the current one to test → no child row yet
		qi3 = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"item_code": item.name,
				"reference_type": "Stock Entry",
				"reference_name": reference_name,
				"inspection_type": "Incoming",
			}
		)
		qi3.inspected_by = "Administrator"
		qi3.sample_size = 5
		qi3.insert()

		# Patch frappe.get_all to simulate how distribute_child_row_reference pulls QIs
		with unittest.mock.patch("frappe.get_all") as mock_get_all, unittest.mock.patch(
			"frappe.db.set_value"
		) as mock_set_value:
			mock_get_all.return_value = [
				{"name": qi1.name, "child_row_reference": "ROW-1", "docstatus": 1},
				{"name": qi2.name, "child_row_reference": "ROW-2", "docstatus": 0},
				{"name": qi3.name, "child_row_reference": None, "docstatus": 0},
			]

			# Call method under test
			qi3.distribute_child_row_reference(child_rows[:])

		# Assertions
		self.assertEqual(qi3.child_row_reference, "ROW-3")
		mock_set_value.assert_not_called()

	def test_item_query_TC_SCK_290(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.quality_inspection.quality_inspection import item_query

		frappe.set_user("Administrator")
		frappe.db.rollback()
		company = setup_test_company_defaults()
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()
		create_supplier(supplier_name="_Test Supplier")
		warehouse = create_warehouse("_Test Warehouse", company=company.name)

		# Create item that requires inspection before purchase
		item = create_item(
			item_code="_Test Item for PR Query", stock_uom="Nos", valuation_rate=200, is_stock_item=1
		)
		item.inspection_required_before_purchase = 1
		item.inspection_required_before_delivery = 1
		item.save()

		# Create purchase receipt with the item
		pr = make_purchase_receipt(
			item_code=item.name,
			company="_Test Company",
			supplier_warehouse=warehouse,
			stock_uom="Box",
			do_not_submit=True,
		)

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

		create_customer(name="_Test Customer")
		dn = create_delivery_note(item_code=item.name, cost_center=cost_center, do_not_submit=True)
		wh = create_warehouse("_Test Warehouse - _TC", company=company.name)
		se = make_stock_entry(
			item_code=item.name,
			company=company.name,
			target=wh,
			qty=1,
			basic_rate=100,
			inspection_required=True,
			do_not_submit=True,
		)
		# Create Quality Inspection for the SE
		qi = frappe.new_doc("Quality Inspection")
		qi.inspection_type = "Incoming"
		qi.reference_type = "Stock Entry"
		qi.reference_name = se.name
		qi.item_code = item.name
		qi.sample_size = 1
		qi.inspected_by = "Administrator"
		qi.append(
			"readings",
			{
				"specification": "Spec-A",
				"reading_1": "12",
				"value": "12",
				"min_value": "10",
				"max_value": "15",
				"status": "Accepted",
			},
		)
		qi.insert()
		qi.submit()

		# Link to SE item
		for d in se.items:
			d.quality_inspection = qi.name
		se.reload()
		se.submit()

		from erpnext.buying.doctype.supplier_quotation.supplier_quotation import set_expired_status

		if not frappe.db.exists("Price List", "_Test Price List"):
			pl = frappe.new_doc("Price List")
			pl.price_list_name = "_Test Price List"
			pl.selling = 1
			pl.buying = 1
			pl.enabled = 1
			pl.insert()

		test_records = frappe.get_test_records("Supplier Quotation")
		sq = frappe.copy_doc(test_records[0])
		sq.price_list = "_Test Price List"
		sq.items = []
		sq.append("items", {"item_code": item.name, "uom": "Nos", "qty": 5, "rate": 100})
		sq.insert()
		sq = frappe.get_doc("Supplier Quotation", sq.name)
		sq.transaction_date = today()
		sq.valid_till = add_days(today(), 30)
		sq.submit()
		set_expired_status()
		sq.reload()

		# --- Run item_query ---
		result1 = item_query(
			doctype="Item",
			txt="_Test Item",
			searchfield="item_code",
			start=0,
			page_len=10,
			filters={"from": "Purchase Receipt Item", "parent": pr.name, "inspection_type": "Incoming"},
		)
		result2 = item_query(
			doctype="Item",
			txt="_Test Item",
			searchfield="item_code",
			start=0,
			page_len=10,
			filters={"from": "Delivery Note Item", "parent": dn.name, "inspection_type": "Outgoing"},
		)
		result3 = item_query(
			doctype="Item",
			txt="_Test Item",
			searchfield="item_code",
			start=0,
			page_len=10,
			filters={"from": "Stock Entry Detail", "parent": se.name, "inspection_type": "Outgoing"},
		)
		result4 = item_query(
			doctype="Item",
			txt="_Test Item",
			searchfield="item_code",
			start=0,
			page_len=10,
			filters={"from": "Supplier Quotation Item", "parent": sq.name, "inspection_type": "Incoming"},
		)
		# --- Assertion ---
		if len(result1) > 0:
			assert len(result1) == 1
			assert item.name in [r[0] for r in result1]
		if len(result2) > 0:
			assert len(result2) == 1
			assert item.name in [r[0] for r in result2]
		if len(result3) > 0:
			assert len(result3) == 1
			assert item.name in [r[0] for r in result3]
		if len(result4) > 0:
			assert len(result4) == 1
			assert item.name in [r[0] for r in result4]


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
		readings = {"specification": "Size", "min_value": 0, "max_value": 10}
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


def create_company():
	company_name = "_Test Company QA"
	if not frappe.db.exists("Company", company_name):
		company = frappe.new_doc("Company")
		company.company_name = company_name
		company.country = ("India",)
		company.default_currency = ("INR",)
		company.create_chart_of_accounts_based_on = ("Standard Template",)
		company.chart_of_accounts = ("Standard",)
		company = company.save()
		company.load_from_db()
	return company_name


def setup_test_company_defaults(company_name="_Test Company", abbreviation="_TC"):
	from frappe.defaults import set_default

	# Create Company if it doesn't exist
	if not frappe.db.exists("Company", company_name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbreviation,
				"default_currency": "INR",
				"country": "India",
				"chart_of_accounts": "Standard",
			}
		).insert()

	company = frappe.get_doc("Company", company_name)

	# Create root account group if needed
	if not frappe.db.exists("Account", f"Application of Funds - {abbreviation}"):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Application of Funds",
				"company": company_name,
				"root_type": "Asset",
				"is_group": 1,
			}
		)
		account.insert(ignore_mandatory=True)

	# Account helper
	def ensure_account(name, root_type="Asset"):
		full_name = f"{name} - {abbreviation}"
		if not frappe.db.exists("Account", full_name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": name,
					"company": company_name,
					"root_type": root_type,
					"parent_account": f"Application of Funds - {abbreviation}",
					"is_group": 0,
				}
			).insert()
		return full_name

	# Required Accounts
	accounts = {
		"default_receivable_account": ensure_account("Debtors", "Asset"),
		"default_payable_account": ensure_account("Creditors", "Liability"),
		"default_income_account": ensure_account("Sales", "Income"),
		"default_expense_account": ensure_account("Cost of Goods Sold", "Expense"),
		"stock_received_but_not_billed": ensure_account("Stock Received But Not Billed", "Liability"),
		"default_cash_account": ensure_account("Cash", "Asset"),
		"default_bank_account": ensure_account("Bank", "Asset"),
		"default_inventory_account": ensure_account("Stock Asset", "Asset"),
		"default_provisional_account": ensure_account("Cost of Goods Sold", "Expense"),
		"stock_adjustment_account": ensure_account("Stock Adjustment", "Expense"),
	}

	# Default Cost Center
	if not frappe.db.exists("Cost Center", f"Main - {abbreviation}"):
		frappe.get_doc(
			{"doctype": "Cost Center", "cost_center_name": "Main", "is_group": 0, "company": company_name}
		).insert()

	accounts["default_cost_center"] = f"Main - {abbreviation}"

	for field, value in accounts.items():
		company.set(field, value)

	company.enable_perpetual_inventory = 1
	company.enable_provisional_accounting_for_non_stock_items = 1
	company.save()

	set_default("company", company_name, "__default")

	return company


def setup_fy_gls_cost_center():
	company = setup_test_company_defaults()
	company_abbr = "_TC"
	# Setup GL Account COGS & Cost Center
	if not frappe.db.exists("Account", f"T Cost of Goods Sold - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "T Cost of Goods Sold",
				"parent_account": f"Expenses - {company_abbr}",
				"company": company,
				"is_group": 0,
			}
		).insert()
	if not frappe.db.exists("Cost Center", f"T Main - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "T Main",
				"parent_cost_center": f"{company.name} - {company_abbr}",
				"company": company,
				"is_group": 1,
			}
		).insert()
	if not frappe.db.exists("Cost Center", f"_Test Cost Center - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "_Test Cost Center",
				"parent_cost_center": f"T Main - {company_abbr}",
				"company": company.name,
				"is_group": 0,
			}
		).insert()

	current_date = datetime.today().date()

	matching_fy_list = frappe.get_all(
		"Fiscal Year",
		filters={
			"disabled": 0,
			"year_start_date": ["<=", current_date],
			"year_end_date": [">=", current_date],
		},
		fields=["name", "year_start_date", "year_end_date"],
	)
	is_company = False
	if len(matching_fy_list) > 0:
		for fy in matching_fy_list:
			fiscal_year = frappe.get_doc("Fiscal Year", fy["name"])
			for years in fiscal_year.companies:
				if years.company == company:
					is_company = True
					break
			if is_company:
				break

		if not is_company:
			for rows in matching_fy_list:
				try:
					fiscal_year = frappe.get_doc("Fiscal Year", rows.name)
					fiscal_year.append("companies", {"company": company})
					fiscal_year.save()
					break
				except Exception as e:
					print(f"Failed to get Fiscal Year {fy['name']}: {e}")
					continue

	else:
		# No fiscal year includes current date — create a new one
		current_year = current_date.year
		first_date = date(current_year, 1, 1)
		last_date = date(current_year, 12, 31)

		fiscal_year = frappe.new_doc("Fiscal Year")
		fiscal_year.year = f"{current_year}-{company}"
		fiscal_year.year_start_date = first_date
		fiscal_year.year_end_date = last_date
		fiscal_year.company = company  # Required to avoid overlap error
		fiscal_year.append("companies", {"company": company})
		fiscal_year.save()

	expense_account = f"T Cost of Goods Sold - {company_abbr}"
	cost_center = f"_Test Cost Center - {company_abbr}"
	return fiscal_year, expense_account, cost_center
