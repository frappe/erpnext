// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Warehouse', {
	setup: function (frm) {
		frm.set_query('account', function (doc) {
			return {
				filters: {
					is_group: 0,
					account_type: 'Stock',
					company: doc.company,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.add_custom_button(__('Stock Balance'), function () {
			frappe.set_route('query-report', 'Stock Balance', {
				warehouse: frm.doc.name,
			});
		});

		frm.add_custom_button(
			frm.doc.is_group
				? __('Convert to Ledger', null, 'Warehouse')
				: __('Convert to Group', null, 'Warehouse'),
			function () {
				convert_to_group_or_ledger(frm);
			},
		);

		if (!frm.doc.is_group && frm.doc.__onload && frm.doc.__onload.account) {
			frm.add_custom_button(
				__('General Ledger', null, 'Warehouse'),
				function () {
					frappe.route_options = {
						account: frm.doc.__onload.account,
						company: frm.doc.company,
					};
					frappe.set_route('query-report', 'General Ledger');
				}
			);
		}
	},
});

function convert_to_group_or_ledger(frm) {
	frappe.call({
		method: 'erpnext.stock.master.warehouse.warehouse.convert_to_group_or_ledger',
		args: {
			docname: frm.doc.name,
			is_group: frm.doc.is_group,
		},
		callback: function () {
			frm.refresh();
		},
	});
}
