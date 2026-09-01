from frappe import _


def get_data():
	return {
		"non_standard_fieldnames": {"MapReduce Job": "document_name"},
		"transactions": [{"label": _("Job"), "items": ["MapReduce Job"]}],
	}
