// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POL Expense', {
	onload: (frm)=>{
		set_party_type(frm);
		frm.set_query("party", function() {
			return {
				"filters": {
					"is_pol_supplier": 1
				}
			};
		});

		frm.set_query("select_cheque_lot", function(){
			return 	{
				"filters":[
					["status", "!=", "Used"],
					["docstatus", "=", "1"],
				]
			}
		});
		// frm.set_value("from_date",frappe.datetime.month_start())
		// frm.set_value("to_date",frappe.datetime.month_end())
		// frm.refresh_field("from_date")
		// frm.refresh_field("to_date")
	},
	equipment:function(frm){
		frm.events.get_previous(frm)
	},
	refresh: function(frm){
		enable_disable(frm);
	},
	paty_type: (frm)=>{
		set_party_type(frm);
	},
	refresh: (frm)=>{
		open_ledger(frm);
	},
	amount:(frm)=>{
		calculate_balance(frm);
	},
	use_cheque_lot: function(frm){
		enable_disable(frm);
	},

	select_cheque_lot: function (frm) {
		if (frm.doc.select_cheque_lot) {
			frappe.call({
				method: "erpnext.accounts.doctype.cheque_lot.cheque_lot.get_cheque_no_and_date",
				args: {
					'name': frm.doc.select_cheque_lot
				},
				callback: function (r) {
					if (r.message) {
						cur_frm.set_value("cheque_no", r.message[0].reference_no);
						cur_frm.set_value("cheque_date", r.message[1].reference_date);
					}
				}
			});
		}
	},
	get_previous:function(frm){
		frappe.call({
			method:"pull_previous_expense",
			doc:frm.doc,
			callback:function(r){
				frm.refresh_field("items")
				frm.refresh_field("previous_balance_amount")
				frm.refresh_field("amount")
				frm.refresh_field("previous_km_reading")
				frm.refresh_field("present_km_reading")
				frm.dirty()
			}
		})
	},
	from_date:function(frm){
		frm.events.get_pol_received(frm)
	},
	to_date:function(frm){
		frm.events.get_pol_received(frm)
	},
	get_pol_received:function(frm){
		if (cint(frm.doc.is_opening) == 1) return
		if (frm.doc.from_date > frm.doc.to_date) frappe.throw("From Date cannot be greater than To Date")
		if (frm.doc.from_date && frm.doc.to_date){
			frappe.call({
				method:"get_pol_received",
				doc:frm.doc,
				callback:function(r){
					frm.refresh_field("pol_received_item")
					frm.refresh_field("total_qty_received")
					frm.refresh_field("total_bill_amount")
					frm.refresh_field("pol_issue_during_the_period")
					frm.dirty()
				}
			})
		}
	},
	cheque_no: function(frm){
		enable_disable(frm);
	},

	cheque_date: function(frm){
		enable_disable(frm);
	},
	"opening_pol_tank_balance": function(frm){
		calculate_pol(frm)
	},
	"pol_issue_during_the_period": function(frm){
		calculate_pol(frm)
	},
	"closing_pol_tank_balance": function(frm){
		calculate_pol(frm)
	},
	"total_petrol_diesel_consumed": function(frm){
		calculate_pol(frm)
	},
	"previous_km_reading": function(frm){
		calculate_pol(frm)
	},
	"present_km_reading": function(frm){
		calculate_pol(frm)
	},
	"total_km_reading": function(frm){
		calculate_pol(frm)
	},
	"average_km_reading": function(frm){
		calculate_pol(frm)
	},
	"uom":function(frm){
		calculate_pol(frm)
	}
});
function enable_disable(frm) {
	if(frm.doc.use_cheque_lot){
		frm.toggle_reqd(['cheque_no','cheque_date'], frm.doc.use_cheque_lot);
	} else {
		frm.toggle_reqd(['cheque_date'], frm.doc.cheque_no);
		frm.toggle_reqd(['cheque_no'], frm.doc.cheque_date);
	}
}

var calculate_balance=(frm)=>{
	if (frm.doc.amount > 0 ){
		cur_frm.set_value("balance_amount",frm.doc.amount)
		cur_frm.set_value("adjusted_amount",0)
	}
}
var open_ledger = (frm)=>{
	if (frm.doc.docstatus === 1) {
		frm.add_custom_button(
		  __("Journal Entry"),
		  function () {
			frappe.route_options = {
			  voucher_no: frm.doc.name,
			  from_date: frm.doc.entry_date,
			  to_date: frm.doc.entry_date,
			  company: frm.doc.company,
			  group_by_voucher: false,
			};
			frappe.set_route("query-report", "General Ledger");
		  },
		  __("View")
		);
	}
}
var open_ledger = (frm)=>{
	if (frm.doc.docstatus === 1) {
		frm.add_custom_button(
		  __("Journal Entry"),
		  function () {
			frappe.route_options = {
			  name: frm.doc.journal_entry,
			  from_date: frm.doc.entry_date,
			  to_date: frm.doc.entry_date,
			  company: frm.doc.company,
			};
			frappe.set_route("List", "Journal Entry");
		  },
		  __("View")
		);
	}
 }
var set_party_type = (frm)=>{
	cur_frm.set_query('paty_type', (frm)=> {
		return {
			'filters': {
				'name': 'Supplier'
			}
		};
	});
}

function calculate_pol(frm){
	if (frm.doc.opening_pol_tank_balance && frm.doc.pol_issue_during_the_period && frm.doc.closing_pol_tank_balance){
		frm.set_value("total_petrol_diesel_consumed", flt(frm.doc.opening_pol_tank_balance) + flt(frm.doc.pol_issue_during_the_period) - flt(frm.doc.closing_pol_tank_balance));
		frm.refresh_field("total_petrol_diesel_consumed")
	}
	if (frm.doc.previous_km_reading && frm.doc.present_km_reading){
		frm.set_value("total_km_reading", parseFloat(frm.doc.present_km_reading) - parseFloat(frm.doc.previous_km_reading));
		frm.refresh_field("total_km_reading")
	}
	if (cur_frm.doc.total_km_reading && cur_frm.doc.total_petrol_diesel_consumed){
		if( frm.doc.uom == "KM")
			cur_frm.set_value('average_km_reading', flt(cur_frm.doc.total_km_reading) / flt(cur_frm.doc.total_petrol_diesel_consumed))
		else 
			cur_frm.set_value('average_km_reading', flt(cur_frm.doc.total_petrol_diesel_consumed) / flt(cur_frm.doc.total_km_reading))
		frm.refresh_field('average_km_reading')
	}
}
