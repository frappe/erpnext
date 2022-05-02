import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext.regional.india import states


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	create_custom_fields(
		{
			"Tax Category": [
				dict(
					fieldname="is_inter_state",
					label="Is Inter State",
					fieldtype="Check",
					insert_after="disabled",
					print_hide=1,
				),
				dict(
					fieldname="is_reverse_charge",
					label="Is Reverse Charge",
					fieldtype="Check",
					insert_after="is_inter_state",
					print_hide=1,
				),
				dict(
					fieldname="tax_category_column_break",
					fieldtype="Column Break",
					insert_after="is_reverse_charge",
				),
				dict(
					fieldname="gst_state",
					label="Source State",
					fieldtype="Select",
					options="\n".join(states),
					insert_after="company",
				),
			]
		},
		update=True,
	)

	tax_category = frappe.qb.DocType("Tax Category")

	frappe.qb.update(tax_category).set(tax_category.is_reverse_charge, 1).where(
		tax_category.name.isin(["Reverse Charge Out-State", "Reverse Charge In-State"])
	).run()
