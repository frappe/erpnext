import frappe
from frappe.utils import flt


def execute():
	"""Sanitize the free-text commission_rate values before the Data -> Percent column change.

	Sales Person and Sales Team stored ``commission_rate`` as Data (varchar). This runs in
	pre_model_sync so the values are clean numbers by the time the schema sync alters the column
	to Percent: a trailing percent sign (e.g. "20%" / "20 %") is stripped, and empty / NULL /
	non-numeric values become 0.
	"""
	for doctype in ("Sales Person", "Sales Team"):
		if not frappe.db.has_column(doctype, "commission_rate"):
			continue

		# Only rewrite the rows the column change can't cast as-is. Plain numeric strings (the vast
		# majority, e.g. "20") are left untouched so this stays a targeted cleanup instead of a
		# full-table rewrite; NULL / empty / non-numeric / percent-sign values become a clean number,
		# otherwise the Data -> Percent change fails under strict SQL mode (Percent is NOT NULL decimal).
		rows = frappe.db.get_all(doctype, fields=["name", "commission_rate"])
		for row in rows:
			if _is_plain_number(row.commission_rate):
				continue
			cleaned = flt(_strip_percent_sign(row.commission_rate))
			frappe.db.set_value(doctype, row.name, "commission_rate", cleaned, update_modified=False)


def _is_plain_number(value) -> bool:
	"""True if the stored value is already a clean numeric string the column change can cast."""
	if value is None:
		return False
	text = str(value)
	if text != text.strip() or "%" in text:
		return False
	try:
		float(text)
	except ValueError:
		return False
	return True


def _strip_percent_sign(value):
	"""Drop a trailing percent sign so "20%" / "20 %" parse as 20 instead of 0."""
	if isinstance(value, str):
		return value.replace("%", "").strip()
	return value
