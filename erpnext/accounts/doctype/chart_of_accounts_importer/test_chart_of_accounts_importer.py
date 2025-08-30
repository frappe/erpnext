# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
import os
import tempfile

from frappe.tests import IntegrationTestCase
from frappe.tests.utils import FrappeTestCase
from erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer import (
    generate_data_from_csv,
    generate_data_from_excel,
)
# We patch reader functions on the module itself
from erpnext.accounts.doctype.chart_of_accounts_importer import chart_of_accounts_importer as importer_module

class TestChartofAccountsImporter(IntegrationTestCase):
        pass


class TestGenerateDataFromCSV(FrappeTestCase):
    """Unit tests for pure CSV parsing logic, independent of DB."""

    def _tmp_csv(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
        try:
            f.write(content)
            f.flush()
            return f.name
        finally:
            f.close()

    def _file_stub(self, path: str):
        return frappe._dict(get_full_path=lambda: path)

    def _cleanup(self, path: str):
        try:
            os.remove(path)
        except Exception:
            pass


    def test_bom_and_empty_rows(self):
        csv_content = u"\ufeffHeader1,Header2,Header3\nA,,C\n  ,  ,  \nB,D\n"
        p = self._tmp_csv(csv_content)
        try:
            data = generate_data_from_csv(self._file_stub(p), as_dict=False)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0][0], "A")
            self.assertEqual(data[0][1], "A")
            self.assertEqual(data[0][2], "C")
            self.assertEqual(data[0][3], "C")
            self.assertGreaterEqual(len(data[0]), 8)
            self.assertEqual(data[1][0], "B")
            self.assertEqual(data[1][1], "D")
        finally:
            self._cleanup(p)


    def test_as_dict_mode(self):
        csv_content = u"\ufeffAccount Name,Account Code,Group?\nCash,,Yes\n"
        p = self._tmp_csv(csv_content)
        try:
            data = generate_data_from_csv(self._file_stub(p), as_dict=True)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            row = data[0]

            # Always present:
            self.assertEqual(row["account_name"], "Cash")
            self.assertEqual(row["account_code"], "")

            # Accept either "group" or "group?" depending on frappe.scrub behavior
            group_val = row.get("group", row.get("group?"))
            self.assertEqual(group_val, "Yes")

            # Optional: ensure there isn't some unexpected third variant
            allowed_keys = {"account_name", "account_code", "group", "group?"}
            self.assertTrue(set(row.keys()).issubset(allowed_keys))
        finally:
            self._cleanup(p)


    def test_empty_csv(self):
        p = self._tmp_csv("")
        try:
            data = generate_data_from_csv(self._file_stub(p))
            self.assertEqual(data, [])
        finally:
            self._cleanup(p)


    def test_headers_only(self):
        p = self._tmp_csv("Col1,Col2\n")
        try:
            data = generate_data_from_csv(self._file_stub(p))
            self.assertEqual(data, [])
        finally:
            self._cleanup(p)


    def test_exactly_8_columns(self):
        headers = ",".join([f"H{i}" for i in range(1, 9)])
        row = ",".join([f"A{i}" for i in range(1, 9)])
        p = self._tmp_csv(headers + "\n" + row + "\n")
        try:
            data = generate_data_from_csv(self._file_stub(p))
            self.assertEqual(len(data[0]), 8)
            self.assertEqual(data[0][0], "A1")
            self.assertEqual(data[0][7], "A8")
        finally:
            self._cleanup(p)


    def test_more_than_8_columns(self):
        headers = ",".join([f"H{i}" for i in range(1, 11)])
        row = ",".join([f"B{i}" for i in range(1, 11)])
        p = self._tmp_csv(headers + "\n" + row + "\n")
        try:
            data = generate_data_from_csv(self._file_stub(p))
            self.assertGreaterEqual(len(data[0]), 10)
            self.assertEqual(data[0][9], "B10")
        finally:
            self._cleanup(p)


    def test_short_rows_are_padded(self):
        p = self._tmp_csv("H1,H2,H3\nX,Y\n")
        try:
            data = generate_data_from_csv(self._file_stub(p))
            self.assertEqual(data[0][0], "X")
            self.assertEqual(data[0][1], "Y")
            self.assertGreaterEqual(len(data[0]), 8)
            self.assertTrue(all(c == "" for c in data[0][2:8]))
        finally:
            self._cleanup(p)

