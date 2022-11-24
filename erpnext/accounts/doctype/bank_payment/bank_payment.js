// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// cur_frm.add_fetch("branch", "expense_bank_account", "paid_from");	
cur_frm.add_fetch("paid_from", "bank_name", "bank_name");	
cur_frm.add_fetch("paid_from", "bank_branch", "bank_branch");	
cur_frm.add_fetch("paid_from", "bank_account_type", "bank_account_type");	
cur_frm.add_fetch("paid_from", "bank_account_no", "bank_account_no");	
frappe.ui.form.on('Bank Payment', {
	setup: function(frm){
		var status = {"Draft": "tomato",
                        "Pending": "orange",
                        "In progress": "blue",
                        "Waiting Acknowledgement": "blue",
						"Processing Acknowledgement": "yellow",
                        "Upload Failed": "red",
                        "Failed": "red",
                        "Completed": "green",
                        "Cancelled": "black"
                        };
		frm.set_indicator_formatter('status',
			function(doc) {
				return status[doc.status];
		});

		frm.set_indicator_formatter('transaction_id',
			function(doc) {
				return status[doc.status];
		});

		frm.set_indicator_formatter('file_name',
			function(doc) {
				return status[doc.status];
		});
	},
	onload: function(frm){
		enable_disable(frm);
		create_custom_buttons(frm);
		
		frm.set_query("paid_from", function() {
			return {
				query: "erpnext.accounts.doctype.bank_payment.bank_payment.get_paid_from",
				filters: {
					branch: frm.doc.branch
				}
			};
		});

		cur_frm.set_query("region", function() {
			return {
				"filters": {
					"is_disabled": 0,
					"is_region": 1
				}
			};
		});
	},
	refresh: function(frm) {
		enable_disable(frm);
		create_custom_buttons(frm);
	},
	onload_post_render: function(frm) {
		if(frm.doc.docstatus == 0){
			frm.get_field("get_transactions").$input.addClass("btn-info");
			frm.get_field("get_transactions").$input.css("padding", "5px 10px");
		}
	},
	branch: function(frm){
		//cur_frm.add_fetch("branch", "expense_bank_account", "paid_from");	
		cur_frm.set_value("paid_from", null);
		cur_frm.set_value("bank_name", null);
		cur_frm.set_value("bank_branch", null);
		cur_frm.set_value("bank_account_no", null);
		cur_frm.set_value("bank_balance", null);
	},
	transaction_type: function(frm){
		enable_disable(frm);
		reset_entries(frm);
	},
	transaction_no: function(frm){
		reset_entries(frm);
	},
	from_date: function(frm){
		reset_entries(frm);
	},
	to_date: function(frm){
		reset_entries(frm);
	},
	region: function(frm){
		reset_entries(frm);
	},
	employee: function(frm){
		reset_entries(frm);
	},
	department: function(frm){
		reset_entries(frm);
	},
	division: function(frm){
		reset_entries(frm);
	},
	paid_from: function(frm){
		// cur_frm.clear_table("items");
		if (!frm.doc.paid_from){
			cur_frm.set_value("bank_name", null);
			cur_frm.set_value("bank_branch", null);
			cur_frm.set_value("bank_account_no", null);
			cur_frm.set_value("bank_balance", null);
		}
		cur_frm.refresh();
	},
	fiscal_year: function(frm){
		reset_entries(frm);
	},
	month: function(frm){
		reset_entries(frm);
	},
	items_on_form_rendered:function(frm, grid_row, cdt, cdn){
   	},
	get_transactions: function(frm){
		get_entries(frm);
	},
	bank_account_no: function(frm){
		fetch_bank_balance(frm);
	},
});

frappe.ui.form.on('Bank Payment Item', {
	bank_name: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		frm.toggle_display(['inr_bank_code', 'inr_purpose_code'], (row.bank_name === 'INR'));
		frm.toggle_reqd(['inr_bank_code', 'inr_purpose_code'], (row.bank_name === 'INR'));
		frm.refresh_fields(['inr_bank_code', 'inr_purpose_code']);
	},
});

