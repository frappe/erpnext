// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// Contributed by Case Solved and sponsored by Nulight Studios
/* eslint-disable */

frappe.provide('frappe.query_reports');

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
		{
			fieldname: "report_name",
			label: __("Report Name"),
			fieldtype: "Read Only",
			default: frappe.query_report.report_name,
			hidden: 1,
			reqd: 1
		},
		{
			fieldname: "mode",
			label: __("Mode"),
			fieldtype: "Read Only",
			default: "run",
			hidden: 1,
			reqd: 1
		}
	],
	onload: function onload(report) {
		// Remove Add Column and Save from menu
		report.page.add_inner_button(__("New Report"), () => new_report(), __("Custom Report"));
		report.page.add_inner_button(__("Load Report"), () => load_report(), __("Custom Report"));
		hide_filters(report);
	}
};

function hide_filters(report) {
	report.page.page_form[0].querySelectorAll('.form-group.frappe-control').forEach(function setHidden(field) {
		if (field.dataset.fieldtype == "Read Only") {
			field.classList.add("hidden");
		}
	});
}

erpnext.TaxDetail = class TaxDetail {
	constructor() {
		this.patch();
		this.load_report();
	}
	// Monkey patch the QueryReport class
	patch() {
		this.qr = frappe.query_report;
		this.super = {
			refresh_report: this.qr.refresh_report,
			show_footer_message: this.qr.show_footer_message
		}
		this.qr.refresh_report = () => this.refresh_report();
		this.qr.show_footer_message = () => this.show_footer_message();
	}
	show_footer_message() {
		// The last thing to run after datatable_render in refresh()
		this.super.show_footer_message.apply(this.qr);
		if (this.qr.report_name !== 'Tax Detail') {
			this.set_value_options();
			this.show_help();
			if (this.loading) {
				this.set_section('');
			}
			this.reload_filter();
		}
		this.loading = false;
	}
	refresh_report() {
		// Infrequent report build (onload), load filters & data
		// super function runs a refresh() serially
		// already run within frappe.run_serially
		this.loading = true;
		this.super.refresh_report.apply(this.qr);
		if (this.qr.report_name !== 'Tax Detail') {
			frappe.call({
				method: 'erpnext.accounts.report.tax_detail.tax_detail.get_custom_reports',
				args: {name: this.qr.report_name}
			}).then((r) => {
				const data = JSON.parse(r.message[this.qr.report_name]['json']);
				this.create_controls();
				this.sections = data.sections || {};
				this.controls['show_detail'].set_input(data.show_detail);
			});
		}
	}
	load_report() {
		// One-off report build like titles, menu, etc
		// Run when this object is created which happens in qr.load_report
		this.qr.menu_items = this.get_menu_items();
	}
	get_menu_items() {
		// Replace Save, remove Add Column
		let new_items = [];
		const save = __('Save');
		const addColumn = __('Add Column');

		for (let item of this.qr.menu_items) {
			if (item.label === save) {
				new_items.push({
					label: save,
					action: () => this.save_report(),
					standard: false
				});
			} else if (item.label === addColumn) {
				// Don't add
			} else {
				new_items.push(item);
			}
		}
		return new_items;
	}
	save_report() {
		if (this.qr.report_name !== 'Tax Detail') {
			frappe.call({
				method:'erpnext.accounts.report.tax_detail.tax_detail.save_custom_report',
				args: {
					reference_report: 'Tax Detail',
					report_name: this.qr.report_name,
					data: {
						columns: this.qr.get_visible_columns(),
						sections: this.sections,
						show_detail: this.controls['show_detail'].get_input_value()
					}
				},
				freeze: true
			}).then((r) => {
				this.set_section('');
			});
		}
	}
	set_value_options() {
		// May be run with no columns or data
		if (this.qr.columns) {
			this.fieldname_lookup = {};
			this.label_lookup = {};
			this.qr.columns.forEach((col, index) => {
				if (col['fieldtype'] == "Currency") {
					this.fieldname_lookup[col['label']] = col['fieldname'];
					this.label_lookup[col['fieldname']] = col['label'];
				}
			});
			const options = Object.keys(this.fieldname_lookup);
			this.controls['value_field'].$wrapper.find("select").empty().add_options(options);
			this.controls['value_field'].set_input(options[0]);
		}
	}
	set_value_label_from_filter() {
		const section_name = this.controls['section_name'].get_input_value();
		const fidx = this.controls['filter_index'].get_input_value();
		if (section_name && fidx) {
			const fieldname = this.sections[section_name][fidx]['fieldname'];
			this.controls['value_field'].set_input(this.label_lookup[fieldname]);
		} else {
			this.controls['value_field'].set_input(Object.keys(this.fieldname_lookup)[0]);
		}
	}
	get_value_fieldname() {
		const curlabel = this.controls['value_field'].get_input_value();
		return this.fieldname_lookup[curlabel];
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
		// Sets the given section name and then reloads the data
		this.controls['filter_index'].set_input('');
		if (name && !this.sections[name]) {
			this.sections[name] = {};
		}
		let options = Object.keys(this.sections);
		options.unshift('');
		this.controls['section_name'].$wrapper.find("select").empty().add_options(options);
		const org_mode = this.qr.get_filter_value('mode');
		let refresh = false;
		if (name) {
			this.controls['section_name'].set_input(name);
			this.qr.set_filter_value('mode', 'edit');
			if (org_mode === 'run') {
				refresh = true;
			}
		} else {
			this.controls['section_name'].set_input('');
			this.qr.set_filter_value('mode', 'run');
			if (org_mode === 'edit') {
				refresh = true;
			}
		}
		if (refresh) {
			this.qr.refresh();
		}
		this.reload_filter();
	}
	reload_filter() {
		const section_name = this.controls['section_name'].get_input_value();
		if (section_name) {
			let fidx = this.controls['filter_index'].get_input_value();
			let section = this.sections[section_name];
			let fidxs = Object.keys(section);
			fidxs.unshift('');
			this.controls['filter_index'].$wrapper.find("select").empty().add_options(fidxs);
			this.controls['filter_index'].set_input(fidx);
		} else {
			this.controls['filter_index'].$wrapper.find("select").empty();
			this.controls['filter_index'].set_input('');
		}
		this.set_table_filters();
	}
	set_table_filters() {
		let filters = {};
		const section_name = this.controls['section_name'].get_input_value();
		const fidx = this.controls['filter_index'].get_input_value();
		if (section_name && fidx) {
			filters = this.sections[section_name][fidx]['filters'];
		}
		this.setAppliedFilters(filters);
		this.set_value_label_from_filter();
	}
	setAppliedFilters(filters) {
		Array.from(this.qr.datatable.header.querySelectorAll('.dt-filter')).map(function setFilters(input) {
			let idx = input.dataset.colIndex;
			if (filters[idx]) {
				input.value = filters[idx];
			} else {
				input.value = null;
			}
		});
		this.qr.datatable.columnmanager.applyFilter(filters);
	}
	delete(name, type) {
		if (type === 'section') {
			delete this.sections[name];
			const new_section = Object.keys(this.sections)[0] || '';
			this.set_section(new_section);
		}
		if (type === 'filter') {
			const cur_section = this.controls['section_name'].get_input_value();
			delete this.sections[cur_section][name];
			this.controls['filter_index'].set_input('');
			this.reload_filter();
		}
	}
	create_controls() {
		let controls = {};
		// SELECT in data.js
		controls['section_name'] = this.qr.page.add_field({
			label: __('Section'),
			fieldtype: 'Select',
			fieldname: 'section_name',
			change: (e) => {
				this.set_section(this.controls['section_name'].get_input_value());
			}
		});
		// BUTTON in button.js
		controls['new_section'] = this.qr.page.add_field({
			label: __('New Section'),
			fieldtype: 'Button',
			fieldname: 'new_section',
			click: () => {
				this.new_section(__('New Section'));
			}
		});
		controls['delete_section'] = this.qr.page.add_field({
			label: __('Delete Section'),
			fieldtype: 'Button',
			fieldname: 'delete_section',
			click: () => {
				let cur_section = this.controls['section_name'].get_input_value();
				if (cur_section) {
					frappe.confirm(__('Are you sure you want to delete section ') + cur_section + '?',
					() => {this.delete(cur_section, 'section')});
				}
			}
		});
		controls['filter_index'] = this.qr.page.add_field({
			label: __('Filter'),
			fieldtype: 'Select',
			fieldname: 'filter_index',
			change: (e) => {
				this.controls['filter_index'].set_input(this.controls['filter_index'].get_input_value());
				this.set_table_filters();
			}
		});
		controls['add_filter'] = this.qr.page.add_field({
			label: __('Add Filter'),
			fieldtype: 'Button',
			fieldname: 'add_filter',
			click: () => {
				let section_name = this.controls['section_name'].get_input_value();
				if (section_name) {
					let prefix = 'Filter';
					let data = {
						filters: this.qr.datatable.columnmanager.getAppliedFilters(),
						fieldname: this.get_value_fieldname()
					}
					const fidxs = Object.keys(this.sections[section_name]);
					let new_idx = prefix + '0';
					if (fidxs.length > 0) {
						const fiidxs = fidxs.map((key) => parseInt(key.replace(prefix, '')));
						new_idx = prefix + (Math.max(...fiidxs) + 1).toString();
					}
					this.sections[section_name][new_idx] = data;
					this.controls['filter_index'].set_input(new_idx);
					this.reload_filter();
				} else {
					frappe.throw(__('Please add or select the Section first'));
				}
			}
		});
		controls['delete_filter'] = this.qr.page.add_field({
			label: __('Delete Filter'),
			fieldtype: 'Button',
			fieldname: 'delete_filter',
			click: () => {
				let cur_filter = this.controls['filter_index'].get_input_value();
				if (cur_filter) {
					frappe.confirm(__('Are you sure you want to delete filter ') + cur_filter + '?',
					() => {this.delete(cur_filter, 'filter')});
				}
			}
		});
		controls['value_field'] = this.qr.page.add_field({
			label: __('Value Column'),
			fieldtype: 'Select',
			fieldname: 'value_field',
			change: (e) => {
				this.controls['value_field'].set_input(this.controls['value_field'].get_input_value());
			}
		});
		controls['save'] = this.qr.page.add_field({
			label: __('Save & Run'),
			fieldtype: 'Button',
			fieldname: 'save',
			click: () => {
				this.save_report();
			}
		});
		controls['show_detail'] = this.qr.page.add_field({
			label: __('Show Detail'),
			fieldtype: 'Check',
			fieldname: 'show_detail',
			default: 1
		});
		this.controls = controls;
	}
	show_help() {
		const help = __(`You can add multiple sections to your custom report using the New Section button above.
			To specify what data goes in each section, specify column filters in the data table, then save with Add Filter.
			Each section can have multiple filters added but be careful with the duplicated data rows.
			You can specify which Currency column will be summed for each filter in the final report with the Value Column
			select box. Use the Show Detail box to see the data rows included in each section in the final report.
			Once you're done, hit Save & Run.`);
		this.qr.$report_footer.append(`<div class="col-md-12">${help}</div>`);
	}
}

if (!window.taxdetail) {
	window.taxdetail = new erpnext.TaxDetail();
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
		title: __('New Report'),
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
				method:'erpnext.accounts.report.tax_detail.tax_detail.save_custom_report',
				args: {
					reference_report: 'Tax Detail',
					report_name: values.report_name,
					columns: frappe.query_report.get_visible_columns(),
					sections: {}
				},
				freeze: true
			}).then((r) => {
				frappe.set_route('query-report', values.report_name);
			});
			dialog.hide();
		}
	});
	dialog.show();
}

function load_report() {
	get_reports(function load_report_cb(reports) {
		const dialog = new frappe.ui.Dialog({
			title: __('Load Report'),
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
				frappe.set_route('query-report', values.report_name);
			}
		});
		dialog.show();
	});
}
