// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Dunning", {
	setup: function (frm) {
		frm.set_query("sales_invoice", "overdue_payments", () => {
			return {
				filters: {
					docstatus: 1,
					company: frm.doc.company,
					customer: frm.doc.customer,
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

		frm.set_query('contact_person', erpnext.queries.contact_query);
		frm.set_query('customer_address', erpnext.queries.address_query);

		// cannot add rows manually, only via button "Fetch Overdue Payments"
		frm.set_df_property("overdue_payments", "cannot_add_rows", true);
	},
	refresh: function (frm) {
		frm.set_df_property("company", "read_only", frm.doc.__islocal ? 0 : 1);
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

		if(frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Overdue Payments"), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.create_dunning",
					source_doctype: "Sales Invoice",
					target: frm,
					setters: {
						customer: frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: "Overdue",
						company: frm.doc.company
					},
				});
			});
		}
	},
	customer_address: function (frm) {
		erpnext.utils.get_address_display(frm, "customer_address");
	},
	company_address: function (frm) {
		erpnext.utils.get_address_display(frm, "company_address");
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
	posting_date: function (frm) {
		frm.trigger("calculate_overdue_days");
	},
	rate_of_interest: function (frm) {
		frm.trigger("calculate_interest_amount");
	},
	dunning_fee: function (frm) {
		frm.trigger("calculate_totals");
	},
	calculate_overdue_days: function (frm) {
		frm.doc.overdue_payments.forEach((row) => {
			if (frm.doc.posting_date && row.due_date) {
				const overdue_days = moment(frm.doc.posting_date).diff(
					row.due_date,
					"days"
				);
				frappe.model.set_value(row.doctype, row.name, "overdue_days", overdue_days);
			}
		});
	},
	calculate_interest_amount: function (frm) {
		frm.doc.overdue_payments.forEach((row) => {
			const interest_per_year = row.outstanding * frm.doc.rate_of_interest / 100;
			const interest_amount = flt((interest_per_year * cint(row.overdue_days)) / 365 || 0, precision("interest_amount"));
			frappe.model.set_value(row.doctype, row.name, "interest_amount", interest_amount);
		});
	},
	calculate_totals: function (frm) {
		const total_interest = frm.doc.overdue_payments
			.reduce((prev, cur) => prev + cur.interest_amount, 0);
		const total_outstanding = frm.doc.overdue_payments
			.reduce((prev, cur) => prev + cur.outstanding, 0);
		const dunning_amount = flt(total_interest + frm.doc.dunning_fee, precision('dunning_amount'));
		const grand_total = flt(total_outstanding + dunning_amount, precision('grand_total'));

		frm.set_value("total_outstanding", total_outstanding);
		frm.set_value("total_interest", total_interest);
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

frappe.ui.form.on("Overdue Payment", {
	interest_amount: function(frm, cdt, cdn) {
		frm.trigger("calculate_totals");
	}
});