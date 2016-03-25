// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.payment_tool");

// Help content
frappe.ui.form.on("Payment Tool", "onload", function(frm) {
	frm.set_value("make_jv_help",
		+ __("Note: If payment is not made against any reference, make Journal Entry manually."));

	frm.set_query("party_type", function() {
		return {
			filters: {"name": ["in", ["Customer", "Supplier"]]}
		};
	});

	frm.set_query("payment_account", function() {
		return {
			filters: {
				"account_type": ["in", ["Bank", "Cash"]],
				"is_group": 0,
				"company": frm.doc.company
			}
		}
	});

	frm.set_query("against_voucher_type", "vouchers", function() {
		if (frm.doc.party_type=="Customer") {
			var doctypes = ["Sales Order", "Sales Invoice", "Journal Entry"];
		} else {
			var doctypes = ["Purchase Order", "Purchase Invoice", "Journal Entry"];
		}

		return {
			filters: { "name": ["in", doctypes] }
		};
	});
});

frappe.ui.form.on("Payment Tool", "refresh", function(frm) {
	frm.disable_save();
	frappe.ui.form.trigger("Payment Tool", "party_type");
});

frappe.ui.form.on("Payment Tool", "party_type", function(frm) {
	frm.set_value("received_or_paid", frm.doc.party_type=="Customer" ? "Received" : "Paid");
});

frappe.ui.form.on("Payment Tool", "party", function(frm) {
	if(frm.doc.party_type && frm.doc.party) {
		return frappe.call({
			method: "erpnext.accounts.party.get_party_account",
			args: {
				company: frm.doc.company,
				party_type: frm.doc.party_type,
				party: frm.doc.party
			},
			callback: function(r) {
				if(!r.exc && r.message) {
					frm.set_value("party_account", r.message);
					erpnext.payment_tool.check_mandatory_to_set_button(frm);
				}
			}
		});
	}
})

frappe.ui.form.on("Payment Tool", "party_account", function(frm) {
	if(frm.doc.party_account) {
		frm.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Account",
				fieldname: "account_currency",
				filters: { name: frm.doc.party_account },
			},
			callback: function(r, rt) {
				if(r.message) {
					frm.set_value("party_account_currency", r.message.account_currency);
					erpnext.payment_tool.check_mandatory_to_set_button(frm);
				}
			}
		});
	}
})

frappe.ui.form.on("Payment Tool", "company", function(frm) {
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

frappe.ui.form.on("Payment Tool", "received_or_paid", function(frm) {
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

// Fetch bank/cash account based on payment mode
frappe.ui.form.on("Payment Tool", "payment_mode", function(frm) {
	return  frappe.call({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
		args: {
				"mode_of_payment": frm.doc.payment_mode,
				"company": frm.doc.company
		},
		callback: function(r, rt) {
			if(r.message) {
				cur_frm.set_value("payment_account", r.message['account']);
			}
		}
	});
});


erpnext.payment_tool.check_mandatory_to_set_button = function(frm) {
	if (frm.doc.company && frm.doc.party_type && frm.doc.party && frm.doc.received_or_paid && frm.doc.party_account) {
		frm.fields_dict.get_outstanding_vouchers.$input.addClass("btn-primary");
	}
}

// Get outstanding vouchers
frappe.ui.form.on("Payment Tool", "get_outstanding_vouchers", function(frm) {
	erpnext.payment_tool.check_mandatory_to_fetch(frm.doc);

	frm.set_value("vouchers", []);

	return  frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_outstanding_vouchers',
		args: {
			args: {
				"company": frm.doc.company,
				"party_type": frm.doc.party_type,
				"received_or_paid": frm.doc.received_or_paid,
				"party": frm.doc.party,
				"party_account": frm.doc.party_account
			}
		},
		callback: function(r, rt) {
			if(r.message) {
				frm.fields_dict.get_outstanding_vouchers.$input.removeClass("btn-primary");
				frm.fields_dict.make_journal_entry.$input.addClass("btn-primary");

				frm.clear_table("vouchers");

				$.each(r.message, function(i, d) {
					var c = frm.add_child("vouchers");
					c.against_voucher_type = d.voucher_type;
					c.against_voucher_no = d.voucher_no;
					c.total_amount = d.invoice_amount;
					c.outstanding_amount = d.outstanding_amount;

					if (frm.doc.set_payment_amount) {
						c.payment_amount = d.outstanding_amount;
					}
				});
			}
			refresh_field("vouchers");
			frm.layout.refresh_sections();
			erpnext.payment_tool.set_total_payment_amount(frm);
		}
	});
});

// validate against_voucher_type
frappe.ui.form.on("Payment Tool Detail", "against_voucher_type", function(frm, cdt, cdn) {
	var row = frappe.model.get_doc(cdt, cdn);
	erpnext.payment_tool.validate_against_voucher(frm, row);
});

erpnext.payment_tool.validate_against_voucher = function(frm, row) {
	var _validate = function(i, row) {
		if (!row.against_voucher_type) {
			return;
		}

		if(frm.doc.party_type=="Customer"
			&& !in_list(["Sales Order", "Sales Invoice", "Journal Entry"], row.against_voucher_type)) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", "");
				frappe.msgprint(__("Against Voucher Type must be one of Sales Order, Sales Invoice or Journal Entry"));
				return false;
			}

		if(frm.doc.party_type=="Supplier"
			&& !in_list(["Purchase Order", "Purchase Invoice", "Journal Entry"], row.against_voucher_type)) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", "");
				frappe.msgprint(__("Against Voucher Type must be one of Purchase Order, Purchase Invoice or Journal Entry"));
				return false;
			}

	}

	if (row) {
		_validate(0, row);
	} else {
		$.each(frm.doc.vouchers || [], _validate);
	}

}

