// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transaction Deletion Record", {
	setup: function (frm) {
		// Set up query for DocTypes to exclude child tables and virtual doctypes
		// Note: Same DocType can be added multiple times with different company_field values
		frm.set_query("doctype_name", "doctypes_to_delete", function () {
			// Build exclusion list from protected and ignored doctypes
			let excluded_doctypes = ["Transaction Deletion Record"]; // Always exclude self

			// Add protected doctypes (fetched in onload)
			if (frm.protected_doctypes_list && frm.protected_doctypes_list.length > 0) {
				excluded_doctypes = excluded_doctypes.concat(frm.protected_doctypes_list);
			}

			// Add doctypes from the ignore list
			if (frm.doc.doctypes_to_be_ignored && frm.doc.doctypes_to_be_ignored.length > 0) {
				frm.doc.doctypes_to_be_ignored.forEach((row) => {
					if (row.doctype_name) {
						excluded_doctypes.push(row.doctype_name);
					}
				});
			}

			let filters = [
				["DocType", "istable", "=", 0], // Exclude child tables
				["DocType", "is_virtual", "=", 0], // Exclude virtual doctypes
			];

			// Only add "not in" filter if we have items to exclude
			if (excluded_doctypes.length > 0) {
				filters.push(["DocType", "name", "not in", excluded_doctypes]);
			}

			return { filters: filters };
		});
	},

	onload: function (frm) {
		if (frm.doc.docstatus == 0) {
			// Fetch protected doctypes list for filtering
			frappe.call({
				method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.get_protected_doctypes",
				callback: function (r) {
					if (r.message) {
						frm.protected_doctypes_list = r.message;
					}
				},
			});

			// Fetch ignored doctypes and populate table
			frappe.call({
				method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.get_doctypes_to_be_ignored",
				callback: function (r) {
					let doctypes_to_be_ignored_array = r.message;
					populate_doctypes_to_be_ignored(doctypes_to_be_ignored_array, frm);
					frm.refresh_field("doctypes_to_be_ignored");
				},
			});
		}
	},

	refresh: function (frm) {
		// Override submit button to show custom confirmation
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.page.clear_primary_action();
			frm.page.set_primary_action(__("Submit"), () => {
				if (!frm.doc.doctypes_to_delete || frm.doc.doctypes_to_delete.length === 0) {
					frappe.msgprint(__("Please generate the To Delete list before submitting"));
					return;
				}

				let message =
					`<div style='margin-bottom: 15px;'><b style='color: #d73939;'>⚠ ${__(
						"Warning: This action cannot be undone!"
					)}</b></div>` +
					`<div style='margin-bottom: 10px;'>${__(
						"You are about to permanently delete data for {0} entries for company {1}.",
						[`<b>${frm.doc.doctypes_to_delete.length}</b>`, `<b>${frm.doc.company}</b>`]
					)}</div>` +
					`<div style='margin-bottom: 10px;'><b>${__("What will be deleted:")}</b></div>` +
					`<ul style='margin-left: 20px; margin-bottom: 10px;'>` +
					`<li><b>${__("DocTypes with a company field:")}</b> ${__(
						"Only records belonging to {0} will be deleted",
						[`<b>${frm.doc.company}</b>`]
					)}</li>` +
					`<li><b>${__("DocTypes without a company field:")}</b> ${__(
						"ALL records will be deleted (entire DocType cleared)"
					)}</li>` +
					`</ul>` +
					`<div style='margin-bottom: 10px; padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;'>` +
					`<b style='color: #856404;'>📦 ${__(
						"IMPORTANT: Create a backup before proceeding!"
					)}</b>` +
					`</div>` +
					`<div style='margin-top: 10px;'>${__(
						"Deletion will start automatically after submission."
					)}</div>`;

				frappe.confirm(
					message,
					() => {
						frm.save("Submit");
					},
					() => {}
				);
			});
		}

		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__("Generate To Delete List"), () => {
				frm.call({
					method: "generate_to_delete_list",
					doc: frm.doc,
					callback: (r) => {
						frappe.show_alert({
							message: __("To Delete list generated with {0} DocTypes", [r.message.count]),
							indicator: "green",
						});
						frm.refresh();
					},
				});
			});

			if (frm.doc.doctypes_to_delete && frm.doc.doctypes_to_delete.length > 0) {
				frm.add_custom_button(
					__("Export"),
					() => {
						open_url_post(
							"/api/method/erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.export_to_delete_template",
							{
								name: frm.doc.name,
							}
						);
					},
					__("Template")
				);

				frm.add_custom_button(__("Remove Zero Counts"), () => {
					let removed_count = 0;
					let rows_to_keep = [];
					frm.doc.doctypes_to_delete.forEach((row) => {
						if (row.document_count && row.document_count > 0) {
							rows_to_keep.push(row);
						} else {
							removed_count++;
						}
					});

					if (removed_count === 0) {
						frappe.msgprint(__("No rows with zero document count found"));
						return;
					}

					frm.doc.doctypes_to_delete = rows_to_keep;
					frm.refresh_field("doctypes_to_delete");
					frm.dirty();

					frappe.show_alert({
						message: __(
							"Removed {0} rows with zero document count. Please save to persist changes.",
							[removed_count]
						),
						indicator: "orange",
					});
				});
			}

			frm.add_custom_button(
				__("Import"),
				() => {
					new frappe.ui.FileUploader({
						doctype: "Transaction Deletion Record",
						docname: frm.doc.name,
						folder: "Home/Attachments",
						restrictions: {
							allowed_file_types: [".csv"],
						},
						on_success: (file_doc) => {
							frappe.call({
								method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.process_import_template",
								args: {
									transaction_deletion_record_name: frm.doc.name,
									file_url: file_doc.file_url,
								},
								freeze: true,
								freeze_message: __("Processing import..."),
								callback: (r) => {
									if (r.message) {
										frappe.show_alert({
											message: __("Imported {0} DocTypes", [r.message.imported]),
											indicator: "green",
										});

										frappe.model.clear_doc(frm.doctype, frm.docname);
										frm.reload_doc();
									}
								},
							});
						},
					});
				},
				__("Template")
			);
		}

		// Only show Retry button for Failed status (deletion starts automatically on submit)
		if (frm.doc.docstatus == 1 && frm.doc.status == "Failed") {
			frm.add_custom_button(__("Retry"), () => {
				frm.call({
					method: "start_deletion_tasks",
					doc: frm.doc,
					callback: () => {
						frappe.show_alert({
							message: __("Deletion process restarted"),
							indicator: "blue",
						});
						frm.reload_doc();
					},
				});
			});
		}
	},
});