class TestGenerateDataFromExcel(FrappeTestCase):
    """Unit tests for Excel parsing, using monkey-patched readers (no real xlsx/xls files)."""

    def setUp(self):
        # Keep originals so we can restore in tearDown
        self._orig_read_xlsx = getattr(importer_module, "read_xlsx_file_from_attached_file", None)
        self._orig_read_xls  = getattr(importer_module, "read_xls_file_from_attached_file", None)

    def tearDown(self):
        # Restore originals (important to avoid cross-test side effects)
        if self._orig_read_xlsx is not None:
            importer_module.read_xlsx_file_from_attached_file = self._orig_read_xlsx
        if self._orig_read_xls is not None:
            importer_module.read_xls_file_from_attached_file = self._orig_read_xls

    def _file_stub(self, content: bytes = b""):
        # Excel path calls file_doc.get_content(); we can return anything since we patch the readers
        return frappe._dict(get_content=lambda: content)

    def test_excel_as_dict_mode_and_empty_rows(self):
        # Simulate what the reader would return: first row headers, then data rows
        rows = [
            ["Account Name", "Account Code", "Group?" ],
            ["Cash",         "",             "Yes"    ],
            ["  ",           "  ",           "   "    ],  # whitespace-only -> should be skipped
            ["Bank",         "123",          ""       ],
        ]
        importer_module.read_xlsx_file_from_attached_file = lambda fcontent: rows

        file_doc = self._file_stub()
        data = generate_data_from_excel(file_doc, extension="xlsx", as_dict=True)
        self.assertEqual(len(data), 2)

        # Row 1 (Cash)
        r0 = data[0]
        self.assertEqual(r0["account_name"], "Cash")
        self.assertEqual(r0["account_code"], "")
        # Accept "group" or "group?" depending on frappe.scrub behavior
        self.assertEqual(r0.get("group", r0.get("group?")), "Yes")

        # Row 2 (Bank)
        r1 = data[1]
        self.assertEqual(r1["account_name"], "Bank")
        self.assertEqual(r1["account_code"], "123")
        self.assertFalse(bool(r1.get("group", r1.get("group?"))))

    def test_excel_list_mode_padding_and_safe_indexing(self):
        rows = [
            ["H1","H2","H3","H4","H5","H6","H7","H8"],
            ["A1","",   "A3"],        # short row; row[1] should backfill from row[0]; row[3] from row[2]
            ["B1","B2"],              # even shorter; safe indexing + padding to >= 8 cols
        ]
        importer_module.read_xlsx_file_from_attached_file = lambda fcontent: rows

        file_doc = self._file_stub()
        data = generate_data_from_excel(file_doc, extension="xlsx", as_dict=False)

        # Row 0: backfills
        self.assertEqual(data[0][0], "A1")
        self.assertEqual(data[0][1], "A1")  # backfilled
        self.assertEqual(data[0][2], "A3")
        self.assertEqual(data[0][3], "A3")  # backfilled
        self.assertGreaterEqual(len(data[0]), 8)

        # Row 1: very short, must be padded
        self.assertEqual(data[1][0], "B1")
        self.assertEqual(data[1][1], "B2")
        self.assertGreaterEqual(len(data[1]), 8)
        self.assertTrue(all(c == "" for c in data[1][2:8]))

    def test_excel_headers_only(self):
        rows = [["Col1","Col2","Col3"]]  # only headers
        importer_module.read_xls_file_from_attached_file = lambda content: rows

        file_doc = self._file_stub()
        data = generate_data_from_excel(file_doc, extension="xls", as_dict=False)
        self.assertEqual(data, [])

    def test_excel_more_than_8_columns_preserved(self):
        headers = [f"H{i}" for i in range(1, 11)]  # 10 cols
        row     = [f"V{i}" for i in range(1, 11)]
        rows = [headers, row]
        importer_module.read_xlsx_file_from_attached_file = lambda fcontent: rows

        file_doc = self._file_stub()
        data = generate_data_from_excel(file_doc, extension="xlsx", as_dict=False)
        self.assertEqual(len(data), 1)
        self.assertGreaterEqual(len(data[0]), 10)
        self.assertEqual(data[0][8],  "V9")
        self.assertEqual(data[0][9],  "V10")
