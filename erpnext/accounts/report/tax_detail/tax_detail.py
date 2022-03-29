# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# Contributed by Case Solved and sponsored by Nulight Studios


import json

import frappe
from frappe import _

# NOTE: Payroll is implemented using Journal Entries which are included as GL Entries

# field lists in multiple doctypes will be coalesced
required_sql_fields = {
	("GL Entry", 1): ["posting_date"],
	("Account",): ["root_type", "account_type"],
	("GL Entry", 2): ["account", "voucher_type", "voucher_no", "debit", "credit"],
	("Purchase Invoice Item", "Sales Invoice Item"): [
		"base_net_amount",
		"item_tax_rate",
		"item_tax_template",
		"item_group",
		"item_name",
	],
	("Purchase Invoice", "Sales Invoice"): ["taxes_and_charges", "tax_category"],
}


def execute(filters=None):
	if not filters:
		return [], []

	fieldlist = required_sql_fields
	fieldstr = get_fieldstr(fieldlist)

	gl_entries = frappe.db.sql(
		"""
		select {fieldstr}
		from `tabGL Entry` ge
		inner join `tabAccount` a on
			ge.account=a.name and ge.company=a.company
		left join `tabSales Invoice` si on
			ge.company=si.company and ge.voucher_type='Sales Invoice' and ge.voucher_no=si.name
		left join `tabSales Invoice Item` sii on
			a.root_type='Income' and si.name=sii.parent
		left join `tabPurchase Invoice` pi on
			ge.company=pi.company and ge.voucher_type='Purchase Invoice' and ge.voucher_no=pi.name
		left join `tabPurchase Invoice Item` pii on
			a.root_type='Expense' and pi.name=pii.parent
		where
			ge.company=%(company)s and
			ge.posting_date>=%(from_date)s and
			ge.posting_date<=%(to_date)s
		order by ge.posting_date, ge.voucher_no
		""".format(
			fieldstr=fieldstr
		),
		filters,
		as_dict=1,
	)

	report_data = modify_report_data(gl_entries)
	summary = None
	if filters["mode"] == "run" and filters["report_name"] != "Tax Detail":
		report_data, summary = run_report(filters["report_name"], report_data)

	# return columns, data, message, chart, report_summary
	return get_columns(fieldlist), report_data, None, None, summary


def run_report(report_name, data):
	"Applies the sections and filters saved in the custom report"
	report_config = json.loads(frappe.get_doc("Report", report_name).json)
	# Columns indexed from 1 wrt colno
	columns = report_config.get("columns")
	sections = report_config.get("sections", {})
	show_detail = report_config.get("show_detail", 1)
	report = {}
	new_data = []
	summary = []
	for section_name, section in sections.items():
		report[section_name] = {"rows": [], "subtotal": 0.0}
		for component_name, component in section.items():
			if component["type"] == "filter":
				for row in data:
					matched = True
					for colno, filter_string in component["filters"].items():
						filter_field = columns[int(colno) - 1]["fieldname"]
						if not filter_match(row[filter_field], filter_string):
							matched = False
							break
					if matched:
						report[section_name]["rows"] += [row]
						report[section_name]["subtotal"] += row["amount"]
			if component["type"] == "section":
				if component_name == section_name:
					frappe.throw(_("A report component cannot refer to its parent section") + ": " + section_name)
				try:
					report[section_name]["rows"] += report[component_name]["rows"]
					report[section_name]["subtotal"] += report[component_name]["subtotal"]
				except KeyError:
					frappe.throw(
						_("A report component can only refer to an earlier section") + ": " + section_name
					)

		if show_detail:
			new_data += report[section_name]["rows"]
		new_data += [{"voucher_no": section_name, "amount": report[section_name]["subtotal"]}]
		summary += [
			{"label": section_name, "datatype": "Currency", "value": report[section_name]["subtotal"]}
		]
		if show_detail:
			new_data += [{}]
	return new_data or data, summary or None


def filter_match(value, string):
	"Approximation to datatable filters"
	import datetime

	if string == "":
		return True
	if value is None:
		value = -999999999999999
	elif isinstance(value, datetime.date):
		return True

	if isinstance(value, str):
		value = value.lower()
		string = string.lower()
		if string[0] == "<":
			return True if string[1:].strip() else False
		elif string[0] == ">":
			return False if string[1:].strip() else True
		elif string[0] == "=":
			return string[1:] in value if string[1:] else False
		elif string[0:2] == "!=":
			return string[2:] not in value
		elif len(string.split(":")) == 2:
			pre, post = string.split(":")
			return True if not pre.strip() and post.strip() in value else False
		else:
			return string in value
	else:
		if string[0] in ["<", ">", "="]:
			operator = string[0]
			if operator == "=":
				operator = "=="
			string = string[1:].strip()
		elif string[0:2] == "!=":
			operator = "!="
			string = string[2:].strip()
		elif len(string.split(":")) == 2:
			pre, post = string.split(":")
			try:
				return True if float(pre) <= value and float(post) >= value else False
			except ValueError:
				return False if pre.strip() else True
		else:
			return string in str(value)

	try:
		num = float(string) if string.strip() else 0
		return frappe.safe_eval(f"{value} {operator} {num}")
	except ValueError:
		if operator == "<":
			return True
		return False


