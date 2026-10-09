frappe.provide("erpnext.accounts");

erpnext.accounts.dimensions = {
	bound_events: new Set(),
	tax_doctypes: ["Sales Taxes and Charges", "Purchase Taxes and Charges", "Advance Taxes and Charges"],

	setup_dimension_filters(frm, doctype) {
		this.accounting_dimensions = [];
		this.default_dimensions = {};
		this.fetch_custom_dimensions(frm, doctype);
	},

	fetch_custom_dimensions(frm, doctype) {
		let me = this;
		frappe.call({
			method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimensions",
			args: {
				with_cost_center_and_project: true,
			},
			callback: function (r) {
				me.setup_header_copy(frm, r.message[0]);
				me.accounting_dimensions = r.message[0].filter((x) => {
					return x.document_type != "Project";
				});
				me.default_dimensions = r.message[1];
				me.setup_filters(frm, doctype);
				me.update_dimension(frm, doctype);
			},
		});
	},

	setup_filters(frm, doctype) {
		if (doctype == "Payment Entry" && this.accounting_dimensions) {
			frm.dimension_filters = this.accounting_dimensions;
		}

		if (this.accounting_dimensions) {
			this.accounting_dimensions.forEach((dimension) => {
				frappe.model.with_doctype(dimension["document_type"], () => {
					let parent_fields = [];
					frappe.meta.get_docfields(doctype).forEach((df) => {
						if (df.fieldtype === "Link" && df.options === "Account") {
							parent_fields.push(df.fieldname);
						} else if (df.fieldtype === "Table") {
							this.setup_child_filters(frm, df.options, df.fieldname, dimension["fieldname"]);
						}

						if (frappe.meta.has_field(doctype, dimension["fieldname"])) {
							this.setup_account_filters(frm, dimension["fieldname"], parent_fields);
						}
					});
				});
			});
		}
	},

	setup_child_filters(frm, doctype, parentfield, dimension) {
		let fields = [];

		if (frappe.meta.has_field(doctype, dimension)) {
			frappe.model.with_doctype(doctype, () => {
				frappe.meta.get_docfields(doctype).forEach((df) => {
					if (df.fieldtype === "Link" && df.options === "Account") {
						fields.push(df.fieldname);
					}
				});

				frm.set_query(dimension, parentfield, function (doc, cdt, cdn) {
					let row = locals[cdt][cdn];
					return erpnext.queries.get_filtered_dimensions(row, fields, dimension, doc.company);
				});
			});
		}
	},

	setup_account_filters(frm, dimension, fields) {
		frm.set_query(dimension, function (doc) {
			return erpnext.queries.get_filtered_dimensions(doc, fields, dimension, doc.company);
		});
	},

	update_dimension(frm, doctype) {
		if (
			!this.accounting_dimensions ||
			!frm.is_new() ||
			!frm.doc.company ||
			!this.default_dimensions?.[frm.doc.company]
		)
			return;

		// don't set default dimensions if any of the dimension is already set due to mapping
		if (frm.doc.__onload?.load_after_mapping) {
			for (const dimension of this.accounting_dimensions) {
				if (frm.doc[dimension["fieldname"]]) return;
			}
		}

		this.accounting_dimensions.forEach((dimension) => {
			const default_dimension = this.default_dimensions[frm.doc.company][dimension["fieldname"]];

			if (!default_dimension) return;

			if (frappe.meta.has_field(doctype, dimension["fieldname"])) {
				frm.set_value(dimension["fieldname"], default_dimension);
			}

			(frm.doc.items || frm.doc.accounts || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, dimension["fieldname"], default_dimension);
			});
		});
	},

	setup_header_copy(frm, dimensions) {
		const fieldnames = dimensions.map((dimension) => dimension.fieldname);

		this.get_tables_with_dimensions(frm.doctype, fieldnames).forEach((table) => {
			this.on_once(table.options, `${table.fieldname}_add`, (frm, cdt, cdn) => {
				this.set_dimensions_in_new_row(frm, frappe.get_doc(cdt, cdn), fieldnames);
			});
		});

		fieldnames
			.filter((fieldname) => frappe.meta.has_field(frm.doctype, fieldname))
			.forEach((fieldname) => {
				this.on_once(frm.doctype, fieldname, (frm) => this.copy_header_to_rows(frm, fieldname));
			});
	},

	on_once(doctype, event, handler) {
		const key = `${doctype}:${event}`;
		if (this.bound_events.has(key)) return;

		this.bound_events.add(key);
		frappe.ui.form.on(doctype, event, handler);
	},

	get_tables_with_dimensions(doctype, fieldnames) {
		return frappe.meta
			.get_docfields(doctype)
			.filter(
				(df) =>
					df.fieldtype === "Table" &&
					!this.tax_doctypes.includes(df.options) &&
					fieldnames.some((fieldname) => frappe.meta.has_field(df.options, fieldname))
			);
	},

	set_dimensions_in_new_row(frm, row, fieldnames) {
		const first_row = frm.doc[row.parentfield][0];
		fieldnames
			.filter((fieldname) => frappe.meta.has_field(row.doctype, fieldname) && !row[fieldname])
			.forEach((fieldname) => {
				const value = frm.doc[fieldname] || (first_row !== row && first_row[fieldname]);
				if (value) frappe.model.set_value(row.doctype, row.name, fieldname, value);
			});
	},

	copy_header_to_rows(frm, fieldname) {
		this.get_tables_with_dimensions(frm.doctype, [fieldname]).forEach((table) => {
			(frm.doc[table.fieldname] || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, fieldname, frm.doc[fieldname]);
			});
		});
	},
};
