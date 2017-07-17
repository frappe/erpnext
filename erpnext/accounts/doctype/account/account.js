// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Account', {
	setup: function(frm) {
		frm.add_fetch('parent_account', 'report_type', 'report_type');
		frm.add_fetch('parent_account', 'root_type', 'root_type');
	},
	onload: function(frm) {
		frm.set_query('parent_account', function(doc) {
			return {
				filters: {
					"is_group": 1,
					"company": doc.company
				}
			};
		});
	},
	refresh: function(frm) {
		if (frm.doc.__islocal) {
			frappe.msgprint(__("Please create new account from Chart of Accounts."));
			throw "cannot create";
		}

		frm.toggle_display('account_name', frm.doc.__islocal);

		// hide fields if group
		frm.toggle_display(['account_type', 'tax_rate'], cint(frm.doc.is_group) == 0);

		// disable fields
		frm.toggle_enable(['account_name', 'is_group', 'company'], false);

		if (cint(frm.doc.is_group) == 0) {
			frm.toggle_display('freeze_account', frm.doc.__onload
				&& frm.doc.__onload.can_freeze_account);
		}

		// read-only for root accounts
		if (!frm.doc.parent_account) {
			frm.set_read_only();
			frm.set_intro(__("This is a root account and cannot be edited."));
		} else {
			// credit days and type if customer or supplier
			frm.set_intro(null);
			frm.trigger('account_type');

			// show / hide convert buttons
			frm.trigger('add_toolbar_buttons');
		}
	},
	account_type: function (frm) {
		if (frm.doc.is_group == 0) {
			frm.toggle_display(['tax_rate'], frm.doc.account_type == 'Tax');
			frm.toggle_display('warehouse', frm.doc.account_type == 'Stock');
		}
	},
	add_toolbar_buttons: function(frm) {
		frm.add_custom_button(__('Chart of Accounts'),
			function () { frappe.set_route("Tree", "Account"); });

		if (frm.doc.is_group == 1) {
			frm.add_custom_button(__('Group to Non-Group'), function () {
				return frappe.call({
					doc: frm.doc,
					method: 'convert_group_to_ledger',
					callback: function() {
						frm.refresh();
					}
				});
			});
		} else if (cint(frm.doc.is_group) == 0) {
			cur_frm.add_custom_button(__('Ledger'), function () {
				frappe.route_options = {
					"account": frm.doc.name,
					"from_date": frappe.sys_defaults.year_start_date,
					"to_date": frappe.sys_defaults.year_end_date,
					"company": frm.doc.company
				};
				frappe.set_route("query-report", "General Ledger");
			});

			frm.add_custom_button(__('Non-Group to Group'), function () {
				return frappe.call({
					doc: frm.doc,
					method: 'convert_ledger_to_group',
					callback: function() {
						frm.refresh();
					}
				});
			});
		}

	}
});