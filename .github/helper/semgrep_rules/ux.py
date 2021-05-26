import frappe
from frappe import msgprint, throw, _


# ruleid: frappe-missing-translate-function
throw("Error Occured")

# ruleid: frappe-missing-translate-function
frappe.throw("Error Occured")

# ruleid: frappe-missing-translate-function
frappe.msgprint("Useful message")

# ruleid: frappe-missing-translate-function
msgprint("Useful message")


# ok: frappe-missing-translate-function
translatedmessage = _("Hello")

# ok: frappe-missing-translate-function
throw(translatedmessage)

# ok: frappe-missing-translate-function
msgprint(translatedmessage)

# ok: frappe-missing-translate-function
msgprint(_("Helpful message"))

# ok: frappe-missing-translate-function
frappe.throw(_("Error occured"))
