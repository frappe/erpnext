// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload_post_render = function(doc) {
	$(cur_frm.get_field("reconcile").input).addClass("btn-info");
}

cur_frm.fields_dict.voucher_no.get_query = function(doc) {
	// TO-do: check for pos, it should not come
	if (!doc.account) msgprint(__("Please select Account first"));
	else {
		return {
			doctype: doc.voucher_type,
			query: "erpnext.accounts.doctype.payment_to_invoice_matching_tool.payment_to_invoice_matching_tool.get_voucher_nos",
			filters: {
				"voucher_type": doc.voucher_type,
				"account": doc.account
			}
		}
	}
}

cur_frm.cscript.voucher_no  = function() {
	return cur_frm.call({
		doc: cur_frm.doc,
		method: "get_voucher_details"
	});
}

cur_frm.cscript.get_against_entries  = function() {
	return cur_frm.call({
		doc: cur_frm.doc,
		method: "get_against_entries"
	});
}

cur_frm.cscript.reconcile  = function() {
	return cur_frm.call({
		doc: cur_frm.doc,
		method: "reconcile"
	});
}

cur_frm.cscript.allocated_amount = function(doc, cdt, cdn) {
	var total_allocated_amount = 0
	$.each(cur_frm.doc.against_entries, function(i, d) {
		if(d.allocated_amount > 0) total_allocated_amount += flt(d.allocated_amount);
		else if (d.allocated_amount < 0) frappe.throw(__("Allocated amount can not be negative"));
	})
	cur_frm.set_value("total_allocated_amount", total_allocated_amount);
}
