// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.tally_migration");

frappe.ui.form.on("Tally Migration", {
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
					frm.dashboard.hide_progress(title);
					frm.reload_doc();
					if (error_occurred) {
						frappe.msgprint({
							message: __("An error has occurred during {0}. Check {1} for more details",
								[
									repl("<a href='/app/tally-migration/%(tally_document)s' class='variant-click'>%(tally_document)s</a>", {
										tally_document: frm.docname
									}),
									"<a href='/app/error-log' class='variant-click'>Error Log</a>"
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
		frm.trigger("show_logs_preview");
		erpnext.tally_migration.failed_import_log = JSON.parse(frm.doc.failed_import_log);
		erpnext.tally_migration.fixed_errors_log = JSON.parse(frm.doc.fixed_errors_log);

		["default_round_off_account", "default_warehouse", "default_cost_center"].forEach(account => {
			frm.toggle_reqd(account, frm.doc.is_master_data_imported === 1)
			frm.toggle_enable(account, frm.doc.is_day_book_data_processed != 1)
		})

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

	erpnext_company: function (frm) {
		frappe.db.exists("Company", frm.doc.erpnext_company).then(exists => {
			if (exists) {
				frappe.msgprint(
					__("Company {0} already exists. Continuing will overwrite the Company and Chart of Accounts", [frm.doc.erpnext_company]),
				);
			}
		});
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
	},

	render_html_table(frm, shown_logs, hidden_logs, field) {
		if (shown_logs && shown_logs.length > 0) {
			frm.toggle_display(field, true);
		} else {
			frm.toggle_display(field, false);
			return
		}
		let rows = erpnext.tally_migration.get_html_rows(shown_logs, field);
		let rows_head, table_caption;

		let table_footer = (hidden_logs && (hidden_logs.length > 0)) ? `<tr class="text-muted">
				<td colspan="4">And ${hidden_logs.length} more others</td>
			</tr>`: "";

		if (field === "fixed_error_log_preview") {
			rows_head = `<th width="75%">${__("Meta Data")}</th>
			<th width="10%">${__("Unresolve")}</th>`
			table_caption = "Resolved Issues"
		} else {
			rows_head = `<th width="75%">${__("Error Message")}</th>
			<th width="10%">${__("Create")}</th>`
			table_caption = "Error Log"
		}

		frm.get_field(field).$wrapper.html(`
			<table class="table table-bordered">
				<caption>${table_caption}</caption>
				<tr class="text-muted">
					<th width="5%">${__("#")}</th>
					<th width="10%">${__("DocType")}</th>
					${rows_head}
				</tr>
				${rows}
				${table_footer}
			</table>
		`);
	},

	show_error_summary(frm) {
		let summary = erpnext.tally_migration.failed_import_log.reduce((summary, row) => {
			if (row.doc) {
				if (summary[row.doc.doctype]) {
					summary[row.doc.doctype] += 1;
				} else {
					summary[row.doc.doctype] = 1;
				}
			}
			return summary
		}, {});
		console.table(summary);
	},

	show_logs_preview(frm) {
		let empty = "[]";
		let import_log = frm.doc.failed_import_log || empty;
		let completed_log = frm.doc.fixed_errors_log || empty;
		let render_section = !(import_log === completed_log && import_log === empty);

		frm.toggle_display("import_log_section", render_section);
		if (render_section) {
			frm.trigger("show_error_summary");
			frm.trigger("show_errored_import_log");
			frm.trigger("show_fixed_errors_log");
		}
	},

	show_errored_import_log(frm) {
		let import_log = erpnext.tally_migration.failed_import_log;
		let logs = import_log.slice(0, 20);
		let hidden_logs = import_log.slice(20);

		frm.events.render_html_table(frm, logs, hidden_logs, "failed_import_preview");
	},

	show_fixed_errors_log(frm) {
		let completed_log = erpnext.tally_migration.fixed_errors_log;
		let logs = completed_log.slice(0, 20);
		let hidden_logs = completed_log.slice(20);

		frm.events.render_html_table(frm, logs, hidden_logs, "fixed_error_log_preview");
	}
});

erpnext.tally_migration.getError = (traceback) => {
	/* Extracts the Error Message from the Python Traceback or Solved error */
	let is_multiline = traceback.trim().indexOf("\n") != -1;
	let message;

	if (is_multiline) {
		let exc_error_idx = traceback.trim().lastIndexOf("\n") + 1
		let error_line = traceback.substr(exc_error_idx)
		let split_str_idx = (error_line.indexOf(':') > 0) ? error_line.indexOf(':') + 1 : 0;
		message = error_line.slice(split_str_idx).trim();
	} else {
		message = traceback;
	}

	return message
}

erpnext.tally_migration.cleanDoc = (obj) => {
	/* Strips all null and empty values of your JSON object */
	let temp = obj;
	$.each(temp, function(key, value){
		if (value === "" || value === null){
			delete obj[key];
		} else if (Object.prototype.toString.call(value) === '[object Object]') {
			erpnext.tally_migration.cleanDoc(value);
		} else if ($.isArray(value)) {
			$.each(value, function (k,v) { erpnext.tally_migration.cleanDoc(v); });
		}
	});
	return temp;
}

erpnext.tally_migration.unresolve = (document) => {
	/* Mark document migration as unresolved ie. move to failed error log */
	let frm = cur_frm;
	let failed_log = erpnext.tally_migration.failed_import_log;
	let fixed_log = erpnext.tally_migration.fixed_errors_log;

	let modified_fixed_log = fixed_log.filter(row => {
		if (!frappe.utils.deep_equal(erpnext.tally_migration.cleanDoc(row.doc), document)) {
			return row
		}
	});

	failed_log.push({ doc: document, exc: `Marked unresolved on ${Date()}` });

	frm.doc.failed_import_log = JSON.stringify(failed_log);
	frm.doc.fixed_errors_log = JSON.stringify(modified_fixed_log);

	frm.dirty();
	frm.save();
}

erpnext.tally_migration.resolve = (document) => {
	/* Mark document migration as resolved ie. move to fixed error log */
	let frm = cur_frm;
	let failed_log = erpnext.tally_migration.failed_import_log;
	let fixed_log = erpnext.tally_migration.fixed_errors_log;

	let modified_failed_log = failed_log.filter(row => {
		if (!frappe.utils.deep_equal(erpnext.tally_migration.cleanDoc(row.doc), document)) {
			return row
		}
	});
	fixed_log.push({ doc: document, exc: `Solved on ${Date()}` });

	frm.doc.failed_import_log = JSON.stringify(modified_failed_log);
	frm.doc.fixed_errors_log = JSON.stringify(fixed_log);

	frm.dirty();
	frm.save();
}

erpnext.tally_migration.create_new_doc = (document) => {
	/* Mark as resolved and create new document */
	erpnext.tally_migration.resolve(document);
	return frappe.call({
		type: "POST",
		method: 'erpnext.erpnext_integrations.doctype.tally_migration.tally_migration.new_doc',
		args: {
			document
		},
		freeze: true,
		callback: function(r) {
			if(!r.exc) {
				frappe.model.sync(r.message);
				frappe.get_doc(r.message.doctype, r.message.name).__run_link_triggers = true;
				frappe.set_route("Form", r.message.doctype, r.message.name);
			}
		}
	});
}

erpnext.tally_migration.get_html_rows = (logs, field) => {
	let index = 0;
	let rows = logs
		.map(({ doc, exc }) => {
			let id = frappe.dom.get_unique_id();
			let traceback = exc;

			let error_message = erpnext.tally_migration.getError(traceback);
			index++;

			let show_traceback = `
				<button class="btn btn-default btn-xs m-3" type="button" data-toggle="collapse" data-target="#${id}-traceback" aria-expanded="false" aria-controls="${id}-traceback">
					${__("Show Traceback")}
				</button>
				<div class="collapse margin-top" id="${id}-traceback">
					<div class="well">
						<pre style="font-size: smaller;">${traceback}</pre>
					</div>
				</div>`;

			let show_doc = `
				<button class='btn btn-default btn-xs m-3' type='button' data-toggle='collapse' data-target='#${id}-doc' aria-expanded='false' aria-controls='${id}-doc'>
					${__("Show Document")}
				</button>
				<div class="collapse margin-top" id="${id}-doc">
					<div class="well">
						<pre style="font-size: smaller;">${JSON.stringify(erpnext.tally_migration.cleanDoc(doc), null, 1)}</pre>
					</div>
				</div>`;

			let create_button = `
				<button class='btn btn-default btn-xs m-3' type='button' onclick='erpnext.tally_migration.create_new_doc(${JSON.stringify(doc)})'>
					${__("Create Document")}
				</button>`

			let mark_as_unresolved = `
				<button class='btn btn-default btn-xs m-3' type='button' onclick='erpnext.tally_migration.unresolve(${JSON.stringify(doc)})'>
					${__("Mark as unresolved")}
				</button>`

			if (field === "fixed_error_log_preview") {
				return `<tr>
							<td>${index}</td>
							<td>
								<div>${doc.doctype}</div>
							</td>
							<td>
								<div>${error_message}</div>
								<div>${show_doc}</div>
							</td>
							<td>
								<div>${mark_as_unresolved}</div>
							</td>
						</tr>`;
			} else {
				return `<tr>
							<td>${index}</td>
							<td>
								<div>${doc.doctype}</div>
							</td>
							<td>
								<div>${error_message}</div>
								<div>${show_traceback}</div>
								<div>${show_doc}</div>
							</td>
							<td>
								<div>${create_button}</div>
							</td>
						</tr>`;
			}
		}).join("");

	return rows
}