// validate against_voucher_type
frappe.ui.form.on("Payment Tool Detail", "against_voucher_no", function(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	if (!row.against_voucher_no) {
		return;
	}

	frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_against_voucher_amount',
		args: {
			"against_voucher_type": row.against_voucher_type,
			"against_voucher_no": row.against_voucher_no,
			"party_account": frm.doc.party_account,
			"company": frm.doc.company
		},
		callback: function(r) {
			if(!r.exc) {
				$.each(r.message, function(k, v) {
					frappe.model.set_value(cdt, cdn, k, v);
				});

				frappe.model.set_value(cdt, cdn, "payment_amount", r.message.outstanding_amount);
			}
		}
	});
});

// Set total payment amount
frappe.ui.form.on("Payment Tool Detail", "payment_amount", function(frm) {
	erpnext.payment_tool.set_total_payment_amount(frm);
});

frappe.ui.form.on("Payment Tool Detail", "vouchers_remove", function(frm) {
	erpnext.payment_tool.set_total_payment_amount(frm);
});

erpnext.payment_tool.set_total_payment_amount = function(frm) {
	var total_amount = 0.00;
	$.each(frm.doc.vouchers || [], function(i, row) {
		if (row.payment_amount && (row.payment_amount <= row.outstanding_amount)) {
			total_amount = total_amount + row.payment_amount;
		} else {
			if(row.payment_amount < 0)
				msgprint(__("Row {0}: Payment amount can not be negative", [row.idx]));
			else if(row.payment_amount > row.outstanding_amount)
				msgprint(__("Row {0}: Payment Amount cannot be greater than Outstanding Amount", [__(row.idx)]));

			frappe.model.set_value(row.doctype, row.name, "payment_amount", 0.0);
		}
	});
	frm.set_value("total_payment_amount", total_amount);
}


// Make Journal Entry
frappe.ui.form.on("Payment Tool", "make_journal_entry", function(frm) {
	erpnext.payment_tool.check_mandatory_to_fetch(frm.doc);

	return  frappe.call({
		method: 'make_journal_entry',
		doc: frm.doc,
		callback: function(r) {
			frm.fields_dict.make_journal_entry.$input.addClass("btn-primary");
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});
});

erpnext.payment_tool.check_mandatory_to_fetch = function(doc) {
	$.each(["Company", "Party Type", "Party", "Received or Paid"], function(i, field) {
		if(!doc[frappe.model.scrub(field)]) frappe.throw(__("Please select {0} first", [field]));
	});
}
