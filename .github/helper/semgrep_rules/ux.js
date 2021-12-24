
// ok: frappe-missing-translate-function-js
frappe.msgprint('{{ _("Both login and password required") }}');

// ruleid: frappe-missing-translate-function-js
frappe.msgprint('What');

// ok: frappe-missing-translate-function-js
frappe.throw('  {{ _("Both login and password required") }}.  ');
