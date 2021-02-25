# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import re

def execute():
	# NOTE: sequence is important
	renamed_fields = get_all_renamed_fields()

	for dt, script_field, ref_dt_field in (("Client Script", "script", "dt"), ("Print Format", "html", "doc_type")):

		cond1 = " or ".join("""{0} like "%%{1}%%" """.format(script_field, d[0].replace("_", "\\_")) for d in renamed_fields)
		cond2 = " and standard = 'No'" if dt == "Print Format" else ""

		for name, script, ref_dt in frappe.db.sql("select name, {0} as script, {1} as ref_dt from `tab{2}` where ({3}) {4}".format(script_field, ref_dt_field, dt, cond1, cond2)):
			update_script(dt, name, ref_dt, script_field, script, renamed_fields)

def get_all_renamed_fields():
	from erpnext.patches.v5_0.rename_table_fieldnames import rename_map

	renamed_fields = (
		("base_amount", "base_net_amount"),
		("net_total", "base_net_total"),
		("net_total_export", "total"),
		("net_total_import", "total"),
		("other_charges_total", "base_total_taxes_and_charges"),
		("other_charges_total_export", "total_taxes_and_charges"),
		("other_charges_added", "base_taxes_and_charges_added"),
		("other_charges_added_import", "taxes_and_charges_added"),
		("other_charges_deducted", "base_taxes_and_charges_deducted"),
		("other_charges_deducted_import", "taxes_and_charges_deducted"),
		("total_tax", "base_total_taxes_and_charges"),
		("grand_total", "base_grand_total"),
		("grand_total_export", "grand_total"),
		("grand_total_import", "grand_total"),
		("rounded_total", "base_rounded_total"),
		("rounded_total_export", "rounded_total"),
		("rounded_total_import", "rounded_total"),
		("in_words", "base_in_words"),
		("in_words_export", "in_words"),
		("in_words_import", "in_words"),
		("tax_amount", "base_tax_amount"),
		("tax_amount_after_discount_amount", "base_tax_amount_after_discount_amount"),
	)

	for fields in rename_map.values():
		renamed_fields += tuple(fields)
	
	return renamed_fields

def update_script(dt, name, ref_dt, script_field, script, renamed_fields):
	for from_field, to_field in renamed_fields:
		if from_field != "entries":
			script = re.sub(r"\b{}\b".format(from_field), to_field, script)
			
	if ref_dt == "Journal Entry":
		script = re.sub(r"\bentries\b", "accounts", script)
	elif ref_dt == "Bank Reconciliation":
		script = re.sub(r"\bentries\b", "journal_entries", script)
	elif ref_dt in ("Sales Invoice", "Purchase Invoice"):
		script = re.sub(r"\bentries\b", "items", script)

	frappe.db.set_value(dt, name, script_field, script)