// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// Contributed by Case Solved and sponsored by Nulight Studios
/* eslint-disable */

frappe.query_reports["Tax Detail"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(frappe.datetime.get_today()),
			reqd: 1,
			width: "60px"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(frappe.datetime.get_today()),
			reqd: 1,
			width: "60px"
		},
	],
	onload: function onload(report) {
		// Remove Add Column and Save from menu
		report.page.add_inner_button(__("New Report"), () => new_report, __("Custom Report"));
		report.page.add_inner_button(__("Load Report"), () => load_report, __("Custom Report"));
	},
	after_datatable_render: (datatable) => {
		if (frappe.query_report.report_name == 'Tax Detail') {
			return;
		}
		if (this.taxreport) {
			this.taxreport.load_report();
		} else {
			this.taxreport = new TaxReport();
		}
	}
};

class TaxReport {
	// construct after datatable is loaded
	constructor() {
		this.report = frappe.query_reports["Tax Detail"];
		this.qr = frappe.query_report;
		this.page = frappe.query_report.page;
		this.create_controls();
		this.sections = {};
		this.mode = 'run';
		this.load_report();
	}
	load_report() {
		// TODO
		this.setup_menu();
		// this.qr.refresh_report()
	}
	setup_menu() {
		this.qr.menu_items.forEach((item, idx) => {
			if (item['label'] == __('Save')) {
				delete this.qr.menu_items[idx];
			}
		})
		this.qr.menu_items.push({
			label: __('Save'),
			action: this.save_report
		})
		this.qr.set_menu_items();
	}
	save_report() {
		// TODO
		frappe.call({
			method:'erpnext.accounts.report.tax_detail.tax_detail.new_custom_report',
			args: {'name': values.report_name},
			freeze: true
		}).then((r) => {
			frappe.set_route("query-report", values.report_name);
		});
	}
	set_value_options() {
		let curcols = [];
		let options = [];
		this.qr.columns.forEach((col, index) => {
			if (col['fieldtype'] == "Currency") {
				curcols.push(index);
				options.push(col['label']);
			}
		});
		this.currency_cols = curcols;
		this.controls['value_field'].$wrapper.find("select").empty().add_options(options);
		this.controls['value_field'].set_input(options[0]);
	}
	add_value_field_to_filters(filters) {
		const curlabel = this.controls['value_field'].value;
		this.currency_cols.forEach(index => {
			if (this.qr.columns[index]['label'] == curlabel) {
				filters['fieldname'] = this.qr.columns[index]['fieldname'];
			}
		});
		return filters;
	}
	new_section(label) {
		const dialog = new frappe.ui.Dialog({
			title: label,
			fields: [{
				fieldname: 'data',
				label: label,
				fieldtype: 'Data'
			}],
			primary_action_label: label,
			primary_action: (values) => {
				dialog.hide();
				this.set_section(values.data);
			}
		});
		dialog.show();
	}
	set_section(name) {
		this.mode = 'edit';
		if (name && !this.sections[name]) {
			this.sections[name] = {};
			this.controls['section_name'].$wrapper.find("select").empty().add_options(Object.keys(this.sections));
		}
		if (name) {
			this.controls['section_name'].set_input(name);
		}
		this.reload();
	}
	reload() {
		if (this.mode == 'edit') {
			const section_name = this.controls['section_name'].value;
			let filters = {};
			if (section_name) {
				let fidx = this.controls['filter_index'].value;
				let section = this.sections[section_name];
				let fidxs = Object.keys(section);
				fidxs.unshift('');
				this.controls['filter_index'].$wrapper.find("select").empty().add_options(fidxs);
				this.controls['filter_index'].set_input(fidx);
				if (fidx != '') {
					filters = section[fidx];
				}
			} else {
				this.controls['filter_index'].$wrapper.find("select").empty();
			}
			// Set filters
			// reload datatable
		} else {
			this.controls['filter_index'].$wrapper.find("select").empty();
			// Query the result from the server & render
		}
	}
	get_select(label, list, type) {
		const dialog = new frappe.ui.Dialog({
			title: label,
			fields: [{
				fieldname: 'select',
				label: label,
				fieldtype: 'Select',
				options: list
			}],
			primary_action_label: label,
			primary_action: (values) => {
				dialog.hide();
				this.exec_select(values.select, type);
			}
		});
		dialog.show();
	}
	delete(name, type) {
		if (type === 'section') {
			delete this.sections[name];
			this.controls['section_name'].$wrapper.find("select").empty().add_options(Object.keys(this.sections));
			this.controls['section_name'].set_input(Object.keys(this.sections)[0] || '');
			this.controls['filter_index'].set_input('');
		}
		if (type === 'filter') {
			let cur_section = this.controls['section_name'].value;
			delete this.sections[cur_section][name];
			this.controls['filter_index'].set_input('');
		}
		this.reload();
	}
	create_controls() {
		if (this.controls) {
			return;
		}
		let controls = {};
		// SELECT in data.js
		controls['section_name'] = this.page.add_field({
			label: __('Section'),
			fieldtype: 'Select',
			fieldname: 'section_name',
			change: (e) => {
				this.set_section();
			}
		});
		// BUTTON in button.js
		controls['new_section'] = this.page.add_field({
			label: __('New Section'),
			fieldtype: 'Button',
			fieldname: 'new_section',
			click: () => {
				this.new_section(__('New Section'));
			}
		});
		controls['delete_section'] = this.page.add_field({
			label: __('Delete Section'),
			fieldtype: 'Button',
			fieldname: 'delete_section',
			click: () => {
				let cur_section = this.controls['section_name'].value;
				if (cur_section) {
					frappe.confirm(__('Are you sure you want to delete section ') + cur_section + '?',
					() => {this.delete(cur_section, 'section')});
				}
			}
		});
		controls['filter_index'] = this.page.add_field({
			label: __('Filter'),
			fieldtype: 'Select',
			fieldname: 'filter_index',
			change: (e) => {
				// TODO
			}
		});
		controls['add_filter'] = this.page.add_field({
			label: __('Add Filter'),
			fieldtype: 'Button',
			fieldname: 'add_filter',
			click: () => {
				let section_name = this.controls['section_name'].value;
				if (section_name) {
					let prefix = 'Filter';
					let filters = this.qr.datatable.columnmanager.getAppliedFilters();
					filters = this.add_value_field_to_filters(filters);
					const fidxs = Object.keys(this.sections[section_name]);
					let new_idx = prefix + '0';
					if (fidxs.length > 0) {
						const fiidxs = fidxs.map((key) => parseInt(key.replace(prefix, '')));
						new_idx = prefix + (Math.max(...fiidxs) + 1).toString();
					}
					this.sections[section_name][new_idx] = filters;
					this.controls['filter_index'].set_input(new_idx);
					this.reload();
				} else {
					frappe.throw(__('Please add or select the Section first'));
				}
			}
		});
		controls['delete_filter'] = this.page.add_field({
			label: __('Delete Filter'),
			fieldtype: 'Button',
			fieldname: 'delete_filter',
			click: () => {
				let cur_filter = this.controls['filter_index'].value;
				if (cur_filter) {
					frappe.confirm(__('Are you sure you want to delete filter ') + cur_filter + '?',
					() => {this.delete(cur_filter, 'filter')});
				}
			}
		});
		controls['value_field'] = this.page.add_field({
			label: __('Value Column'),
			fieldtype: 'Select',
			fieldname: 'value_field',
			change: (e) => {
				// TODO
			}
		});
		controls['save'] = this.page.add_field({
			label: __('Save & Run'),
			fieldtype: 'Button',
			fieldname: 'save',
			click: () => {
				// TODO: Save to db
				this.mode = 'run';
				this.reload();
			}
		});
		this.controls = controls;
		this.set_value_options();
		this.show_help();
	}
	show_help() {
		const help = __('You can add multiple sections to your custom report using the New Section button above. To specify what data goes in each section, specify column filters below, then save with Add Filter. Each section can have multiple filters added. You can specify which Currency column will be summed for each filter in the final report with the Value Column select box.');
		this.qr.show_status(help);
	}
}


