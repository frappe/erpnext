// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Patient Appointment Analytics'] = {
	"filters": [
		{
			fieldname: 'tree_type',
			label: __('Tree Type'),
			fieldtype: 'Select',
			options: ['Healthcare Practitioner', 'Medical Department'],
			default: 'Healthcare Practitioner',
			reqd: 1
		},
		{
			fieldname: 'status',
			label: __('Appointment Status'),
			fieldtype: 'Select',
			options:[
				{label: __('Scheduled'), value: 'Scheduled'},
				{label: __('Open'), value: 'Open'},
				{label: __('Closed'), value: 'Closed'},
				{label: __('Expired'), value: 'Expired'},
				{label: __('Cancelled'), value: 'Cancelled'}
			]
		},
		{
			fieldname: 'appointment_type',
			label: __('Appointment Type'),
			fieldtype: 'Link',
			options: 'Appointment Type'
		},
		{
			fieldname: 'practitioner',
			label: __('Healthcare Practitioner'),
			fieldtype: 'Link',
			options: 'Healthcare Practitioner'
		},
		{
			fieldname: 'department',
			label: __('Medical Department'),
			fieldtype: 'Link',
			options: 'Medical Department'
		},
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			default: frappe.defaults.get_user_default('year_start_date'),
			reqd: 1
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			default: frappe.defaults.get_user_default('year_end_date'),
			reqd: 1
		},
		{
			fieldname: 'range',
			label: __('Range'),
			fieldtype: 'Select',
			options:[
				{label: __('Weekly'), value: 'Weekly'},
				{label: __('Monthly'), value: 'Monthly'},
				{label: __('Quarterly'), value: 'Quarterly'},
				{label: __('Yearly'), value: 'Yearly'}
			],
			default: 'Monthly',
			reqd: 1
		}
	]
};
