"""Test for Italy regional patch: rename_italy_customer_name_fields.

This test is completely DB-based to avoid dependencies on ERPNext test fixtures.
"""

import unittest

import frappe
from frappe.utils import now


class TestRenameItalyCustomerNameFields(unittest.TestCase):
	"""Test the patch that renames Italy regional custom fields on Customer."""

	OLD_FIRST_NAME_FIELD = "Customer-first_name"
	OLD_LAST_NAME_FIELD = "Customer-last_name"
	NEW_FIRST_NAME_FIELD = "Customer-italy_customer_first_name"
	NEW_LAST_NAME_FIELD = "Customer-italy_customer_last_name"

	@classmethod
	def setUpClass(cls):
		# Connect to the site
		if not frappe.db:
			frappe.connect()
		cls.test_customer_name = "_Test Italy Patch Customer"

	def setUp(self):
		"""Set up test scenario: create old fields and test customer."""
		self._cleanup_fields()
		self._cleanup_test_customer()
		self._create_old_custom_fields_direct()
		self._add_old_columns_to_db()
		self._create_test_customer_direct()

	def tearDown(self):
		"""Clean up after test."""
		self._cleanup_test_customer()
		self._cleanup_fields()
		self._drop_old_columns_if_exist()
		# Restore new fields from Italy setup
		try:
			from erpnext.regional.italy.setup import make_custom_fields

			make_custom_fields(update=True)
		except (ImportError, AttributeError, ValueError) as e:
			# Ignore setup failures in tearDown, but log for debugging
			frappe.logger().warning(f"Failed to restore Italy setup in tearDown: {e}")
		frappe.db.rollback()

	def _cleanup_fields(self):
		"""Remove both old and new custom fields."""
		for field_name in [
			self.OLD_FIRST_NAME_FIELD,
			self.OLD_LAST_NAME_FIELD,
			self.NEW_FIRST_NAME_FIELD,
			self.NEW_LAST_NAME_FIELD,
		]:
			if frappe.db.exists("Custom Field", field_name):
				frappe.db.delete("Custom Field", {"name": field_name})

	def _cleanup_test_customer(self):
		"""Remove test customer if exists."""
		if frappe.db.exists("Customer", self.test_customer_name):
			# Delete directly from DB to avoid controller validation
			frappe.db.delete("Customer", {"name": self.test_customer_name})

	def _create_old_custom_fields_direct(self):
		"""Create the old custom fields directly in DB to bypass validation.

		This simulates the legacy state where Italy regional setup created
		fields with names that now conflict with standard Customer fields.
		"""
		current_time = now()

		# Insert old first_name custom field directly
		frappe.db.sql(
			"""
			INSERT INTO `tabCustom Field`
			(name, creation, modified, modified_by, owner, docstatus,
			 dt, fieldname, fieldtype, label, insert_after, depends_on)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		""",
			(
				self.OLD_FIRST_NAME_FIELD,
				current_time,
				current_time,
				"Administrator",
				"Administrator",
				0,
				"Customer",
				"first_name",
				"Data",
				"First Name",
				"customer_name",
				"eval:doc.customer_type == 'Individual'",
			),
		)

		# Insert old last_name custom field directly
		frappe.db.sql(
			"""
			INSERT INTO `tabCustom Field`
			(name, creation, modified, modified_by, owner, docstatus,
			 dt, fieldname, fieldtype, label, insert_after, depends_on)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		""",
			(
				self.OLD_LAST_NAME_FIELD,
				current_time,
				current_time,
				"Administrator",
				"Administrator",
				0,
				"Customer",
				"last_name",
				"Data",
				"Last Name",
				"first_name",
				"eval:doc.customer_type == 'Individual'",
			),
		)

		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- required after raw SQL INSERT in test setup

	def _add_old_columns_to_db(self):
		"""Ensure old columns exist in the database table."""
		frappe.clear_cache()  # Clear cache to get fresh column info
		if not frappe.db.has_column("Customer", "first_name"):
			frappe.db.sql_ddl("ALTER TABLE `tabCustomer` ADD COLUMN `first_name` VARCHAR(140)")
		if not frappe.db.has_column("Customer", "last_name"):
			frappe.db.sql_ddl("ALTER TABLE `tabCustomer` ADD COLUMN `last_name` VARCHAR(140)")
		frappe.clear_cache()  # Clear cache after adding columns

	def _drop_old_columns_if_exist(self):
		"""Drop old columns if they still exist."""
		frappe.clear_cache()  # Clear cache to get fresh column info
		try:
			if frappe.db.has_column("Customer", "first_name"):
				frappe.db.sql_ddl("ALTER TABLE `tabCustomer` DROP COLUMN `first_name`")
		except frappe.db.InternalError as e:
			# Column might already be dropped or locked
			frappe.logger().debug(f"Could not drop first_name column: {e}")
		try:
			if frappe.db.has_column("Customer", "last_name"):
				frappe.db.sql_ddl("ALTER TABLE `tabCustomer` DROP COLUMN `last_name`")
		except frappe.db.InternalError as e:
			# Column might already be dropped or locked
			frappe.logger().debug(f"Could not drop last_name column: {e}")
		frappe.clear_cache()  # Clear cache after dropping columns

	def _create_test_customer_direct(self):
		"""Create a test customer directly in DB to avoid controller dependencies."""
		current_time = now()

		# Insert customer directly into DB
		frappe.db.sql(
			"""
			INSERT INTO `tabCustomer`
			(name, creation, modified, modified_by, owner, docstatus,
			 customer_name, customer_type, first_name, last_name)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		""",
			(
				self.test_customer_name,
				current_time,
				current_time,
				"Administrator",
				"Administrator",
				0,
				self.test_customer_name,
				"Individual",
				"Mario",
				"Rossi",
			),
		)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- required after raw SQL INSERT in test setup

	def test_patch_renames_fields_and_migrates_data(self):
		"""Test that the patch renames fields and migrates data correctly."""
		# Verify old fields exist before patch
		self.assertTrue(frappe.db.exists("Custom Field", self.OLD_FIRST_NAME_FIELD))
		self.assertTrue(frappe.db.exists("Custom Field", self.OLD_LAST_NAME_FIELD))

		# Verify old data exists
		old_first_name = frappe.db.get_value("Customer", self.test_customer_name, "first_name")
		old_last_name = frappe.db.get_value("Customer", self.test_customer_name, "last_name")
		self.assertEqual(old_first_name, "Mario")
		self.assertEqual(old_last_name, "Rossi")

		# Execute the patch
		from erpnext.patches.v15_0.rename_italy_customer_name_fields import execute

		execute()

		# Verify old Custom Field documents are deleted
		self.assertFalse(frappe.db.exists("Custom Field", self.OLD_FIRST_NAME_FIELD))
		self.assertFalse(frappe.db.exists("Custom Field", self.OLD_LAST_NAME_FIELD))

		# Verify new Custom Field documents exist
		self.assertTrue(frappe.db.exists("Custom Field", self.NEW_FIRST_NAME_FIELD))
		self.assertTrue(frappe.db.exists("Custom Field", self.NEW_LAST_NAME_FIELD))

		# Verify data was migrated to new columns
		new_first_name = frappe.db.get_value("Customer", self.test_customer_name, "italy_customer_first_name")
		new_last_name = frappe.db.get_value("Customer", self.test_customer_name, "italy_customer_last_name")
		self.assertEqual(new_first_name, "Mario")
		self.assertEqual(new_last_name, "Rossi")

		# Note: first_name/last_name columns are NOT dropped because they are
		# standard Customer fields (Read Only, fetch from customer_primary_contact)

	def test_patch_skips_non_italy_fields(self):
		"""Test that the patch skips fields that are not Italy regional fields."""
		# Delete the Italy regional fields created in setUp
		self._cleanup_fields()
		self._drop_old_columns_if_exist()
		self._cleanup_test_customer()

		current_time = now()

		# Create a custom field with same name but without Italy's depends_on
		frappe.db.sql(
			"""
			INSERT INTO `tabCustom Field`
			(name, creation, modified, modified_by, owner, docstatus,
			 dt, fieldname, fieldtype, label, insert_after)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		""",
			(
				self.OLD_FIRST_NAME_FIELD,
				current_time,
				current_time,
				"Administrator",
				"Administrator",
				0,
				"Customer",
				"first_name",
				"Data",
				"First Name",
				"customer_name",
			),
		)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- required after raw SQL INSERT in test setup

		# Execute the patch
		from erpnext.patches.v15_0.rename_italy_customer_name_fields import execute

		execute()

		# The non-Italy field should still exist (not renamed)
		self.assertTrue(frappe.db.exists("Custom Field", self.OLD_FIRST_NAME_FIELD))

		# Verify new Italy fields were NOT created (since this wasn't an Italy field)
		self.assertFalse(frappe.db.exists("Custom Field", self.NEW_FIRST_NAME_FIELD))
		self.assertFalse(frappe.db.exists("Custom Field", self.NEW_LAST_NAME_FIELD))


if __name__ == "__main__":
	unittest.main()
