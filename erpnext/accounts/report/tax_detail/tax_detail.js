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
		hide_filters();
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

function hide_filters() {
	frappe.query_report.page.page_form[0].querySelectorAll('.form-group.frappe-control').forEach(function setHidden(field) {
		if (field.dataset.fieldtype == "Read Only") {
			field.classList.add("hidden");
		}
	});
}

class TaxReport {
	// construct after datatable is loaded
	constructor() {
		this.qr = frappe.query_report;
		this.page = frappe.query_report.page;
		this.create_controls();
		this.load_report();
	}
	load_report() {
		if (this.loaded) {
			return;
		}
		const report_name = this.qr.report_name;
		this.report_name.value = report_name;
		frappe.call({
			method: 'erpnext.accounts.report.tax_detail.tax_detail.get_custom_reports',
			args: {name: report_name},
			freeze: true
		}).then((r) => {
			const data = JSON.parse(r.message[report_name]['json']);
			this.sections = data.sections || {};
			this.controls['show_detail'].set_input(data.show_detail);
			this.set_section();
		})
		this.loaded = 1;
	}
	save_report() {
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
			this.reload();
		});
	}
	set_value_options() {
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
	set_value_label_from_filter() {
		const section_name = this.controls['section_name'].value;
		const fidx = this.controls['filter_index'].value;
		if (section_name && fidx) {
			const fieldname = this.sections[section_name][fidx]['fieldname'];
			this.controls['value_field'].set_input(this.label_lookup[fieldname]);
		} else {
			this.controls['value_field'].set_input(Object.keys(this.fieldname_lookup)[0]);
		}
	}
	get_value_fieldname() {
		const curlabel = this.controls['value_field'].value;
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
	get_filter_controls() {
		this.qr.filters.forEach(filter => {
			if (filter['fieldname'] == 'mode') {
				this.mode = filter;
			}
			if (filter['fieldname'] == 'report_name') {
				this.report_name = filter;
			}
		});
	}
	set_mode(mode) {
		this.mode.value = mode;
	}
	edit_mode() {
		return this.mode.value == 'edit';
	}
	set_section(name) {
		if (name && !this.sections[name]) {
			this.sections[name] = {};
		}
		let options = Object.keys(this.sections);
		options.unshift('');
		this.controls['section_name'].$wrapper.find("select").empty().add_options(options);
		if (name) {
			this.controls['section_name'].set_input(name);
		} else {
			this.controls['section_name'].set_input('');
		}
		if (this.controls['section_name'].value) {
			this.set_mode('edit');
		} else {
			this.set_mode('run');
		}
		this.controls['filter_index'].set_input('');
		this.reload();
	}
	reload_filter() {
		const section_name = this.controls['section_name'].value;
		if (section_name) {
			let fidx = this.controls['filter_index'].value;
			let section = this.sections[section_name];
			let fidxs = Object.keys(section);
			fidxs.unshift('');
			this.controls['filter_index'].$wrapper.find("select").empty().add_options(fidxs);
			this.controls['filter_index'].set_input(fidx);
		} else {
			this.controls['filter_index'].$wrapper.find("select").empty();
			this.controls['filter_index'].set_input('');
		}
		this.set_filters();
	}
	set_filters() {
		let filters = {};
		const section_name = this.controls['section_name'].value;
		const fidx = this.controls['filter_index'].value;
		if (section_name && fidx) {
			filters = this.sections[section_name][fidx]['filters'];
		}
		this.setAppliedFilters(filters);
		this.qr.datatable.columnmanager.applyFilter(filters);
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
	}
	reload() {
		// Reloads the data. When the datatable is reloaded, load_report()
		// will be run by the after_datatable_render event.
		// TODO: why does this trigger multiple reloads?
		this.qr.refresh();
		this.show_help();
		if (this.edit_mode()) {
			this.reload_filter();
		} else {
			this.controls['filter_index'].$wrapper.find("select").empty();
		}
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
				this.set_section(this.controls['section_name'].get_input_value());
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
				this.controls['filter_index'].set_input(this.controls['filter_index'].get_input_value());
				this.set_filters();
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
				this.controls['value_field'].set_input(this.controls['value_field'].get_input_value());
			}
		});
		controls['save'] = this.page.add_field({
			label: __('Save & Run'),
			fieldtype: 'Button',
			fieldname: 'save',
			click: () => {
				this.controls['section_name'].set_input('');
				this.set_mode('run');
				this.save_report();
			}
		});
		controls['show_detail'] = this.page.add_field({
			label: __('Show Detail'),
			fieldtype: 'Check',
			fieldname: 'show_detail',
			default: 1
		});
		this.controls = controls;
		this.set_value_options();
		this.get_filter_controls();
		this.show_help();
	}
	show_help() {
		const help = __(`You can add multiple sections to your custom report using the New Section button above.
			To specify what data goes in each section, specify column filters below, then save with Add Filter.
			Each section can have multiple filters added.
			You can specify which Currency column will be summed for each filter in the final report with the Value Column select box.
			Once you're done, hit Save & Run.`);
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

function override_menu() {
	//TODO: Replace save button
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
				method:'erpnext.accounts.report.tax_detail.tax_detail.save_custom_report',
				args: {
					reference_report: 'Tax Detail',
					report_name: values.report_name,
					columns: frappe.query_report.get_visible_columns(),
					sections: {}
				},
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
