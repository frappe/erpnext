import frappe
from frappe.utils import cstr, strip_html


def execute():
	for doctype in ("Lead", "Prospect", "Opportunity"):
		if not frappe.db.has_column(doctype, "notes"):
			continue

		dt = frappe.qb.DocType(doctype)
		records = (
			frappe.qb.from_(dt).select(dt.name, dt.notes).where(dt.notes.isnotnull() & dt.notes != "")
		).run(as_dict=True)

		for d in records:
			if strip_html(cstr(d.notes)).strip():
				doc = frappe.get_doc(doctype, d.name)
				doc.append("notes", {"note": d.notes})
				doc.update_child_table("notes")

		frappe.db.sql_ddl(f"alter table `tab{doctype}` drop column `notes`")
