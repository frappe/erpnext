import frappe


def execute():
	"""Rename Italy regional custom fields to avoid conflict with standard Customer fields.

	The Italy regional setup created custom fields 'first_name' and 'last_name' on Customer
	which conflict with the standard read-only fields that fetch from customer_primary_contact.
	This patch renames them to 'italy_customer_first_name' and 'italy_customer_last_name'.
	"""
	# Check if old fields exist and are the Italy regional ones
	old_first_name_exists = frappe.db.exists("Custom Field", "Customer-first_name")
	old_last_name_exists = frappe.db.exists("Custom Field", "Customer-last_name")

	is_italy_first_name = False
	is_italy_last_name = False

	if old_first_name_exists:
		field_doc = frappe.get_doc("Custom Field", "Customer-first_name")
		is_italy_first_name = field_doc.depends_on and "customer_type" in field_doc.depends_on

	if old_last_name_exists:
		field_doc = frappe.get_doc("Custom Field", "Customer-last_name")
		is_italy_last_name = field_doc.depends_on and "customer_type" in field_doc.depends_on

	# If neither field is the Italy regional one, nothing to do
	if not is_italy_first_name and not is_italy_last_name:
		return

	# Step 1: Delete old Custom Field documents FIRST (to avoid duplicate field validation error)
	if is_italy_first_name:
		frappe.delete_doc("Custom Field", "Customer-first_name", force=True)

	if is_italy_last_name:
		frappe.delete_doc("Custom Field", "Customer-last_name", force=True)

	# Step 2: Create the new fields
	from erpnext.regional.italy.setup import make_custom_fields
	make_custom_fields(update=True)

	# Step 3: Migrate data from old columns to new columns (if old columns still exist in DB)
	if is_italy_first_name and frappe.db.has_column("Customer", "first_name"):
		frappe.db.sql("""
			UPDATE `tabCustomer`
			SET italy_customer_first_name = first_name
			WHERE first_name IS NOT NULL AND first_name != ''
			AND (italy_customer_first_name IS NULL OR italy_customer_first_name = '')
		""")
		# Drop old column
		frappe.db.sql_ddl("ALTER TABLE `tabCustomer` DROP COLUMN `first_name`")

	if is_italy_last_name and frappe.db.has_column("Customer", "last_name"):
		frappe.db.sql("""
			UPDATE `tabCustomer`
			SET italy_customer_last_name = last_name
			WHERE last_name IS NOT NULL AND last_name != ''
			AND (italy_customer_last_name IS NULL OR italy_customer_last_name = '')
		""")
		# Drop old column
		frappe.db.sql_ddl("ALTER TABLE `tabCustomer` DROP COLUMN `last_name`")
