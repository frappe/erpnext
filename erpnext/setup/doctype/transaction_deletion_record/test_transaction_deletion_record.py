# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTransactionDeletionRecord(FrappeTestCase):
	def setUp(self):
		create_company("Dunder Mifflin Paper Co")

	def tearDown(self):
		frappe.db.rollback()

	def test_doctypes_contain_company_field(self):
		tdr = create_transaction_deletion_doc("Dunder Mifflin Paper Co")
		for doctype in tdr.doctypes:
			contains_company = False
			doctype_fields = frappe.get_meta(doctype.doctype_name).as_dict()["fields"]
			for doctype_field in doctype_fields:
				if doctype_field["fieldtype"] == "Link" and doctype_field["options"] == "Company":
					contains_company = True
					break
			self.assertTrue(contains_company)

	def test_no_of_docs_is_correct(self):
		for _i in range(5):
			create_task("Dunder Mifflin Paper Co")
		tdr = create_transaction_deletion_doc("Dunder Mifflin Paper Co")
		tdr.reload()
		for doctype in tdr.doctypes:
			if doctype.doctype_name == "Task":
				self.assertEqual(doctype.no_of_docs, 5)

	def test_deletion_is_successful(self):
		create_task("Dunder Mifflin Paper Co")
		create_transaction_deletion_doc("Dunder Mifflin Paper Co")
		tasks_containing_company = frappe.get_all("Task", filters={"company": "Dunder Mifflin Paper Co"})
		self.assertEqual(tasks_containing_company, [])

	def test_company_transaction_deletion_request(self):
		from erpnext.setup.doctype.company.company import create_transaction_deletion_request

		# don't reuse below company for other test cases
		company = "Deep Space Exploration"
		create_company(company)

		# below call should not raise any exceptions or throw errors
		create_transaction_deletion_request(company)

	def test_only_the_owning_company_field_is_used(self):
		tdr = frappe.new_doc("Transaction Deletion Record")
		fields = tdr.get_doctypes_with_company_field(tdr.get_doctypes_to_be_ignored_list())
		self.assertTrue(fields)
		self.assertEqual({row.fieldname for row in fields}, {"company"})
		self.assertEqual([row.parent for row in fields].count("Sales Invoice"), 1)
		# Shipment has only pickup and delivery company links, so its owner is ambiguous.
		self.assertNotIn("Shipment", {row.parent for row in fields})

	def test_intercompany_invoice_children_and_ledgers_survive(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.stock.doctype.item.test_item import make_item

		customer_group, territory = frappe.get_cached_value(
			"Customer", "_Test Customer", ["customer_group", "territory"]
		)
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Transaction deletion internal customer",
				"customer_group": customer_group,
				"territory": territory,
				"is_internal_customer": 1,
				"represents_company": "_Test Company 7",
				"companies": [{"company": "_Test Company"}],
			}
		).insert()
		item = make_item(properties={"is_stock_item": 0}).name
		invoice = create_sales_invoice(
			customer=customer.name, item_code=item, qty=1, rate=1000, is_internal_customer=1
		)
		self.assertEqual(invoice.represents_company, "_Test Company 7")
		filters = {"voucher_type": "Sales Invoice", "voucher_no": invoice.name}
		gl_entries = frappe.get_all("GL Entry", filters=filters, pluck="name", order_by="name")
		payment_entries = frappe.get_all(
			"Payment Ledger Entry", filters=filters, pluck="name", order_by="name"
		)
		self.assertTrue(gl_entries)
		self.assertTrue(payment_entries)

		tdr = create_transaction_deletion_doc("_Test Company 7")
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), 1)
		self.assertTrue(frappe.db.exists("Sales Invoice Item", invoice.items[0].name))
		self.assertEqual(
			frappe.get_all("GL Entry", filters=filters, pluck="name", order_by="name"), gl_entries
		)
		self.assertEqual(
			frappe.get_all("Payment Ledger Entry", filters=filters, pluck="name", order_by="name"),
			payment_entries,
		)

	def test_custom_company_field_is_used(self):
		custom_field = frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "Item Price",
				"fieldname": "company",
				"label": "Company",
				"fieldtype": "Link",
				"options": "Company",
			}
		)
		# Insert the metadata row only, so the test does not alter the table.
		custom_field.db_insert()
		tdr = frappe.new_doc("Transaction Deletion Record")
		fields = tdr.get_doctypes_with_company_field(tdr.get_doctypes_to_be_ignored_list())
		self.assertIn(("Item Price", "company"), {(row.parent, row.fieldname) for row in fields})

	def test_start_deletion_rejects_draft_and_completed_records(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		with patch.object(tdr, "enqueue_task") as enqueue:
			with self.assertRaises(frappe.ValidationError):
				tdr.start_deletion_tasks()
			tdr.db_set({"docstatus": 1, "status": "Completed"})
			with self.assertRaises(frappe.ValidationError):
				tdr.start_deletion_tasks()
			enqueue.assert_not_called()
		self.assertEqual(tdr.db_get("status"), "Completed")

	def test_failed_deletion_can_be_retried(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		tdr.db_set(
			{"docstatus": 1, "status": "Failed", "delete_leads_and_addresses": 1, "delete_bin_data": 1}
		)
		with patch.object(tdr, "enqueue_task") as enqueue:
			tdr.start_deletion_tasks()
		enqueue.assert_called_once_with(task="Delete Leads and Addresses")
		self.assertEqual(tdr.db_get("status"), "Running")
		self.assertEqual(tdr.db_get("delete_leads_and_addresses"), 0)
		self.assertEqual(tdr.db_get("delete_bin_data"), 0)

	def test_retry_refuses_another_running_deletion(self):
		failed = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		failed.insert()
		failed.db_set({"docstatus": 1, "status": "Failed"})
		running = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		running.insert()
		running.db_set({"docstatus": 1, "status": "Running"})
		with patch.object(failed, "enqueue_task") as enqueue, self.assertRaises(frappe.ValidationError):
			failed.start_deletion_tasks()
		enqueue.assert_not_called()
		self.assertEqual(failed.db_get("status"), "Failed")

	def test_single_transaction_deletion_propagates_failure(self):
		from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
			TransactionDeletionRecord,
		)

		create_task("_Test Company 7")
		with patch.object(
			TransactionDeletionRecord,
			"delete_docs_linked_with_specified_company",
			side_effect=RuntimeError("Deletion failed"),
		):
			with self.assertRaisesRegex(RuntimeError, "Deletion failed"):
				create_transaction_deletion_doc("_Test Company 7")

	def test_bins_are_rebuilt_after_transactions(self):
		tdr = frappe.new_doc("Transaction Deletion Record")
		self.assertEqual(list(tdr.task_to_internal_method_map)[-1], "Delete Bins")
		tdr.company = "_Test Company 7"
		tdr.insert()
		tdr.db_set({"docstatus": 1, "status": "Running"})
		with patch.object(tdr, "enqueue_task") as enqueue:
			tdr.delete_bins()
		enqueue.assert_called_once_with(task="Delete Leads and Addresses")
		self.assertEqual(tdr.db_get("status"), "Running")
		self.assertEqual(tdr.db_get("delete_bin_data"), 0)

	def test_full_deletion_clears_bin_values_after_removing_stock(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		company = "_Test Company 7"
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Stores"})
		item = make_item().name
		make_stock_entry(item_code=item, company=company, target=warehouse, qty=10, rate=100)
		make_stock_entry(item_code=item, target="_Test Warehouse - _TC", qty=7, rate=100)
		bin = frappe.get_doc("Bin", {"item_code": item, "warehouse": warehouse})
		tdr = create_transaction_deletion_doc(company)
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertEqual(tdr.db_get("delete_bin_data"), 1)
		self.assertFalse(frappe.db.exists("Bin", bin.name))
		other_bin = frappe.get_doc("Bin", {"item_code": item, "warehouse": "_Test Warehouse - _TC"})
		self.assertEqual((other_bin.actual_qty, other_bin.stock_value), (7, 700))

	def test_keeps_address_shared_with_other_company_lead(self):
		leads = [
			frappe.get_doc({"doctype": "Lead", "first_name": first_name, "company": company}).insert()
			for first_name, company in (("Deletion Lead", "_Test Company 7"), ("Other Lead", "_Test Company"))
		]
		address_fields = {
			"doctype": "Address",
			"address_type": "Billing",
			"address_line1": "Test street",
			"city": "Mumbai",
			"country": "India",
		}
		address = frappe.get_doc(
			{
				**address_fields,
				"address_title": "Shared deletion test",
				"links": [{"link_doctype": "Lead", "link_name": lead.name} for lead in leads],
			}
		).insert()
		exclusive_address = frappe.get_doc(
			{
				**address_fields,
				"address_title": "Exclusive deletion test",
				"links": [{"link_doctype": "Lead", "link_name": leads[0].name}],
			}
		).insert()
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		tdr.db_set("status", "Running")
		with patch.object(tdr, "enqueue_task"):
			tdr.delete_lead_addresses()

		self.assertTrue(frappe.db.exists("Address", address.name))
		self.assertFalse(frappe.db.exists("Address", exclusive_address.name))
		self.assertTrue(
			frappe.db.exists("Dynamic Link", {"parent": address.name, "link_name": leads[1].name})
		)
		self.assertFalse(
			frappe.db.exists("Dynamic Link", {"parent": address.name, "link_name": leads[0].name})
		)

	def test_lead_contacts_preserve_other_company_links(self):
		leads = [
			frappe.get_doc({"doctype": "Lead", "first_name": "Deletion contact", "company": company}).insert()
			for company in ("_Test Company 7", "_Test Company")
		]
		shared = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Shared deletion contact",
				"links": [{"link_doctype": "Lead", "link_name": lead.name} for lead in leads],
			}
		).insert()
		exclusive = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Exclusive deletion contact",
				"email_ids": [{"email_id": "deletion@example.com"}],
				"links": [{"link_doctype": "Lead", "link_name": leads[0].name}],
			}
		).insert()
		create_transaction_deletion_doc("_Test Company 7")
		self.assertFalse(frappe.db.exists("Contact", exclusive.name))
		self.assertFalse(frappe.db.exists("Contact Email", {"parent": exclusive.name}))
		shared.reload()
		self.assertEqual(
			[(row.link_doctype, row.link_name) for row in shared.links], [("Lead", leads[1].name)]
		)

	def test_deletion_preserves_naming_series_counter(self):
		task = frappe.get_doc({"doctype": "Task", "company": "_Test Company 7", "subject": "Series"}).insert()
		prefix = task.name.rsplit("-", 1)[0] + "-"
		counter = frappe.db.get_value("Series", prefix, "current", order_by="name")
		self.assertTrue(counter)
		tdr = create_transaction_deletion_doc("_Test Company 7")
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertFalse(frappe.db.exists("Task", task.name))
		self.assertEqual(frappe.db.get_value("Series", prefix, "current", order_by="name"), counter)

	def test_company_configuration_survives_transaction_deletion(self):
		from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
			get_doctypes_to_be_ignored,
		)

		expected = {
			"Pricing Rule",
			"Tax Rule",
			"Shipping Rule",
			"Putaway Rule",
			"Authorization Rule",
			"Project",
			"Promotional Scheme",
			"Loyalty Program",
			"Accounting Dimension Filter",
			"Accounting Period",
			"Cost Center Allocation",
			"Journal Entry Template",
			"Dunning Type",
			"Payment Gateway Account",
			"Email Digest",
			"UAE VAT Settings",
			"South Africa VAT Settings",
			"Shareholder",
			"Vehicle",
			"Plant Floor",
			"Asset Maintenance Team",
		}
		self.assertFalse(expected - set(get_doctypes_to_be_ignored()))

		project = frappe.get_doc(
			{"doctype": "Project", "project_name": "Transaction deletion test", "company": "_Test Company 7"}
		).insert()
		tdr = create_transaction_deletion_doc("_Test Company 7")
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertTrue(frappe.db.exists("Project", project.name))
		self.assertFalse(expected & {row.doctype_name for row in tdr.doctypes})

	def test_deletion_removes_ancillary_references_only_for_deleted_documents(self):
		from frappe.desk.doctype.tag.tag import add_tag

		tasks = [
			frappe.get_doc({"doctype": "Task", "company": company, "subject": "Deletion references"}).insert()
			for company in ("_Test Company 7", "_Test Company")
		]
		references = []
		for task in tasks:
			rows = [
				frappe.get_doc(
					{
						"doctype": "ToDo",
						"description": "Follow up",
						"allocated_to": "Administrator",
						"reference_type": "Task",
						"reference_name": task.name,
					}
				).insert(),
				frappe.get_doc(
					{
						"doctype": "Notification Log",
						"subject": "Task notification",
						"for_user": "Administrator",
						"type": "Alert",
						"document_type": "Task",
						"document_name": task.name,
					}
				).insert(),
			]
			frappe.share.add("Task", task.name, "Guest", read=1, notify=0)
			add_tag("Deletion references", "Task", task.name)
			references.append(rows)

		create_transaction_deletion_doc("_Test Company 7")
		for index, task in enumerate(tasks):
			for row in references[index]:
				self.assertEqual(bool(frappe.db.exists(row.doctype, row.name)), bool(index))
			for doctype, filters in (
				("DocShare", {"share_doctype": "Task", "share_name": task.name}),
				("Tag Link", {"document_type": "Task", "document_name": task.name}),
			):
				self.assertEqual(bool(frappe.db.exists(doctype, filters)), bool(index))

	def test_detached_attachments_have_a_review_folder_and_shared_files_survive(self):
		task = frappe.get_doc(
			{"doctype": "Task", "company": "_Test Company 7", "subject": "File cleanup"}
		).insert()
		other = frappe.get_doc(
			{"doctype": "Task", "company": "_Test Company", "subject": "Shared file"}
		).insert()
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "deletion-review.txt",
				"content": b"deletion review",
				"is_private": 1,
				"attached_to_doctype": "Task",
				"attached_to_name": task.name,
			}
		).insert()
		shared_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_url": file.file_url,
				"is_private": 1,
				"attached_to_doctype": "Task",
				"attached_to_name": other.name,
			}
		).insert()
		tdr = create_transaction_deletion_doc("_Test Company 7")
		file.reload()
		self.assertFalse(file.attached_to_name)
		self.assertEqual(file.folder, "Home/Transaction Deletion Review")
		shared_file.reload()
		self.assertEqual(shared_file.attached_to_name, other.name)
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": tdr.doctype, "reference_name": tdr.name, "comment_type": "Info"},
			)
		)

	def test_deletion_resets_company_transaction_history(self):
		frappe.db.set_value(
			"Company",
			"_Test Company 7",
			{
				"transactions_annual_history": '{"123": 1}',
				"total_monthly_sales": 100,
				"sales_monthly_history": '{"123": 100}',
			},
		)
		frappe.clear_document_cache("Company", "_Test Company 7")
		tdr = create_transaction_deletion_doc("_Test Company 7")
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertFalse(frappe.get_cached_value("Company", "_Test Company 7", "transactions_annual_history"))
		self.assertFalse(frappe.db.get_value("Company", "_Test Company 7", "sales_monthly_history"))

	def test_deletion_recalculates_shared_batch_quantity(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"has_batch_no": 1, "create_new_batch": 0}).name
		batch = frappe.get_doc(
			{"doctype": "Batch", "batch_id": frappe.generate_hash(length=10), "item": item}
		).insert()
		warehouse = frappe.db.get_value(
			"Warehouse", {"company": "_Test Company 7", "warehouse_name": "Stores"}
		)
		make_stock_entry(
			item_code=item, company="_Test Company 7", target=warehouse, qty=5, rate=100, batch_no=batch.name
		)
		other_receipt = make_stock_entry(
			item_code=item, target="_Test Warehouse - _TC", qty=7, rate=100, batch_no=batch.name
		)
		self.assertEqual(batch.db_get("batch_qty"), 12)
		tdr = create_transaction_deletion_doc("_Test Company 7")
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertEqual(batch.db_get("batch_qty"), 7)
		self.assertTrue(frappe.db.exists("Stock Entry", other_receipt.name))


def create_company(company_name):
	company = frappe.get_doc({"doctype": "Company", "company_name": company_name, "default_currency": "INR"})
	company.insert(ignore_if_duplicate=True)


def create_transaction_deletion_doc(company):
	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	tdr.insert()
	tdr.process_in_single_transaction = True
	tdr.submit()
	tdr.start_deletion_tasks()
	return tdr


def create_task(company):
	task = frappe.get_doc({"doctype": "Task", "company": company, "subject": "Delete"})
	task.insert()
