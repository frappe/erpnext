// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process Payment Reconciliation", {
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
		if (frm.doc.docstatus==1 && ['Queued', 'Paused'].find(x => x == frm.doc.status)) {
			let execute_btn = __("Start / Resume")

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: 'erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_job_for_doc',
					args: {
						docname: frm.doc.name
					}
				}).then(r => {
					if(!r.exc) {
						frappe.show_alert(__("Job Started"));
						frm.reload_doc();
					}
				});
			});
		}
		if (frm.doc.docstatus==1 && ['Completed', 'Running', 'Paused', 'Partially Reconciled'].find(x => x == frm.doc.status)) {
			frm.call({
				'method': "erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.get_reconciled_count",
				args: {
					"docname": frm.docname,
				}
			}).then(r => {
				if (r.message) {
					let progress = 0;
					let description = "";

					if (r.message.processed) {
						progress = (r.message.processed/r.message.total) * 100;
						description = r.message.processed + "/" + r.message.total +  " processed";
					} else if (r.message.total == 0 && frm.doc.status == "Completed") {
						progress = 100;
					}


					frm.dashboard.add_progress('Reconciliation Progress', progress, description);
				}
			})
		}
		if (frm.doc.docstatus==1 && frm.doc.status == 'Running') {
			let execute_btn = __("Pause")

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					'method': "erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.pause_job_for_doc",
					args: {
						"docname": frm.docname,
					}
				}).then(r => {
					if (!r.exc) {
						frappe.show_alert(__("Job Paused"));
						frm.reload_doc()
					}
				});

			});
		}
	},
	company(frm) {
		frm.set_value('party', '');
		frm.set_value('receivable_payable_account', '');
	},
	party_type(frm) {
		frm.set_value('party', '');
	},

	party(frm) {
		frm.set_value('receivable_payable_account', '');
		if (!frm.doc.receivable_payable_account && frm.doc.party_type && frm.doc.party) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: frm.doc.company,
					party_type: frm.doc.party_type,
					party: frm.doc.party
				},
				callback: (r) => {
					if (!r.exc && r.message) {
						frm.set_value("receivable_payable_account", r.message);
					}
					frm.refresh();

				}
			});
		}
	}
});