var fetch_bank_balance = function(frm){
	if(frm.doc.bank_account_no){
		frappe.call({
			method: "erpnext.integrations.bank_api.fetch_balance",
			args: {
				account_no: frm.doc.bank_account_no,
			},
			callback: function(r) {
				if(r.message) {
					console.log(r.message);
					if(r.message.status == "0")
						frm.set_value("bank_balance", r.message.balance_amount);
					else	
						frappe.throw("Unable to fetch Bank Balance");
				}
			}
		});
	}
}

var create_custom_buttons = function(frm){
	if(!frm.is_new() && !frm.is_dirty()){
		if(frm.doc.docstatus == 1){
			if(frm.doc.status == "Pending"){
				frm.page.set_primary_action(__('Process Payment'), () => {
					process_payment(frm);
				});
			} else if(frm.doc.status == "Upload Failed"){
				frm.page.set_primary_action(__('Re-upload Files'), () => {
					reupload_files(frm);
				});
			}
		}
	}
}

var enable_disable = function(frm){
	var permitted_doctypes = ['Bonus', 'Employee Loan Payment', 'LTC', 'PBVA', 'Salary'];
	frm.toggle_display(['fiscal_year', 'region', 'employee', 'department', 'division'], permitted_doctypes.includes(frm.doc.transaction_type));
	frm.toggle_display(['month'], ['Employee Loan Payment', 'Salary'].includes(frm.doc.transaction_type));
	frm.toggle_display(['transaction_no', 'from_date', 'to_date'], !permitted_doctypes.includes(frm.doc.transaction_type) && frm.doc.transaction_type);
	frm.toggle_display(['from_date', 'to_date'], !permitted_doctypes.includes(frm.doc.transaction_type) && frm.doc.transaction_type && !frm.doc.transaction_no);

	frm.toggle_reqd(['fiscal_year'], permitted_doctypes.includes(frm.doc.transaction_type));
	frm.toggle_reqd(['month'], ['Employee Loan Payment', 'Salary'].includes(frm.doc.transaction_type));
	frm.toggle_reqd(['from_date', 'to_date'], !permitted_doctypes.includes(frm.doc.transaction_type) && frm.doc.transaction_type && !frm.doc.transaction_no);
}

var process_payment = function(frm){
	frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Bank Payment Settings",
            name: "BOBL",
        },
        callback(r) {
            if(r.message) {
                var from_time = r.message.from_time;
				var to_time = r.message.to_time;
				var currentdate = new Date();
				var currenttime = currentdate.getHours() + ":" + currentdate.getMinutes() + ":" + currentdate.getSeconds();
                if(currenttime < from_time && currenttime > to_time){
					frappe.throw("BOBL Bank Payment Transaction is allowed from " + from_time + " to " + to_time)
				}
				frappe.call({
					method: "process_payment",
					doc: frm.doc,
					callback: function(r){
						cur_frm.reload_doc();
					},
					freeze: true,
					freeze_message: "Processing payment.... Please Wait",
				})
            }
        }
    });
	

}

var reupload_files = function(frm){
	frappe.call({
		method: "reupload_files",
		doc: frm.doc,
		callback: function(r){
			cur_frm.refresh();
		},
		freeze: true,
		freeze_message: "Re-uploading the files.... Please Wait",
	})
}

function reset_entries(frm){
	cur_frm.clear_table("items");
	cur_frm.clear_table("banks");
	cur_frm.clear_table("debit_notes");
	cur_frm.clear_table("uploads");
	cur_frm.refresh_fields("items");
	cur_frm.refresh_fields("banks");
	cur_frm.refresh_fields("debit_notes");
	cur_frm.refresh_fields("uploads");

	cur_frm.set_value('total_amount', 0);
	cur_frm.refresh_field("total_amount");
}

function get_entries(frm){
	cur_frm.set_value('total_amount', 0);
	cur_frm.clear_table("items");
	cur_frm.clear_table("banks");
	cur_frm.clear_table("debit_notes");
	if (frm.doc.transaction_type){
		frappe.call({
			method: "get_entries",
			doc: cur_frm.doc,
			callback: function(r){
				if(r.message){
					cur_frm.set_value('total_amount', r.message);
				}
				cur_frm.refresh_fields();
			},
			freeze: true,
            freeze_message: "Fetching Transaction Details.... Please Wait",
		});
	}
	cur_frm.refresh_fields();
}