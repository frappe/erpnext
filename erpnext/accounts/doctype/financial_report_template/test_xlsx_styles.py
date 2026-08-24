# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import unittest

from frappe.utils.xlsxutils import XLSXMetadata

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	get_special_view_cells,
	get_xlsx_styles,
)

BOLD = {"bold": True}
DANGER = {"font_color": "#dc3545"}
SUCCESS = {"font_color": "#28a745"}
GROWTH_FORMAT = {"num_format": '+0.00"%";-0.00"%";0"%"'}


def standard_columns(overrides=None):
	"""account + two period columns + total, as `get_columns` emits them."""
	columns = {
		0: {"fieldname": "account", "fieldtype": "Link"},
		1: {"fieldname": "mar_2026", "fieldtype": "Currency", "options": "currency"},
		2: {"fieldname": "jun_2026", "fieldtype": "Currency", "options": "currency"},
		3: {"fieldname": "total", "fieldtype": "Currency", "options": "currency"},
	}
	for col_idx, extra in (overrides or {}).items():
		columns[col_idx].update(extra)
	return columns


def standard_rows():
	return {
		# group row
		1: {
			"account": "Income",
			"is_group": 1,
			"parent_account": "",
			"mar_2026": 10.0,
			"jun_2026": -5.0,
			"total": 5.0,
			"currency": "INR",
		},
		# leaf row
		2: {
			"account": "Sales",
			"is_group": 0,
			"parent_account": "Income",
			"mar_2026": 10.0,
			"jun_2026": -5.0,
			"total": 5.0,
			"currency": "INR",
		},
		# top-level total row that reddens negatives
		3: {
			"account": "Profit for the year",
			"warn_if_negative": True,
			"mar_2026": -2.0,
			"jun_2026": 4.0,
			"total": 2.0,
			"currency": "INR",
		},
	}


