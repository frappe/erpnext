// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.tally_migration");

frappe.ui.form.on("Tally Migration", {
	set_default_company(frm) {
		if (!frm.doc.erpnext_company && frappe.defaults.get_user_default("Company")) {
			frm.set_value("erpnext_company", frappe.defaults.get_user_default("Company"));
		}
	},

	set_queries(frm) {
		["default_warehouse", "default_cost_center"].forEach(account => {
			frm.set_query(account, () => ({ filters: {company: frm.doc.erpnext_company, is_group: 0} }));
		});

		frm.set_query("default_round_off_account", () => { 
			return {
				filters: {
					company: frm.doc.erpnext_company,
					root_type: 'Expense',
					is_group: 0
				}
			};
		});
	},

	setup_realtime_listener(frm) {
		frappe.realtime.on("tally_migration_progress_update", (data) => {
			if (data.user != frappe.session.user) return;

			const percentage = (data.progress / data.total) * 100;
			const progress_chart = frm.dashboard._progress_map && frm.dashboard._progress_map[data.title];
			frm.dashboard.show_progress(data.title, percentage, data.message);

			if (percentage == 100 || percentage < 0) {
				frappe.dom.freeze();
				setTimeout(() => {
					frm.reload_doc();
					frappe.dom.unfreeze();
					progress_chart && frm.dashboard.hide_progress(data.title);
					frm.percentage = percentage;
					frm.trigger("show_after_import_message");
				}, 1000);
			}
		});
	},

	onload: function (frm) {
		frm.trigger("set_default_company");
		frm.trigger("set_queries");
		frm.trigger("setup_realtime_listener");
	},

	refresh: function (frm) {
		frm.page.hide_icon_group();
		frm.page.show_menu();
		frm.trigger("render_error_log_table");
		
		const error_log = JSON.parse(frm.doc.error_log);
		const unresolved_errors = error_log.find(e => e.status == 'Failed');

		if (frm.doc.master_data && !frm.doc.is_master_data_imported) {
			if (frm.doc.is_master_data_processed) {
				if (frm.doc.status != "Importing Master Data" && !unresolved_errors) {
					const label = !error_log.length ? __("Import Master Data") : __("Resume Import");
					frm.events.add_button(frm, label, "import_master_data");
				}
			} else {
				if (frm.doc.status != "Processing Master Data" && frm.doc.erpnext_company) {
					frm.events.add_button(frm, __("Process Master Data"), "process_master_data");
				}
			}
		}

		if (frm.doc.day_book_data && !frm.doc.is_day_book_data_imported) {
			if (frm.doc.is_day_book_data_processed) {
				if (frm.doc.status != "Importing Day Book Data" && !unresolved_errors) {
					const label = !error_log.length ? __("Import Day Book Data") : __("Resume Import");
					frm.events.add_button(frm, label, "import_day_book_data");
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

	show_after_import_message(frm) {
		if (frm.doc.status.indexOf("Processing") != -1) return;
		const error_log = JSON.parse(frm.doc.error_log);
		const unresolved_errors = error_log.find(e => e.status == 'Failed');
		if (unresolved_errors) {
			frappe.msgprint({
				message: __("You had errors while migrating data. Please resolve them manually to continue."),
				indicator: "orange",
				title: __("Partial Success")
			});
		} else if (frm.percentage < 0) {
			const error_log_link = `<a href='desk#List/Error%20Log/List?method=Tally%20Migration%20Error'>Error Log</a>`
			frappe.msgprint({
				message: __("You had errors while processing / importing data. Please check {0} for more information.", [error_log_link]),
				indicator: "orange",
				title: __("Partial Success")
			});
		}
	},

	hide_resolved_errors(frm) {
		frm.save();
	},

	render_error_log_table(frm) {
		let error_log = JSON.parse(frm.doc.error_log);
		let unresolved_errors = []
		if (frm.doc.hide_resolved_errors)
			unresolved_errors = error_log.reduce((acc, e, idx) => {
				if (in_list(['Failed', 'Pending'], e.status)) {
					acc.push(idx);
				}
				return acc;
			}, []);

		const $wrapper = frm.get_field('error_log_html').$wrapper;
		if (error_log) {
			const rows = error_log.map((err, idx) => {
				if (frm.doc.hide_resolved_errors && !in_list(unresolved_errors, idx)) return ``;

				const skip_document = `
					<button 
						class="btn btn-default btn-xs" onclick="erpnext.tally_migration.skip_document(${idx})">
						Skip Document
					</button>`;
				const create_document = `
					<button
						class="btn btn-default btn-xs" onclick="erpnext.tally_migration.create_document(${idx})">
						Create Document
					</button>`;
				const mark_as_created = `
					<button
						class="btn btn-default btn-xs" onclick="erpnext.tally_migration.mark_as_created(${idx})">
						Mark as Created
					</button>`;
				const indicator_color = err.status == 'Failed' ? 'red' : err.status == 'Pending' ? 'orange' : 'green';
				const actions = err.status == 'Failed' ? 
					`${skip_document} ${create_document}` : 
					err.status == 'Pending' ? `${skip_document} ${mark_as_created} <br> ${create_document}` : ``;

				return `
					<tr>
						<td>${idx + 1}</td>
						<td>${err.doc.doctype}</td>
						<td>${err.error}</td>
						<td><span class="indicator ${indicator_color}">${err.status}</td>
						<td>${actions}</td>
					</tr>`;

			}).join('');

			if (!rows) {
				frm.toggle_display('error_log_section', false);
				return ``;
			}

			const skip_all_button = `
				<button
					class="btn btn-default btn-xs" onclick="erpnext.tally_migration.skip_all()">
					Skip All
				</button>`;

			$wrapper.html(
				`${skip_all_button}
				<table class="table table-bordered">
					<tr class="text-muted">
						<th style="width: 6%">${__('Sr. No.')}</th>
						<th style="width: 9%">${__('Document')}</th>
						<th>${__('Error')}</th>
						<th style="width: 9%">${__('Status')}</th>
						<th style="width: 23%">${__('Actions')}</th>
					</tr>
					${rows}
				</table>`
			);
		}
	}
});

erpnext.tally_migration.create_document = (idx) => {
	const error_log = update_error_status(idx, 'Pending');
	const doc = error_log[idx].doc;

	frappe.model.with_doctype(doc.doctype, () => {
		const new_doc = frappe.model.get_new_doc(doc.doctype);
		Object.assign(new_doc, doc);
		frappe.model.sync(new_doc);

		for (let fieldname in new_doc) {
			let df = frappe.meta.get_field(new_doc.doctype, fieldname);
			if (df && frappe.model.table_fields.includes(df.fieldtype)) {
				$.each(new_doc[fieldname] || {}, function(k,d) {
					d.parent = new_doc.name;
					d.parenttype = new_doc.doctype;
					d.parentfield = fieldname
				})
			}
		}

		frappe.set_route("Form", new_doc.doctype, new_doc.name);
	});
}

erpnext.tally_migration.skip_document = (idx) => {
	update_error_status(idx, 'Skipped');
}

erpnext.tally_migration.skip_all = () => {
	const frm = cur_frm;
	const error_log = JSON.parse(frm.doc.error_log);
	error_log.forEach(e => {
		e.status != 'Created' && (e.status = 'Skipped');
	});
	frm.doc.error_log = JSON.stringify(error_log);
	frm.dirty()
	frm.save();
}

erpnext.tally_migration.mark_as_created = (idx) => {
	update_error_status(idx, 'Created');
}

const update_error_status = (idx, status) => {
	const frm = cur_frm;
	const error_log = JSON.parse(frm.doc.error_log);
	if (error_log[idx].status != status) {
		error_log[idx].status = status;
		frm.doc.error_log = JSON.stringify(error_log);
		frm.dirty()
		frm.save();
	}

	return error_log;
}