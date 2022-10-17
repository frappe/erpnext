// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// get tax rate
frappe.provide("erpnext.taxes");
frappe.provide("erpnext.taxes.flags");

frappe.ui.form.on(cur_frm.doctype, {
	setup: function(frm) {
		// set conditional display for rate column in taxes
		$(frm.wrapper).on('grid-row-render', function(e, grid_row) {
			if(in_list(['Sales Taxes and Charges', 'Purchase Taxes and Charges'], grid_row.doc.doctype)) {
				erpnext.taxes.set_conditional_mandatory_rate_or_amount(grid_row);
			}
		});
	},
	onload: function(frm) {
		if(frm.get_field("taxes")) {
			frm.set_query("account_head", "taxes", function(doc) {
				if(frm.cscript.tax_table == "Sales Taxes and Charges") {
					var account_type = ["Tax", "Chargeable", "Expense Account"];
				} else {
					var account_type = ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation"];
				}

				return {
					query: "erpnext.controllers.queries.tax_account_query",
					filters: {
						"account_type": account_type,
						"company": doc.company,
						"disabled": 0
					}
				}
			});
			frm.set_query("cost_center", "taxes", function(doc) {
				return {
					filters: {
						"company": doc.company,
						"is_group": 0
					}
				};
			});
		}
	},
	validate: function(frm) {
		// neither is absolutely mandatory
		if(frm.get_docfield("taxes")) {
			frm.get_docfield("taxes", "rate").reqd = 0;
			frm.get_docfield("taxes", "tax_amount").reqd = 0;
		}

	},
	taxes_on_form_rendered: function(frm) {
		erpnext.taxes.set_conditional_mandatory_rate_or_amount(frm.open_grid_row());
	},

	allocate_advances_automatically: function(frm) {
		if(frm.doc.allocate_advances_automatically) {
			frappe.call({
				doc: frm.doc,
				method: "set_advances",
				callback: function(r, rt) {
					refresh_field("advances");
				}
			})
		}
	}
});

frappe.ui.form.on('Sales Invoice Payment', {
	mode_of_payment: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		get_payment_mode_account(frm, d.mode_of_payment, function(account){
			frappe.model.set_value(cdt, cdn, 'account', account)
		})
	}
});

frappe.ui.form.on("Sales Invoice", {
	payment_terms_template: function() {
		cur_frm.trigger("disable_due_date");
	}
});

frappe.ui.form.on('Purchase Invoice', {
	mode_of_payment: function(frm) {
		get_payment_mode_account(frm, frm.doc.mode_of_payment, function(account){
			frm.set_value('cash_bank_account', account);
		})
	},

	payment_terms_template: function() {
		cur_frm.trigger("disable_due_date");
	}
});

frappe.ui.form.on("Payment Schedule", {
	payment_schedule_remove: function() {
		cur_frm.trigger("disable_due_date");
	},

});

frappe.ui.form.on('Payment Entry', {
	mode_of_payment: function(frm) {
		get_payment_mode_account(frm, frm.doc.mode_of_payment, function(account){
			var payment_account_field = frm.doc.payment_type == "Receive" ? "paid_to" : "paid_from";
			frm.set_value(payment_account_field, account);
		})
	}
})

frappe.ui.form.on('Salary Structure', {
	mode_of_payment: function(frm) {
		get_payment_mode_account(frm, frm.doc.mode_of_payment, function(account){
			frm.set_value("payment_account", account);
		})
	}
})

var get_payment_mode_account = function(frm, mode_of_payment, callback) {
	if(!frm.doc.company) {
		frappe.throw({message:__("Please select a Company first."), title: __("Mandatory")});
	}

	if(!mode_of_payment) {
		return;
	}

	return  frappe.call({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
		args: {
			"mode_of_payment": mode_of_payment,
			"company": frm.doc.company
		},
		callback: function(r, rt) {
			if(r.message) {
				callback(r.message.account)
			}
		}
	});
}

cur_frm.cscript.account_head = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];

	if (doc.docstatus == 1) {
		// Should not trigger any changes on change post submit
		return;
	}

	if(!d.charge_type && d.account_head){
		frappe.msgprint(__("Please select Charge Type first"));
		frappe.model.set_value(cdt, cdn, "account_head", "");
	} else if (d.account_head) {
		frappe.call({
			type:"GET",
			method: "erpnext.controllers.accounts_controller.get_tax_rate",
			args: {"account_head":d.account_head},
			callback: function(r) {
				if (d.charge_type!=="Actual") {
					frappe.model.set_value(cdt, cdn, "rate", r.message.tax_rate || 0);
				}
				frappe.model.set_value(cdt, cdn, "description", r.message.account_name);
			}
		})
	}
}