class TestXlsxStyles(unittest.TestCase):
	"""Pure styling assertions — needs a site connection, but no fixtures."""

	def styles_at(self, result, row_idx, col_idx):
		registry = result["styles"]
		ids = result["cell_styles"].get((row_idx, col_idx), []) + result["row_styles"].get(row_idx, [])
		return [registry[i] for i in ids]

	def build(self, columns, rows, **filters):
		filters.setdefault("company", "_Test Company")
		return get_xlsx_styles(XLSXMetadata(column_map=columns, row_map=rows, filters=filters))

	def test_standard_report_view_bolds_whole_row(self):
		result = self.build(standard_columns(), standard_rows())

		# group row and top-level row are bold across every column
		for col_idx in range(4):
			self.assertIn(BOLD, self.styles_at(result, 1, col_idx))
			self.assertIn(BOLD, self.styles_at(result, 3, col_idx))

		# leaf row is not
		self.assertNotIn(BOLD, self.styles_at(result, 2, 0))

	def test_standard_warn_if_negative_reddens_only_negatives(self):
		result = self.build(standard_columns(), standard_rows())

		self.assertIn(DANGER, self.styles_at(result, 3, 1))  # -2.0
		self.assertNotIn(DANGER, self.styles_at(result, 3, 2))  # 4.0
		# a row without the flag is never reddened
		self.assertNotIn(DANGER, self.styles_at(result, 1, 2))  # -5.0

	def test_standard_growth_skips_first_period_and_total(self):
		cells = get_special_view_cells(
			XLSXMetadata(
				column_map=standard_columns(), row_map=standard_rows(), filters={"selected_view": "Growth"}
			)
		)

		self.assertEqual({col for _, col in cells}, {2})

	def test_standard_growth_skips_first_column_of_each_dimension(self):
		# a second dimension starts at column 2
		columns = standard_columns({2: {"is_first_in_dimension": True}})
		cells = get_special_view_cells(
			XLSXMetadata(column_map=columns, row_map=standard_rows(), filters={"selected_view": "Growth"})
		)

		self.assertEqual(cells, {})

	def test_standard_margin_covers_every_period_but_not_total(self):
		cells = get_special_view_cells(
			XLSXMetadata(
				column_map=standard_columns(), row_map=standard_rows(), filters={"selected_view": "Margin"}
			)
		)

		self.assertEqual({col for _, col in cells}, {1, 2})

	def test_special_view_cells_are_excluded_from_bold(self):
		result = self.build(standard_columns(), standard_rows(), selected_view="Margin")

		# account column of the group row stays bold ...
		self.assertIn(BOLD, self.styles_at(result, 1, 0))
		# ... while its percentage cells are styled only by the special view pass
		self.assertNotIn(BOLD, self.styles_at(result, 1, 1))
		self.assertIn(SUCCESS, self.styles_at(result, 1, 1))
		self.assertIn(DANGER, self.styles_at(result, 1, 2))  # -5.0

	def test_growth_keeps_first_period_bold(self):
		result = self.build(standard_columns(), standard_rows(), selected_view="Growth")

		# first period is not a percentage column in Growth, so it is still bold
		self.assertIn(BOLD, self.styles_at(result, 1, 1))
		self.assertNotIn(BOLD, self.styles_at(result, 1, 2))
		self.assertIn(GROWTH_FORMAT, self.styles_at(result, 1, 2))

	def test_template_requires_period_keys(self):
		columns = {
			0: {"fieldname": "account", "fieldtype": "Data"},
			1: {"fieldname": "mar_2026", "fieldtype": "Currency"},
		}
		rows = {1: {"account": "Revenue", "mar_2026": 12.0}}
		filters = {"selected_view": "Margin", "report_template": "T1"}

		# no `_segment_info`, so the UI applies no percentage styling either
		self.assertEqual(
			get_special_view_cells(XLSXMetadata(column_map=columns, row_map=rows, filters=filters)), {}
		)

		rows[1]["_segment_info"] = {"period_keys": ["mar_2026"]}
		self.assertEqual(
			get_special_view_cells(XLSXMetadata(column_map=columns, row_map=rows, filters=filters)),
			{(1, 1): 12.0},
		)

	def test_template_growth_skips_first_period_of_every_segment(self):
		columns = {
			0: {"fieldname": "seg_0_account", "fieldtype": "Data"},
			1: {"fieldname": "seg_0_mar_2026", "fieldtype": "Currency"},
			2: {"fieldname": "seg_0_jun_2026", "fieldtype": "Currency"},
			3: {"fieldname": "seg_1_mar_2026", "fieldtype": "Currency"},
			4: {"fieldname": "seg_1_jun_2026", "fieldtype": "Currency"},
			5: {"fieldname": "seg_1_total", "fieldtype": "Currency"},
		}
		rows = {
			1: {
				"_segment_info": {"period_keys": ["mar_2026", "jun_2026"]},
				"seg_0_account": "Revenue",
				"seg_0_mar_2026": 1.0,
				"seg_0_jun_2026": 2.0,
				"seg_1_mar_2026": 3.0,
				"seg_1_jun_2026": 4.0,
				"seg_1_total": 7.0,
			}
		}
		cells = get_special_view_cells(
			XLSXMetadata(
				column_map=columns,
				row_map=rows,
				filters={"selected_view": "Growth", "report_template": "T1"},
			)
		)

		# each segment's `mar_2026` is its first period, and `seg_1_total` is an amount
		self.assertEqual({col for _, col in cells}, {2, 4})

	def test_template_percentage_cells_skip_row_flags(self):
		columns = {
			0: {"fieldname": "account", "fieldtype": "Data"},
			1: {"fieldname": "mar_2026", "fieldtype": "Currency"},
		}
		rows = {
			1: {
				"account": "Revenue",
				"bold": 1,
				"italic": 1,
				"mar_2026": 12.0,
				"_segment_info": {"period_keys": ["mar_2026"]},
			}
		}
		result = self.build(columns, rows, selected_view="Margin", report_template="T1")

		self.assertIn(BOLD, self.styles_at(result, 1, 0))
		# the percentage cell gets the special view styling only
		self.assertNotIn(BOLD, self.styles_at(result, 1, 1))
		self.assertIn(SUCCESS, self.styles_at(result, 1, 1))
