frappe.provide("frappe.ui.form");

frappe.ui.form.LinkCustomerFields = class LinkCustomerFields extends frappe.ui.form.QuickEntryForm {
	constructor(doctype, after_insert, init_callback, doc, force) {
		super(doctype, after_insert, init_callback, doc, force);
		this.skip_redirect_on_error = true;
	}

	render_dialog() {
		this.docfields = this.get_variant_fields().concat(this.docfields);
		let new_docfields = [];
		this.docfields.forEach((df) => {
			new_docfields.push(df);
			if (df.fieldname === "city") {
				new_docfields.push({
					fieldtype: "Column Break",
					fieldname: "column_break_1",
				});
			}
		});
		this.docfields = new_docfields;
		super.render_dialog();
		this.set_default_values();
	}

	insert() {
		if (!this.dialog.doc.address_title) {
			this.dialog.doc.address_title = this.dialog.doc.link_name || this.dialog.doc.link_doctype;
		}

		let link_doctype = this.dialog.doc.link_doctype;
		let link_name = this.dialog.doc.link_name;

		delete this.dialog.doc.link_doctype;
		delete this.dialog.doc.link_name;

		if (link_doctype && link_name) {
			this.dialog.doc.links = [
				{
					link_doctype: link_doctype,
					link_name: link_name,
				},
			];
		}

		return super.insert();
	}

	async set_default_values() {
		if (cur_frm && cur_frm.doc) {
			await this.dialog.set_value("link_doctype", cur_frm.doctype);
			await this.dialog.set_value("link_name", cur_frm.doc.name);
		}
	}

	get_variant_fields() {
		var variant_fields = [
			{
				fieldname: "link_doctype",
				fieldtype: "Link",
				label: "Link Document Type",
				options: "DocType",
				get_query: () => {
					return {
						query: "frappe.contacts.address_and_contact.filter_dynamic_link_doctypes",
						filters: {
							fieldtype: "HTML",
							fieldname: "address_html",
						},
					};
				},
				onchange: async () => {
					const { value, last_value } = this.dialog.get_field("link_doctype");

					if (value !== last_value) {
						await this.dialog.set_value("link_name", "");
					}
				},
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "link_name",
				fieldtype: "Dynamic Link",
				label: "Link Name",
				link: "link_doctype",
				get_options: (df) => df.doc.link_doctype,
			},
			{ fieldtype: "Section Break" },
		];

		return variant_fields;
	}
};

frappe.ui.form.AddressQuickEntryForm = frappe.ui.form.LinkCustomerFields;
