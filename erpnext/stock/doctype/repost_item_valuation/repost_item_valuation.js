// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Repost Item Valuation', {
	setup: function(frm) {
		frm.set_query("warehouse", () => {
			let filters = {
				'is_group': 0
			};
			if (frm.doc.company) filters['company'] = frm.doc.company;
			return {filters: filters};
		});

		frm.set_query("voucher_type", () => {
			return {
				filters: {
					name: ['in', ['Purchase Receipt', 'Purchase Invoice', 'Delivery Note',
						'Sales Invoice', 'Stock Entry', 'Stock Reconciliation']]
				}
			};
		});

		if (frm.doc.company) {
			frm.set_query("voucher_no", () => {
				return {
					filters: {
						company: frm.doc.company,
						docstatus: 1
					}
				};
			});
		}

		frm.trigger('setup_realtime_progress');
	},

	setup_realtime_progress: function(frm) {
		frappe.realtime.on('item_reposting_progress', data => {
			if (frm.doc.name !== data.name) {
				return;
			}

			if (frm.doc.status == 'In Progress') {
				frm.doc.current_index = data.current_index;
				frm.doc.items_to_be_repost = data.items_to_be_repost;

				frm.dashboard.reset();
				frm.trigger('show_reposting_progress');
			}
		});
	},

	refresh: function(frm) {
		if (frm.doc.status == "Failed" && frm.doc.docstatus==1) {
			frm.add_custom_button(__('Restart'), function () {
				frm.trigger("restart_reposting");
			}).addClass("btn-primary");
		}

		frm.trigger('show_reposting_progress');

		if (frm.doc.status === 'Queued' && frm.doc.docstatus === 1) {
			frm.trigger('execute_reposting');
		}
	},

	execute_reposting(frm) {
		frm.add_custom_button(__("Start Reposting"), () => {
			frappe.call({
				method: 'erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.execute_repost_item_valuation',
				callback: function() {
					frappe.msgprint(__('Reposting has been started in the background.'));
				}
			});
		});
	},

	show_reposting_progress: function(frm) {
		var bars = [];

		let total_count = frm.doc.items_to_be_repost ? JSON.parse(frm.doc.items_to_be_repost).length : 0;
		let progress = flt(cint(frm.doc.current_index) / total_count * 100, 2) || 0.5;
		var title = __('Reposting Completed {0}%', [progress]);

		bars.push({
			'title': title,
			'width': progress + '%',
			'progress_class': 'progress-bar-success'
		});

		frm.dashboard.add_progress(__('Reposting Progress'), bars);
	},

	restart_reposting: function(frm) {
		frappe.call({
			method: "restart_reposting",
			doc: frm.doc,
			callback: function(r) {
				if (!r.exc) {
					frm.refresh();
				}
			}
		});
	}
});