function get_reports(cb) {
	frappe.call({
		method: 'erpnext.accounts.report.tax_detail.tax_detail.get_custom_reports',
		freeze: true
	}).then((r) => {
		cb(r.message);
	})
}

function new_report() {
	const dialog = new frappe.ui.Dialog({
		title: __("New Report"),
		fields: [
			{
				fieldname: 'report_name',
				label: __('Report Name'),
				fieldtype: 'Data',
				default: 'VAT Return'
			}
		],
		primary_action_label: __('Create'),
		primary_action: function new_report_pa(values) {
			frappe.call({
				method:'erpnext.accounts.report.tax_detail.tax_detail.new_custom_report',
				args: {'name': values.report_name},
				freeze: true
			}).then((r) => {
				frappe.set_route("query-report", values.report_name);
			});
			dialog.hide();
		}
	});
	dialog.show();
}

function load_report() {
	get_reports(function load_report_cb(reports) {
		const dialog = new frappe.ui.Dialog({
			title: __("Load Report"),
			fields: [
				{
					fieldname: 'report_name',
					label: __('Report Name'),
					fieldtype: 'Select',
					options: Object.keys(reports)
				}
			],
			primary_action_label: __('Load'),
			primary_action: function load_report_pa(values) {
				dialog.hide();
				frappe.set_route("query-report", values.report_name);
			}
		});
		dialog.show();
	});
}
