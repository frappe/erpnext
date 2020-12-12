import frappe
from frappe import _
from frappe import msgprint


REQUIRED_FIELDS = {
	"Sales Invoice": [
		{
			"field_name": "company_address",
			"regulation": "§ 14 Abs. 4 Nr. 1 UStG"
		},
		{
			"field_name": "company_tax_id",
			"regulation": "§ 14 Abs. 4 Nr. 2 UStG"
		},
		{
			"field_name": "taxes",
			"regulation": "§ 14 Abs. 4 Nr. 8 UStG"
		},
		{
			"field_name": "customer_address",
			"regulation": "§ 14 Abs. 4 Nr. 1 UStG",
			"condition": "base_grand_total > 250"
		}
	]
}


def validate_regional(doc):
	"""Check if required fields for this document are present."""
	required_fields = REQUIRED_FIELDS.get(doc.doctype)
	if not required_fields:
		return

	meta = frappe.get_meta(doc.doctype)
	field_map = {field.fieldname: field.label for field in meta.fields}

	for field in required_fields:
		condition = field.get("condition")
		if condition and not frappe.safe_eval(condition, doc.as_dict()):
			continue

		field_name = field.get("field_name")
		regulation = field.get("regulation")
		if field_name and not doc.get(field_name):
			missing(field_map.get(field_name), regulation)


def missing(field_label, regulation):
	"""Notify the user that a required field is missing."""
	context = 'Specific for Germany. Example: Remember to set Company Tax ID. It is required by § 14 Abs. 4 Nr. 2 UStG.'
	msgprint(_('Remember to set {field_label}. It is required by {regulation}.', context=context).format(
			field_label=frappe.bold(_(field_label)),
			regulation=regulation
		)
	)
