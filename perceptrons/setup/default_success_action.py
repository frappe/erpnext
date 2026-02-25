from frappe import _

doctype_list = [
	"Purchase Receipt",
	"Purchase Invoice",
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
]


def get_message(doctype):
	# Properly format the string with translated doctype
	return _("{0} has been submitted successfully").format(doctype)


def get_first_success_message(doctype):
	# Reuse the get_message function for consistency
	return get_message(doctype)


def get_default_success_action():
	# Loop through each doctype in the list and return formatted actions
	return [
		{
			"doctype": "Success Action",
			"ref_doctype": doctype,
			"message": get_message(doctype),
			"first_success_message": get_first_success_message(doctype),
			"next_actions": "new\nprint\nemail",
		}
		for doctype in doctype_list
	]
