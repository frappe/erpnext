// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("POS Closing Entry", {
	onload: async function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["POS Invoice Merge Log", "Sales Invoice"];
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
				() => frm.trigger("get_invoices"),
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

	get_invoices(frm) {
		return frappe.call({
			method: "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_invoices",
			args: {
				start: frappe.datetime.get_datetime_as_string(frm.doc.period_start_date),
				end: frappe.datetime.get_datetime_as_string(frm.doc.period_end_date),
				pos_profile: frm.doc.pos_profile,
				user: frm.doc.user,
			},
			callback: (r) => {
				let inv_docs = r.message.invoices;
				set_transaction_form_data(inv_docs, frm);
				refresh_payments(r.message.payments, frm);
				add_taxes(r.message.taxes, frm);
				refresh_fields(frm);
			},
		});
	},
});

frappe.ui.form.on("POS Closing Entry Detail", {
	closing_amount: (frm, cdt, cdn) => {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "difference", flt(row.closing_amount - row.expected_amount));
	},
});

function set_transaction_form_data(data, frm) {
	data.forEach((d) => {
		add_to_transaction(d, frm);
		frm.doc.grand_total += flt(d.grand_total);
		frm.doc.net_total += flt(d.net_total);
		frm.doc.total_quantity += flt(d.total_qty);
		frm.doc.total_taxes_and_charges += flt(d.total_taxes_and_charges);
	});
}

function add_to_transaction(d, frm) {
	const field = d.doctype === "POS Invoice" ? "pos_invoices" : "sales_invoices";
	frm.add_child(field, {
		posting_date: d.posting_date,
		grand_total: d.grand_total,
		customer: d.customer,
		is_return: d.is_return,
		return_against: d.return_against,
		...(d.doctype === "POS Invoice" && { pos_invoice: d.name }),
		...(d.doctype === "Sales Invoice" && { sales_invoice: d.name }),
	});
}

function refresh_payments(payments, frm) {
	payments.forEach((p) => {
		const payment = frm.doc.payment_reconciliation.find(
			(pay) => pay.mode_of_payment === p.mode_of_payment
		);
		if (payment) {
			payment.expected_amount += flt(p.amount);
			payment.closing_amount = payment.expected_amount;
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

function add_taxes(taxes, frm) {
	taxes.forEach((t) => {
		frm.add_child("taxes", {
			account_head: t.account_head,
			amount: t.tax_amount,
		});
	});
}

function reset_values(frm) {
	frm.set_value("pos_invoices", []);
	frm.set_value("sales_invoices", []);
	frm.set_value("payment_reconciliation", []);
	frm.set_value("taxes", []);
	frm.set_value("grand_total", 0);
	frm.set_value("net_total", 0);
	frm.set_value("total_taxes_and_charges", 0);
	frm.set_value("total_quantity", 0);
}

function refresh_fields(frm) {
	frm.refresh_field("pos_invoices");
	frm.refresh_field("sales_invoices");
	frm.refresh_field("payment_reconciliation");
	frm.refresh_field("taxes");
	frm.refresh_field("grand_total");
	frm.refresh_field("net_total");
	frm.refresh_field("total_taxes_and_charges");
	frm.refresh_field("total_quantity");
}
