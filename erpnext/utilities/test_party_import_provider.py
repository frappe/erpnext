# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import csv
import io
from unittest.mock import patch

import frappe
from frappe.core.doctype.data_import.exporter import Exporter
from frappe.core.doctype.data_import.import_provider import get_import_provider
from frappe.core.doctype.data_import.importer import INSERT, UPDATE, Importer

from erpnext.tests.utils import ERPNextTestSuite

USER = "party-import@example.com"
PREFIX = "_Test Party Import"


class TestPartyImportProvider(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": USER,
					"first_name": "Party Import",
					"send_welcome_email": 0,
					"roles": [{"role": "Sales Master Manager"}, {"role": "Purchase Master Manager"}],
				}
			).insert(ignore_permissions=True)
		cls.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0})
		cls.territory = frappe.db.get_value("Territory", {"is_group": 0})
		cls.supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0})
		frappe.cache.delete_value("data_import_column_header_map")
		frappe.db.commit()  # nosemgrep

	def setUp(self):
		self.started = frappe.utils.now()
		# The importer commits every row, so the test's rollback can't undo it.
		self.addCleanup(self.delete_imported_records)

	def test_insert_creates_contacts_and_addresses(self):
		for party, party_columns, party_values in (
			(
				"Customer",
				["customer_name", "customer_type", "customer_group", "territory"],
				[f"{PREFIX} Customer", "Company", self.customer_group, self.territory],
			),
			("Supplier", ["supplier_name", "supplier_group"], [f"{PREFIX} Supplier", self.supplier_group]),
		):
			with self.subTest(party=party):
				blank = [""] * len(party_values)
				self.run_import(
					party,
					INSERT,
					[
						[
							*party_columns,
							"contacts.first_name",
							"contacts.email_id",
							"contacts.is_primary_contact",
							"addresses.address_line1",
							"addresses.city",
							"addresses.country",
							"addresses.is_primary_address",
						],
						[*party_values, "Ann", "ann@example.com", "", "1 Main St", "Berlin", "Germany", ""],
						[*blank, "Bob", "bob@example.com", "1", "9 Dock Rd", "Hamburg", "Germany", "1"],
						[*blank, "Cy", "cy@example.com", "", "", "", "", ""],
					],
				)

				name = self.get_party(party, party_values[0])
				self.assertEqual(len(self.linked("Contact", party, name)), 3)
				self.assertEqual(len(self.linked("Address", party, name)), 2)

				key = frappe.scrub(party)
				primary_contact, primary_address = frappe.db.get_value(
					party, name, [f"{key}_primary_contact", f"{key}_primary_address"]
				)
				self.assertEqual(frappe.db.get_value("Contact", primary_contact, "first_name"), "Bob")
				self.assertEqual(
					frappe.db.get_value("Address", primary_address, "address_line1"), "9 Dock Rd"
				)

	def test_update_reuses_existing_contacts_and_addresses(self):
		columns = [
			"customer_name",
			"customer_type",
			"customer_group",
			"territory",
			"contacts.email_id",
			"addresses.address_line1",
			"addresses.city",
			"addresses.country",
		]
		values = [
			f"{PREFIX} Reimport",
			"Company",
			self.customer_group,
			self.territory,
			"reimport@example.com",
			"1 Main St",
			"Berlin",
			"Germany",
		]
		self.run_import("Customer", INSERT, [columns, values])
		name = self.get_party("Customer", values[0])
		primary = frappe.db.get_value(
			"Customer", name, ["customer_primary_contact", "customer_primary_address"]
		)

		self.run_import("Customer", UPDATE, [["ID", *columns], [name, *values]])

		self.assertEqual(len(self.linked("Contact", "Customer", name)), 1)
		self.assertEqual(len(self.linked("Address", "Customer", name)), 1)
		self.assertEqual(
			frappe.db.get_value("Customer", name, ["customer_primary_contact", "customer_primary_address"]),
			primary,
		)

	def test_plain_headers_map_only_when_unambiguous(self):
		importer = self.get_importer(
			"Supplier",
			INSERT,
			[
				["Supplier Name", "Country", "Address Line 1", "City/Town", "Mobile No", "Email Address"],
				[f"{PREFIX} Plain", "Germany", "1 Main St", "Berlin", "+49 30 111", "plain@example.com"],
			],
		)
		mapped = {}
		for column in importer.import_file.columns:
			df = column.df
			if df:
				table = df.child_table_df.fieldname if df.get("is_child_table_field") else "Supplier"
				mapped[column.header_title] = f"{table}.{df.fieldname}"
			else:
				mapped[column.header_title] = None

		self.assertEqual(
			mapped,
			{
				"Supplier Name": "Supplier.supplier_name",
				# Supplier has its own Country field, so the header stays with it.
				"Country": "Supplier.country",
				"Address Line 1": "addresses.address_line1",
				"City/Town": "addresses.city",
				"Mobile No": "contacts.mobile_no",
				# Both Contact and Address have Email Address; the user picks one in the mapper.
				"Email Address": None,
			},
		)

	def test_address_without_line_1_fails_only_that_row(self):
		columns = [
			"customer_name",
			"customer_type",
			"customer_group",
			"territory",
			"contacts.email_id",
			"addresses.address_line1",
			"addresses.city",
			"addresses.country",
		]
		party = ["Company", self.customer_group, self.territory]
		self.run_import(
			"Customer",
			INSERT,
			[
				columns,
				[f"{PREFIX} No Line 1", *party, "noline1@example.com", "", "Berlin", "Germany"],
				[f"{PREFIX} Good", *party, "good@example.com", "5 Good St", "Berlin", "Germany"],
			],
		)

		failed = frappe.get_all(
			"Data Import Log",
			filters={"data_import": ["is", "not set"], "success": 0, "creation": [">=", self.started]},
			pluck="messages",
		)
		self.assertEqual(len(failed), 1)
		self.assertIn("Value missing for Address: Address Line 1", failed[0])
		# The failed row is rolled back as a whole, including its contact.
		self.assertFalse(frappe.db.exists("Customer", {"customer_name": f"{PREFIX} No Line 1"}))
		self.assertFalse(frappe.db.exists("Contact", {"email_id": "noline1@example.com"}))
		self.assertTrue(frappe.db.exists("Customer", {"customer_name": f"{PREFIX} Good"}))

	def test_contact_names_fall_back_to_party_name(self):
		self.run_import(
			"Customer",
			INSERT,
			[
				[
					"customer_name",
					"customer_type",
					"customer_group",
					"territory",
					"contacts.first_name",
					"contacts.email_id",
				],
				["John Paul Smith", "Individual", self.customer_group, self.territory, "", "jps@example.com"],
				["", "", "", "", "Ann", "ann-jps@example.com"],
				[f"{PREFIX} Company", "Company", self.customer_group, self.territory, "", "co@example.com"],
			],
		)

		contact = frappe.db.get_value(
			"Contact", {"email_id": "jps@example.com"}, ["first_name", "middle_name", "last_name"]
		)
		self.assertEqual(contact, ("John", "Paul", "Smith"))
		self.assertEqual(
			frappe.db.get_value("Contact", {"email_id": "ann-jps@example.com"}, "first_name"), "Ann"
		)
		self.assertEqual(
			frappe.db.get_value("Contact", {"email_id": "co@example.com"}, "company_name"),
			f"{PREFIX} Company",
		)

	def test_export_includes_contacts_and_addresses(self):
		self.run_import(
			"Customer",
			INSERT,
			[
				[
					"customer_name",
					"customer_type",
					"customer_group",
					"territory",
					"contacts.first_name",
					"contacts.email_id",
					"contacts.is_primary_contact",
					"addresses.address_line1",
					"addresses.city",
					"addresses.country",
				],
				[
					f"{PREFIX} Export",
					"Company",
					self.customer_group,
					self.territory,
					"Ann",
					"ann-export@example.com",
					"",
					"1 Main St",
					"Berlin",
					"Germany",
				],
				["", "", "", "", "Bob", "bob-export@example.com", "1", "", "", ""],
			],
		)
		name = self.get_party("Customer", f"{PREFIX} Export")

		with self.set_user(USER):
			export = Exporter(
				"Customer",
				export_fields={
					"Customer": ["name", "customer_name"],
					"contacts": ["first_name", "email_id"],
					"addresses": ["address_line1", "city"],
				},
				export_data=True,
				export_filters={"name": name},
			).get_csv_array()

		self.assertEqual(
			export,
			[
				[
					"ID",
					"Customer Name",
					"First Name (Contact)",
					"Email Address (Contact)",
					"Address Line 1 (Address)",
					"City/Town (Address)",
				],
				# the primary contact comes first
				[name, f"{PREFIX} Export", "Bob", "bob-export@example.com", "1 Main St", "Berlin"],
				["", "", "Ann", "ann-export@example.com", "", ""],
			],
		)

		# importing the export back as an update applies it without duplicating the linked records
		export[1][1] = f"{PREFIX} Export Renamed"
		self.run_import("Customer", UPDATE, export)
		self.assertEqual(frappe.db.get_value("Customer", name, "customer_name"), f"{PREFIX} Export Renamed")
		self.assertEqual(len(self.linked("Contact", "Customer", name)), 2)
		self.assertEqual(len(self.linked("Address", "Customer", name)), 1)

	def test_export_orders_by_each_partys_own_primary(self):
		columns = ["customer_name", "customer_type", "customer_group", "territory", "contacts.email_id"]
		for party, email in (("A", "shared@example.com"), ("B", "own-b@example.com")):
			values = [f"{PREFIX} Shared {party}", "Company", self.customer_group, self.territory, email]
			self.run_import("Customer", INSERT, [columns, values])
		party_a = self.get_party("Customer", f"{PREFIX} Shared A")
		party_b = self.get_party("Customer", f"{PREFIX} Shared B")

		# A's primary contact also links to B, where it is not the primary
		shared = frappe.get_doc(
			"Contact", frappe.db.get_value("Customer", party_a, "customer_primary_contact")
		)
		shared.append("links", {"link_doctype": "Customer", "link_name": party_b})
		shared.save(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep
		self.assertTrue(shared.is_primary_contact)

		with self.set_user(USER):
			export = Exporter(
				"Customer",
				export_fields={"Customer": ["name"], "contacts": ["email_id", "is_primary_contact"]},
				export_data=True,
				export_filters={"name": party_b},
			).get_csv_array()

		self.assertEqual(
			export[1:],
			[[party_b, "own-b@example.com", 1], ["", "shared@example.com", 0]],
		)

	def test_tables_the_user_cannot_read_are_left_out(self):
		has_permission = frappe.has_permission

		def cannot_read_contacts(doctype, *args, **kwargs):
			return doctype != "Contact" and has_permission(doctype, *args, **kwargs)

		with self.set_user(USER), patch("frappe.has_permission", cannot_read_contacts):
			tables = [
				t["fieldname"] for t in get_import_provider("Customer").get_import_fields()["child_tables"]
			]
			# a request naming the table anyway gets no column for it
			header = Exporter(
				"Customer",
				export_fields={"Customer": ["customer_name"], "contacts": ["email_id"]},
			).get_csv_array()[0]

		self.assertNotIn("contacts", tables)
		self.assertIn("addresses", tables)
		self.assertEqual(header, ["Customer Name"])

	def get_importer(self, doctype, import_type, rows):
		content = io.StringIO()
		csv.writer(content).writerows(rows)
		file = frappe.get_doc(
			doctype="File",
			file_name=f"{frappe.generate_hash(length=10)}.csv",
			content=content.getvalue(),
			is_private=1,
		).insert(ignore_permissions=True)
		frappe.db.commit()  # so a failed row's rollback doesn't remove the file  # nosemgrep
		self.addCleanup(frappe.delete_doc, "File", file.name, ignore_permissions=True)

		data_import = frappe.get_doc(
			doctype="Data Import",
			reference_doctype=doctype,
			import_type=import_type,
			import_file=file.file_url,
		)
		return Importer(doctype, data_import=data_import)

	def run_import(self, doctype, import_type, rows):
		importer = self.get_importer(doctype, import_type, rows)
		with self.set_user(USER):
			return importer.import_data()

	def get_party(self, doctype, party_name):
		return frappe.db.get_value(
			doctype, {f"{frappe.scrub(doctype)}_name": party_name, "creation": [">=", self.started]}
		)

	def linked(self, doctype, link_doctype, link_name):
		return frappe.get_all(
			doctype,
			filters=[
				["Dynamic Link", "link_doctype", "=", link_doctype],
				["Dynamic Link", "link_name", "=", link_name],
			],
			pluck="name",
		)

	def delete_imported_records(self):
		for party in ("Customer", "Supplier"):
			name_field = f"{frappe.scrub(party)}_name"
			for row in frappe.get_all(
				party, filters={"creation": [">=", self.started]}, fields=["name", name_field]
			):
				if not (row[name_field].startswith(PREFIX) or row[name_field] == "John Paul Smith"):
					continue
				for doctype in ("Contact", "Address"):
					for name in self.linked(doctype, party, row.name):
						frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
				frappe.delete_doc(party, row.name, force=True, ignore_permissions=True)
		frappe.db.delete(
			"Data Import Log", {"data_import": ["is", "not set"], "creation": [">=", self.started]}
		)
		frappe.db.commit()  # nosemgrep
