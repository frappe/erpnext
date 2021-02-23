// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// Contributed by Case Solved and sponsored by Nulight Studios
/* eslint-disable */

frappe.query_reports["Tax Detail"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(frappe.datetime.get_today()),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(frappe.datetime.get_today()),
			"reqd": 1,
			"width": "60px"
		},
	],
	onload: function(report) {
		report.page.add_inner_button(__("New Report"), () => new_report(), __("Custom Report"));
		report.page.add_inner_button(__("Load Report"), () => load_report(), __("Custom Report"));
		load_page_report();
	}
};

class TaxReport {
	constructor() {
		this.report = frappe.query_reports["Tax Detail"]
		this.qr = frappe.query_report
		this.page = frappe.query_report.page
		this.create_controls()
	}
	save_report() {
		frappe.call({
			method:'erpnext.accounts.report.tax_detail.tax_detail.new_custom_report',
			args: {'name': values.report_name},
			freeze: true
		}).then((r) => {
			frappe.set_route("query-report", values.report_name);
		});
	}
	create_controls() {
		this.section_name = this.page.add_field({
			label: 'Section',
			fieldtype: 'Select',
			fieldname: 'section_name',
			change() {
				this.taxreport.set_section()
			}
		});
		this.new_section = this.page.add_field({
			label: 'New Section',
			fieldtype: 'Button',
			fieldname: 'new_section'
		});
		this.delete_section = this.page.add_field({
			label: 'Delete Section',
			fieldtype: 'Button',
			fieldname: 'delete_section'
		});
		this.page.add_field({
			label: 'Filter',
			fieldtype: 'Select',
			fieldname: 'filter_index'
		});
		this.page.add_field({
			label: 'Add Filter',
			fieldtype: 'Button',
			fieldname: 'add_filter'
		});
		this.page.add_field({
			label: 'Delete Filter',
			fieldtype: 'Button',
			fieldname: 'delete_filter'
		});
		this.page.add_field({
			label: 'Value Column',
			fieldtype: 'Select',
			fieldname: 'value_field',
		});
		this.page.add_field({
			label: 'Save',
			fieldtype: 'Button',
			fieldname: 'save'
		});
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
				label: 'Report Name',
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

function load_page_report() {
	if (frappe.query_report.report_name === 'Tax Detail') {
		return;
	}
	this.taxreport = new TaxReport();
}

function load_report() {
	get_reports(function load_report_cb(reports) {
		const dialog = new frappe.ui.Dialog({
			title: __("Load Report"),
			fields: [
				{
					fieldname: 'report_name',
					label: 'Report Name',
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
