// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("POS Closing Entry", {
	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["POS Invoice Merge Log"];
		frm.set_query("pos_profile", function (doc) {
			return {
				filters: { user: doc.user },
			};
		});

		frm.set_query("user", function (doc) {
			return {
				query: "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_cashiers",
				filters: { parent: doc.pos_profile },
			};
		});

		frm.set_query("pos_opening_entry", function (doc) {
			return { filters: { status: "Open", docstatus: 1 } };
		});

		if (frm.doc.docstatus === 0 && !frm.doc.amended_from)
			frm.set_value("period_end_date", frappe.datetime.now_datetime());

		frappe.realtime.on("closing_process_complete", async function (data) {
			await frm.reload_doc();
			if (frm.doc.status == "Failed" && frm.doc.error_message) {
				frappe.msgprint({
					title: __("POS Closing Failed"),
					message: frm.doc.error_message,
					indicator: "orange",
					clear: true,
				});
			}
		});

		set_html_data(frm);

		if (frm.doc.docstatus == 1) {
			if (!frm.doc.posting_date) {
				frm.set_value("posting_date", frappe.datetime.nowdate());
			}
			if (!frm.doc.posting_time) {
				frm.set_value("posting_time", frappe.datetime.now_time());
			}
		}
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status == "Failed") {
			const issue = '<a id="jump_to_error" style="text-decoration: underline;">issue</a>';
			frm.dashboard.set_headline(
				__(
					"POS Closing failed while running in a background process. You can resolve the {0} and retry the process again.",
					[issue]
				)
			);

			$("#jump_to_error").on("click", (e) => {
				e.preventDefault();
				frappe.utils.scroll_to(cur_frm.get_field("error_message").$wrapper, true, 30);
			});

			frm.add_custom_button(__("Retry"), function () {
				frm.call("retry", {}, () => {
					frm.reload_doc();
				});
			});
		}
	},

	pos_opening_entry(frm) {
		if (
			frm.doc.pos_opening_entry &&
			frm.doc.period_start_date &&
			frm.doc.period_end_date &&
			frm.doc.user
		) {
			reset_values(frm);
			frappe.run_serially([
				() => frappe.dom.freeze(__("Loading Invoices! Please Wait...")),
				() => frm.trigger("set_opening_amounts"),
				() => frm.trigger("get_pos_invoices"),
				() => frappe.dom.unfreeze(),
			]);
		}
	},

	set_opening_amounts(frm) {
		return frappe.db
			.get_doc("POS Opening Entry", frm.doc.pos_opening_entry)
			.then(({ balance_details }) => {
				balance_details.forEach((detail) => {
					frm.add_child("payment_reconciliation", {
						mode_of_payment: detail.mode_of_payment,
						opening_amount: detail.opening_amount,
						expected_amount: detail.opening_amount,
					});
				});
			});
	},

	get_pos_invoices(frm) {
		return frappe.call({
			method: "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_pos_invoices",
			args: {
				start: frappe.datetime.get_datetime_as_string(frm.doc.period_start_date),
				end: frappe.datetime.get_datetime_as_string(frm.doc.period_end_date),
				pos_profile: frm.doc.pos_profile,
				user: frm.doc.user,
			},
			callback: (r) => {
				let pos_docs = r.message;
				set_form_data(pos_docs, frm);
				refresh_fields(frm);
				set_html_data(frm);
			},
		});
	},

	before_save: async function (frm) {
		frappe.dom.freeze(__("Processing Sales! Please Wait..."));

		frm.set_value("grand_total", 0);
		frm.set_value("net_total", 0);
		frm.set_value("total_quantity", 0);
		frm.set_value("taxes", []);

		for (let row of frm.doc.payment_reconciliation) {
			row.expected_amount = row.opening_amount;
		}

		await Promise.all([
			frappe.call({
				method: "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_pos_invoices",
				args: {
					start: frappe.datetime.get_datetime_as_string(frm.doc.period_start_date),
					end: frappe.datetime.get_datetime_as_string(frm.doc.period_end_date),
					pos_profile: frm.doc.pos_profile,
					user: frm.doc.user,
				},
				callback: (r) => {
					let pos_invoices = r.message;
					for (let doc of pos_invoices) {
						frm.doc.grand_total += flt(doc.grand_total);
						frm.doc.net_total += flt(doc.net_total);
						frm.doc.total_quantity += flt(doc.total_qty);
						refresh_payments(doc, frm, false);
						refresh_taxes(doc, frm);
						refresh_fields(frm);
						set_html_data(frm);
					}
				},
			}),
		]);
		frappe.dom.unfreeze();
	},
});

frappe.ui.form.on("POS Closing Entry Detail", {
	closing_amount: (frm, cdt, cdn) => {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "difference", flt(row.closing_amount - row.expected_amount));
	},
});

function set_form_data(data, frm) {
	data.forEach((d) => {
		add_to_pos_transaction(d, frm);
		frm.doc.grand_total += flt(d.grand_total);
		frm.doc.net_total += flt(d.net_total);
		frm.doc.total_quantity += flt(d.total_qty);
		refresh_payments(d, frm, true);
		refresh_taxes(d, frm);
	});
}

function add_to_pos_transaction(d, frm) {
	frm.add_child("pos_transactions", {
		pos_invoice: d.name,
		posting_date: d.posting_date,
		grand_total: d.grand_total,
		customer: d.customer,
	});
}

function refresh_payments(d, frm, is_new) {
	d.payments.forEach((p) => {
		const payment = frm.doc.payment_reconciliation.find(
			(pay) => pay.mode_of_payment === p.mode_of_payment
		);
		if (p.account == d.account_for_change_amount) {
			p.amount -= flt(d.change_amount);
		}
		if (payment) {
			payment.expected_amount += flt(p.amount);
			if (is_new) payment.closing_amount = payment.expected_amount;
			payment.difference = payment.closing_amount - payment.expected_amount;
		} else {
			frm.add_child("payment_reconciliation", {
				mode_of_payment: p.mode_of_payment,
				opening_amount: 0,
				expected_amount: p.amount,
				closing_amount: 0,
			});
		}
	});
}

function refresh_taxes(d, frm) {
	d.taxes.forEach((t) => {
		const tax = frm.doc.taxes.find((tx) => tx.account_head === t.account_head && tx.rate === t.rate);
		if (tax) {
			tax.amount += flt(t.tax_amount);
		} else {
			frm.add_child("taxes", {
				account_head: t.account_head,
				rate: t.rate,
				amount: t.tax_amount,
			});
		}
	});
}

function reset_values(frm) {
	frm.set_value("pos_transactions", []);
	frm.set_value("payment_reconciliation", []);
	frm.set_value("taxes", []);
	frm.set_value("grand_total", 0);
	frm.set_value("net_total", 0);
	frm.set_value("total_quantity", 0);
}

function refresh_fields(frm) {
	frm.refresh_field("pos_transactions");
	frm.refresh_field("payment_reconciliation");
	frm.refresh_field("taxes");
	frm.refresh_field("grand_total");
	frm.refresh_field("net_total");
	frm.refresh_field("total_quantity");
}

function set_html_data(frm) {
	if (frm.doc.docstatus === 1 && frm.doc.status == "Submitted") {
		frappe.call({
			method: "get_payment_reconciliation_details",
			doc: frm.doc,
			callback: (r) => {
				frm.get_field("payment_reconciliation_details").$wrapper.html(r.message);
			},
		});
	}
}
