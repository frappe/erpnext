// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.share_transfer");

frappe.ui.form.on('Share Transfer', {
	refresh: function(frm) {
		// Don't show Parties which are a Company
		let shareholders = ['from_shareholder', 'to_shareholder'];
		// if (frm.doc.company) {
		// 	let currency = await frappe.db.get_value("Company", frm.doc.company, "default_currency");
		// 	console.log("currency",currency);
		// }
		shareholders.forEach((shareholder) => {
			frm.fields_dict[shareholder].get_query = function() {
				return {
					filters: [
						["Shareholder", "is_company", "=", 0]
					]
				};
			};
		});
		frm.set_query("equity_or_liability_account", function() {
			return {
				filters: {
					"is_group":0,
					"root_type": ["in",["Equity","Liability"]],
					"company": frm.doc.company,
					// "account_currency": currency.message.default_currency
				}	
			};
		});
		frm.set_query("asset_account", function() {
			
			return {
				filters: {
					"is_group":0,
					"root_type":"Asset",
					"company": frm.doc.company,
					// "account_currency": currency.message.default_currency
				}
			};
		});
		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Make Journal Entry'), function () {
				erpnext.share_transfer.make_jv(frm);
			})
		}	
	},
	no_of_shares: (frm) => {
		if (frm.doc.rate != undefined || frm.doc.rate != null){
			erpnext.share_transfer.update_amount(frm);
		}
	},
	rate: (frm) => {
		if (frm.doc.no_of_shares != undefined || frm.doc.no_of_shares != null){
			erpnext.share_transfer.update_amount(frm);
		}
	},

	
});

erpnext.share_transfer.update_amount = function(frm) {
	frm.doc.amount = frm.doc.no_of_shares * frm.doc.rate;
	frm.refresh_field("amount");
};

erpnext.share_transfer.make_jv = function (frm) {
	if (frm.doc.transfer_type == "Transfer") {
		var account = frm.doc.equity_or_liability_account;
		var payment_account = frm.doc.equity_or_liability_account;
	}
	else 
	{
		var account =(frm.doc.transfer_type == "Issue") ? frm.doc.asset_account : frm.doc.equity_or_liability_account;
		var payment_account = (frm.doc.transfer_type == "Issue") ? frm.doc.equity_or_liability_account : frm.doc.asset_account;
	}
	frappe.call({
		args: {
			"company": frm.doc.company,
			"account": account,
			"amount": frm.doc.amount,
			"payment_account": payment_account
		},
		method: "erpnext.hr.doctype.employee_loan.employee_loan.make_jv_entry",
		callback: function (r) {
			if (r.message) {
				r.message.voucher_type = "Journal Entry";
				r.message.user_remark = "";
			}	
			var doc = frappe.model.sync(r.message)[0];
			frappe.set_route("Form", doc.doctype, doc.name);
		}
	})
}
