// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("branch","cost_center","cost_center");
cur_frm.add_fetch("utility_services","expense_account","expense_account");
cur_frm.add_fetch("utility_services","bank_account","bank_account");
cur_frm.add_fetch("utility_service_type","party","party");
cur_frm.add_fetch("utility_service_type","expense_account","debit_account");
frappe.ui.form.on('Utility Bill', {
	onload: function(frm){
		if(frm.doc.workflow_state != "Draft" && !cur_frm.doc.__islocal){
			cur_frm.set_df_property("item", "disabled", 1);
			cur_frm.set_df_property("utility_services", "read_only", 1);
			cur_frm.set_df_property("posting_date", "read_only", 1);
			cur_frm.set_df_property("branch", "read_only", 1);
			cur_frm.set_df_property("tds_percent", "read_only", 1);
			cur_frm.set_df_property("get_details", "disabled", 1);
		}
		frappe.model.get_value('Bank Payment Settings', {'name': 'BOBL'}, 'enable_one_to_one',
			function(d) {
				if(d.enable_one_to_one == 0){
					cur_frm.set_df_property("bank_balance", "hidden", 1);
				}
			});
	},
	refresh: function(frm) {
		cur_frm.set_query("utility_services", function() {
			return {
				"filters": {
					"branch": frm.doc.branch
				}
			}
		 });
		 if(!frm.doc.direct_payment && frm.doc.docstatus === 1 && (frm.doc.payment_status === "Payment Successful" || frm.doc.payment_status === "Partial Payment")){
			frm.add_custom_button("Create Direct Payment", function() {
				frappe.call({
					"method": "make_direct_payment",
					"doc": cur_frm.doc,
					callback: function(r, rt) {
						if(r.message){
							frm.refresh_fields();
							frappe.set_route("Form", "Direct Payment", r.message);
						}
					}
				});
			}).addClass("btn-primary");
		 }
	},
	"tds_percent": function(frm) {
		calculate_tds(frm);
	},
	"branch": function(frm) {
		cur_frm.set_value("utility_services","");
	},
	"utility_services": function(frm){
		if(frm.doc.utility_services)
			get_utility_services(frm);
	},
	"get_details": function(frm){
		if(frm.doc.utility_services)
			get_utility_outstandings(frm);
	}
});

function get_utility_outstandings(frm){
	return frappe.call({
		method: "get_utility_outstandings",
		doc: cur_frm.doc,
		callback: function(r, rt) {
			frm.refresh_field("item");
			frm.refresh_fields();
		},
		freeze: true,
		freeze_message: "Fetching Utility Outstanding Amount..... Please Wait"
	});     
}

function get_utility_services(frm){
	if (frm.doc.utility_services && frm.doc.branch){
		return frappe.call({
			method: "get_utility_services",
			doc: cur_frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("item");
				frm.refresh_fields();
			},
			freeze: true,
			freeze_message: "Fetching Utility Outstanding Amount..... Please Wait"
		});     
	}else{
		frappe.msgprint("To fetch Utility Outstanding Amount, provide Branch and Utility Services ID");
	}
}

function calculate_tds(frm) {
	frappe.call({
		method: "erpnext.accounts.doctype.direct_payment.direct_payment.get_tds_account",
		args: {
			percent: frm.doc.tds_percent,
			payment_type: "Payment"
		},
		callback: function(r) {
			if(r.message) {
				frm.set_value("tds_account", r.message);
				cur_frm.refresh_field("tds_account");
			}
		}
	})
}

frappe.ui.form.on('Utility Bill Item', {
	invoice_amount: function(frm, cdt, cdn) {
		calculate_net_amount(frm, cdt, cdn);
	},
	tds_applicable: function(frm, cdt, cdn) {
		calculate_net_amount(frm, cdt, cdn);
	},
});

function calculate_net_amount(frm,cdt,cdn){
	var item = frappe.get_doc(cdt,cdn);
	var net_amount=0.00; var tds_amount=0.00; var total_inv_amount=0.00; var total_tds_amount=0.00; var total_net_amount = 0.00;
	if(item.invoice_amount > 0){
		if(frm.doc.tds_percent >0 && item.tds_applicable){
			tds_amount = parseFloat(item.invoice_amount) * parseFloat(frm.doc.tds_percent/100);
		}else{
			frappe.model.set_value(cdt, cdn, "tds_amount", 0.00);
		}

		net_amount = parseFloat(item.invoice_amount) - parseFloat(tds_amount);
		
		frappe.model.set_value(cdt, cdn, "net_amount", net_amount);
		frappe.model.set_value(cdt, cdn, "tds_amount", tds_amount);
	}
	frm.doc.item.forEach(function(d){
		total_inv_amount += parseFloat(d.invoice_amount);
		total_net_amount += parseFloat(d.net_amount);
		total_tds_amount += parseFloat(d.tds_amount);
	});
	frm.set_value("total_bill_amount", total_inv_amount);
	frm.set_value("total_tds_amount", total_tds_amount);
	frm.set_value("net_payable_amount", total_net_amount);
}