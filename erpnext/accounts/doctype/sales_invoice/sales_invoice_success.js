frappe.provide('frappe.success_action');

frappe.success_action['Sales Invoice'] = {
	first_creation_message: __('First invoice has been created'),
	message: __('Invoice has been submitted'),
	actions: [
		'New',
		'Print',
		'Email'
	],
};
