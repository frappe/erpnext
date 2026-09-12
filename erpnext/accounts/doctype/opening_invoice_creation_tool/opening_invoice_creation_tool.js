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
			// A new form has no server-assigned run name until Create Invoices starts it.
			if (!frm.is_new() && data.run_name !== frm.doc.name) return;
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

						frm.reload_doc();
						frappe.show_alert({
							message: __("{0} succeeded, {1} failed.", [
								data.successes || 0,
								data.errors || 0,
							]),
							indicator: data.errors ? "orange" : "green",
						});
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
		if (frm.is_new()) {
			// Keep the singleton workflow: start processing before unresolved parties are link-validated.
			frm.disable_save();
		}

		if (!frm.is_new() && frm.doc.status !== "Pending") {
			frm.disable_save();
			frm.set_read_only();
		}
		frm.trigger("create_missing_party");
		if (["Success", "Partial Success", "Error"].includes(frm.doc.status)) {
			frm.trigger("make_result_dashboard");
		} else if ((frm.is_new() || frm.doc.status === "Pending") && !frm.doc.import_in_progress) {
			frm.trigger("make_dashboard");
		}
		if (!frm.is_new() && frm.doc.status !== "Pending") {
			frm.add_custom_button(__("View Result Logs"), () => {
				frappe.route_options = { opening_invoice_creation_tool: frm.doc.name };
				frappe.set_route("List", "Opening Invoice Creation Log");
			});
			return;
		}

		frm.page.set_primary_action(__("Create Invoices"), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			const args = {
				btn: $(btn_primary),
				no_spinner: true,
			};

			if (frm.is_new()) {
				return frappe
					.xcall(
						"erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool.create_and_start_import",
						{ doc: frm.doc },
						undefined,
						{ no_spinner: true }
					)
					.then((message) =>
						frappe.set_route("Form", "Opening Invoice Creation Tool", message.name)
					);
			}

			return frm.call({ ...args, doc: frm.doc, method: "make_invoices" });
		});

		frm.trigger("update_party_labels");
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
						(frm.doc.__onload ??= {}).temporary_opening_account = r.message;
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
		frm.trigger("update_party_labels");
	},

	make_dashboard: function (frm) {
		let { max_count = {}, opening_invoices_summary = {} } = frm.doc.__onload || {};
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

	make_result_dashboard: function (frm) {
		const summary = frm.doc.__onload?.import_result_summary;
		if (!summary) return;
		const status_theme = {
			Success: "green",
			"Partial Success": "amber",
			Error: "red",
		}[frm.doc.status];

		frm.dashboard.add_section(
			`<div class="d-flex align-items-center justify-content-between mb-4">
				<span class="text-muted">${__("Opening Invoice Creation")}</span>
				<span class="es-badge" data-theme="${status_theme}" data-variant="subtle">${__(frm.doc.status)}</span>
			</div>
			<div class="row">
				<div class="col-sm-4">
					<div class="text-muted mb-1">${__("Processed")}</div>
					<div class="h4 mb-0">${summary.total}</div>
				</div>
				<div class="col-sm-4">
					<div class="text-muted mb-1">${__("Succeeded")}</div>
					<div class="h4 mb-0">${summary.successes}</div>
				</div>
				<div class="col-sm-4">
					<div class="text-muted mb-1">${__("Failed")}</div>
					<div class="h4 mb-0">${summary.failures}</div>
				</div>
			</div>`,
			__("Import Result")
		);
	},

	update_invoice_table: function (frm) {
		const temporary_opening_account = frm.doc.__onload?.temporary_opening_account;
		$.each(frm.doc.invoices, (idx, row) => {
			if (!row.temporary_opening_account && temporary_opening_account) {
				row.temporary_opening_account = temporary_opening_account;
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
