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
			default: "edit",
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
			this.show_help();
			if (this.loading) {
				this.set_section('');
			} else {
				this.reload_component('');
			}
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
		// Replace Save action
		let new_items = [];
		const save = __('Save');

		for (let item of this.qr.menu_items) {
			if (item.label === save) {
				new_items.push({
					label: save,
					action: () => this.save_report(),
					standard: false
				});
			} else {
				new_items.push(item);
			}
		}
		return new_items;
	}
	save_report() {
		this.check_datatable();
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
	check_datatable() {
		if (!this.qr.datatable) {
			frappe.throw(__('Please change the date range to load data first'));
		}
	}
	set_section(name) {
		// Sets the given section name and then reloads the data
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
		this.reload_component('');
	}
	reload_component(component_name) {
		const section_name = this.controls['section_name'].get_input_value();
		if (section_name) {
			const section = this.sections[section_name];
			const component_names = Object.keys(section);
			component_names.unshift('');
			this.controls['component'].$wrapper.find("select").empty().add_options(component_names);
			this.controls['component'].set_input(component_name);
			if (component_name) {
				this.controls['component_type'].set_input(section[component_name].type);
			}
		} else {
			this.controls['component'].$wrapper.find("select").empty();
			this.controls['component'].set_input('');
		}
		this.set_table_filters();
	}
	set_table_filters() {
		let filters = {};
		const section_name = this.controls['section_name'].get_input_value();
		const component_name = this.controls['component'].get_input_value();
		if (section_name && component_name) {
			const component_type = this.sections[section_name][component_name].type;
			if (component_type === 'filter') {
				filters = this.sections[section_name][component_name]['filters'];
			}
		}
		this.setAppliedFilters(filters);
	}
	setAppliedFilters(filters) {
		if (this.qr.datatable) {
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
	}
	delete(name, type) {
		if (type === 'section') {
			delete this.sections[name];
			const new_section = Object.keys(this.sections)[0] || '';
			this.set_section(new_section);
		}
		if (type === 'component') {
			const cur_section = this.controls['section_name'].get_input_value();
			delete this.sections[cur_section][name];
			this.reload_component('');
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
				frappe.prompt({
					label: __('Section Name'),
					fieldname: 'name',
					fieldtype: 'Data'
				}, (values) => {
					this.set_section(values.name);
				});
			}
		});
		controls['delete_section'] = this.qr.page.add_field({
			label: __('Delete Section'),
			fieldtype: 'Button',
			fieldname: 'delete_section',
			click: () => {
				let cur_section = this.controls['section_name'].get_input_value();
				if (cur_section) {
					frappe.confirm(__('Are you sure you want to delete section') + ' ' + cur_section + '?',
					() => {this.delete(cur_section, 'section')});
				}
			}
		});
		controls['component'] = this.qr.page.add_field({
			label: __('Component'),
			fieldtype: 'Select',
			fieldname: 'component',
			change: (e) => {
				this.reload_component(this.controls['component'].get_input_value());
			}
		});
		controls['component_type'] = this.qr.page.add_field({
			label: __('Component Type'),
			fieldtype: 'Select',
			fieldname: 'component_type',
			default: 'filter',
			options: [
				{label: __('Filtered Row Subtotal'), value: 'filter'},
				{label: __('Section Subtotal'), value: 'section'}
			]
		});
		controls['add_component'] = this.qr.page.add_field({
			label: __('Add Component'),
			fieldtype: 'Button',
			fieldname: 'add_component',
			click: () => {
				this.check_datatable();
				let section_name = this.controls['section_name'].get_input_value();
				if (section_name) {
					const component_type = this.controls['component_type'].get_input_value();
					let idx = 0;
					const names = Object.keys(this.sections[section_name]);
					if (names.length > 0) {
						const idxs = names.map((key) => parseInt(key.match(/\d+$/)) || 0);
						idx = Math.max(...idxs) + 1;
					}
					const filters = this.qr.datatable.columnmanager.getAppliedFilters();
					if (component_type === 'filter') {
						const name = 'Filter' + idx.toString();
						let data = {
							type: component_type,
							filters: filters
						}
						this.sections[section_name][name] = data;
						this.reload_component(name);
					} else if (component_type === 'section') {
						if (filters && Object.keys(filters).length !== 0) {
							frappe.show_alert({
								message: __('Column filters ignored'),
								indicator: 'yellow'
							});
						}
						let data = {
							type: component_type
						}
						frappe.prompt({
							label: __('Section'),
							fieldname: 'section',
							fieldtype: 'Select',
							options: Object.keys(this.sections)
						}, (values) => {
							this.sections[section_name][values.section] = data;
							this.reload_component(values.section);
						});
					} else {
						frappe.throw(__('Please select the Component Type first'));
					}
				} else {
					frappe.throw(__('Please select the Section first'));
				}
			}
		});
		controls['delete_component'] = this.qr.page.add_field({
			label: __('Delete Component'),
			fieldtype: 'Button',
			fieldname: 'delete_component',
			click: () => {
				const component = this.controls['component'].get_input_value();
				if (component) {
					frappe.confirm(__('Are you sure you want to delete component') + ' ' + component + '?',
					() => {this.delete(component, 'component')});
				}
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
		const help = __('Your custom report is built from General Ledger Entries within the date range. You can add multiple sections to the report using the New Section button. Each component added to a section adds a subset of the data into the specified section. Beware of duplicated data rows. The Filtered Row component type saves the datatable column filters to specify the added data. The Section component type refers to the data in a previously defined section, but it cannot refer to its parent section. The Amount column is summed to give the section subtotal. Use the Show Detail box to see the data rows included in each section in the final report. Once finished, hit Save & Run. Report contributed by');
		this.qr.$report_footer.append('<div class="col-md-12"><strong>' + __('Help') + `: </strong>${help}<a href="https://www.casesolved.co.uk"> Case Solved</a></div>`);
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
					data: {
						columns: [],
						sections: {},
						show_detail: 1
					}
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
