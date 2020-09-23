// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.tally_migration");

frappe.ui.form.on("Tally Migration", {
	setup(frm) {
		frappe.realtime.on('data_import_refresh', ({ data_import }) => {
			frm.import_in_progress = false;
			frappe.db.get_doc('Data Import', data_import).then(doc => {
				const { total } = frm.doc.processed_files.find(f => f.data_import === data_import);
				const { status } = doc;
				const indicator = status === 'Success' ? 'green' : status === 'Error' ? 'red' : 'orange';
				const message =  status === 'Success' ? `${total} records imported sucessfully` : ``;

				frm.events.update_data_import_status(frm, data_import, status, indicator, message);
				frappe.model.set_value("Tally Migration Processed File", data_import, "status", status);
				frappe.model.set_value("Tally Migration Processed File", data_import, "is_imported", status === 'Success');
				frm.save();
				frm.reload_doc();
			});
		});
		frappe.realtime.on('data_import_progress', data => {
			frm.import_in_progress = true;

			const { current, data_import, total } = data;
			const status = "In Progress";
			const indicator = "green";
			const message = `Importing ${current} out of ${total} records.`;

			frm.events.update_data_import_status(frm, data_import, status, indicator, message);
		});
	},

	update_data_import_status(frm, data_import, status, indicator, message) {
		const $wrapper = frm.get_field("processed_files_html").$wrapper;
		const $status_col = $wrapper.find(`.data-import-status[data-import="${escape(data_import)}"]`);
		$status_col.html(`
			<span class="indicator ${indicator}"/> ${status}
			<span class="text-muted small"> - ${message}</span>
		`);
	},

	onload: function (frm) {
		if (!frm.doc.erpnext_company && frappe.defaults.get_user_default("Company")) {
			frm.set_value("erpnext_company", frappe.defaults.get_user_default("Company"));
		}
		
		["default_warehouse", "default_cost_center"].forEach(account => {
			frm.set_query(account, () => ({ filters: {company: frm.doc.erpnext_company} }));
		})

		frm.set_query("default_round_off_account", () => { 
			return {
				filters: {
					company: frm.doc.erpnext_company, 
					root_type: 'Expense',
					is_group: 0
				}
			}
		});

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
		frm.page.hide_icon_group();
		frm.page.show_menu();
		frm.trigger("show_processed_files");
		frm.trigger("check_migration_status");

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
				if (frm.doc.status != "Processing Master Data" && frm.doc.erpnext_company) {
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

	check_migration_status(frm) {
		if (!frm.doc.processed_files.length) return;

		const master_data = frm.doc.processed_files.filter(f => f.tally_data_type == 'Master');
		const daybook_data = frm.doc.processed_files.filter(f => f.tally_data_type == 'DayBook');
		const unimported_master_data = master_data.filter(f => !f.is_imported);
		const unimported_daybook_data = daybook_data.filter(f => !f.is_imported);
		if (master_data.length && !unimported_master_data.length && !frm.doc.is_master_data_imported) {
			frm.set_value("is_master_data_imported", 1);
			frm.set_value("hide_successful_imports", 1);
			frm.save();
		} else if (daybook_data.length && !unimported_daybook_data.length && !frm.doc.is_day_book_data_imported) {
			frm.set_value("is_day_book_data_imported", 1);
			frm.set_value("hide_successful_imports", 1);
			frm.save();
		}
	},

	hide_successful_imports(frm) {
		frm.save();
	},

	async show_processed_files(frm) {
		const $wrapper = frm.get_field("processed_files_html").$wrapper;
		const { hide_successful_imports, processed_files } = frm.doc;

		if (!processed_files?.length) return $wrapper.html('');

		let data = []
		
		const custom_imports = processed_files
			.filter(f => f.import_type === 'Custom')
			.filter(f => hide_successful_imports ? !f.is_imported : true);
		data = data.concat(custom_imports);

		const data_import_names = processed_files
			.filter(f => f.data_import)
			.filter(f => hide_successful_imports ? !f.is_imported : true)
			.map(f => f.data_import);

		const res = await frappe.db.get_list("Data Import", {
			filters: { name: ['in', data_import_names] },
			fields: ['status', 'reference_doctype as doctype_name', 'name as data_import', 'import_log', 'template_warnings'],
			order_by: "creation"
		});

		const data_import_rows = res.map(d => {
			const warnings = JSON.parse(d.template_warnings || '[]').length;
			const errors = JSON.parse(d.import_log || '[]').filter(d => !d.success).length;
			const success = JSON.parse(d.import_log || '[]').filter(d => d.success).length;
			const { status, data_import, doctype_name } = d;
			const { total, is_imported } = processed_files.find(f => f.data_import === data_import);
			return { warnings, doctype_name, errors, success, status, data_import, total, is_imported };
		});
		data = data.concat(data_import_rows);

		if (!data.length) frm.toggle_display("processed_files_section");

		frm.events.render_processed_files_html($wrapper, data);
	},

	render_processed_files_html($wrapper, data=[]) {
		if (!data.length) {
			return $wrapper.html(``);
		}
		
		const table_caption = "Start importing your data";
		const rows = data.map(
			(d, idx) => d.method ? get_custom_import_row_html(idx, d) : get_data_import_row_html(idx, d)
		).join("");

		$wrapper.html(`
			<table class="table table-bordered">
				<caption>${table_caption}</caption>
				<tr class="text-muted">
					<th width="7%">${__("Sr. No")}</th>
					<th width="20%">${__("Document Type")}</th>
					<th>${__("Status")}</th>
					<th width="20%">${__("Actions")}</th>
				</tr>
				${rows}
			</table>
		`);
	}
});

function get_custom_import_row_html(idx, data) {
	const { doctype_name, status, method, file_url } = data;
	const indicator = status === 'Success' ? 'green' : status === 'Error' ? 'red' : 'orange';

	let message = __(``);
	const import_btn = `<button 
		class='btn btn-default btn-xs' type='button'
		onclick='erpnext.tally_migration.custom_import("${method}", "${file_url}")'>Start Import</button>`
	const open_list_btn = `
		<a class='btn btn-default btn-xs' type='button' 
			href="#List/${doctype_name}" target="_blank">
			Open ${doctype_name} List
		</a>`
	const actions = status === 'Success' ? open_list_btn : import_btn;

	return (
		`<tr>
			<td>${idx + 1}</td>
			<td><div>${doctype_name}</div></td>
			<td>
				<div>
					<span class="indicator ${indicator}" /> ${status}
					<span class="text-muted small"> - ${message}</span>
				</div>
			</td>
			<td><div>${actions}</div></td>
		</tr>`);
}

function get_data_import_row_html(idx, data) {
	const { doctype_name, status, warnings, errors, success, data_import, total, is_imported } = data;
	const indicator = status === 'Success' ? 'green' : status === 'Error' ? 'red' : 'orange';

	const pending_message = __(`${total} record{0} will be imported`, [total > 1 ? 's' : '']);
	const warning_message = __(`${warnings} warning{0} need to be reviewed.`, [warnings > 1 ? 's' : '']);
	const success_message = __(`${success} record{0} imported sucessfully`, [success > 1 ? 's' : '']);
	const ignore_errors = !is_imported ? `
		<a class="grey text-muted" onclick="erpnext.tally_migration.ignore_errors('${data_import}')">
			Ignore errors?
		</a>` : '';
	const error_message = __(`${errors} error{0} need to be fixed. ${ignore_errors}`, [errors > 1 ? 's' : '']);

	let message = pending_message;
	if (status === 'Success' || is_imported) message = success_message;
	else if (warnings) message = warning_message;
	else if (errors) message = error_message;
	
	const import_btn_label = status === 'Pending' && !warnings && !errors ? __("Start Import") : __("Retry");
	const import_btn = `<button 
		class='btn btn-default btn-xs' type='button' 
		onclick='erpnext.tally_migration.import("${data_import}")'>
		${import_btn_label}
	</button>`;
	const open_data_import_btn = `<a 
		class='btn btn-default btn-xs' type='button' 
		href="#Form/Data Import/${data_import}" target="_blank">
		Open Data Import
	</a>`;
	const actions = status === 'Pending' && !warnings && !errors ? 
		import_btn : status === 'Success' || is_imported ? 
		open_data_import_btn : 
		import_btn + '<span class="margin-left"/>' + open_data_import_btn;

	return (
	`<tr>
		<td>${idx + 1}</td>
		<td><div>${doctype_name}</div></td>
		<td>
			<div class="data-import-status" data-import="${escape(data_import)}">
				<span class="indicator ${indicator}" /> ${status}
				<span class="text-muted small"> - ${message}</span>
			</div>
		</td>
		<td><div>${actions}</div></td>
	</tr>`);
}

erpnext.tally_migration.import = (data_import) => {
	if (cur_frm.import_in_progress) return;

	frappe.call({
		method: 'frappe.core.doctype.data_import.data_import.form_start_import',
		args: { data_import },
		freeze: true
	});
}

erpnext.tally_migration.custom_import = (method, file) => {
	if (cur_frm.import_in_progress) return;

	cur_frm.call({
		doc: cur_frm.doc,
		method: `${method}`,
		args: { file },
		freeze: true,
		callback: () => cur_frm.reload_doc()
	});
}

erpnext.tally_migration.ignore_errors = (data_import) => {
	const processed_file = cur_frm.doc.processed_files.find(f => f.data_import === data_import);
	frappe.model.set_value(processed_file.doctype, processed_file.name, "is_imported", 1);
	cur_frm.trigger("check_migration_status");
	cur_frm.save();
}