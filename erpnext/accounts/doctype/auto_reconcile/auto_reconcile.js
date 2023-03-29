// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Auto Reconcile", {
	onload: function(frm) {
		// set queries
		frm.set_query("party_type", function() {
			return {
				"filters": {
					"name": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			}
		});
		frm.set_query('receivable_payable_account',  function(doc) {
			return {
				filters: {
					"company": doc.company,
					"is_group": 0,
					"account_type": frappe.boot.party_account_types[doc.party_type]
				}
			};
		});
		frm.set_query('cost_center', function(doc) {
			return {
				filters: {
					"company": doc.company,
					"is_group": 0,
				}
			};
		});
		frm.set_query('bank_cash_account', function(doc) {
			return {
				filters:[
					['Account', 'company', '=', doc.company],
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'in', ['Bank', 'Cash']]
				]
			};
		});
	},
	refresh: function(frm) {
		if (frm.doc.docstatus==1 && ['Queued', 'Running'].find(x => x == frm.doc.status)) {
			var execute_btn = __("Reconcile in Background")

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: 'erpnext.accounts.doctype.auto_reconcile.auto_reconcile.run_reconciliation_job',
				});
			});
		}
		if (frm.doc.docstatus==1 && ['Completed', 'Running', "Partially Reconciled"].find(x => x == frm.doc.status)) {
			frm.call({
				'method': "erpnext.accounts.doctype.auto_reconcile.auto_reconcile.get_progress",
				args: {
					"docname": frm.docname,
				}
			}).then(r => {
				if (r) {
					frm.dashboard.add_progress('Reconciliation Progress', r.message);
				}
			})
		}
	}
});
