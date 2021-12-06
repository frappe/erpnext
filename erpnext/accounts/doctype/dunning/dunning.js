// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Dunning", {
	setup: function (frm) {
		frm.set_query("sales_invoice", () => {
			return {
				filters: {
					docstatus: 1,
					company: frm.doc.company,
					outstanding_amount: [">", 0],
					status: "Overdue"
				},
			};
		});
		frm.set_query("income_account", () => {
			return {
				filters: {
					company: frm.doc.company,
					root_type: "Income",
					is_group: 0
				}
			};
		});
	},
	refresh: function (frm) {
		frm.set_df_property("company", "read_only", frm.doc.__islocal ? 0 : 1);
		frm.set_df_property(
			"sales_invoice",
			"read_only",
			frm.doc.__islocal ? 0 : 1
		);
		if (frm.doc.docstatus === 1 && frm.doc.status === "Unresolved") {
			frm.add_custom_button(__("Resolve"), () => {
				frm.set_value("status", "Resolved");
			});
		}
		if (frm.doc.docstatus === 1 && frm.doc.status !== "Resolved") {
			frm.add_custom_button(
				__("Payment"),
				function () {
					frm.events.make_payment_entry(frm);
				},__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}

		if(frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": frm.doc.posting_date,
					"company": frm.doc.company,
					"show_cancelled_entries": frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __('View'));
		}
	},
	overdue_days: function (frm) {
		frappe.db.get_value(
			"Dunning Type",
			{
				start_day: ["<", frm.doc.overdue_days],
				end_day: [">=", frm.doc.overdue_days],
			},
			"dunning_type",
			(r) => {
				if (r) {
					frm.set_value("dunning_type", r.dunning_type);
				} else {
					frm.set_value("dunning_type", "");
					frm.set_value("rate_of_interest", "");
					frm.set_value("dunning_fee", "");
				}
			}
		);
	},
	dunning_type: function (frm) {
		frm.trigger("get_dunning_letter_text");
	},
	language: function (frm) {
		frm.trigger("get_dunning_letter_text");
	},
	get_dunning_letter_text: function (frm) {
		if (frm.doc.dunning_type) {
			frappe.call({
				method:
				"erpnext.accounts.doctype.dunning.dunning.get_dunning_letter_text",
				args: {
					dunning_type: frm.doc.dunning_type,
					language: frm.doc.language,
					doc: frm.doc,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("body_text", r.message.body_text);
						frm.set_value("closing_text", r.message.closing_text);
						frm.set_value("language", r.message.language);
					} else {
						frm.set_value("body_text", "");
						frm.set_value("closing_text", "");
					}
				},
			});
		}
	},
	due_date: function (frm) {
		frm.trigger("calculate_overdue_days");
	},
	posting_date: function (frm) {
		frm.trigger("calculate_overdue_days");
	},
	rate_of_interest: function (frm) {
		frm.trigger("calculate_interest_and_amount");
	},
	outstanding_amount: function (frm) {
		frm.trigger("calculate_interest_and_amount");
	},
	interest_amount: function (frm) {
		frm.trigger("calculate_interest_and_amount");
	},
	dunning_fee: function (frm) {
		frm.trigger("calculate_interest_and_amount");
	},
	sales_invoice: function (frm) {
		frm.trigger("calculate_overdue_days");
	},
	calculate_overdue_days: function (frm) {
		if (frm.doc.posting_date && frm.doc.due_date) {
			const overdue_days = moment(frm.doc.posting_date).diff(
				frm.doc.due_date,
				"days"
			);
			frm.set_value("overdue_days", overdue_days);
		}
	},
	calculate_interest_and_amount: function (frm) {
		const interest_per_year = frm.doc.outstanding_amount * frm.doc.rate_of_interest / 100;
		const interest_amount = flt((interest_per_year * cint(frm.doc.overdue_days)) / 365 || 0, precision('interest_amount'));
		const dunning_amount = flt(interest_amount + frm.doc.dunning_fee, precision('dunning_amount'));
		const grand_total = flt(frm.doc.outstanding_amount + dunning_amount, precision('grand_total'));
		frm.set_value("interest_amount", interest_amount);
		frm.set_value("dunning_amount", dunning_amount);
		frm.set_value("grand_total", grand_total);
	},
	make_payment_entry: function (frm) {
		return frappe.call({
			method:
			"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
			args: {
				dt: frm.doc.doctype,
				dn: frm.doc.name,
			},
			callback: function (r) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route("Form", doc[0].doctype, doc[0].name);
			},
		});
	},
});
