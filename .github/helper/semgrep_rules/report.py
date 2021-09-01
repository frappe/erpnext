from frappe import _


# ruleid: frappe-missing-translate-function-in-report-python
{"label": "Field Label"}

# ruleid: frappe-missing-translate-function-in-report-python
dict(label="Field Label")


# ok: frappe-missing-translate-function-in-report-python
{"label": _("Field Label")}

# ok: frappe-missing-translate-function-in-report-python
dict(label=_("Field Label"))
