import frappe

FIELDS_NOW_TEXT_EDITOR = {
	"Delivery Stop": "customer_address",
	"Project User": "project_status",
}


def execute():
	for doctype, fieldname in FIELDS_NOW_TEXT_EDITOR.items():
		rows = frappe.get_all(
			doctype,
			filters=[[fieldname, "like", "%\n%"], [fieldname, "not like", "%<%"]],
			fields=["name", fieldname],
		)
		for row in rows:
			html = row[fieldname].replace("\n", "<br>")
			frappe.db.set_value(doctype, row.name, fieldname, html, update_modified=False)