frappe.ui.form.on("Transaction Deletion Record To Delete", {
	doctype_name: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.doctype_name) {
			// Fetch company fields for auto-selection (only if exactly 1 field exists)
			frappe.call({
				method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.get_company_link_fields",
				args: {
					doctype_name: row.doctype_name,
				},
				callback: function (r) {
					if (r.message && r.message.length === 1 && !row.company_field) {
						frappe.model.set_value(cdt, cdn, "company_field", r.message[0]);
					} else if (r.message && r.message.length > 1) {
						// Show message with available options when multiple company fields exist
						frappe.show_alert({
							message: __("Multiple company fields available: {0}. Please select manually.", [
								r.message.join(", "),
							]),
							indicator: "blue",
						});
					}
				},
			});

			// Auto-populate child DocTypes and document count
			frm.call({
				method: "populate_doctype_details",
				doc: frm.doc,
				args: {
					doctype_name: row.doctype_name,
					company: frm.doc.company,
					company_field: row.company_field,
				},
				callback: function (r) {
					if (r.message) {
						if (r.message.error) {
							frappe.msgprint({
								title: __("Error"),
								indicator: "red",
								message: __("Error getting details for {0}: {1}", [
									row.doctype_name,
									r.message.error,
								]),
							});
						}
						frappe.model.set_value(cdt, cdn, "child_doctypes", r.message.child_doctypes || "");
						frappe.model.set_value(cdt, cdn, "document_count", r.message.document_count || 0);
					}
				},
			});
		}
	},

	company_field: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.doctype_name && row.company_field !== undefined) {
			// Check for duplicates using composite key (doctype_name + company_field)
			let duplicates = frm.doc.doctypes_to_delete.filter(
				(r) =>
					r.doctype_name === row.doctype_name &&
					r.company_field === row.company_field &&
					r.name !== row.name
			);
			if (duplicates.length > 0) {
				frappe.msgprint(
					__("DocType {0} with company field '{1}' is already in the list", [
						row.doctype_name,
						row.company_field || __("(none)"),
					])
				);
				frappe.model.set_value(cdt, cdn, "company_field", "");
				return;
			}

			// Recalculate document count if company_field changes
			if (row.doctype_name) {
				frm.call({
					method: "populate_doctype_details",
					doc: frm.doc,
					args: {
						doctype_name: row.doctype_name,
						company: frm.doc.company,
						company_field: row.company_field,
					},
					callback: function (r) {
						if (r.message && r.message.document_count !== undefined) {
							frappe.model.set_value(cdt, cdn, "document_count", r.message.document_count || 0);
						}
					},
				});
			}
		}
	},
});

function populate_doctypes_to_be_ignored(doctypes_to_be_ignored_array, frm) {
	if (frm.doc.doctypes_to_be_ignored.length === 0) {
		var i;
		for (i = 0; i < doctypes_to_be_ignored_array.length; i++) {
			frm.add_child("doctypes_to_be_ignored", {
				doctype_name: doctypes_to_be_ignored_array[i],
			});
		}
	}
}
