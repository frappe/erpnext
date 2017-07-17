
cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on("Fees", {
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
					"academic_term": (frm.doc.academic_term)
				}
			};
		});

		// debit account for booking the fee 
		frm.set_query("debit_to", function(doc) {
			return {
				filters: {
					'account_type': 'Receivable',
					'is_group': 0,
					'company': doc.company
				}
			}
		});

		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.get_today()		
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
		}
		if(frm.doc.docstatus===1 && frm.doc.outstanding_amount>0) {
			frm.add_custom_button(__("Payment Request"), function() {
				frm.events.make_payment_request(frm)
			}, __("Make"));
			frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
		if(frm.doc.docstatus===1 && frm.doc.outstanding_amount!=0) {
			frm.add_custom_button(__("Payment"), function() {
				frm.events.make_payment_entry(frm)
			}, __("Make"));
			frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
	},
		// if (frm.doc.docstatus === 1 && (frm.doc.total_amount > frm.doc.paid_amount)) {
		// 	frm.add_custom_button(__("Collect Fees"), function() {
		// 		frappe.prompt({fieldtype:"Float", label: __("Amount Paid"), fieldname:"amt"},
		// 			function(data) {
		// 				frappe.call({
		// 					method:"erpnext.schools.api.collect_fees",
		// 					args: {
		// 						"fees": frm.doc.name,
		// 						"amt": data.amt
		// 					},
		// 					callback: function(r) {
		// 						frm.doc.paid_amount = r.message
		// 						frm.doc.outstanding_amount = frm.doc.total_amount - r.message
		// 						frm.refresh()
		// 					}
		// 				});
		// 			}, __("Enter Paid Amount"), __("Collect"));
		// 	});
		// }

	make_payment_request: function(frm) {
		frappe.call({
			method:"erpnext.accounts.doctype.payment_request.payment_request.make_payment_request",
			args: {
				"dt": cur_frm.doc.doctype,
				"dn": cur_frm.doc.name,
				"recipient_id": cur_frm.doc.contact_email
			},
			callback: function(r) {
				if(!r.exc){
					var doc = frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			}
		})
	},

	set_posting_time: function(frm) {
		frm.refresh()
	},

	program: function(frm) {
		if (frm.doc.program && frm.doc.academic_term) {
			frappe.call({
				method: "erpnext.schools.api.get_fee_structure",
				args: {
					"program": frm.doc.program,
					"academic_term": frm.doc.academic_term
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("fee_structure" ,r.message);
					}
				}
			});
		}
	},

	academic_term: function() {
		frappe.ui.form.trigger("Fees", "program");
	},

	fee_structure: function(frm) {
		frm.set_value("components" ,"");
		if (frm.doc.fee_structure) {
			frappe.call({
				method: "erpnext.schools.api.get_fee_components",
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
