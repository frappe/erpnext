// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");
<<<<<<< HEAD

frappe.ui.form.on("Payment Reconciliation Payment", {
	invoice_number: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.invoice_number) {
			var parts = row.invoice_number.split(' | ');
			var invoice_type = parts[0];
			var invoice_number = parts[1];

			var invoice_amount = frm.doc.invoices.filter(function(d) {
				return d.invoice_type === invoice_type && d.invoice_number === invoice_number;
			})[0].outstanding_amount;

			frappe.model.set_value(cdt, cdn, "allocated_amount", Math.min(invoice_amount, row.amount));

			frm.call({
				doc: frm.doc,
				method: 'get_difference_amount',
				args: {
					child_row: row
				},
				callback: function(r, rt) {
					if(r.message) {
						frappe.model.set_value(cdt, cdn,
							"difference_amount", r.message);
					}
				}
			});
		}
	}
});

erpnext.accounts.PaymentReconciliationController = frappe.ui.form.Controller.extend({
	onload: function() {
=======
erpnext.accounts.PaymentReconciliationController = class PaymentReconciliationController extends frappe.ui.form.Controller {
	onload() {
>>>>>>> 3e404f15ff (refactor: payment reconciliation tool (#27128))
		var me = this;

		this.frm.set_query("party_type", function() {
			return {
				"filters": {
					"name": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			}
		});

		this.frm.set_query('receivable_payable_account', function() {
			check_mandatory(me.frm);
			return {
				filters: {
					"company": me.frm.doc.company,
					"is_group": 0,
					"account_type": frappe.boot.party_account_types[me.frm.doc.party_type]
				}
			};
		});

		this.frm.set_query('bank_cash_account', function() {
			check_mandatory(me.frm, true);
			return {
				filters:[
					['Account', 'company', '=', me.frm.doc.company],
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
				frappe.throw({message: __("Please Select a Company First"), title: title});
			} else if (!frm.doc.company || !frm.doc.party_type) {
				frappe.throw({message: __("Please Select Both Company and Party Type First"), title: title});
			}
		};
	},

	refresh: function() {
		this.frm.disable_save();
<<<<<<< HEAD
		this.toggle_primary_action();
	},

	onload_post_render: function() {
		this.toggle_primary_action();
	},

	party: function() {
		var me = this
=======

		if (this.frm.doc.receivable_payable_account) {
			this.frm.add_custom_button(__('Get Unreconciled Entries'), () =>
				this.frm.trigger("get_unreconciled_entries")
			);
		}
		if (this.frm.doc.invoices.length && this.frm.doc.payments.length) {
			this.frm.add_custom_button(__('Allocate'), () =>
				this.frm.trigger("allocate")
			);
		}
		if (this.frm.doc.allocation.length) {
			this.frm.add_custom_button(__('Reconcile'), () =>
				this.frm.trigger("reconcile")
			);
		}
	}

	company() {
		var me = this;
		this.frm.set_value('receivable_payable_account', '');
		me.frm.clear_table("allocation");
		me.frm.clear_table("invoices");
		me.frm.clear_table("payments");
		me.frm.refresh_fields();
		me.frm.trigger('party');
	}

	party() {
		var me = this;
>>>>>>> 3e404f15ff (refactor: payment reconciliation tool (#27128))
		if (!me.frm.doc.receivable_payable_account && me.frm.doc.party_type && me.frm.doc.party) {
			return frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					company: me.frm.doc.company,
					party_type: me.frm.doc.party_type,
					party: me.frm.doc.party
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						me.frm.set_value("receivable_payable_account", r.message);
					}
					me.frm.refresh();
				}
			});
		}
	},

	get_unreconciled_entries: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_unreconciled_entries',
			callback: function(r, rt) {
				if (!(me.frm.doc.payments.length || me.frm.doc.invoices.length)) {
					frappe.throw({message: __("No invoice and payment records found for this party")});
				}
				me.frm.refresh();
			}
		});

	},

<<<<<<< HEAD
	reconcile: function() {
=======
	allocate() {
		var me = this;
		let payments = me.frm.fields_dict.payments.grid.get_selected_children();
		if (!(payments.length)) {
			payments = me.frm.doc.payments;
		}
		let invoices = me.frm.fields_dict.invoices.grid.get_selected_children();
		if (!(invoices.length)) {
			invoices = me.frm.doc.invoices;
		}
		return me.frm.call({
			doc: me.frm.doc,
			method: 'allocate_entries',
			args: {
				payments: payments,
				invoices: invoices
			},
			callback: function() {
				me.frm.refresh();
			}
		});
	}

	reconcile() {
>>>>>>> 3e404f15ff (refactor: payment reconciliation tool (#27128))
		var me = this;
		var show_dialog = me.frm.doc.allocation.filter(d => d.difference_amount && !d.difference_account);

		if (show_dialog && show_dialog.length) {

			this.data = [];
			const dialog = new frappe.ui.Dialog({
				title: __("Select Difference Account"),
				fields: [
					{
						fieldname: "allocation", fieldtype: "Table", label: __("Allocation"),
						data: this.data, in_place_edit: true,
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
							fieldtype:'Link',
							options: 'Account',
							in_list_view: 1,
							label: __("Difference Account"),
							fieldname: 'difference_account',
							reqd: 1,
							get_query: function() {
								return {
									filters: {
										company: me.frm.doc.company,
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
				],
				primary_action: function() {
					const args = dialog.get_values()["allocation"];

					args.forEach(d => {
						frappe.model.set_value("Payment Reconciliation Allocation", d.docname,
							"difference_account", d.difference_account);
					});

					me.reconcile_payment_entries();
					dialog.hide();
				},
				primary_action_label: __('Reconcile Entries')
			});

			this.frm.doc.allocation.forEach(d => {
				if (d.difference_amount && !d.difference_account) {
					dialog.fields_dict.allocation.df.data.push({
						'docname': d.name,
						'reference_name': d.reference_name,
						'difference_amount': d.difference_amount,
						'difference_account': d.difference_account,
					});
				}
			});

			this.data = dialog.fields_dict.allocation.df.data;
			dialog.fields_dict.allocation.grid.refresh();
			dialog.show();
		} else {
			this.reconcile_payment_entries();
		}
	},

	reconcile_payment_entries: function() {
		var me = this;

		return this.frm.call({
			doc: me.frm.doc,
			method: 'reconcile',
			callback: function(r, rt) {
				me.frm.clear_table("allocation");
				me.frm.refresh_fields();
				me.frm.refresh();
			}
		});
<<<<<<< HEAD
	},

	set_invoice_options: function() {
		var me = this;
		var invoices = [];

		$.each(me.frm.doc.invoices || [], function(i, row) {
			if (row.invoice_number && !in_list(invoices, row.invoice_number))
				invoices.push(row.invoice_type + " | " + row.invoice_number);
		});

		if (invoices) {
			this.frm.fields_dict.payments.grid.update_docfield_property(
				'invoice_number', 'options', "\n" + invoices.join("\n")
			);

			$.each(me.frm.doc.payments || [], function(i, p) {
				if(!in_list(invoices, cstr(p.invoice_number))) p.invoice_number = null;
			});
		}

		refresh_field("payments");
	},

	toggle_primary_action: function() {
		if ((this.frm.doc.payments || []).length) {
			this.frm.fields_dict.reconcile.$input
				&& this.frm.fields_dict.reconcile.$input.addClass("btn-primary");
			this.frm.fields_dict.get_unreconciled_entries.$input
				&& this.frm.fields_dict.get_unreconciled_entries.$input.removeClass("btn-primary");
		} else {
			this.frm.fields_dict.reconcile.$input
				&& this.frm.fields_dict.reconcile.$input.removeClass("btn-primary");
			this.frm.fields_dict.get_unreconciled_entries.$input
				&& this.frm.fields_dict.get_unreconciled_entries.$input.addClass("btn-primary");
		}
	}

});
=======
	}
};
>>>>>>> 3e404f15ff (refactor: payment reconciliation tool (#27128))

$.extend(cur_frm.cscript, new erpnext.accounts.PaymentReconciliationController({frm: cur_frm}));
