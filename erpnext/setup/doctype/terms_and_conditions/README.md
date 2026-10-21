Order / Contract terms that can be attached to any sale or purchase transaction.

Terms templates support document fields, standard Jinja filters, translation, and common date,
number, and text helpers through `frappe.utils`. `frappe.format`, `frappe.format_value`,
`frappe.format_date`, and `frappe.bold` remain available.
Formatting uses supplied values without document lookups. Pass the currency explicitly.

Use `frappe.get_list` or `frappe.db.get_list` for database reads. These helpers accept a DocType,
dictionary filters, simple field names, an order, and `limit_page_length`. They return only fields
and records readable by both the caller and the template's last editor. Password and masked fields
are excluded. Raw SQL, `get_all`, query builders, unchecked document getters, nested rendering,
HTTP requests, and permission overrides are unavailable.
