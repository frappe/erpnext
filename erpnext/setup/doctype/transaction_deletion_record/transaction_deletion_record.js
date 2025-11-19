// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transaction Deletion Record", {
	setup: function (frm) {
		// Set up query for DocTypes to exclude child tables and virtual doctypes
		// Note: Same DocType can be added multiple times with different company_field values
		frm.set_query("doctype_name", "doctypes_to_delete", function () {
			return {
				filters: [
					["DocType", "istable", "=", 0], // Exclude child tables
					["DocType", "is_virtual", "=", 0], // Exclude virtual doctypes
				],
			};
		});
	},

	onload: function (frm) {
		if (frm.doc.docstatus == 0) {
			let doctypes_to_be_ignored_array;
			frappe.call({
				method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.get_doctypes_to_be_ignored",
				callback: function (r) {
					doctypes_to_be_ignored_array = r.message;
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
				// Validate before showing confirmation
				if (!frm.doc.doctypes_to_delete || frm.doc.doctypes_to_delete.length === 0) {
					frappe.msgprint(__("Please generate the To Delete list before submitting"));
					return;
				}

				let message =
					"<div style='margin-bottom: 15px;'><b style='color: #d73939;'>⚠ Warning: This action cannot be undone!</b></div>" +
					"<div style='margin-bottom: 10px;'>You are about to permanently delete data for <b>" +
					frm.doc.doctypes_to_delete.length +
					" entries</b> for company <b>" +
					frm.doc.company +
					"</b>.</div>" +
					"<div style='margin-bottom: 10px;'><b>What will be deleted:</b></div>" +
					"<ul style='margin-left: 20px; margin-bottom: 10px;'>" +
					"<li><b>DocTypes with a company field:</b> Only records belonging to <b>" +
					frm.doc.company +
					"</b> will be deleted</li>" +
					"<li><b>DocTypes without a company field:</b> ALL records will be deleted (entire DocType cleared)</li>" +
					"</ul>" +
					"<div style='margin-bottom: 10px; padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;'>" +
					"<b style='color: #856404;'>📦 IMPORTANT: Create a backup before proceeding!</b>" +
					"</div>" +
					"<div style='margin-top: 10px;'>Deletion will start automatically after submission.</div>";

				frappe.confirm(
					message,
					() => {
						// User confirmed - now submit
						frm.save("Submit");
					},
					() => {
						// User cancelled - do nothing
					}
				);
			});
		}

		if (frm.doc.docstatus == 0) {
			// Add Generate To Delete List button for draft documents
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

			// Add Export Template button if To Delete list exists
			if (frm.doc.doctypes_to_delete && frm.doc.doctypes_to_delete.length > 0) {
				frm.add_custom_button(
					__("Export"),
					() => {
						// Use standard Frappe download pattern
						open_url_post(
							"/api/method/erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.export_to_delete_template",
							{
								name: frm.doc.name,
							}
						);
					},
					__("Template")
				);

				// Add Remove Zero Counts button
				frm.add_custom_button(__("Remove Zero Counts"), () => {
					let removed_count = 0;

					// Create a copy of the array to avoid modification during iteration
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

					// Replace the entire array with filtered rows
					frm.doc.doctypes_to_delete = rows_to_keep;
					frm.refresh_field("doctypes_to_delete");

					// Mark form as modified so user can save
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

			// Add Import Template button
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
							// File uploaded, now process it
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
										// Force reload from database by clearing local doc cache
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
				// Entry point for retry after failure
				frm.call({
					method: "start_deletion_tasks",
					doc: frm.doc,
					callback: () => {
						// Reload the document to show updated status
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
			// Auto-populate child DocTypes and document count using server-side method
			frm.call({
				method: "populate_doctype_details",
				doc: frm.doc,
				args: {
					doctype_name: row.doctype_name,
					company: frm.doc.company,
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
