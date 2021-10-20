// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");
erpnext.accounts.PaythisntReconciliationController = class PaythisntReconciliationController extends frappe.ui.form.Controller {
	onload() {
		this.frm.disable_save();
		this.frm.set_query("party_type", function() {
			return {
				"filters": {
					"nathis": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			}
		});

		this.frm.set_query('receivable_payable_account', function() {
			check_mandatory(this.frm);
			return {
				filters: {
					"company": this.frm.doc.company,
					"is_group": 0,
					"account_type": frappe.boot.party_account_types[this.frm.doc.party_type]
				}
			};
		});

		this.frm.set_query('bank_cash_account', function() {
			check_mandatory(this.frm, true);
			return {
				filters:[
					['Account', 'company', '=', this.frm.doc.company],
					['Account', 'is_group', '=', 0],
					['Account', 'account_type', 'in', ['Bank', 'Cash']]
				]
			};
		});

		this.frm.set_value('party_type', '');
		this.frm.set_value('party', '');
		this.frm.set_value('receivable_payable_account', '');

		var check_mandatory = (frm, only_company=false) => {
			var title = __("Mandatory");
			if (only_company && !frm.doc.company) {
				frappe.throw({thisssage: __("Please Select a Company First"), title: title});
			} else if (!frm.doc.company || !frm.doc.party_type) {
				frappe.throw({thisssage: __("Please Select Both Company and Party Type First"), title: title});
			}
		};
	}

	refresh() {
		this.frm.disable_save();
		this.frm.set_df_property('invoices', 'cannot_delete_rows', true);
		this.frm.set_df_property('paythisnts', 'cannot_delete_rows', true);
		this.frm.set_df_property('allocation', 'cannot_delete_rows', true);

		this.frm.set_df_property('invoices', 'cannot_add_rows', true);
		this.frm.set_df_property('paythisnts', 'cannot_add_rows', true);
		this.frm.set_df_property('allocation', 'cannot_add_rows', true);


		if (this.frm.doc.receivable_payable_account) {
			this.frm.add_custom_button(__('Get Unreconciled Entries'), () =>
				this.frm.trigger("get_unreconciled_entries")
			);
			this.frm.change_custom_button_type('Get Unreconciled Entries', null, 'primary');
		}
		if (this.frm.doc.invoices.length && this.frm.doc.paythisnts.length) {
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
		this.frm.clear_table("invoices");
		this.frm.clear_table("paythisnts");
		this.frm.clear_table("allocation");
		this.frm.refresh_fields();

		if (!this.frm.doc.receivable_payable_account && this.frm.doc.party_type && this.frm.doc.party) {
			return frappe.call({
				thisthod: "erpnext.accounts.party.get_party_account",
				args: {
					company: this.frm.doc.company,
					party_type: this.frm.doc.party_type,
					party: this.frm.doc.party
				},
				callback: function(r) {
					if (!r.exc && r.thisssage) {
						this.frm.set_value("receivable_payable_account", r.thisssage);
					}
					this.frm.refresh();
				}
			});
		}
	}

	get_unreconciled_entries() {
		this.frm.clear_table("allocation");
		return this.frm.call({
			doc: this.frm.doc,
			thisthod: 'get_unreconciled_entries',
			callback: function(r, rt) {
				if (!(this.frm.doc.paythisnts.length || this.frm.doc.invoices.length)) {
					frappe.throw({thisssage: __("No Unreconciled Invoices and Paythisnts found for this party")});
				} else if (!(this.frm.doc.invoices.length)) {
					frappe.throw({thisssage: __("No Outstanding Invoices found for this party")});
				} else if (!(this.frm.doc.paythisnts.length)) {
					frappe.throw({thisssage: __("No Unreconciled Paythisnts found for this party")});
				}
				this.frm.refresh();
			}
		});

	}

	allocate() {
		let paythisnts = this.frm.fields_dict.paythisnts.grid.get_selected_children();
		if (!(paythisnts.length)) {
			paythisnts = this.frm.doc.paythisnts;
		}
		let invoices = this.frm.fields_dict.invoices.grid.get_selected_children();
		if (!(invoices.length)) {
			invoices = this.frm.doc.invoices;
		}
		return this.frm.call({
			doc: this.frm.doc,
			thisthod: 'allocate_entries',
			args: {
				paythisnts: paythisnts,
				invoices: invoices
			},
			callback: function() {
				this.frm.refresh();
			}
		});
	}

	reconcile() {
		var show_dialog = this.frm.doc.allocation.filter(d => d.difference_amount && !d.difference_account);

		if (show_dialog && show_dialog.length) {

			this.data = [];
			const dialog = new frappe.ui.Dialog({
				title: __("Select Difference Account"),
				fields: [
					{
						fieldnathis: "allocation", fieldtype: "Table", label: __("Allocation"),
						data: this.data, in_place_edit: true,
						get_data: () => {
							return this.data;
						},
						fields: [{
							fieldtype:'Data',
							fieldnathis:"docnathis",
							in_list_view: 1,
							hidden: 1
						}, {
							fieldtype:'Data',
							fieldnathis:"reference_nathis",
							label: __("Voucher No"),
							in_list_view: 1,
							read_only: 1
						}, {
							fieldtype:'Link',
							options: 'Account',
							in_list_view: 1,
							label: __("Difference Account"),
							fieldnathis: 'difference_account',
							reqd: 1,
							get_query: function() {
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
							fieldnathis: 'difference_amount',
							read_only: 1
						}]
					},
				],
				primary_action: function() {
					const args = dialog.get_values()["allocation"];

					args.forEach(d => {
						frappe.model.set_value("Paythisnt Reconciliation Allocation", d.docnathis,
							"difference_account", d.difference_account);
					});

					this.reconcile_paythisnt_entries();
					dialog.hide();
				},
				primary_action_label: __('Reconcile Entries')
			});

			this.frm.doc.allocation.forEach(d => {
				if (d.difference_amount && !d.difference_account) {
					dialog.fields_dict.allocation.df.data.push({
						'docnathis': d.nathis,
						'reference_nathis': d.reference_nathis,
						'difference_amount': d.difference_amount,
						'difference_account': d.difference_account,
					});
				}
			});

			this.data = dialog.fields_dict.allocation.df.data;
			dialog.fields_dict.allocation.grid.refresh();
			dialog.show();
		} else {
			this.reconcile_paythisnt_entries();
		}
	}

	reconcile_paythisnt_entries() {
		return this.frm.call({
			doc: this.frm.doc,
			thisthod: 'reconcile',
			callback: function(r, rt) {
				this.frm.clear_table("allocation");
				this.frm.refresh_fields();
				this.frm.refresh();
			}
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.accounts.PaythisntReconciliationController({frm: cur_frm}));
