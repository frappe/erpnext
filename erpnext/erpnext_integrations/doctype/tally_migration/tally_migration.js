// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

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
		frm.trigger("show_import_log");
		["default_round_off_account", "default_warehouse", "default_cost_center"].forEach(account => {
			frm.toggle_reqd(account, frm.doc.is_master_data_imported === 1)
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
	show_import_log(frm) {
		let index = 0;
		let import_log = JSON.parse(frm.doc.failed_import_log || "[]");
		let logs = import_log.slice(0, 20);
		let hidden_logs = import_log.slice(20);

		frm.toggle_display("import_log_section", logs.length > 0);


		const getError = (traceback) => {
			let exc_error_idx = traceback.trim().lastIndexOf("\n") + 1
			let error_line = traceback.substr(exc_error_idx)
			let split_str_idx = (error_line.indexOf(':') > 0) ? error_line.indexOf(':') + 1 : 0;

			return error_line.slice(split_str_idx).trim();
		}

		const cleanDoc = (obj) => {
			let temp = obj;
			$.each(temp, function(key, value){
				if (value === "" || value === null){
					delete obj[key];
				} else if (Object.prototype.toString.call(value) === '[object Object]') {
					cleanDoc(value);
				} else if ($.isArray(value)) {
					$.each(value, function (k,v) { cleanDoc(v); });
				}
			});
			return temp;
		};

		let rows = logs
			.map(({ doc, exc }) => {
				let id = frappe.dom.get_unique_id();
				let traceback = exc;

				let error_message = getError(traceback);
				index++;

				let html = `
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
							<pre style="font-size: smaller;">${JSON.stringify(cleanDoc(doc), null, 1)}</pre>
						</div>
					</div>`;

				let create_button = `
					<button class='btn btn-default btn-xs m-3' type='button' onclick='frappe.new_doc("${doc.doctype}", ${JSON.stringify(doc)})'>
						${__("Create Document")}
					</button>`

				return `<tr>
							<td>${index}</td>
							<td>
								<div>${doc.doctype}</div>
							</td>
							<td>
								<div>${error_message}</div>
								<div>${html}</div>
								<div>${show_doc}</div>
							</td>
							<td>
								<div>${create_button}</div>
							</td>
						</tr>`;
				})
			.join("");

		frm.get_field("failed_import_preview").$wrapper.html(`
			<table class="table table-bordered">
				<tr class="text-muted">
					<th width="5%">${__("#")}</th>
					<th width="10%">${__("DocType")}</th>
					<th width="75%">${__("Error Message")}</th>
					<th width="10%">${__("Create")}</th>
				</tr>
				${rows}
				<tr class="text-muted">
					<td colspan="4">And ${hidden_logs.length} more others</td>
				</tr>
			</table>
		`);
	}
});
