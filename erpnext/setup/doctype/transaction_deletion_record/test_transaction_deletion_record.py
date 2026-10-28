from unittest.mock import patch
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestTransactionDeletionRecord(ERPNextTestSuite):
	def setUp(self):
		# Clear all deletion cache flags from previous tests
		self._clear_all_deletion_cache_flags()

	def _clear_all_deletion_cache_flags(self):
		"""Clear all deletion_running_doctype:* cache keys"""
		# Get all keys matching the pattern
		cache_keys = frappe.cache.get_keys("deletion_running_doctype:*")
		if cache_keys:
			for key in cache_keys:
				# Decode bytes to string if needed
				key_str = key.decode() if isinstance(key, bytes) else key
				# Extract just the key name (remove site prefix if present)
				# Keys are in format: site_prefix|deletion_running_doctype:DocType
				if "|" in key_str:
					key_name = key_str.split("|")[1]
				else:
					key_name = key_str
				frappe.cache.delete_value(key_name)

	def test_doctypes_contain_company_field(self):
		"""Test that all DocTypes in To Delete list have a valid company link field"""
		tdr = create_and_submit_transaction_deletion_doc("_Test Company 7")
		for doctype_row in tdr.doctypes_to_delete:
			# If company_field is specified, verify it's a valid Company link field
			if doctype_row.company_field:
				field_found = False
				doctype_fields = frappe.get_meta(doctype_row.doctype_name).as_dict()["fields"]
				for doctype_field in doctype_fields:
					if (
						doctype_field["fieldname"] == doctype_row.company_field
						and doctype_field["fieldtype"] == "Link"
						and doctype_field["options"] == "Company"
					):
						field_found = True
						break
				self.assertTrue(
					field_found,
					f"DocType {doctype_row.doctype_name} should have company field '{doctype_row.company_field}'",
				)

	def test_no_of_docs_is_correct(self):
		"""Test that document counts are calculated correctly in To Delete list"""
		for _ in range(5):
			create_task("_Test Company 7")
		tdr = create_and_submit_transaction_deletion_doc("_Test Company 7")
		tdr.reload()

		# Check To Delete list has correct count
		task_found = False
		for doctype in tdr.doctypes_to_delete:
			if doctype.doctype_name == "Task":
				self.assertEqual(doctype.document_count, 5)
				task_found = True
				break
		self.assertTrue(task_found, "Task should be in To Delete list")

	def test_deletion_is_successful(self):
		"""Test that deletion actually removes documents"""
		create_task("_Test Company 7")
		create_and_submit_transaction_deletion_doc("_Test Company 7")
		tasks_containing_company = frappe.get_all("Task", filters={"company": "_Test Company 7"})
		self.assertEqual(tasks_containing_company, [])

	def test_company_transaction_deletion_request(self):
		"""Test creation via company deletion request method"""
		from erpnext.setup.doctype.company.company import create_transaction_deletion_request

		# don't reuse below company for other test cases
		company = "_Test Company 7"

		# below call should not raise any exceptions or throw errors
		create_transaction_deletion_request(company)

	def test_generate_to_delete_list(self):
		"""Test automatic generation of To Delete list"""
		company = "_Test Company 7"
		create_task(company)

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.insert()

		# Generate To Delete list
		tdr.generate_to_delete_list()
		tdr.reload()

		# Should have at least Task in the list
		self.assertGreater(len(tdr.doctypes_to_delete), 0)
		task_in_list = any(d.doctype_name == "Task" for d in tdr.doctypes_to_delete)
		self.assertTrue(task_in_list, "Task should be in To Delete list")

	def test_generated_list_uses_owning_company_for_sales_invoice(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		tdr.generate_to_delete_list()

		fields = [row.company_field for row in tdr.doctypes_to_delete if row.doctype_name == "Sales Invoice"]
		self.assertEqual(fields, ["company"])

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
		gl_entries = frappe.get_all(
			"GL Entry", filters=filters, fields=["name", "account", "debit", "credit"], order_by="name"
		)
		payment_entries = frappe.get_all(
			"Payment Ledger Entry", filters=filters, fields=["name", "amount", "delinked"], order_by="name"
		)
		self.assertEqual(len(gl_entries), 2)
		self.assertEqual(len(payment_entries), 1)
		delete = create_and_submit_transaction_deletion_doc("_Test Company 7")
		self.assertEqual(delete.db_get("status"), "Completed")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), 1)
		self.assertTrue(frappe.db.exists("Sales Invoice Item", invoice.items[0].name))
		self.assertEqual(
			frappe.get_all(
				"GL Entry", filters=filters, fields=["name", "account", "debit", "credit"], order_by="name"
			),
			gl_entries,
		)
		self.assertEqual(
			frappe.get_all(
				"Payment Ledger Entry",
				filters=filters,
				fields=["name", "amount", "delinked"],
				order_by="name",
			),
			payment_entries,
		)

	def test_rejects_secondary_company_field_for_owned_documents(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.append(
			"doctypes_to_delete", {"doctype_name": "Sales Invoice", "company_field": "represents_company"}
		)
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_rejects_ambiguous_company_field_for_shipment(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.append("doctypes_to_delete", {"doctype_name": "Shipment", "company_field": "pickup_company"})
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_start_deletion_rejects_draft_and_completed_records(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.append("doctypes_to_delete", {"doctype_name": "Task", "company_field": "company"})
		tdr.insert()

		try:
			with patch.object(tdr, "enqueue_task"):
				with self.assertRaises(frappe.ValidationError):
					tdr.start_deletion_tasks()
				tdr.db_set({"docstatus": 1, "status": "Completed"})
				with self.assertRaises(frappe.ValidationError):
					tdr.start_deletion_tasks()
		finally:
			tdr._clear_deletion_cache()

	def test_retry_checks_saved_status(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		tdr.docstatus = 1
		tdr.status = "Failed"
		with patch.object(tdr, "enqueue_task"), self.assertRaises(frappe.ValidationError):
			tdr.start_deletion_tasks()

	def test_failed_deletion_can_be_retried(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.append("doctypes_to_delete", {"doctype_name": "Task", "company_field": "company"})
		tdr.insert()
		tdr.db_set({"docstatus": 1, "status": "Failed"})
		try:
			with patch.object(tdr, "enqueue_task"):
				tdr.start_deletion_tasks()
			self.assertEqual(tdr.db_get("status"), "Running")
		finally:
			tdr._clear_deletion_cache()

	def test_retry_revalidates_changed_company_fields(self):
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		custom_field = create_custom_field(
			"Item Price",
			{"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company"},
		)
		tdr = frappe.get_doc(
			{
				"doctype": "Transaction Deletion Record",
				"company": "_Test Company 7",
				"doctypes_to_delete": [{"doctype_name": "Item Price", "company_field": "company"}],
			}
		)
		try:
			tdr.insert()
			with patch.object(tdr, "enqueue_task") as enqueue:
				tdr.submit()
				tdr.db_set("status", "Failed")
				tdr._clear_deletion_cache()
				frappe.delete_doc("Custom Field", custom_field.name, force=True)
				enqueue.reset_mock()
				with self.assertRaises(frappe.ValidationError):
					tdr.start_deletion_tasks()
				enqueue.assert_not_called()
			self.assertEqual(tdr.db_get("status"), "Failed")
		finally:
			tdr._clear_deletion_cache()
			frappe.db.rollback()
			frappe.delete_doc("Custom Field", custom_field.name, force=True)
			frappe.db.commit()
			frappe.clear_cache(doctype="Item Price")

	def test_retry_rechecks_completed_and_previously_empty_doctypes(self):
		company = "_Test Company 7"
		create_deletion_journal(company)
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
		for doctype in ("Journal Entry", "GL Entry", "Task"):
			tdr.append("doctypes_to_delete", {"doctype_name": doctype, "company_field": "company"})
		tdr.insert()
		tdr.batch_size = 1
		try:
			with patch.object(tdr, "enqueue_task"):
				tdr.submit()
				tdr.initialize_doctypes_to_be_deleted_table()
				for _ in range(2):
					tdr.execute_task("Delete Transactions")
					tdr.reload()
				self.assertEqual(
					next(row.done for row in tdr.doctypes if row.doctype_name == "Journal Entry"), 1
				)
				frappe.db.savepoint("before_failed_deletion_task")
				rollback = frappe.db.rollback
				with patch.object(
					tdr,
					"get_number_of_docs_linked_with_specified_company",
					side_effect=RuntimeError("Worker failed"),
				):
					with patch.object(
						frappe.db,
						"rollback",
						side_effect=lambda: rollback(save_point="before_failed_deletion_task"),
					):
						tdr.execute_task("Delete Transactions")
				tdr.reload()
				self.assertEqual(tdr.status, "Failed")
				self.assertIn("Worker failed", tdr.error_log)
				self.assertIsNone(frappe.cache.get_value("deletion_running_doctype:Journal Entry"))
				journal = create_deletion_journal(company)
				task = frappe.get_doc(
					{"doctype": "Task", "company": company, "subject": "Created while failed"}
				).insert()
				self.assertEqual(
					frappe.db.count(
						"GL Entry", {"voucher_type": "Journal Entry", "voucher_no": journal.name}
					),
					2,
				)
				tdr.start_deletion_tasks()
				for task_name in tdr.task_to_internal_method_map:
					for _ in range(10):
						tdr.reload()
						tdr.execute_task(task_name)
						if (
							task_name != "Delete Transactions"
							or tdr.db_get("delete_transactions_status") == "Completed"
						):
							break
			self.assertEqual(tdr.db_get("status"), "Completed")
			self.assertFalse(frappe.db.exists("Journal Entry", journal.name))
			self.assertFalse(frappe.db.exists("Task", task.name))
			self.assertEqual(
				frappe.db.count("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": journal.name}), 0
			)
		finally:
			tdr._clear_deletion_cache()

	def test_retry_refuses_another_running_deletion(self):
		records = []
		try:
			for company in ("_Test Company 7", "_Test Company 6"):
				tdr = frappe.get_doc(
					{
						"doctype": "Transaction Deletion Record",
						"company": company,
						"doctypes_to_delete": [{"doctype_name": "Task", "company_field": "company"}],
					}
				).insert()
				records.append(tdr)
				with patch.object(tdr, "enqueue_task"):
					tdr.submit()
				if len(records) == 1:
					tdr.db_set("status", "Failed")
					tdr._clear_deletion_cache()
			with patch.object(records[0], "enqueue_task"), self.assertRaises(frappe.ValidationError):
				records[0].start_deletion_tasks()
			self.assertEqual(frappe.cache.get_value("deletion_running_doctype:Task"), records[1].name)
		finally:
			for tdr in records:
				tdr._clear_deletion_cache()

	def test_cache_cleanup_preserves_another_deletions_lock(self):
		tdr = frappe.get_doc(
			{
				"doctype": "Transaction Deletion Record",
				"company": "_Test Company 7",
				"doctypes_to_delete": [{"doctype_name": "Task", "company_field": "company"}],
			}
		).insert()
		frappe.cache.set_value("deletion_running_doctype:Task", "Another deletion", expires_in_sec=60)
		try:
			tdr._clear_deletion_cache()
			self.assertEqual(frappe.cache.get_value("deletion_running_doctype:Task"), "Another deletion")
		finally:
			frappe.cache.delete_value("deletion_running_doctype:Task")

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
				delete_selected_doctypes("_Test Company 7", ["Task"])

	def test_keeps_address_shared_with_other_company_lead(self):
		leads = [
			frappe.get_doc({"doctype": "Lead", "first_name": first_name, "company": company}).insert()
			for first_name, company in (("Deletion Lead", "_Test Company 7"), ("Other Lead", "_Test Company"))
		]
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "Shared deletion test",
				"address_type": "Billing",
				"address_line1": "Test street",
				"city": "Mumbai",
				"country": "India",
				"links": [{"link_doctype": "Lead", "link_name": lead.name} for lead in leads],
			}
		).insert()
		exclusive_address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "Exclusive deletion test",
				"address_type": "Billing",
				"address_line1": "Test street",
				"city": "Mumbai",
				"country": "India",
				"links": [{"link_doctype": "Lead", "link_name": leads[0].name}],
			}
		).insert()
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.append("doctypes_to_delete", {"doctype_name": "Lead", "company_field": "company"})
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

	def test_deletes_documents_created_after_list_generation(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		tdr.generate_to_delete_list()
		task_row = next(row for row in tdr.doctypes_to_delete if row.doctype_name == "Task")
		self.assertEqual(task_row.document_count, 0)
		create_task("_Test Company 7")
		task_name = frappe.db.get_value("Task", {"company": "_Test Company 7", "subject": "Delete"}, "name")
		tdr.process_in_single_transaction = True
		tdr.submit()
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertFalse(frappe.db.exists("Task", task_name))

	def test_late_submitted_journal_and_ledger_are_deleted_together(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		company = (
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "Deletion late journal",
					"abbr": "TDLJ",
					"country": "India",
					"default_currency": "INR",
					"enable_perpetual_inventory": 1,
				}
			)
			.insert()
			.name
		)
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Stores"})
		make_stock_entry(item_code=make_item().name, company=company, target=warehouse, qty=1, rate=100)
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company}).insert()
		tdr.generate_to_delete_list()
		self.assertEqual(
			next(row.document_count for row in tdr.doctypes_to_delete if row.doctype_name == "Journal Entry"),
			0,
		)
		self.assertGreater(
			next(row.document_count for row in tdr.doctypes_to_delete if row.doctype_name == "GL Entry"), 0
		)
		journal = create_deletion_journal(company)
		self.assertEqual(
			frappe.db.count("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": journal.name}), 2
		)
		tdr.process_in_single_transaction = True
		tdr.submit()
		self.assertEqual(tdr.db_get("status"), "Completed")
		self.assertFalse(frappe.db.exists("Journal Entry", journal.name))
		self.assertEqual(frappe.db.count("Journal Entry Account", {"parent": journal.name}), 0)
		self.assertEqual(
			frappe.db.count("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": journal.name}), 0
		)

	def test_validation_prevents_child_tables(self):
		"""Test that child tables cannot be added to To Delete list"""
		company = "_Test Company 7"

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.append("doctypes_to_delete", {"doctype_name": "Sales Invoice Item"})  # Child table

		# Should throw validation error
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_validation_prevents_protected_doctypes(self):
		"""Test that protected DocTypes cannot be added to To Delete list"""
		company = "_Test Company 7"

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.append("doctypes_to_delete", {"doctype_name": "DocType"})  # Protected

		# Should throw validation error
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_csv_export_import(self):
		"""Test CSV export and import functionality with company_field column"""
		company = "_Test Company 7"
		create_task(company)

		# Create and generate To Delete list
		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.insert()
		tdr.generate_to_delete_list()
		tdr.reload()

		original_count = len(tdr.doctypes_to_delete)
		self.assertGreater(original_count, 0)

		# Export as CSV
		tdr.export_to_delete_template_method()
		csv_content = frappe.response.get("result")
		self.assertIsNotNone(csv_content)
		self.assertIn("doctype_name", csv_content)
		self.assertIn("company_field", csv_content)  # New: verify company_field column exists

		# Create new record and import
		tdr2 = frappe.new_doc("Transaction Deletion Record")
		tdr2.company = company
		tdr2.insert()
		result = tdr2.import_to_delete_template_method(csv_content)
		tdr2.reload()

		# Should have same entries (counts may differ due to new task)
		self.assertEqual(len(tdr2.doctypes_to_delete), original_count)
		self.assertGreaterEqual(result["imported"], 1)

		# Verify company_field values are preserved
		for row in tdr2.doctypes_to_delete:
			if row.doctype_name == "Task":
				# Task should have company field set
				self.assertIsNotNone(row.company_field, "Task should have company_field set after import")

	def test_import_rejects_unknown_company_field(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.insert()
		result = tdr.import_to_delete_template_method(
			"doctype_name,company_field\nItem Price,missing_company\n"
		)
		self.assertEqual(result["imported"], 0)
		self.assertEqual(result["skipped"], 1)
		self.assertFalse(tdr.doctypes_to_delete)

	def test_custom_company_field_is_used_for_import(self):
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		from erpnext.stock.doctype.item.test_item import make_item

		custom_field = create_custom_field(
			"Item Price",
			{"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company"},
		)
		self.assertIsNotNone(custom_field)
		try:
			tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
			tdr.insert()
			tdr.generate_to_delete_list()
			rows = [row for row in tdr.doctypes_to_delete if row.doctype_name == "Item Price"]
			self.assertEqual([row.company_field for row in rows], ["company"])
			result = tdr.import_to_delete_template_method("doctype_name,company_field\nItem Price,company\n")
			self.assertEqual(result["imported"], 1)
			self.assertEqual(tdr.doctypes_to_delete[0].company_field, "company")
			price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
			prices = [
				frappe.get_doc(
					{
						"doctype": "Item Price",
						"item_code": make_item().name,
						"price_list": price_list,
						"price_list_rate": 100,
						"company": company,
					}
				).insert()
				for company in ("_Test Company 7", "_Test Company")
			]
			invalid = tdr.import_to_delete_template_method(
				"doctype_name,company_field\nItem Price,missing_company\n"
			)
			self.assertEqual(invalid, {"imported": 0, "skipped": 1})
			self.assertEqual(tdr.doctypes_to_delete[0].company_field, "company")
			omitted = tdr.import_to_delete_template_method("doctype_name\nItem Price\n")
			self.assertEqual(omitted["imported"], 1)
			self.assertEqual(tdr.doctypes_to_delete[0].company_field, "company")
			tdr.process_in_single_transaction = True
			tdr.submit()
			self.assertEqual(tdr.db_get("status"), "Completed")
			self.assertFalse(frappe.db.exists("Item Price", prices[0].name))
			self.assertTrue(frappe.db.exists("Item Price", prices[1].name))
		finally:
			frappe.db.rollback()
			frappe.delete_doc("Custom Field", custom_field.name, force=True)
			frappe.db.commit()
			frappe.clear_cache(doctype="Item Price")

	def test_csv_import_tolerates_short_rows(self):
		"""Test that CSV rows omitting trailing columns are imported with an auto-detected company_field"""
		company = "_Test Company 7"

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.insert()

		# Row omits the trailing company_field and child_doctypes columns; csv.DictReader fills
		# them with None, which used to raise on None.strip().
		csv_content = "doctype_name,company_field,child_doctypes\nSales Invoice\n"
		result = tdr.import_to_delete_template_method(csv_content)
		tdr.reload()

		self.assertEqual(result["imported"], 1)
		self.assertEqual(len(tdr.doctypes_to_delete), 1)

		row = tdr.doctypes_to_delete[0]
		self.assertEqual(row.doctype_name, "Sales Invoice")
		# company_field was not provided, so it should be auto-detected as "company"
		self.assertEqual(row.company_field, "company")

	def test_csv_import_all_skipped_rows_preserves_existing_to_delete_list(self):
		"""Test that an all-skipped CSV import does not wipe an existing To Delete list"""
		company = "_Test Company 7"
		create_task(company)

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.insert()
		tdr.generate_to_delete_list()
		tdr.reload()

		original_doctype_names = [row.doctype_name for row in tdr.doctypes_to_delete]
		self.assertGreater(len(original_doctype_names), 0)

		protected_doctype = "DocType"
		nonexistent_doctype = "Nonexistent Doctype For Import Test"
		csv_content = (
			"doctype_name,company_field,child_doctypes\n"
			f"{protected_doctype},,\n"
			f"{nonexistent_doctype},,\n"
		)
		result = tdr.import_to_delete_template_method(csv_content)

		self.assertEqual(result["imported"], 0)
		self.assertGreater(result["skipped"], 0)

		tdr.reload()
		self.assertEqual(len(tdr.doctypes_to_delete), len(original_doctype_names))
		self.assertEqual([row.doctype_name for row in tdr.doctypes_to_delete], original_doctype_names)

	def test_progress_tracking(self):
		"""Test that deleted checkbox is marked when DocType deletion completes"""
		company = "_Test Company 7"
		create_task(company)

		tdr = create_and_submit_transaction_deletion_doc(company)
		tdr.reload()

		# After deletion, Task should be marked as deleted in To Delete list
		# Note: Must match using composite key (doctype_name + company_field)
		task_row = None
		for doctype in tdr.doctypes_to_delete:
			if doctype.doctype_name == "Task":
				task_row = doctype
				break

		if task_row:
			self.assertEqual(task_row.deleted, 1, "Task should be marked as deleted")

	def test_composite_key_validation(self):
		"""Test that duplicate (doctype_name + company_field) combinations are prevented"""
		company = "_Test Company 7"

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.append("doctypes_to_delete", {"doctype_name": "Task", "company_field": "company"})
		tdr.append("doctypes_to_delete", {"doctype_name": "Task", "company_field": "company"})  # Duplicate!

		# Should throw validation error for duplicate composite key
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_rejects_unscoped_company_owned_doctype(self):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": "_Test Company 7"})
		tdr.append("doctypes_to_delete", {"doctype_name": "Task"})
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_company_field_validation(self):
		"""Test that invalid company_field values are rejected"""
		company = "_Test Company 7"

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		# Add Task with invalid company field
		tdr.append("doctypes_to_delete", {"doctype_name": "Task", "company_field": "nonexistent_field"})

		# Should throw validation error for invalid company field
		with self.assertRaises(frappe.ValidationError):
			tdr.insert()

	def test_get_naming_series_prefix_with_dot(self):
		"""Test prefix extraction for standard dot-separated naming series"""
		from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
			TransactionDeletionRecord,
		)

		# Standard patterns with dot separator
		self.assertEqual(TransactionDeletionRecord.get_naming_series_prefix("TDL.####", "Task"), "TDL")
		self.assertEqual(TransactionDeletionRecord.get_naming_series_prefix("PREFIX.#####", "Task"), "PREFIX")
		self.assertEqual(
			TransactionDeletionRecord.get_naming_series_prefix("TASK-.YYYY.-.#####", "Task"), "TASK-.YYYY.-"
		)

	def test_get_naming_series_prefix_with_brace(self):
		"""Test prefix extraction for format patterns with brace separators"""
		from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
			TransactionDeletionRecord,
		)

		# Format patterns with brace separator
		self.assertEqual(
			TransactionDeletionRecord.get_naming_series_prefix("QA-ACT-{#####}", "Quality Action"), "QA-ACT-"
		)
		self.assertEqual(
			TransactionDeletionRecord.get_naming_series_prefix("PREFIX-{####}", "Task"), "PREFIX-"
		)
		self.assertEqual(TransactionDeletionRecord.get_naming_series_prefix("{####}", "Task"), "")

	def test_get_naming_series_prefix_fallback(self):
		"""Test prefix extraction fallback for patterns without standard separators"""
		from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
			TransactionDeletionRecord,
		)

		# Edge case: pattern with # but no dot or brace (shouldn't happen in practice)
		self.assertEqual(TransactionDeletionRecord.get_naming_series_prefix("PREFIX####", "Task"), "PREFIX")
		# Edge case: pattern with no # at all
		self.assertEqual(
			TransactionDeletionRecord.get_naming_series_prefix("JUSTPREFIX", "Task"), "JUSTPREFIX"
		)

	def test_cache_flag_management(self):
		"""Test that cache flags can be set and cleared correctly"""
		company = "_Test Company 7"
		create_task(company)

		tdr = frappe.new_doc("Transaction Deletion Record")
		tdr.company = company
		tdr.insert()
		tdr.generate_to_delete_list()
		tdr.reload()

		# Test _set_deletion_cache
		tdr._set_deletion_cache()

		# Verify flag is set for Task specifically
		cached_value = frappe.cache.get_value("deletion_running_doctype:Task")
		self.assertEqual(cached_value, tdr.name, "Cache flag should be set for Task")

		# Test _clear_deletion_cache
		tdr._clear_deletion_cache()

		# Verify flag is cleared
		cached_value = frappe.cache.get_value("deletion_running_doctype:Task")
		self.assertIsNone(cached_value, "Cache flag should be cleared for Task")

	def test_check_for_running_deletion_blocks_save(self):
		"""Test that check_for_running_deletion_job blocks saves when cache flag exists"""
		from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
			check_for_running_deletion_job,
		)

		company = "_Test Company 7"

		# Manually set cache flag to simulate running deletion
		frappe.cache.set_value("deletion_running_doctype:Task", "TDR-00001", expires_in_sec=60)

		try:
			# Try to validate a new Task
			new_task = frappe.new_doc("Task")
			new_task.company = company
			new_task.subject = "Should be blocked"

			# Should throw error when cache flag exists
			with self.assertRaises(frappe.ValidationError) as context:
				check_for_running_deletion_job(new_task)

			error_message = str(context.exception)
			self.assertIn("currently deleting", error_message)
			self.assertIn("TDR-00001", error_message)
		finally:
			# Cleanup: clear the manually set flag
			frappe.cache.delete_value("deletion_running_doctype:Task")

	def test_check_for_running_deletion_allows_save_when_no_flag(self):
		"""Test that documents can be saved when no deletion is running"""
		company = "_Test Company 7"

		# Ensure no cache flag exists
		frappe.cache.delete_value("deletion_running_doctype:Task")

		# Try to create and save a new Task
		new_task = frappe.new_doc("Task")
		new_task.company = company
		new_task.subject = "Should be allowed"

		# Should NOT throw error when no cache flag - actually save it
		try:
			new_task.insert()
			# Cleanup
			frappe.delete_doc("Task", new_task.name)
		except frappe.ValidationError as e:
			self.fail(f"Should allow save when no deletion is running, but got: {e}")

	def test_only_one_deletion_allowed_globally(self):
		"""Test that only one deletion can be submitted at a time (global enforcement)"""
		company1 = "_Test Company 6"
		company2 = "_Test Company 7"

		# Create and submit first deletion (but don't start it)
		tdr1 = frappe.new_doc("Transaction Deletion Record")
		tdr1.company = company1
		tdr1.insert()
		tdr1.append("doctypes_to_delete", {"doctype_name": "Task", "company_field": "company"})
		tdr1.save()
		tdr1.submit()  # Status becomes "Queued"

		try:
			# Try to submit second deletion for different company
			tdr2 = frappe.new_doc("Transaction Deletion Record")
			tdr2.company = company2  # Different company!
			tdr2.insert()
			tdr2.append("doctypes_to_delete", {"doctype_name": "Lead", "company_field": "company"})
			tdr2.save()

			# Should throw error - only one deletion allowed globally
			with self.assertRaises(frappe.ValidationError) as context:
				tdr2.submit()

			self.assertIn("already", str(context.exception).lower())
			self.assertIn(tdr1.name, str(context.exception))
		finally:
			# Cleanup
			tdr1.cancel()


def create_and_submit_transaction_deletion_doc(company):
	"""Create and execute a transaction deletion record"""
	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	tdr.insert()

	tdr.generate_to_delete_list()
	tdr.reload()

	tdr.process_in_single_transaction = True
	tdr.submit()
	return tdr


def create_task(company):
	task = frappe.get_doc({"doctype": "Task", "company": company, "subject": "Delete"})
	task.insert()

def create_deletion_journal(company):
	abbr, cost_center = frappe.get_cached_value("Company", company, ["abbr", "cost_center"])
	return (
		frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": company,
				"posting_date": frappe.utils.today(),
				"accounts": [
					{
						"account": f"Cash - {abbr}",
						"cost_center": cost_center,
						"debit_in_account_currency": 100,
					},
					{
						"account": f"Sales - {abbr}",
						"cost_center": cost_center,
						"credit_in_account_currency": 100,
					},
				],
			}
		)
		.insert()
		.submit()
	)



def delete_selected_doctypes(company, doctypes):
	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	for doctype in doctypes:
		tdr.append("doctypes_to_delete", {"doctype_name": doctype, "company_field": "company"})
	tdr.insert()
	tdr.process_in_single_transaction = True
	tdr.submit()
	return tdr
