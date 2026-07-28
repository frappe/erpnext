// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Repost Accounting Ledger", {
	setup: function (frm) {
		frm.fields_dict["vouchers"].grid.get_field("voucher_type").get_query = function (doc) {
			return {
				query: "erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger.get_repost_allowed_types",
			};
		};

		frm.fields_dict["vouchers"].grid.get_field("voucher_no").get_query = function (doc) {
			if (doc.company) {
				return {
					filters: {
						company: doc.company,
						docstatus: 1,
					},
				};
			}
		};
	},

	refresh: function (frm) {
		// the server refuses only while the job is alive, so a dead one can be restarted here
		if (frm.doc.docstatus == 1 && !["Completed", "Cancelled"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Start Reposting"), () => {
				frm.events.start_repost(frm);
			});
		}

		if (frm.doc.docstatus != 2) {
			frm.add_custom_button(__("Show Preview"), () => {
				frm.events.generate_preview(frm);
			});
		}
	},

	generate_preview: function (frm) {
		frm.call({
			method: "generate_preview",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Generating Preview"),
			callback: function (r) {
				if (r && r.message) {
					let content = r.message;
					let opts = {
						title: "Preview",
						subtitle: "preview",
						content: content,
						print_settings: { orientation: "landscape" },
						columns: [],
						data: [],
					};
					frappe.render_grid(opts);
				}
			},
		});
	},

	start_repost: function (frm) {
		frm.call({
			method: "start_repost",
			doc: frm.doc,
			callback: function (r) {
				frm.reload_doc();
			},
		});
	},
});
