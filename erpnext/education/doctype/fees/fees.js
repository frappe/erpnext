// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on("Fees", {
	setup: function(frm) {
		frm.add_fetch("fee_structure", "receivable_account", "receivable_account");
		frm.add_fetch("fee_structure", "income_account", "income_account");
		frm.add_fetch("fee_structure", "cost_center", "cost_center");
	},

	onload: function(frm){
		frm.set_query("academic_term",function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
		frm.set_query("fee_structure",function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
		frm.set_query("receivable_account", function(doc) {
			return {
				filters: {
					'account_type': 'Receivable',
					'is_group': 0,
					'company': doc.company
				}
			};
		});
		frm.set_query("income_account", function(doc) {
			return {
				filters: {
					'account_type': 'Income Account',
					'is_group': 0,
					'company': doc.company
				}
			};
		});
		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.get_today();
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 0 && frm.doc.set_posting_time) {
			frm.set_df_property('posting_date', 'read_only', 0);
			frm.set_df_property('posting_time', 'read_only', 0);
		} else {
			frm.set_df_property('posting_date', 'read_only', 1);
			frm.set_df_property('posting_time', 'read_only', 1);
		}
		if(frm.doc.docstatus===1) {
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
			frm.add_custom_button(__("Payments"), function() {
				frappe.set_route("List", "Payment Entry", {"Payment Entry Reference.reference_name": frm.doc.name});
			}, __("View"));
		}
		if(frm.doc.docstatus===1 && frm.doc.outstanding_amount>0) {
			frm.add_custom_button(__("Payment Request"), function() {
				frm.events.make_payment_request(frm);
			}, __("Make"));
			frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
		if(frm.doc.docstatus===1 && frm.doc.outstanding_amount!=0) {
			frm.add_custom_button(__("Payment"), function() {
				frm.events.make_payment_entry(frm);
			}, __("Make"));
			frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
	},

	student: function(frm) {
		if (frm.doc.student) {
			frappe.call({
				method:"erpnext.education.api.get_current_enrollment",
				args: {
					"student": frm.doc.student,
					"academic_year": frm.doc.academic_year
				},
				callback: function(r) {
					if(r){
						$.each(r.message, function(i, d) {
							frm.set_value(i,d);
						});
					}
				}
			});
		}
	},

	make_payment_request: function(frm) {
		if (!frm.doc.student_email) {
			frappe.msgprint(__("Please set the Email ID for the Student to send the Payment Request"));
		} else {
			frappe.call({
				method:"erpnext.accounting.doctype.payment_request.payment_request.make_payment_request",
				args: {
					"dt": frm.doc.doctype,
					"dn": frm.doc.name,
					"recipient_id": frm.doc.student_email
				},
				callback: function(r) {
					if(!r.exc){
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", doc[0].doctype, doc[0].name);
					}
				}
			});
		}
	},

	make_payment_entry: function(frm) {
		return frappe.call({
			method: "erpnext.accounting.doctype.payment_entry.payment_entry.get_payment_entry",
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
			},
			callback: function(r) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route("Form", doc[0].doctype, doc[0].name);
			}
		});
	},

	set_posting_time: function(frm) {
		frm.refresh();
	},

	academic_term: function() {
		frappe.ui.form.trigger("Fees", "program");
	},

	fee_structure: function(frm) {
		frm.set_value("components" ,"");
		if (frm.doc.fee_structure) {
			frappe.call({
				method: "erpnext.education.api.get_fee_components",
				args: {
					"fee_structure": frm.doc.fee_structure
				},
				callback: function(r) {
					if (r.message) {
						$.each(r.message, function(i, d) {
							var row = frappe.model.add_child(frm.doc, "Fee Component", "components");
							row.fees_category = d.fees_category;
							row.amount = d.amount;
						});
					}
					refresh_field("components");
					frm.trigger("calculate_total_amount");
				}
			});
		}
	},

	calculate_total_amount: function(frm) {
		var grand_total = 0;
		for(var i=0;i<frm.doc.components.length;i++) {
			grand_total += frm.doc.components[i].amount;
		}
		frm.set_value("grand_total", grand_total);
	}
});


frappe.ui.form.on("Fee Component", {
	amount: function(frm) {
		frm.trigger("calculate_total_amount");
	}
});
