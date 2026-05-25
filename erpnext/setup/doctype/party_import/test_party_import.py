# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import csv
import io

import frappe

from erpnext.tests.utils import ERPNextTestSuite

CUSTOMER_CODE = "TC-IMPORT-001"
CUSTOMER_NAME = "Test Import Customer Xyz"
SUPPLIER_CODE = "TS-IMPORT-001"
SUPPLIER_NAME = "Test Import Supplier Xyz"

C_CODE = ("Customer", "Party Code")
C_NAME = ("Customer", "Customer Name")
C_GROUP = ("Customer", "Customer Group")

S_CODE = ("Supplier", "Party Code")
S_NAME = ("Supplier", "Supplier Name")
S_GROUP = ("Supplier", "Supplier Group")

A_LINE1 = ("Address", "Address Line 1")
A_CITY = ("Address", "City/Town")
A_COUNTRY = ("Address", "Country")
A_EMAIL = ("Address", "Email Address")
A_PHONE = ("Address", "Phone")

CON_FNAME = ("Contact", "First Name")
CON_LNAME = ("Contact", "Last Name")
CON_EMAIL = ("Contact", "Email Address")
CON_PHONE = ("Contact", "Phone")

CON_EMAIL_CHILD = ("Contact Email", "Email ID")
CON_PHONE_CHILD = ("Contact Phone", "Number")


def rows(cols, *data_rows):
	return [
		[c[0] for c in cols],
		[c[1] for c in cols],
		*data_rows,
	]


