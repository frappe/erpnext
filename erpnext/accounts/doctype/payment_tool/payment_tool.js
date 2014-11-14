// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.payment_tool");

// Help content
frappe.ui.form.on("Payment Tool", "onload", function(frm) {
	frm.set_value("make_jv_help", '<i class="icon-hand-right"></i> '
		+ __("Note: If payment is not made against any reference, make Journal Voucher manually."));

	frm.set_query("payment_account", function() {
		return {
			filters: [
				['Account', 'account_type', 'in', 'Bank, Cash'],
				['Account', 'group_or_ledger', '=', 'Ledger'],
				['Account', 'company', '=', frm.doc.company]
			]
		}
	});

	frm.set_query("against_voucher_type", "payment_tool_details", function() {
		return {
			filters: {"name": ["in", ["Sales Invoice", "Purchase Invoice", "Journal Voucher", "Sales Order", "Purchase Order"]]}
		};
	});
});

frappe.ui.form.on("Payment Tool", "refresh", function(frm) {
	frappe.ui.form.trigger("Payment Tool", "party_type");
});

frappe.ui.form.on("Payment Tool", "party_type", function(frm) {
	frm.toggle_reqd("customer", frm.doc.party_type == "Customer");
	frm.toggle_reqd("supplier", frm.doc.party_type == "Supplier");
});

frappe.ui.form.on("Payment Tool", "company", function(frm) {
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

frappe.ui.form.on("Payment Tool", "received_or_paid", function(frm) {
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

// Set party account name
frappe.ui.form.on("Payment Tool", "customer", function(frm) {
	erpnext.payment_tool.set_party_account(frm);
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

frappe.ui.form.on("Payment Tool", "supplier", function(frm) {
	erpnext.payment_tool.set_party_account(frm);
	erpnext.payment_tool.check_mandatory_to_set_button(frm);
});

erpnext.payment_tool.check_mandatory_to_set_button = function(frm) {
	if (frm.doc.company && frm.doc.party_type && frm.doc.received_or_paid && (frm.doc.customer || frm.doc.supplier)) {
		frm.fields_dict.get_outstanding_vouchers.$input.addClass("btn-primary");
	}
}

//Set Button color
erpnext.payment_tool.set_party_account = function(frm) {
	if(frm.doc.party_type == "Customer") {
		var party_name = frm.doc.customer;
	} else {
		var party_name = frm.doc.supplier;
	}
	return  frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_party_account',
		args: {
			party_type: frm.doc.party_type,
			party_name: party_name
		},
		callback: function(r, rt) {
			if(!r.exc) {
				frm.set_value("party_account", r.message);
			}
		}
	});
}

// Get outstanding vouchers
frappe.ui.form.on("Payment Tool", "get_outstanding_vouchers", function(frm) {
	erpnext.payment_tool.check_mandatory_to_fetch(frm.doc);

	frm.set_value("payment_tool_details", []);

	return  frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_outstanding_vouchers',
		args: {
			args: {
				"company": frm.doc.company,
				"party_type": frm.doc.party_type,
				"received_or_paid": frm.doc.received_or_paid,
				"party_name": frm.doc.party_type == "Customer" ? frm.doc.customer : frm.doc.supplier,
				"party_account": frm.doc.party_account
			}
		},
		callback: function(r, rt) {
			if(r.message) {
				frm.fields_dict.get_outstanding_vouchers.$input.removeClass("btn-primary");
				frm.fields_dict.make_journal_voucher.$input.addClass("btn-primary");

				frappe.model.clear_table(frm.doc, "payment_tool_details");
				$.each(r.message, function(i, d) {
					var invoice_detail = frappe.model.add_child(frm.doc, "Payment Tool Detail", "payment_tool_details");
					invoice_detail.against_voucher_type = d.voucher_type;
					invoice_detail.against_voucher_no = d.voucher_no;
					invoice_detail.total_amount = d.invoice_amount;
					invoice_detail.outstanding_amount = d.outstanding_amount;
				});
			}
			refresh_field("payment_tool_details");
			erpnext.payment_tool.set_total_payment_amount(frm);
		}
	});
});

// validate against_voucher_type
frappe.ui.form.on("Payment Tool Detail", "against_voucher_type", function(frm) {
	erpnext.payment_tool.validate_against_voucher(frm);
});

erpnext.payment_tool.validate_against_voucher = function(frm) {
	$.each(frm.doc.payment_tool_details || [], function(i, row) {
		if(frm.doc.party_type=="Customer"
			&& !in_list(["Sales Order", "Sales Invoice", "Journal Voucher"], row.against_voucher_type)) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", "");
				frappe.throw(__("Against Voucher Type must be one of Sales Order, Sales Invoice or Journal Voucher"))
			}

		if(frm.doc.party_type=="Supplier"
			&& !in_list(["Purchase Order", "Purchase Invoice", "Journal Voucher"], row.against_voucher_type)) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", "");
				frappe.throw(__("Against Voucher Type must be one of Purchase Order, Purchase Invoice or Journal Voucher"))
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

frappe.ui.form.on("Payment Tool Detail", "payment_tool_details_remove", function(frm) {
	erpnext.payment_tool.set_total_payment_amount(frm);
});

erpnext.payment_tool.set_total_payment_amount = function(frm) {
	var total_amount = 0.00;
	$.each(frm.doc.payment_tool_details || [], function(i, row) {
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


// Make Journal voucher
frappe.ui.form.on("Payment Tool", "make_journal_voucher", function(frm) {
	erpnext.payment_tool.check_mandatory_to_fetch(frm.doc);

	return  frappe.call({
		method: 'make_journal_voucher',
		doc: frm.doc,
		callback: function(r) {
			frm.fields_dict.make_journal_voucher.$input.addClass("btn-primary");
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});
});

erpnext.payment_tool.check_mandatory_to_fetch = function(doc) {
	var check_fields = [
		['Company', doc.company],
		['Party Type', doc.party_type],
		['Received Or Paid', doc.received_or_paid],
		['Customer / Supplier', doc.party_type == "Customer" ? doc.customer : doc.supplier]
	];

	$.each(check_fields, function(i, v) {
		if(!v[1]) frappe.throw(__("Please select {0} first", [v[0]]));
	});
}
