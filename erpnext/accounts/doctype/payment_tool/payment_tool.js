// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.payment_tool");

frappe.ui.form.on("Payment Tool", "onload", function(frm) {
	var help_content = '<i class="icon-hand-right"></i> Note:<br>'+
		'<ul>If payment is not made against any reference, make Journal Voucher manually.</ul>';
	frm.set_value("make_jv_help", help_content);
});

frappe.ui.form.on("Payment Tool", "get_outstanding_vouchers", function(frm) {
	return  frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_outstanding_vouchers',
		args: {
			args: {
				"company": frm.doc.company,
				"party_type": frm.doc.party_type,
				"received_or_paid": frm.doc.received_or_paid,
				"customer": frm.doc.customer,
				"supplier": frm.doc.supplier,
				"account_name": frm.doc.account_name
			}
		},
		callback: function(r, rt) {
			frm.set_value("payment_tool_voucher_details", []);
			$.each(r.message, function(i, d) {
				var invoice_detail = frappe.model.add_child(frm.doc, "Payment Tool Voucher Detail", "payment_tool_voucher_details");
				invoice_detail.against_voucher_type = d.voucher_type;
				invoice_detail.against_voucher_no = d.voucher_no;
				invoice_detail.total_amount = d.invoice_amount;
				invoice_detail.outstanding_amount = d.outstanding_amount;
			});

			refresh_field("payment_tool_voucher_details");
		}
	});
});

frappe.ui.form.on("Payment Tool", "make_journal_voucher", function(frm) {
	erpnext.payment_tool.set_new_jv(frm);
});

frappe.ui.form.on("Payment Tool", "customer", function(frm) {
	erpnext.payment_tool.set_account_name(frm);
});

frappe.ui.form.on("Payment Tool", "supplier", function(frm) {
	erpnext.payment_tool.set_account_name(frm);
});

frappe.ui.form.on("Payment Tool Voucher Detail", "payment_amount", function(frm) {
	erpnext.payment_tool.set_total_payment_amount(frm);
});

frappe.ui.form.on("Payment Tool Voucher Detail", "payment_tool_voucher_details_remove", function(frm) {
	var total_amount = frappe.model.get_value("Payment Tool", frm.doc, "total_payment_amount");
	erpnext.payment_tool.set_total_payment_amount(frm);
});

erpnext.payment_tool.set_new_jv = function(frm) {
	var total_payment_amount = 0.00;
	var jv = frappe.model.make_new_doc_and_get_name('Journal Voucher');
	var invoice_voucher_type = {"Sales Invoice": "against_invoice",
							"Purchase Invoice": "against_voucher",
							"Journal Voucher": "against_jv",
							"Sales Order": "against_sales_order",
							"Purchase Order": "against_purchase_order"
							};

	jv = locals['Journal Voucher'][jv];
	jv.company = frm.doc.company;
	jv.voucher_type = 'Journal Entry';
	jv.cheque_no = frm.doc.reference_no;
	jv.cheque_date = frm.doc.reference_date;

	$.each(frm.doc.payment_tool_voucher_details || [], function(i, row) {
		var d1 = frappe.model.add_child(jv, 'Journal Voucher Detail', 'entries');
		d1.account = frm.doc.account_name;
		
		if (frm.doc.received_or_paid == "Paid") {
		d1.debit = flt(row.payment_amount);
		} else if (frm.doc.received_or_paid == "Received") {
		d1.credit = flt(row.payment_amount);	
		}

		if (row.against_voucher_type == "Sales Order" || row.against_voucher_type == "Purchase Order") {
			d1.is_advance = "Yes";
		} else {
			d1.is_advance = "No";
		}

		d1[invoice_voucher_type[row.against_voucher_type]] = row.against_voucher_no;

		total_payment_amount = flt(total_payment_amount) + flt(d1.debit) - flt(d1.credit);
	});		

	console.log(total_payment_amount);

	var d2 = frappe.model.add_child(jv, 'Journal Voucher Detail', 'entries');
	d2.account = frm.doc.payment_account;
	if (total_payment_amount < 0.00) {
		d2.debit = Math.abs(total_payment_amount);
	} else {
		d2.credit = Math.abs(total_payment_amount);
	}

	loaddoc('Journal Voucher', jv.name);
}

erpnext.payment_tool.set_account_name = function(frm) {
	if(frm.doc.party_type == "Customer") {
		var party_name = frm.doc.customer;
	} else {
		var party_name = frm.doc.supplier;
	}
	return  frappe.call({
		method: 'erpnext.accounts.doctype.payment_tool.payment_tool.get_account_name',
		args: {
			party_type: frm.doc.party_type,
			party_name: party_name
		},
		callback: function(r, rt) {
			if(!r.exc) {
				frm.set_value("account_name", r.message);
			}
		}
	});
}

erpnext.payment_tool.set_total_payment_amount = function(frm) {
	var total_amount = 0.00;
	$.each(frm.doc.payment_tool_voucher_details || [], function(i, row) {
			if (row.payment_amount >= row.outstanding_amount) {
				frappe.throw(__("Row {0}: Payment Amount cannot be greater than Outstanding Amount", [__(row.idx)]));
			} else if (row.payment_amount && (row.payment_amount <= row.outstanding_amount)) {
				total_amount = total_amount + row.payment_amount;
			}
	});
	frm.set_value("total_payment_amount", total_amount);
}

