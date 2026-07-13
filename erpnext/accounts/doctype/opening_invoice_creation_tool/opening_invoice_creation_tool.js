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
						frm.page.clear_indicator();
						frm.dashboard.hide_progress();

						if (!data.errors) {
							frm.clear_table("invoices");
							frm.refresh_fields();
							const message =
								frm.doc.invoice_type == "Sales"
									? __("Opening Sales Invoice(s) have been created.")
									: __("Opening Purchase Invoice(s) have been created.");
							frappe.show_alert({
								message: message,
								indicator: "green",
							});
						} else {
							frm.refresh_fields();
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

		if (frm.doc.create_missing_party) {
			frm.set_df_property("party", "fieldtype", "Data", frm.doc.name, "invoices");
		}
	},

	setup_company_filters: function (frm) {
		frm.events.apply_company_query_filter(frm, "cost_center", "invoices", { is_group: 0 });
		frm.events.apply_company_query_filter(frm, "project", "invoices");
		frm.events.apply_company_query_filter(frm, "project");
		frm.events.apply_company_query_filter(frm, "cost_center", undefined, { is_group: 0 });
		frm.events.apply_company_query_filter(frm, "temporary_opening_account", "invoices", {
			account_type: "Temporary",
			is_group: 0,
		});
	},

	apply_company_query_filter: function (frm, field_name, child_doctype = null, filters = {}) {
		const query = function (doc) {
			return {
				filters: {
					company: doc.company,
					...filters,
				},
			};
		};

		if (child_doctype) {
			frm.set_query(field_name, child_doctype, query);
		} else {
			frm.set_query(field_name, query);
		}
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
		frm.clear_table("invoices");
		frm.refresh_fields();
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
});

frappe.ui.form.on("Opening Invoice Creation Tool Item", {
	invoices_add: (frm, cdt, cdn) => {
		const row = frappe.get_doc(cdt, cdn);
		const field_copy = [];

		["project", "cost_center"].forEach((fieldname) => {
			if (frm.doc[fieldname]) {
				frappe.model.set_value(cdt, cdn, fieldname, frm.doc[fieldname]);
			} else {
				field_copy.push(fieldname);
			}
		});

		frm.script_manager.copy_from_first_row("invoices", row, field_copy);
		frm.trigger("update_invoice_table");
	},
});