def abbrev(dt):
	return "".join(l[0].lower() for l in dt.split(" ")) + "."


def doclist(dt, dfs):
	return [abbrev(dt) + f for f in dfs]


def as_split(fields):
	for field in fields:
		split = field.split(" as ")
		yield (split[0], split[1] if len(split) > 1 else split[0])


def coalesce(doctypes, fields):
	coalesce = []
	for name, new_name in as_split(fields):
		sharedfields = ", ".join(abbrev(dt) + name for dt in doctypes)
		coalesce += [f"coalesce({sharedfields}) as {new_name}"]
	return coalesce


def get_fieldstr(fieldlist):
	fields = []
	for doctypes, docfields in fieldlist.items():
		if len(doctypes) == 1 or isinstance(doctypes[1], int):
			fields += doclist(doctypes[0], docfields)
		else:
			fields += coalesce(doctypes, docfields)
	return ", ".join(fields)


def get_columns(fieldlist):
	columns = {}
	for doctypes, docfields in fieldlist.items():
		fieldmap = {name: new_name for name, new_name in as_split(docfields)}
		for doctype in doctypes:
			if isinstance(doctype, int):
				break
			meta = frappe.get_meta(doctype)
			# get column field metadata from the db
			fieldmeta = {}
			for field in meta.get("fields"):
				if field.fieldname in fieldmap.keys():
					new_name = fieldmap[field.fieldname]
					fieldmeta[new_name] = {
						"label": _(field.label),
						"fieldname": new_name,
						"fieldtype": field.fieldtype,
						"options": field.options,
					}
			# edit the columns to match the modified data
			for field in fieldmap.values():
				col = modify_report_columns(doctype, field, fieldmeta[field])
				if col:
					columns[col["fieldname"]] = col
	# use of a dict ensures duplicate columns are removed
	return list(columns.values())


def modify_report_columns(doctype, field, column):
	"Because data is rearranged into other columns"
	if doctype in ["Sales Invoice Item", "Purchase Invoice Item"]:
		if field in ["item_tax_rate", "base_net_amount"]:
			return None

	if doctype == "GL Entry" and field in ["debit", "credit"]:
		column.update({"label": _("Amount"), "fieldname": "amount"})

	if field == "taxes_and_charges":
		column.update({"label": _("Taxes and Charges Template")})
	return column


def modify_report_data(data):
	import json

	new_data = []
	for line in data:
		if line.debit:
			line.amount = -line.debit
		else:
			line.amount = line.credit
		# Remove Invoice GL Tax Entries and generate Tax entries from the invoice lines
		if "Invoice" in line.voucher_type:
			if line.account_type not in ("Tax", "Round Off"):
				new_data += [line]
				if line.item_tax_rate:
					tax_rates = json.loads(line.item_tax_rate)
					for account, rate in tax_rates.items():
						tax_line = line.copy()
						tax_line.account_type = "Tax"
						tax_line.account = account
						if line.voucher_type == "Sales Invoice":
							line.amount = line.base_net_amount
							tax_line.amount = line.base_net_amount * (rate / 100)
						if line.voucher_type == "Purchase Invoice":
							line.amount = -line.base_net_amount
							tax_line.amount = -line.base_net_amount * (rate / 100)
						new_data += [tax_line]
		else:
			new_data += [line]
	return new_data


# JS client utilities

custom_report_dict = {
	"ref_doctype": "GL Entry",
	"report_type": "Custom Report",
	"reference_report": "Tax Detail",
}


@frappe.whitelist()
def get_custom_reports(name=None):
	filters = custom_report_dict.copy()
	if name:
		filters["name"] = name
	reports = frappe.get_list("Report", filters=filters, fields=["name", "json"], as_list=False)
	reports_dict = {rep.pop("name"): rep for rep in reports}
	# Prevent custom reports with the same name
	reports_dict["Tax Detail"] = {"json": None}
	return reports_dict


@frappe.whitelist()
def save_custom_report(reference_report, report_name, data):
	if reference_report != "Tax Detail":
		frappe.throw(_("The wrong report is referenced."))
	if report_name == "Tax Detail":
		frappe.throw(_("The parent report cannot be overwritten."))

	doc = {
		"doctype": "Report",
		"report_name": report_name,
		"is_standard": "No",
		"module": "Accounts",
		"json": data,
	}
	doc.update(custom_report_dict)

	try:
		newdoc = frappe.get_doc(doc)
		newdoc.insert()
		frappe.msgprint(_("Report created successfully"))
	except frappe.exceptions.DuplicateEntryError:
		dbdoc = frappe.get_doc("Report", report_name)
		dbdoc.update(doc)
		dbdoc.save()
		frappe.msgprint(_("Report updated successfully"))
	return report_name
