// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");
erpnext.accounts.PaymentReconciliationController = class PaymentReconciliationController extends (
	frappe.ui.form.Controller
) {
	onload() {
		const default_company = frappe.defaults.get_default("company");
		this.frm.set_value("company", default_company);

		this.frm.set_value("party_type", "");
		this.frm.set_value("party", "");
		this.frm.set_value("receivable_payable_account", "");

		this.frm.set_query("party_type", () => {
			return {
				filters: {
					name: ["in", Object.keys(frappe.boot.party_account_types)],
				},
			};
		});

		this.frm.set_query("receivable_payable_account", () => {
			return {
				filters: {
					company: this.frm.doc.company,
					is_group: 0,
					account_type: frappe.boot.party_account_types[this.frm.doc.party_type],
					root_type: this.frm.doc.party_type == "Customer" ? "Asset" : "Liability",
				},
			};
		});

		this.frm.set_query("default_advance_account", () => {
			return {
				filters: {
					company: this.frm.doc.company,
					is_group: 0,
					account_type: this.frm.doc.party_type == "Customer" ? "Receivable" : "Payable",
					root_type: this.frm.doc.party_type == "Customer" ? "Liability" : "Asset",
				},
			};
		});

		this.frm.set_query("cost_center", () => {
			return {
				filters: {
					company: this.frm.doc.company,
					is_group: 0,
				},
			};
		});
		this.frm.set_query("cost_center", "to_pay", () => {
			return {
				filters: {
					company: this.frm.doc.company,
					is_group: 0,
				},
			};
		});
		this.frm.set_query("cost_center", "to_receive", () => {
			return {
				filters: {
					company: this.frm.doc.company,
					is_group: 0,
				},
			};
		});
		this.frm.set_query("cost_center", "allocation", () => {
			return {
				filters: {
					company: this.frm.doc.company,
					is_group: 0,
				},
			};
		});
	}

	refresh() {
		this.frm.disable_save();
		this.set_party_from_route();

		this.frm.set_df_property("to_receive", "cannot_delete_rows", true);
		this.frm.set_df_property("to_pay", "cannot_delete_rows", true);
		this.frm.set_df_property("allocation", "cannot_delete_rows", true);

		this.frm.set_df_property("to_receive", "cannot_add_rows", true);
		this.frm.set_df_property("to_pay", "cannot_add_rows", true);
		this.frm.set_df_property("allocation", "cannot_add_rows", true);

		if (this.frm.doc.party) {
			this.frm.add_custom_button(__("Get Unreconciled Entries"), () =>
				this.frm.trigger("get_unreconciled_entries")
			);
			this.frm.change_custom_button_type(__("Get Unreconciled Entries"), null, "primary");
		}
		if (this.frm.doc.to_receive.length && this.frm.doc.to_pay.length) {
			this.frm.add_custom_button(__("Allocate"), () => this.frm.trigger("allocate"));
			this.frm.change_custom_button_type(__("Allocate"), null, "primary");
			this.frm.change_custom_button_type(__("Get Unreconciled Entries"), null, "default");
		}
		if (this.frm.doc.allocation.length) {
			this.frm.add_custom_button(__("Reconcile"), () => this.frm.trigger("reconcile"));
			this.frm.change_custom_button_type(__("Reconcile"), null, "primary");
			this.frm.change_custom_button_type(__("Get Unreconciled Entries"), null, "default");
			this.frm.change_custom_button_type(__("Allocate"), null, "default");
		}

		this.frm.trigger("set_query_for_dimension_filters");
		this.update_totals();
		this.bind_totals_on_row_select();

		// check for any running reconciliation jobs
		if (this.frm.doc.party) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation.is_auto_process_enabled",
				callback: (r) => {
					if (r.message) {
						this.frm
							.call({
								method: "erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.is_any_doc_running",
								args: {
									for_filter: {
										company: this.frm.doc.company,
										party_type: this.frm.doc.party_type,
										party: this.frm.doc.party,
										receivable_payable_account:
											this.frm.doc.receivable_payable_account || null,
									},
								},
							})
							.then((r) => {
								if (r.message) {
									let doc_link = frappe.utils.get_form_link(
										"Process Payment Reconciliation",
										r.message,
										true
									);
									let msg = __(
										"Payment Reconciliation Job: {0} is running for this party. Can't reconcile now.",
										[doc_link]
									);
									this.frm.dashboard.add_comment(msg, "yellow");
								}
							});
					}
				},
			});
		}
	}
	set_party_from_route() {
		const { company, party_type, party } = frappe.route_options || {};
		if (!party) return;
		frappe.route_options = null;
		this.frm.set_value({ company, party_type, party }).then(() => {
			if (this.frm.doc.receivable_payable_account) this.frm.trigger("get_unreconciled_entries");
		});
	}
	set_query_for_dimension_filters() {
		frappe.call({
			method: "erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation.get_queries_for_dimension_filters",
			args: {
				company: this.frm.doc.company,
			},
			callback: (r) => {
				if (!r.exc && r.message) {
					r.message.forEach((x) => {
						this.frm.set_query(x.fieldname, () => {
							return {
								filters: x.filters,
							};
						});
					});
				}
			},
		});
	}

	company() {
		this.frm.set_value("party", "");
		this.frm.set_value("receivable_payable_account", "");
	}

	party_type() {
		this.frm.set_value("party", "");
	}

	party() {
		this.frm.set_value("receivable_payable_account", "");
		this.frm.trigger("clear_child_tables");

		if (!this.frm.doc.receivable_payable_account && this.frm.doc.party_type && this.frm.doc.party) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: this.frm.doc.company,
					party_type: this.frm.doc.party_type,
					party: this.frm.doc.party,
					include_advance: 1,
				},
				callback: (r) => {
					if (!r.exc && r.message) {
						if (typeof r.message === "string") {
							this.frm.set_value("receivable_payable_account", r.message);
						} else if (Array.isArray(r.message)) {
							this.frm.set_value("receivable_payable_account", r.message[0]);
							this.frm.set_value("default_advance_account", r.message[1]);
						}
					}
					this.frm.refresh();
				},
			});
		}
	}

	receivable_payable_account() {
		this.frm.trigger("clear_child_tables");
		this.frm.refresh();
	}

	clear_child_tables() {
		this.frm.clear_table("to_receive");
		this.frm.clear_table("to_pay");
		this.frm.clear_table("allocation");
		this.frm.refresh_fields();
		this.update_totals();
	}

	update_totals() {
		const to_receive = this.frm.fields_dict.to_receive.grid.get_selected_children();
		const to_pay = this.frm.fields_dict.to_pay.grid.get_selected_children();
		const sum = (rows) => rows.reduce((total, row) => total + flt(row.outstanding_amount), 0);
		const total_invoice_amount = sum(to_receive);
		const total_payment_amount = sum(to_pay);

		this.frm.set_value({
			currency: [...to_receive, ...to_pay][0]?.currency || this.frm.doc.currency,
			total_invoice_amount,
			total_payment_amount,
			difference_amount: total_invoice_amount - total_payment_amount,
		});
	}

	bind_totals_on_row_select() {
		["to_receive", "to_pay"].forEach((fieldname) => {
			this.frm.fields_dict[fieldname].grid.wrapper
				.off("click.pr_totals")
				.on("click.pr_totals", ".grid-row-check", () => this.update_totals());
		});
	}

	get_unreconciled_entries() {
		this.frm.clear_table("allocation");
		return this.frm.call({
			doc: this.frm.doc,
			method: "get_unreconciled_entries",
			callback: () => {
				this.update_totals();
				if (!(this.frm.doc.to_pay.length || this.frm.doc.to_receive.length)) {
					frappe.throw({
						message: __("No Unreconciled entries found for this party"),
					});
				} else if (!this.frm.doc.to_receive.length) {
					frappe.throw({ message: __("No 'To Receive' entries found for this party") });
				} else if (!this.frm.doc.to_pay.length) {
					frappe.throw({ message: __("No 'To Pay' entries found for this party") });
				}
				this.frm.refresh();
			},
		});
	}

	allocate() {
		const to_receive_rows = this.frm.fields_dict.to_receive.grid.get_selected_children();
		const to_pay_rows = this.frm.fields_dict.to_pay.grid.get_selected_children();

		const args = {};
		if (to_receive_rows.length) args.to_receive = to_receive_rows;
		if (to_pay_rows.length) args.to_pay = to_pay_rows;

		return this.frm.call({
			doc: this.frm.doc,
			method: "allocate_entries",
			args: args,
			callback: () => {
				this.frm.refresh();
			},
		});
	}

	reconcile() {
		var show_dialog = this.frm.doc.allocation.filter((d) => d.difference_amount);

		if (show_dialog && show_dialog.length) {
			this.data = [];
			const dialog = new frappe.ui.Dialog({
				title: __("Select Difference Account"),
				size: "extra-large",
				fields: [
					{
						fieldname: "allocation",
						fieldtype: "Table",
						label: __("Allocation"),
						data: this.data,
						in_place_edit: true,
						cannot_add_rows: true,
						get_data: () => {
							return this.data;
						},
						fields: [
							{
								fieldtype: "Data",
								fieldname: "docname",
								in_list_view: 1,
								hidden: 1,
							},
							{
								fieldtype: "Data",
								fieldname: "voucher_no",
								label: __("Voucher No"),
								in_list_view: 1,
								read_only: 1,
							},
							{
								fieldtype: "Date",
								fieldname: "gain_loss_posting_date",
								label: __("Posting Date"),
								in_list_view: 1,
								reqd: 1,
							},
							{
								fieldtype: "Link",
								options: "Account",
								in_list_view: 1,
								label: __("Difference Account"),
								fieldname: "difference_account",
								reqd: 1,
								get_query: () => {
									return {
										filters: {
											company: this.frm.doc.company,
											is_group: 0,
										},
									};
								},
							},
							{
								fieldtype: "Currency",
								in_list_view: 1,
								label: __("Difference Amount"),
								fieldname: "difference_amount",
								read_only: 1,
							},
						],
					},
					{
						fieldtype: "HTML",
						options: __(
							"New Journal Entry will be posted for the difference amount. The Posting Date can be modified."
						).bold(),
					},
				],
				primary_action: () => {
					const args = dialog.get_values()["allocation"];

					args.forEach((d) => {
						frappe.model.set_value(
							"Payment Reconciliation Allocation",
							d.docname,
							"difference_account",
							d.difference_account
						);
						frappe.model.set_value(
							"Payment Reconciliation Allocation",
							d.docname,
							"gain_loss_posting_date",
							d.gain_loss_posting_date
						);
					});

					this.reconcile_payment_entries();
					dialog.hide();
				},
				primary_action_label: __("Reconcile Entries"),
			});

			const paid_side =
				frappe.boot.party_account_types[this.frm.doc.party_type] === "Receivable" ? "to_pay" : "to_receive";
			this.frm.doc.allocation.forEach((d) => {
				if (d.difference_amount) {
					dialog.fields_dict.allocation.df.data.push({
						docname: d.name,
						voucher_no: d[`${paid_side}_voucher_no`],
						difference_amount: d.difference_amount,
						difference_account: d.difference_account,
						gain_loss_posting_date: d.gain_loss_posting_date,
					});
				}
			});

			this.data = dialog.fields_dict.allocation.df.data;
			dialog.fields_dict.allocation.grid.refresh();
			dialog.show();
		} else {
			this.reconcile_payment_entries();
		}
	}

	reconcile_payment_entries() {
		return this.frm.call({
			doc: this.frm.doc,
			method: "reconcile",
			callback: () => {
				this.frm.clear_table("allocation");
				this.frm.refresh();
			},
		});
	}
};

frappe.ui.form.on("Payment Reconciliation Allocation", {
	allocated_amount: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const same_row = (x, side) =>
			x.voucher_type == row[`${side}_voucher_type`] &&
			x.voucher_no == row[`${side}_voucher_no`] &&
			(x.voucher_row || "") == (row[`${side}_voucher_row`] || "");
		const recv = (frm.doc.to_receive || []).filter((x) => same_row(x, "to_receive"));
		const pay = (frm.doc.to_pay || []).filter((x) => same_row(x, "to_pay"));
		if (!recv.length || !pay.length) return;

		frm.call({
			doc: frm.doc,
			method: "calculate_difference_on_allocation_change",
			args: {
				payment_entry: pay,
				invoice: recv,
				allocated_amount: row.allocated_amount,
			},
			callback: (r) => {
				frappe.model.set_value(cdt, cdn, "difference_amount", r.message || 0);
			},
		});
	},
});

frappe.ui.form.set_controller("Payment Reconciliation", erpnext.accounts.PaymentReconciliationController);
