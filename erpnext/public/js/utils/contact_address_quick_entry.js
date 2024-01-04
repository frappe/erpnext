frappe.provide('frappe.ui.form');

frappe.ui.form.ContactAddressQuickEntryForm = class ContactAddressQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	map_field_names = {
		"email_address": "email_id",
		"mobile_number": "mobile_no",
	};

	map_mandatory_depends_on = {
		Address: "eval:doc.address_line1",
	};

	constructor(doctype, after_insert, init_callback, doc, force) {
		super(doctype, after_insert, init_callback, doc, force);
		this.skip_redirect_on_error = true;
	}

	async render_dialog() {
		this.mandatory = this.mandatory.concat(this.get_variant_fields());

		for (const m of this.mandatory) {
			// Grab the original df from the doctype definition
			if (m.fieldname) {
				let fieldname = m.fieldname;
				fieldname = this.map_field_names[fieldname] ?? fieldname;

				const dt = m._for_doctype ?? this.doctype;
				await frappe.model.with_doctype(dt);

				const original_df = frappe.meta.get_docfield(dt, fieldname);
				if (original_df) {
					const default_value = frappe.defaults.get_default(fieldname);
					Object.assign(m, {
						"hidden": m.hidden ? 1 : original_df.hidden,
						"default": default_value,
					});

					if (default_value) {
						this.doc[fieldname] = default_value;
					}

					// Don't make fields required until one of them is filled
					if (this.map_mandatory_depends_on[dt] && original_df.reqd) {
						m.mandatory_depends_on = this.map_mandatory_depends_on[dt];
					}
				}
			}
		}

		super.render_dialog();
	}

	insert() {
		/**
		 * Using alias fieldnames because the doctype definition define "email_id" and "mobile_no" as readonly fields.
		 * Therefor, resulting in the fields being "hidden".
		 */
		Object.entries(this.map_field_names).forEach(([fieldname, new_fieldname]) => {
			this.dialog.doc[new_fieldname] = this.dialog.doc[fieldname];
			delete this.dialog.doc[fieldname];
		});

		return super.insert();
	}

	get_variant_fields() {
		var variant_fields = [{
			fieldtype: "Section Break",
			label: __("Primary Contact Details"),
			collapsible: 1
		},
		{
			_for_doctype: "Contact",
			label: __("Email Id"),
			fieldname: "email_address",
			fieldtype: "Data",
			options: "Email",
		},
		{
			fieldtype: "Column Break"
		},
		{
			_for_doctype: "Contact",
			label: __("Mobile Number"),
			fieldname: "mobile_number",
			fieldtype: "Data"
		},
		{
			fieldtype: "Section Break",
			label: __("Primary Address Details"),
			collapsible: 1
		},
		{
			_for_doctype: "Address",
			label: __("Address Line 1"),
			fieldname: "address_line1",
			fieldtype: "Data"
		},
		{
			_for_doctype: "Address",
			label: __("Address Line 2"),
			fieldname: "address_line2",
			fieldtype: "Data"
		},
		{
			_for_doctype: "Address",
			label: __("ZIP Code"),
			fieldname: "pincode",
			fieldtype: "Data"
		},
		{
			fieldtype: "Column Break"
		},
		{
			_for_doctype: "Address",
			label: __("City"),
			fieldname: "city",
			fieldtype: "Data"
		},
		{
			_for_doctype: "Address",
			label: __("State"),
			fieldname: "state",
			fieldtype: "Data"
		},
		{
			_for_doctype: "Address",
			label: __("Country"),
			fieldname: "country",
			fieldtype: "Link",
			options: "Country"
		},
		{
			label: __("Customer POS Id"),
			fieldname: "customer_pos_id",
			fieldtype: "Data",
			hidden: 1
		}];

		return variant_fields;
	}
}