cur_frm.cscript.validate_taxes_and_charges = function(cdt, cdn) {
	var d = locals[cdt][cdn];
	var msg = "";

	if (d.account_head && !d.description) {
		// set description from account head
		d.description = d.account_head.split(' - ').slice(0, -1).join(' - ');
	}

	if (!d.charge_type && (d.row_id || d.rate || d.tax_amount)) {
		msg = __("Please select Charge Type first");
		d.row_id = "";
		d.rate = d.tax_amount = 0.0;
	} else if ((d.charge_type == 'Actual' || d.charge_type == 'On Net Total' || d.charge_type == 'On Paid Amount') && d.row_id) {
		msg = __("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'");
		d.row_id = "";
	} else if ((d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total') && d.row_id) {
		if (d.idx == 1) {
			msg = __("Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row");
			d.charge_type = '';
		} else if (!d.row_id) {
			msg = __("Please specify a valid Row ID for row {0} in table {1}", [d.idx, __(d.doctype)]);
			d.row_id = "";
		} else if (d.row_id && d.row_id >= d.idx) {
			msg = __("Cannot refer row number greater than or equal to current row number for this Charge type");
			d.row_id = "";
		}
	}
	if (msg) {
		frappe.validated = false;
		refresh_field("taxes");
		frappe.throw(msg);
	}

}

cur_frm.cscript.validate_inclusive_tax = function(tax) {
	var actual_type_error = function() {
		var msg = __("Actual type tax cannot be included in Item rate in row {0}", [tax.idx])
		frappe.throw(msg);
	};

	var on_previous_row_error = function(row_range) {
		var msg = __("For row {0} in {1}. To include {2} in Item rate, rows {3} must also be included",
			[tax.idx, __(tax.doctype), tax.charge_type, row_range])
		frappe.throw(msg);
	};

	if(cint(tax.included_in_print_rate)) {
		if(tax.charge_type == "Actual") {
			// inclusive tax cannot be of type Actual
			actual_type_error();
		} else if(tax.charge_type == "On Previous Row Amount" &&
			!cint(this.frm.doc["taxes"][tax.row_id - 1].included_in_print_rate)
		) {
			// referred row should also be an inclusive tax
			on_previous_row_error(tax.row_id);
		} else if(tax.charge_type == "On Previous Row Total") {
			var taxes_not_included = $.map(this.frm.doc["taxes"].slice(0, tax.row_id),
				function(t) { return cint(t.included_in_print_rate) ? null : t; });
			if(taxes_not_included.length > 0) {
				// all rows above this tax should be inclusive
				on_previous_row_error(tax.row_id == 1 ? "1" : "1 - " + tax.row_id);
			}
		} else if(tax.category == "Valuation") {
			frappe.throw(__("Valuation type charges can not marked as Inclusive"));
		}
	}
}

if(!erpnext.taxes.flags[cur_frm.cscript.tax_table]) {
	erpnext.taxes.flags[cur_frm.cscript.tax_table] = true;

	frappe.ui.form.on(cur_frm.cscript.tax_table, "row_id", function(frm, cdt, cdn) {
		cur_frm.cscript.validate_taxes_and_charges(cdt, cdn);
	});

	frappe.ui.form.on(cur_frm.cscript.tax_table, "rate", function(frm, cdt, cdn) {
		cur_frm.cscript.validate_taxes_and_charges(cdt, cdn);
	});

	frappe.ui.form.on(cur_frm.cscript.tax_table, "tax_amount", function(frm, cdt, cdn) {
		cur_frm.cscript.validate_taxes_and_charges(cdt, cdn);
	});

	frappe.ui.form.on(cur_frm.cscript.tax_table, "charge_type", function(frm, cdt, cdn) {
		frm.cscript.validate_taxes_and_charges(cdt, cdn);
		var open_form = frm.open_grid_row();
		if(open_form) {
			erpnext.taxes.set_conditional_mandatory_rate_or_amount(open_form);
		} else {
			// apply in current row
			erpnext.taxes.set_conditional_mandatory_rate_or_amount(frm.get_field('taxes').grid.get_row(cdn));
		}
	});

	frappe.ui.form.on(cur_frm.cscript.tax_table, "included_in_print_rate", function(frm, cdt, cdn) {
		var tax = frappe.get_doc(cdt, cdn);
		try {
			cur_frm.cscript.validate_taxes_and_charges(cdt, cdn);
			cur_frm.cscript.validate_inclusive_tax(tax);
		} catch(e) {
			tax.included_in_print_rate = 0;
			refresh_field("included_in_print_rate", tax.name, tax.parentfield);
			throw e;
		}
	});
}

erpnext.taxes.set_conditional_mandatory_rate_or_amount = function(grid_row) {
	if(grid_row) {
		if(grid_row.doc.charge_type==="Actual") {
			grid_row.toggle_editable("tax_amount", true);
			grid_row.toggle_reqd("tax_amount", true);
			grid_row.toggle_editable("rate", false);
			grid_row.toggle_reqd("rate", false);
		} else {
			grid_row.toggle_editable("rate", true);
			grid_row.toggle_reqd("rate", true);
			grid_row.toggle_editable("tax_amount", false);
			grid_row.toggle_reqd("tax_amount", false);
		}
	}
}
