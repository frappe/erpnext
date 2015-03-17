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
				"group_or_ledger": "Ledger",
				"company": frm.doc.company
			}
		}
	});

	frm.set_query("against_voucher_type", "vouchers", function() {
		return {
			filters: {"name": ["in", ["Sales Invoice", "Purchase Invoice", "Journal Entry", "Sales Order", "Purchase Order"]]}
		};
	});
});

frappe.ui.form.on("Payment Tool", "refresh", function(frm) {
	frappe.ui.form.trigger("Payment Tool", "party_type");
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

frappe.ui.form.on("Payment Tool", "company", function(frm) {
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

frappe.ui.form.on("Payment Tool", "received_or_paid", function(frm) {
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

frappe.ui.form.on("Payment Tool", "party", function(frm) {
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
				frm.doc.set_value("payment_account", r.message['bank_cash_account']
);
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
				});
			}
			refresh_field("vouchers");
			frm.layout.refresh_sections();
			erpnext.payment_tool.set_total_payment_amount(frm);
		}
	});
});

// validate against_voucher_type
frappe.ui.form.on("Payment Tool Detail", "against_voucher_type", function(frm) {
	erpnext.payment_tool.validate_against_voucher(frm);
});

erpnext.payment_tool.validate_against_voucher = function(frm) {
	$.each(frm.doc.vouchers || [], function(i, row) {
		if(frm.doc.party_type=="Customer"
			&& !in_list(["Sales Order", "Sales Invoice", "Journal Entry"], row.against_voucher_type)) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", "");
				frappe.throw(__("Against Voucher Type must be one of Sales Order, Sales Invoice or Journal Entry"))
			}

		if(frm.doc.party_type=="Supplier"
			&& !in_list(["Purchase Order", "Purchase Invoice", "Journal Entry"], row.against_voucher_type)) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", "");
				frappe.throw(__("Against Voucher Type must be one of Purchase Order, Purchase Invoice or Journal Entry"))
			}

	});
}

// validate against_voucher_type
frappe.ui.form.on("Payment Tool Detail", "against_voucher_no", function(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_against_voucher_amount',
		args: {
			"against_voucher_type": row.against_voucher_type,
			"against_voucher_no": row.against_voucher_no
		},
		callback: function(r) {
			if(!r.exc) {
				$.each(r.message, function(k, v) {
					frappe.model.set_value(cdt, cdn, k, v);
				});
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
			else if(row.payment_amount >= row.outstanding_amount)
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
