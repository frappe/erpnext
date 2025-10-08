# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import zipfile
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate import unzip_file


class DummyFile:
	def __init__(self, file_name):
		self.file_name = file_name


class TestRemittanceofTDScertificate(FrappeTestCase):
	def test_get_pan_list_TC_B_187(self):
		from erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate import (
			get_pan_list,
		)

		certificate_name_list = [
			{"file_name": "ABCDE1234F_cert.pdf"},
			{"file_name": "XYZ9876543_tax.pdf"},
			{"file_name": "NOT_A_PDF.txt"},
		]

		expected_result = [
			{"file_name": "ABCDE1234F_cert.pdf", "pan": "ABCDE1234F"},
			{"file_name": "XYZ9876543_tax.pdf", "pan": "XYZ9876543"},
		]

		result = get_pan_list(certificate_name_list)
		self.assertEqual(result, expected_result)

	def setUp(self):
		content = b"Dummy content"
		self.test_file = save_file(
			fname="test_attachment.txt",
			content=content,
			dt="User",
			dn=frappe.session.user,
			folder=None,
			decode=False,
		)
		self.test_zip_file = save_file(
			fname="test_attachment.txt.zip",
			content=content,
			dt="User",
			dn=frappe.session.user,
			folder=None,
			decode=False,
		)
		self.test_item = {"file_name": self.test_file.file_name}
		self.test_zip_item = {"file_name": self.test_zip_file.file_name}

	def test_create_attachment_TC_B_188(self):
		from erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate import (
			create_attachment,
		)

		result = create_attachment(self.test_item)

		self.assertIn("fname", result)
		self.assertIn("fcontent", result)
		self.assertEqual(result["fcontent"], b"Dummy content")

	def test_get_emails_and_unrecored_pan_list_TC_B_189(self):
		from erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate import (
			get_emails_and_unrecored_pan_list,
		)

		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Supplier With Email",
				"pan": "ABCDE1234F",
				"email_id": "supplier@example.com",
			}
		).insert(ignore_if_duplicate=True)

		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Supplier Without Email",
				"pan": "DGAPK9160G",
				"email_id": "",
			}
		).insert(ignore_if_duplicate=True)

		test_data = [
			{"pan": "ABCDE1234F", "file_name": "file1.pdf"},
			{"pan": "DGAPK9160G", "file_name": "file2.pdf"},
			{"pan": "DGAPK9160T", "file_name": "file3.pdf"},
		]

		unrecorded_pan, emails_and_pan_list, pan_without_emails = get_emails_and_unrecored_pan_list(test_data)

		self.assertEqual(len(emails_and_pan_list), 1)
		self.assertEqual(emails_and_pan_list[0]["pan"], "ABCDE1234F")
		self.assertEqual(emails_and_pan_list[0]["status"], "Success")

		self.assertEqual(len(pan_without_emails), 1)
		self.assertEqual(pan_without_emails[0]["pan"], "DGAPK9160G")
		self.assertEqual(pan_without_emails[0]["status"], "Failure")

		self.assertEqual(len(unrecorded_pan), 1)
		self.assertEqual(unrecorded_pan[0]["pan"], "DGAPK9160T")
		self.assertEqual(unrecorded_pan[0]["status"], "Failure")

	def test_get_email_list_TC_B_225(self):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Supplier With Email",
				"pan": "ABCDE1234F",
				"email_id": "email@domain.com",
			}
		).insert(ignore_if_duplicate=True)

		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Supplier Without Email",
				"pan": "DGAPK9160G",
				"email_id": "",
			}
		).insert(ignore_if_duplicate=True)

		doc = frappe.get_doc(
			{
				"doctype": "Remittance of TDS certificate",
				"email_template": "Dispatch Notification",
				"upload_doc": "self.test_file",
			}
		).insert()

		filenames = ["PAN123_certificate.pdf", "PAN456_certificate.pdf", "PAN789_certificate.pdf"]
		for fname in filenames:
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": fname,
					"attached_to_doctype": doc.doctype,
					"attached_to_name": doc.name,
					"is_private": 1,
					"content": "Dummy content for testing",
				}
			).insert()

		import erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate
		from erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate import (
			get_email_list,
			get_pan_list,
		)

		# def mock_get_pan_list(certificate_name_list):
		# 	return [
		# 		{"pan": "ABCDE1234F", "file_name": "PAN123_certificate.pdf"},
		# 		{"pan": "DGAPK9160G", "file_name": "PAN456_certificate.pdf"},
		# 		{"pan": "DGAPK9160T", "file_name": "PAN789_certificate.pdf"},
		# 	]

		# erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate.get_pan_list = mock_get_pan_list

		emails_and_pan_list = get_email_list(doc)

		self.assertEqual(len(emails_and_pan_list), 1)
		self.assertEqual(emails_and_pan_list[0]["pan"], "ABCDE1234F")

		error_logs = doc.error_logs
		self.assertEqual(len(error_logs), 3)

		statuses = [log.status for log in error_logs]
		self.assertIn("Success", statuses)
		self.assertIn("Failure", statuses)

	def test_unzip_file_TC_B_226(self):
		import io

		zip_buffer = io.BytesIO()
		with zipfile.ZipFile(zip_buffer, "w") as zip_file:
			zip_file.writestr("test_inside.txt", "This is test content")

		zip_buffer.seek(0)

		file_doc = save_file(
			fname="test_file.zip",
			content=zip_buffer.getvalue(),
			dt="User",
			dn="frappe.session.user",
			is_private=0,
		)
		file_doc.reload()

		extracted_files = unzip_file(file_doc.file_name)

		self.assertTrue(extracted_files)
		extracted_file_names = [f.file_name for f in extracted_files]
		self.assertIn("test_inside.txt", extracted_file_names)

	@patch("erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate.unzip_file")
	def test_unpack_TC_B_227(self, mock_unzip_file):
		doc = frappe.get_doc(
			{
				"doctype": "Remittance of TDS Certificate",
				"upload_doc": "/files/test.zip",
				"subject": "Test Email",
				"description": "This is a test email body.",
				"sender_email": "test@example.com",
			}
		)

		mock_unzip_file.return_value = None

		with patch(
			"erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate.get_email_list"
		) as mock_get_email_list, patch(
			"erpnext.buying.doctype.remittance_of_tds_certificate.remittance_of_tds_certificate.create_attachment"
		) as mock_create_attachment, patch("frappe.sendmail") as mock_sendmail:
			mock_get_email_list.return_value = [
				{
					"email_id": "user@example.com",
					"file_name": "test.pdf",
					"pan": "ABCDE1234F",
					"supplier_name": "Test Supplier",
					"reason": "",
					"status": "",
				}
			]
			mock_create_attachment.return_value = {"fid": "dummy"}

			result = doc.unpack()
			self.assertEqual(result, 1)
			mock_sendmail.assert_called_once()