class TestPartyImport(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.cg = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
		cls.sg = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "Services"
		cls.ter = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "Rest Of The World"

	def _csv_file(self, row_data):
		buf = io.StringIO()
		csv.writer(buf).writerows(row_data)
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "test_party_import.csv",
				"content": ("﻿" + buf.getvalue()).encode("utf-8"),
				"is_private": 1,
			}
		)
		f.insert(ignore_permissions=True)
		return f.file_url

	def _run_import(self, party_type, row_data, **kwargs):
		from erpnext.setup.doctype.party_import.party_importer import PartyImporter

		doc = frappe.get_doc(
			{
				"doctype": "Party Import",
				"party_type": party_type,
				"import_file": self._csv_file(row_data),
				"status": "Draft",
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		PartyImporter(doc).run()
		doc.reload()
		return doc

	def _linked(self, link_doctype, link_name, parenttype):
		return frappe.get_all(
			"Dynamic Link",
			filters={"link_doctype": link_doctype, "link_name": link_name, "parenttype": parenttype},
			pluck="parent",
		)

	def test_party_code_becomes_doc_name_and_customer_name_is_display_name(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg],
			),
		)
		self.assertEqual(doc.status, "Success")
		self.assertTrue(frappe.db.exists("Customer", CUSTOMER_CODE), "doc.name must be the party_code")
		self.assertEqual(
			frappe.db.get_value("Customer", CUSTOMER_CODE, "customer_name"),
			CUSTOMER_NAME,
			"customer_name must be the human-readable name from the file",
		)

	def test_when_party_code_empty_customer_name_is_used_as_name(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP],
				["", CUSTOMER_NAME, self.cg],
			),
		)
		self.assertEqual(doc.status, "Success")
		self.assertTrue(
			frappe.db.exists("Customer", CUSTOMER_NAME),
			"when party_code is blank, doc.name should be the customer_name",
		)

	def test_supplier_party_code_becomes_doc_name(self):
		doc = self._run_import(
			"Supplier",
			rows(
				[S_CODE, S_NAME, S_GROUP],
				[SUPPLIER_CODE, SUPPLIER_NAME, self.sg],
			),
		)
		self.assertEqual(doc.status, "Success")
		self.assertTrue(frappe.db.exists("Supplier", SUPPLIER_CODE))
		self.assertEqual(
			frappe.db.get_value("Supplier", SUPPLIER_CODE, "supplier_name"),
			SUPPLIER_NAME,
		)

	def test_import_log_shows_party_name_and_code(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg],
			),
		)
		success_rows = [r for r in doc.import_log if r.status == "Success"]
		self.assertTrue(success_rows)
		self.assertEqual(success_rows[0].party_name, CUSTOMER_NAME)
		self.assertEqual(success_rows[0].party_code, CUSTOMER_CODE)

	def test_address_is_created_and_linked_to_customer(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, A_LINE1, A_CITY, A_COUNTRY],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "123 Main St", "Mumbai", "India"],
			),
		)
		self.assertEqual(doc.status, "Success")
		self.assertTrue(frappe.db.exists("Customer", CUSTOMER_CODE))

		addr_names = self._linked("Customer", CUSTOMER_CODE, "Address")
		log_dump = [(r.status, r.message) for r in doc.import_log]
		self.assertTrue(addr_names, f"Address missing. log={log_dump}")

		addr = frappe.get_doc("Address", addr_names[0])
		self.assertEqual(addr.city, "Mumbai")
		self.assertEqual(addr.address_line1, "123 Main St")

		links = frappe.get_all(
			"Dynamic Link",
			filters={"parent": addr_names[0], "link_doctype": "Customer", "link_name": CUSTOMER_CODE},
		)
		self.assertEqual(len(links), 1)

	def test_address_failure_marks_row_as_error(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, A_CITY, A_COUNTRY],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Mumbai", "India"],
			),
		)
		self.assertTrue(frappe.db.exists("Customer", CUSTOMER_CODE), "Party should still be created")
		self.assertFalse(self._linked("Customer", CUSTOMER_CODE, "Address"))

		error_rows = [r for r in doc.import_log if r.status == "Error"]
		self.assertTrue(error_rows)
		self.assertIn("Address", error_rows[0].message)
		self.assertEqual(doc.status, "Error")

	def test_address_is_created_and_linked_to_supplier(self):
		doc = self._run_import(
			"Supplier",
			rows(
				[S_CODE, S_NAME, S_GROUP, A_LINE1, A_CITY, A_COUNTRY],
				[SUPPLIER_CODE, SUPPLIER_NAME, self.sg, "456 Vendor Rd", "Pune", "India"],
			),
		)
		self.assertEqual(doc.status, "Success")
		addr_names = self._linked("Supplier", SUPPLIER_CODE, "Address")
		log_dump = [(r.status, r.message) for r in doc.import_log]
		self.assertTrue(addr_names, f"Address missing. log={log_dump}")
		links = frappe.get_all(
			"Dynamic Link",
			filters={"parent": addr_names[0], "link_doctype": "Supplier", "link_name": SUPPLIER_CODE},
		)
		self.assertEqual(len(links), 1)

	def test_contact_is_created_and_linked_to_customer(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_LNAME],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "Sharma"],
			),
		)
		self.assertEqual(doc.status, "Success")

		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		log_dump = [(r.status, r.message) for r in doc.import_log]
		self.assertTrue(cont_names, f"Contact missing. log={log_dump}")

		contact = frappe.get_doc("Contact", cont_names[0])
		self.assertEqual(contact.first_name, "Rahul")
		self.assertEqual(contact.last_name, "Sharma")
		links = frappe.get_all(
			"Dynamic Link",
			filters={"parent": cont_names[0], "link_doctype": "Customer", "link_name": CUSTOMER_CODE},
		)
		self.assertEqual(len(links), 1)

	def test_contact_with_email_and_phone(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_LNAME, CON_EMAIL, CON_PHONE],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "Sharma", "rahul@test.com", "9876543210"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertTrue(cont_names)
		contact = frappe.get_doc("Contact", cont_names[0])
		self.assertIn("rahul@test.com", [e.email_id for e in contact.email_ids])
		self.assertIn("9876543210", [p.phone for p in contact.phone_nos])

	def test_contact_email_and_phone_via_child_table_subsection(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_EMAIL_CHILD, CON_PHONE_CHILD],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "rahul@child.com", "1112223333"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		log_dump = [(r.status, r.message) for r in doc.import_log]
		self.assertTrue(cont_names, f"Contact missing. log={log_dump}")
		contact = frappe.get_doc("Contact", cont_names[0])
		self.assertIn("rahul@child.com", [e.email_id for e in contact.email_ids])
		self.assertIn("1112223333", [p.phone for p in contact.phone_nos])

	def test_address_email_does_not_collide_with_contact_email(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, A_LINE1, A_CITY, A_COUNTRY, A_EMAIL, CON_FNAME, CON_EMAIL],
				[
					CUSTOMER_CODE,
					CUSTOMER_NAME,
					self.cg,
					"123 Main St",
					"Mumbai",
					"India",
					"billing@acme.com",
					"Rahul",
					"rahul@acme.com",
				],
			),
		)
		log_dump = [(r.status, r.message) for r in doc.import_log]
		self.assertEqual(doc.status, "Success", log_dump)

		addr_names = self._linked("Customer", CUSTOMER_CODE, "Address")
		self.assertTrue(addr_names, f"Address missing. log={log_dump}")
		self.assertEqual(frappe.db.get_value("Address", addr_names[0], "email_id"), "billing@acme.com")

		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertTrue(cont_names)
		contact = frappe.get_doc("Contact", cont_names[0])
		self.assertIn("rahul@acme.com", [e.email_id for e in contact.email_ids])
		self.assertNotIn("billing@acme.com", [e.email_id for e in contact.email_ids])

	def test_single_mode_bare_email_phone_become_primary_child_rows(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_EMAIL, CON_PHONE],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "single@acme.com", "5550001111"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertTrue(cont_names)
		contact = frappe.get_doc("Contact", cont_names[0])

		self.assertEqual(len(contact.email_ids), 1)
		self.assertEqual(contact.email_ids[0].email_id, "single@acme.com")
		self.assertTrue(contact.email_ids[0].is_primary)

		self.assertEqual(len(contact.phone_nos), 1)
		self.assertEqual(contact.phone_nos[0].phone, "5550001111")
		self.assertTrue(contact.phone_nos[0].is_primary_mobile_no)

	def test_contact_with_bare_and_child_emails_both_appended(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_EMAIL, CON_EMAIL_CHILD],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "primary@acme.com", "secondary@acme.com"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertTrue(cont_names)
		contact = frappe.get_doc("Contact", cont_names[0])
		emails = [e.email_id for e in contact.email_ids]
		self.assertIn("primary@acme.com", emails)
		self.assertIn("secondary@acme.com", emails)
		primaries = [e.email_id for e in contact.email_ids if e.is_primary]
		self.assertEqual(primaries, ["primary@acme.com"])

	def test_contact_is_created_and_linked_to_supplier(self):
		doc = self._run_import(
			"Supplier",
			rows(
				[S_CODE, S_NAME, S_GROUP, CON_FNAME, CON_LNAME],
				[SUPPLIER_CODE, SUPPLIER_NAME, self.sg, "Priya", "Sharma"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Supplier", SUPPLIER_CODE, "Contact")
		log_dump = [(r.status, r.message) for r in doc.import_log]
		self.assertTrue(cont_names, f"Contact missing. log={log_dump}")
		links = frappe.get_all(
			"Dynamic Link",
			filters={"parent": cont_names[0], "link_doctype": "Supplier", "link_name": SUPPLIER_CODE},
		)
		self.assertEqual(len(links), 1)

	def test_no_duplicate_on_reimport(self):
		row_data = rows(
			[C_CODE, C_NAME, C_GROUP],
			[CUSTOMER_CODE, CUSTOMER_NAME, self.cg],
		)
		self._run_import("Customer", row_data)
		self._run_import("Customer", row_data)
		self.assertEqual(frappe.db.count("Customer", {"customer_name": CUSTOMER_NAME}), 1)

	def test_same_contact_name_across_rows_merges_emails_and_phones(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_LNAME, CON_EMAIL, CON_PHONE],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "Sharma", "first@acme.com", "5550001111"],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "Sharma", "second@acme.com", "5550002222"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertEqual(len(cont_names), 1, "expected one merged contact, got multiple")
		contact = frappe.get_doc("Contact", cont_names[0])
		emails = sorted(e.email_id for e in contact.email_ids)
		phones = sorted(p.phone for p in contact.phone_nos)
		self.assertEqual(emails, ["first@acme.com", "second@acme.com"])
		self.assertEqual(phones, ["5550001111", "5550002222"])
		primary_emails = [e.email_id for e in contact.email_ids if e.is_primary]
		self.assertEqual(primary_emails, ["first@acme.com"])

	def test_different_contact_names_create_separate_contacts(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_LNAME, CON_EMAIL],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "Sharma", "rahul@acme.com"],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Priya", "Mehta", "priya@acme.com"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertEqual(len(cont_names), 2)

	def test_existing_contact_in_db_gets_emails_appended(self):
		cust = frappe.new_doc("Customer")
		cust.name = CUSTOMER_CODE
		cust.flags.name_set = True
		cust.customer_name = CUSTOMER_NAME
		cust.customer_type = "Company"
		cust.customer_group = self.cg
		cust.territory = self.ter
		cust.flags.ignore_permissions = True
		cust.insert()

		existing_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Rahul",
				"last_name": "Sharma",
				"email_ids": [{"email_id": "pre_existing@acme.com", "is_primary": 1}],
				"links": [{"link_doctype": "Customer", "link_name": CUSTOMER_CODE}],
			}
		).insert(ignore_permissions=True)

		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, CON_FNAME, CON_LNAME, CON_EMAIL],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Rahul", "Sharma", "from_import@acme.com"],
			),
		)
		self.assertEqual(doc.status, "Success")
		cont_names = self._linked("Customer", CUSTOMER_CODE, "Contact")
		self.assertEqual(len(cont_names), 1)
		self.assertEqual(cont_names[0], existing_contact.name)
		contact = frappe.get_doc("Contact", cont_names[0])
		emails = sorted(e.email_id for e in contact.email_ids)
		self.assertEqual(emails, ["from_import@acme.com", "pre_existing@acme.com"])
		primary = [e.email_id for e in contact.email_ids if e.is_primary]
		self.assertEqual(primary, ["pre_existing@acme.com"])

	def test_multiple_rows_same_party_code_creates_multiple_addresses(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, A_LINE1, A_CITY, A_COUNTRY],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Billing Addr", "Mumbai", "India"],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "Shipping Addr", "Delhi", "India"],
			),
		)
		self.assertEqual(doc.status, "Success")
		self.assertEqual(frappe.db.count("Customer", {"customer_name": CUSTOMER_NAME}), 1)
		self.assertEqual(len(self._linked("Customer", CUSTOMER_CODE, "Address")), 2)

	def test_existing_party_gets_address_added(self):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": CUSTOMER_NAME,
				"customer_type": "Company",
				"customer_group": self.cg,
				"territory": self.ter,
			}
		).insert(ignore_permissions=True)

		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, A_LINE1, A_CITY, A_COUNTRY],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "456 Side St", "Pune", "India"],
			),
		)
		self.assertEqual(doc.status, "Success")
		self.assertEqual(frappe.db.count("Customer", {"customer_name": CUSTOMER_NAME}), 1)
		existing_name = frappe.db.get_value("Customer", {"customer_name": CUSTOMER_NAME}, "name")
		self.assertTrue(self._linked("Customer", existing_name, "Address"))

	def test_partial_success_when_some_addresses_fail(self):
		doc = self._run_import(
			"Customer",
			rows(
				[C_CODE, C_NAME, C_GROUP, A_LINE1, A_CITY, A_COUNTRY],
				[CUSTOMER_CODE, CUSTOMER_NAME, self.cg, "123 Main St", "Mumbai", "India"],
				["TC-IMPORT-002", "Test Customer 2", self.cg, "", "Delhi", "India"],
			),
		)
		self.assertEqual(doc.status, "Partial Success")
		self.assertTrue(frappe.db.exists("Customer", CUSTOMER_CODE))
		self.assertTrue(frappe.db.exists("Customer", "TC-IMPORT-002"))
		self.assertTrue(self._linked("Customer", CUSTOMER_CODE, "Address"))
