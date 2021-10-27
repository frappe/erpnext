// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Commission', {
	setup: function(frm) {
		frm.set_query("commission_based_on", function() {
			return {
				filters: [
					['name', 'in', ["Sales Order", "Sales Invoice"]]
				]
			};
		});
	},
	refresh: function(frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.custom_buttons) frm.clear_custom_buttons();
			frm.events.add_context_buttons(frm);
		}
	},

	sales_person: function (frm) {
		frm.clear_table('contributions');
		frm.refresh();
	},

	get_contributions: function (frm) {
		frm.clear_table("contributions");
		return frappe.call({
			doc: frm.doc,
			method: 'add_contributions',
			callback: function () {
				frm.dirty();
				frm.save();
				frm.refresh();
			},
		});
	},

	add_context_buttons: function (frm) {
		if (!frm.doc.reference_name) {
			if (frm.doc.pay_via_salary) {
				frm.add_custom_button(__("Create Additional Salary"), function () {
					create_additional_salary(frm);
				}).addClass("btn-primary");
			} else {
				frm.add_custom_button(__("Create Payment Entry"), function () {
					create_payment_entry(frm);
				}).addClass("btn-primary");
			}
		}
	},

});

const create_payment_entry = function (frm) {
	var d = new frappe.ui.Dialog({
		title: __("Select Mode of Payment"),
		fields: [
			{
				'fieldname': 'mode_of_payment',
				'fieldtype': 'Link',
				'label': __('Mode of Payment'),
				'options': 'Mode of Payment',
				"get_query": function () {
					return {
						filters: {
							type: ["in", ["Bank", "Cash"]]
						}
					};
				},
				'reqd': 1
			}
		],
	});
	d.set_primary_action(__('Create'), function() {
		d.hide();
		var arg = d.get_values();
		frappe.confirm(__("Creating Payment Entry. Do you want to proceed?"),
			function () {
				frappe.call({
					method: 'payout_entry',
					args: {
						"mode_of_payment": arg.mode_of_payment
					},
					callback: function () {
						frappe.set_route(
							'Form', "Payment Entry", {
								"Payment Entry Reference.reference_name": frm.doc.name
							}
						);
					},
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Creating Payment Entry')
				});
			},
			function () {
				if (frappe.dom.freeze_count) {
					frappe.dom.unfreeze();
					frm.events.refresh(frm);
				}
			}
		);
	});
	d.show();
};

const create_additional_salary = function (frm) {
	frappe.confirm(__("Creating Additional Salary. Do you want to proceed?"),
		function () {
			frappe.call({
				method: 'payout_entry',
				args: {},
				callback: function () {
					frappe.set_route(
						"Form", "Additional Salary", {
							"Additional Salary.ref_docname": frm.doc.name
						}
					);
				},
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Creating Additional Salary')
			});
		},
		function () {
			if (frappe.dom.freeze_count) {
				frappe.dom.unfreeze();
				frm.events.refresh(frm);
			}
		}
	);
};