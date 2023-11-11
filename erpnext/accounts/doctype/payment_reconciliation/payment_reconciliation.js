// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");
erpnext.accounts.PaymentReconciliationController = class PaymentReconciliationController extends frappe.ui.form.Controller {
	onload() {
		const default_company = frappe.defaults.get_default('company');
		this.frm.set_value('company', default_company);

		this.frm.set_value('party_type', '');
		this.frm.set_value('party', '');
		this.frm.set_value('receivable_payable_account', '');

		this.frm.set_query("party_type", () => {
			return {
				"filters": {
					"name": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			}
		});

		this.frm.set_query('receivable_payable_account', () => {
			return {
				filters: {
					"company": this.frm.doc.company,
					"is_group": 0,
					"account_type": frappe.boot.party_account_types[this.frm.doc.party_type]
				}
			};
		});

		this.frm.set_query('bank_cash_account', () => {
			return {
				filters:[
					['Account', 'company', '=', this.frm.doc.company],
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'in', ['Bank', 'Cash']]
				]
			};
		});

		this.frm.set_query("cost_center", () => {
			return {
				"filters": {
					"company": this.frm.doc.company,
					"is_group": 0
				}
			}
		});
	}

	refresh() {
		this.frm.disable_save();

		this.frm.set_df_property('invoices', 'cannot_delete_rows', true);
		this.frm.set_df_property('payments', 'cannot_delete_rows', true);
		this.frm.set_df_property('allocation', 'cannot_delete_rows', true);

		this.frm.set_df_property('invoices', 'cannot_add_rows', true);
		this.frm.set_df_property('payments', 'cannot_add_rows', true);
		this.frm.set_df_property('allocation', 'cannot_add_rows', true);


		if (this.frm.doc.receivable_payable_account) {
			this.frm.add_custom_button(__('Get Unreconciled Entries'), () =>
				this.frm.trigger("get_unreconciled_entries")
			);
			this.frm.change_custom_button_type('Get Unreconciled Entries', null, 'primary');
		}
		if (this.frm.doc.invoices.length && this.frm.doc.payments.length) {
			this.frm.add_custom_button(__('Allocate'), () =>
				this.frm.trigger("allocate")
			);
			this.frm.change_custom_button_type('Allocate', null, 'primary');
			this.frm.change_custom_button_type('Get Unreconciled Entries', null, 'default');
		}
		if (this.frm.doc.allocation.length) {
			this.frm.add_custom_button(__('Reconcile'), () =>
				this.frm.trigger("reconcile")
			);
			this.frm.change_custom_button_type('Reconcile', null, 'primary');
			this.frm.change_custom_button_type('Get Unreconciled Entries', null, 'default');
			this.frm.change_custom_button_type('Allocate', null, 'default');
		}

		// check for any running reconciliation jobs
		if (this.frm.doc.receivable_payable_account) {
			this.frm.call({
				doc: this.frm.doc,
				method: 'is_auto_process_enabled',
				callback: (r) => {
					if (r.message) {
						this.frm.call({
							'method': "erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.is_any_doc_running",
							"args": {
								for_filter: {
									company: this.frm.doc.company,
									party_type: this.frm.doc.party_type,
									party: this.frm.doc.party,
									receivable_payable_account: this.frm.doc.receivable_payable_account
								}
							}
						}).then(r => {
							if (r.message) {
								let doc_link = frappe.utils.get_form_link("Process Payment Reconciliation", r.message, true);
								let msg = __("Payment Reconciliation Job: {0} is running for this party. Can't reconcile now.", [doc_link]);
								this.frm.dashboard.add_comment(msg, "yellow");
							}
						});
					}
				}
			});
		}

	}

	company() {
		this.frm.set_value('party', '');
		this.frm.set_value('receivable_payable_account', '');
	}

	party_type() {
		this.frm.set_value('party', '');
	}

	party() {
		this.frm.set_value('receivable_payable_account', '');
		this.frm.trigger("clear_child_tables");

		if (!this.frm.doc.receivable_payable_account && this.frm.doc.party_type && this.frm.doc.party) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: this.frm.doc.company,
					party_type: this.frm.doc.party_type,
					party: this.frm.doc.party
				},
				callback: (r) => {
					if (!r.exc && r.message) {
						this.frm.set_value("receivable_payable_account", r.message);
					}
					this.frm.refresh();

				}
			});
		}
	}

	receivable_payable_account() {
		this.frm.trigger("clear_child_tables");
		this.frm.refresh();
	}

	invoice_name() {
		this.frm.trigger("get_unreconciled_entries");
	}

	payment_name() {
		this.frm.trigger("get_unreconciled_entries");
	}


	clear_child_tables() {
		this.frm.clear_table("invoices");
		this.frm.clear_table("payments");
		this.frm.clear_table("allocation");
		this.frm.refresh_fields();
	}

	get_unreconciled_entries() {
		this.frm.clear_table("allocation");
		return this.frm.call({
			doc: this.frm.doc,
			method: 'get_unreconciled_entries',
			callback: () => {
				if (!(this.frm.doc.payments.length || this.frm.doc.invoices.length)) {
					frappe.throw({message: __("No Unreconciled Invoices and Payments found for this party and account")});
				} else if (!(this.frm.doc.invoices.length)) {
					frappe.throw({message: __("No Outstanding Invoices found for this party")});
				} else if (!(this.frm.doc.payments.length)) {
					frappe.throw({message: __("No Unreconciled Payments found for this party")});
				}
				this.frm.refresh();
			}
		});

	}

	allocate() {
		let payments = this.frm.fields_dict.payments.grid.get_selected_children();
		if (!(payments.length)) {
			payments = this.frm.doc.payments;
		}
		let invoices = this.frm.fields_dict.invoices.grid.get_selected_children();
		if (!(invoices.length)) {
			invoices = this.frm.doc.invoices;
		}
		return this.frm.call({
			doc: this.frm.doc,
			method: 'allocate_entries',
			args: {
				payments: payments,
				invoices: invoices
			},
			callback: () => {
				this.frm.refresh();
			}
		});
	}

	reconcile() {
		var show_dialog = this.frm.doc.allocation.filter(d => d.difference_amount);

		if (show_dialog && show_dialog.length) {

			this.data = [];
			const dialog = new frappe.ui.Dialog({
				title: __("Select Difference Account"),
				size: 'extra-large',
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
						fields: [{
							fieldtype:'Data',
							fieldname:"docname",
							in_list_view: 1,
							hidden: 1
						}, {
							fieldtype:'Data',
							fieldname:"reference_name",
							label: __("Voucher No"),
							in_list_view: 1,
							read_only: 1
						}, {
							fieldtype:'Date',
							fieldname:"gain_loss_posting_date",
							label: __("Posting Date"),
							in_list_view: 1,
							reqd: 1,
						}, {

							fieldtype:'Link',
							options: 'Account',
							in_list_view: 1,
							label: __("Difference Account"),
							fieldname: 'difference_account',
							reqd: 1,
							get_query: () => {
								return {
									filters: {
										company: this.frm.doc.company,
										is_group: 0
									}
								}
							}
						}, {
							fieldtype:'Currency',
							in_list_view: 1,
							label: __("Difference Amount"),
							fieldname: 'difference_amount',
							read_only: 1
						}]
					},
					{
						fieldtype: 'HTML',
						options: "<b> New Journal Entry will be posted for the difference amount </b>"
					}
				],
				primary_action: () => {
					const args = dialog.get_values()["allocation"];

					args.forEach(d => {
						frappe.model.set_value("Payment Reconciliation Allocation", d.docname,
							"difference_account", d.difference_account);
						frappe.model.set_value("Payment Reconciliation Allocation", d.docname,
							"gain_loss_posting_date", d.gain_loss_posting_date);

					});

					this.reconcile_payment_entries();
					dialog.hide();
				},
				primary_action_label: __('Reconcile Entries')
			});

			this.frm.doc.allocation.forEach(d => {
				if (d.difference_amount) {
					dialog.fields_dict.allocation.df.data.push({
						'docname': d.name,
						'reference_name': d.reference_name,
						'difference_amount': d.difference_amount,
						'difference_account': d.difference_account,
						'gain_loss_posting_date': d.gain_loss_posting_date
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
			method: 'reconcile',
			callback: () => {
				this.frm.clear_table("allocation");
				this.frm.refresh();
			}
		});
	}
};

frappe.ui.form.on('Payment Reconciliation Allocation', {
	allocated_amount: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		// filter invoice
		let invoice = frm.doc.invoices.filter((x) => (x.invoice_number == row.invoice_number));
		// filter payment
		let payment = frm.doc.payments.filter((x) => (x.reference_name == row.reference_name));

		frm.call({
			doc: frm.doc,
			method: 'calculate_difference_on_allocation_change',
			args: {
				payment_entry: payment,
				invoice: invoice,
				allocated_amount: row.allocated_amount
			},
			callback: (r) => {
				if (r.message) {
					row.difference_amount = r.message;
					frm.refresh();
				}
			}
		});
	}
});



extend_cscript(cur_frm.cscript, new erpnext.accounts.PaymentReconciliationController({frm: cur_frm}));
