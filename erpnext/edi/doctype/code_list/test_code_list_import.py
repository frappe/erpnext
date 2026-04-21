# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
import requests

from erpnext.edi.doctype.code_list import code_list_import
from erpnext.tests.utils import ERPNextTestSuite

SAMPLE_GENERICODE = b"""<?xml version="1.0" encoding="UTF-8"?>
<CodeList>
	<Identification>
		<ShortName>Test Code List</ShortName>
		<Version>1.0</Version>
		<CanonicalUri>test-code-list</CanonicalUri>
		<LongName>Code list for tests</LongName>
		<Agency>
			<ShortName>Test Agency</ShortName>
			<Identifier>TEST</Identifier>
		</Agency>
		<LocationUri>https://example.com/codelists/test.xml</LocationUri>
	</Identification>
	<CanonicalVersionUri>test-code-list-v1</CanonicalVersionUri>
	<ColumnSet>
		<Column Id="code" />
		<Column Id="name" />
		<Column Id="category" />
	</ColumnSet>
	<SimpleCodeList>
		<Row>
			<Value ColumnRef="code"><SimpleValue>A</SimpleValue></Value>
			<Value ColumnRef="name"><SimpleValue>Alpha</SimpleValue></Value>
			<Value ColumnRef="category"><SimpleValue>Group 1</SimpleValue></Value>
		</Row>
		<Row>
			<Value ColumnRef="code"><SimpleValue>B</SimpleValue></Value>
			<Value ColumnRef="name"><SimpleValue>Beta</SimpleValue></Value>
			<Value ColumnRef="category"><SimpleValue>Group 2</SimpleValue></Value>
		</Row>
		<Row>
			<Value ColumnRef="code"><SimpleValue>C</SimpleValue></Value>
			<Value ColumnRef="name"><SimpleValue>Gamma</SimpleValue></Value>
			<Value ColumnRef="category"><SimpleValue>Group 1</SimpleValue></Value>
		</Row>
	</SimpleCodeList>
</CodeList>
"""


class TestCodeListImport(ERPNextTestSuite):
	def test_import_genericode_rejects_remote_file_url(self):
		self.set_upload_context(
			file_name="trusted.xml",
			file_url="https://example.com/codelists/trusted.xml",
		)

		with patch("erpnext.edi.doctype.code_list.code_list_import.requests.get") as mock_get:
			with self.assertRaisesRegex(
				frappe.ValidationError, "Importing Code Lists from remote URLs is not allowed."
			):
				code_list_import.import_genericode()

		mock_get.assert_not_called()

	def test_import_genericode_rejects_file_scheme_url(self):
		self.set_upload_context(
			file_name="trusted.xml",
			file_url="file:///tmp/trusted.xml",
		)

		with patch("erpnext.edi.doctype.code_list.code_list_import.requests.get") as mock_get:
			with self.assertRaisesRegex(
				frappe.ValidationError, "Importing Code Lists from remote URLs is not allowed."
			):
				code_list_import.import_genericode()

		mock_get.assert_not_called()

	def test_import_genericode_from_trusted_url(self):
		response = Mock()
		response.content = SAMPLE_GENERICODE
		response.raise_for_status.return_value = None

		with patch(
			"erpnext.edi.doctype.code_list.code_list_import.requests.get",
			return_value=response,
		) as mock_get:
			import_result = code_list_import.import_genericode_from_url(
				"https://example.com/codelists/trusted.xml"
			)

		self.assert_import_response(import_result)
		mock_get.assert_called_once_with(
			"https://example.com/codelists/trusted.xml",
			timeout=code_list_import.GENERICODE_FETCH_TIMEOUT,
		)

		file_doc = frappe.get_doc("File", import_result["file"])
		self.assertEqual(file_doc.file_name, "trusted.xml")
		self.assertFalse(file_doc.file_url.startswith("https://"))

	def test_import_genericode_from_trusted_url_propagates_fetch_errors(self):
		with patch(
			"erpnext.edi.doctype.code_list.code_list_import.requests.get",
			side_effect=requests.Timeout,
		):
			with self.assertRaises(requests.Timeout):
				code_list_import.import_genericode_from_url("https://example.com/codelists/trusted.xml")

	def test_import_genericode_from_uploaded_file_returns_metadata(self):
		self.set_upload_context(content=SAMPLE_GENERICODE, file_name="uploaded_genericode.xml")

		import_result = code_list_import.import_genericode()

		self.assert_import_response(import_result)

		file_doc = frappe.get_doc("File", import_result["file"])
		self.assertEqual(file_doc.file_name, "uploaded_genericode.xml")

	def test_process_genericode_import_reads_file_doc_content(self):
		self.set_upload_context(content=SAMPLE_GENERICODE, file_name="uploaded_genericode.xml")

		import_result = code_list_import.import_genericode()
		count = code_list_import.process_genericode_import(
			code_list_name=import_result["code_list"],
			file_name=import_result["file"],
			code_column="code",
			title_column="name",
		)

		self.assertEqual(count, 3)
		self.assertEqual(frappe.db.count("Common Code", {"code_list": import_result["code_list"]}), 3)
		self.assertEqual(
			frappe.db.get_value(
				"Common Code",
				{"code_list": import_result["code_list"], "common_code": "A"},
				"title",
			),
			"Alpha",
		)

	def test_import_genericode_from_local_file_url(self):
		source_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "library_genericode.xml",
				"content": SAMPLE_GENERICODE,
				"is_private": 1,
			}
		).insert()
		self.set_upload_context(file_name=source_file.file_name, file_url=source_file.file_url)

		import_result = code_list_import.import_genericode()

		self.assert_import_response(import_result)

	def set_upload_context(
		self,
		content: bytes | None = None,
		file_name: str = "genericode.xml",
		file_url: str | None = None,
		docname: str | None = None,
	):
		attrs = ("form_dict", "uploaded_file", "uploaded_file_url", "uploaded_filename")
		originals = {attr: getattr(frappe.local, attr, None) for attr in attrs}

		frappe.local.form_dict = frappe._dict(doctype="Code List", docname=docname)
		frappe.local.uploaded_file = content
		frappe.local.uploaded_file_url = file_url
		frappe.local.uploaded_filename = file_name

		def restore():
			for attr, value in originals.items():
				setattr(frappe.local, attr, value)

		self.addCleanup(restore)

	def assert_import_response(self, import_result):
		self.assertEqual(
			set(import_result),
			{
				"code_list",
				"code_list_title",
				"file",
				"columns",
				"example_values",
				"filterable_columns",
			},
		)
		self.assertEqual(import_result["code_list"], "test-code-list-v1")
		self.assertEqual(import_result["code_list_title"], "Test Code List")
		self.assertEqual(import_result["columns"], ["code", "name", "category"])
		self.assertEqual(import_result["example_values"]["code"], ["A", "B", "C"])
		self.assertEqual(import_result["example_values"]["name"], ["Alpha", "Beta", "Gamma"])
		self.assertEqual(import_result["example_values"]["category"], ["Group 1", "Group 2", "Group 1"])
		self.assertCountEqual(import_result["filterable_columns"]["category"], ["Group 1", "Group 2"])
		self.assertTrue(frappe.db.exists("Code List", import_result["code_list"]))
		self.assertTrue(frappe.db.exists("File", import_result["file"]))
