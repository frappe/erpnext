// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tally Migration', {
	onload: function (frm) {
		let reload_status = true;
		frappe.realtime.on("tally_migration_progress_update", function (data) {
			if (reload_status) {
				frappe.model.with_doc(frm.doc.doctype, frm.doc.name, () => {
					frm.refresh_header();
				});
				reload_status = false;
			}
			frm.dashboard.show_progress(data.title, (data.count / data.total) * 100, data.message);
			let error_occurred = data.count === -1;
			if (data.count == data.total || error_occurred) {
				window.setTimeout((title) => {
					frm.dashboard.hide_progress(title)
					frm.reload_doc();
					if (error_occurred) {
						frappe.msgprint({
							message: __("An error has occurred during {0}. Check {1} for more details",
								[
									repl("<a href='#Form/Tally Migration/%(tally_document)s' class='variant-click'>%(tally_document)s</a>", {
										tally_document: frm.docname
									}),
									"<a href='#List/Error Log' class='variant-click'>Error Log</a>"
								]
							),
							title: __("Tally Migration Error"),
							indicator: "red"
						});
					}
				}, 2000, data.title);
			}
		});
	},
	refresh: function (frm) {
		if (frm.doc.master_data && !frm.doc.is_master_data_imported) {
			if (frm.doc.is_master_data_processed) {
				if (frm.doc.status != "Importing Master Data") {
					frm.events.add_button(frm, __("Import Master Data"), "import_master_data");
				}
			} else {
				if (frm.doc.status != "Processing Master Data") {
					frm.events.add_button(frm, __("Process Master Data"), "process_master_data");
				}
			}
		}
		if (frm.doc.day_book_data && !frm.doc.is_day_book_data_imported) {
			if (frm.doc.is_day_book_data_processed) {
				if (frm.doc.status != "Importing Day Book Data") {
					frm.events.add_button(frm, __("Import Day Book Data"), "import_day_book_data");
				}
			} else {
				if (frm.doc.status != "Processing Day Book Data") {
					frm.events.add_button(frm, __("Process Day Book Data"), "process_day_book_data");
				}
			}
		}
	},
	add_button: function (frm, label, method) {
		frm.add_custom_button(
			label,
			() => {
				frm.call({
					doc: frm.doc,
					method: method,
					freeze: true
				});
				frm.reload_doc();
			}
		);
	}
});
