// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Opening Invoice Creation Tool", {
	setup: function (frm) {
		frm.set_query("party_type", "invoices", function (doc, cdt, cdn) {
			return {
				filters: {
					name: ["in", "Customer, Supplier"],
				},
			};
		});

		if (frm.doc.company) {
			frm.trigger("setup_company_filters");
		}

		frappe.realtime.on("opening_invoice_creation_progress", (data) => {
			if (!frm.doc.import_in_progress) {
				frm.dashboard.reset();
				frm.doc.import_in_progress = true;
			}
			if (data.count == data.total) {
				setTimeout(
					() => {
						frm.doc.import_in_progress = false;
						frm.clear_table("invoices");
						frm.refresh_fields();
						frm.page.clear_indicator();
						frm.dashboard.hide_progress();

						if (frm.doc.invoice_type == "Sales") {
							frappe.msgprint(__("Opening Sales Invoices have been created."));
						} else {
							frappe.msgprint(__("Opening Purchase Invoices have been created."));
						}
					},
					1500,
					data.title
				);
				return;
			}

			frm.dashboard.show_progress(data.title, (data.count / data.total) * 100, data.message);
			frm.page.set_indicator(__("In Progress"), "orange");
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function (frm) {
		frm.disable_save();
		frm.trigger("create_missing_party");
		!frm.doc.import_in_progress && frm.trigger("make_dashboard");
		frm.page.set_primary_action(__("Create Invoices"), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			let freeze_message;
			if (frm.doc.invoice_type == "Sales") {
				freeze_message = __("Creating Sales Invoices ...");
			} else {
				freeze_message = __("Creating Purchase Invoices ...");
			}

			return frm.call({
				doc: frm.doc,
				btn: $(btn_primary),
				method: "make_invoices",
				freeze: 1,
				freeze_message: freeze_message,
			});
		});

		frm.trigger("update_party_labels");
	},

	setup_company_filters: function (frm) {
		frm.set_query("cost_center", "invoices", function (doc, cdt, cdn) {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query("cost_center", function (doc) {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query("temporary_opening_account", "invoices", function (doc, cdt, cdn) {
			return {
				filters: {
					company: doc.company,
				},
			};
		});
	},

	company: function (frm) {
		if (frm.doc.company) {
			frm.trigger("setup_company_filters");

			frappe.call({
				method: "erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool.get_temporary_opening_account",
				args: {
					company: frm.doc.company,
				},
				callback: (r) => {
					if (r.message) {
						frm.doc.__onload.temporary_opening_account = r.message;
						frm.trigger("update_invoice_table");
					}
				},
			});
		}
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	invoice_type: function (frm) {
		$.each(frm.doc.invoices, (idx, row) => {
			row.party_type = frm.doc.invoice_type == "Sales" ? "Customer" : "Supplier";
			frappe.model.set_value(row.doctype, row.name, "party", "");
			frappe.model.set_value(row.doctype, row.name, "party_name", "");
		});
		frm.clear_table("invoices");
		frm.refresh_fields();
		frm.trigger("update_party_labels");
	},

	make_dashboard: function (frm) {
		let max_count = frm.doc.__onload.max_count;
		let opening_invoices_summary = frm.doc.__onload.opening_invoices_summary;
		if (!$.isEmptyObject(opening_invoices_summary)) {
			let section = frm.dashboard.add_section(
				frappe.render_template("opening_invoice_creation_tool_dashboard", {
					data: opening_invoices_summary,
					max_count: max_count,
				}),
				__("Opening Invoices Summary")
			);

			section.on("click", ".invoice-link", function () {
				let doctype = $(this).attr("data-type");
				let company = $(this).attr("data-company");
				frappe.set_route("List", doctype, { is_opening: "Yes", company: company, docstatus: 1 });
			});
			frm.dashboard.show();
		}
	},

	update_invoice_table: function (frm) {
		$.each(frm.doc.invoices, (idx, row) => {
			if (!row.temporary_opening_account) {
				row.temporary_opening_account = frm.doc.__onload.temporary_opening_account;
			}

			if (!row.cost_center) {
				row.cost_center = frm.doc.cost_center;
			}

			row.party_type = frm.doc.invoice_type == "Sales" ? "Customer" : "Supplier";
		});
	},

	create_missing_party: function (frm) {
		if (frm.doc.create_missing_party) {
			frm.fields_dict["invoices"].grid.update_docfield_property("party", "reqd", 0);
			frm.fields_dict["invoices"].grid.update_docfield_property("party_name", "read_only", 0);
		} else {
			frm.fields_dict["invoices"].grid.update_docfield_property("party", "reqd", 1);
			frm.fields_dict["invoices"].grid.update_docfield_property("party_name", "read_only", 1);
		}
		frm.refresh_field("invoices");
	},

	update_party_labels: function (frm) {
		let is_sales = frm.doc.invoice_type == "Sales";

		frm.fields_dict["invoices"].grid.update_docfield_property(
			"party",
			"label",
			is_sales ? "Customer ID" : "Supplier ID"
		);
		frm.fields_dict["invoices"].grid.update_docfield_property(
			"party_name",
			"label",
			is_sales ? "Customer Name" : "Supplier Name"
		);

		frm.set_df_property(
			"create_missing_party",
			"description",
			is_sales
				? __("If party does not exist, create it using the Customer Name field.")
				: __("If party does not exist, create it using the Supplier Name field.")
		);

		frm.refresh_field("invoices");
		frm.refresh_field("create_missing_party");
	},
});

frappe.ui.form.on("Opening Invoice Creation Tool Item", {
	party: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.party) {
			frappe.model.set_value(cdt, cdn, "party_name", "");
			return;
		}

		let party_type = frm.doc.invoice_type == "Sales" ? "Customer" : "Supplier";
		let name_field = party_type === "Customer" ? "customer_name" : "supplier_name";

		frappe.db.get_value(party_type, row.party, name_field, (r) => {
			frappe.model.set_value(cdt, cdn, "party_name", r?.[name_field] || "");
		});
	},

	invoices_add: (frm) => {
		frm.trigger("update_invoice_table");
	},
});
