// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transporter Invoice', {
	refresh: function(frm) {
		if(frm.doc.docstatus===1){
			frm.add_custom_button(__('Ledger'), function(){
				frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: frm.doc.posting_date,
						company: frm.doc.company,
						group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			},__('View'));
			cur_frm.add_custom_button(__('Make Payment'), function(doc) {
				frm.events.make_payment_entry(frm)
			},__('Create'))
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			cur_frm.page.set_inner_btn_group_as_primary(__('View'));
		}
		total_html(frm);
	},
	make_payment_entry:function(frm){
		frappe.call({
			method:
			"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
			args: {
				dt: frm.doc.doctype,
				dn: frm.doc.name,
			},
			callback: function (r) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route("Form", doc[0].doctype, doc[0].name);
			},
		});
	},
	onload:function(frm){
		frm.set_query("credit_account", function() {
			return {
				filters: {
					is_group: 0
				}
			}
		})
		frm.fields_dict['deductions'].grid.get_field('account').get_query = function(){
			return {
				filters: {is_group:0}
			}
		}
		frm.set_query("equipment", function() {
			return {
				filters: {
					hired_equipment: 1
				}
			}
		})
		total_html(frm);
	},
	from_date: function(frm){
		frm.events.reset_items(frm);
	},
	to_date: function(frm){
		frm.events.reset_items(frm);
	},
	equipment: function(frm){
		frm.events.reset_items(frm);
	},
	reset_items:function(frm){
		cur_frm.clear_table("items");
		cur_frm.clear_table("pols");
		calculate_totals(frm);
	},
	get_details:function(frm){
		frm.events.reset_items(frm);
		frappe.call({
			method:'get_payment_details',
			doc:frm.doc,
			callback:function(r){
				total_html(frm);
				frm.refresh_fields();
				frm.dirty()
			},
			freeze: false,
			freeze_message: "Loading Data..... Please Wait"
		})
	},
	supplier:function(frm){
		if (frm.doc.supplier){
			frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					party_type:"Supplier",
					party:frm.doc.supplier,
					company: frm.doc.company,
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("credit_account",r.message)
						frm.refresh_fields("credit_account")
					}
				}
			});
		}
	}
});

var calculate_totals = function(frm){
	cur_frm.call({
		method: "calculate_total",
		doc:frm.doc,
		callback: function(r, rt){
			total_html(frm);
			frm.dirty()
		},
	});
}
var total_html = function(frm){
	$(cur_frm.fields_dict.total_html.wrapper).html('<table style="width: 100%; font-weight: bold;"></table>');	
	var row = "";
	row += get_row('Total No.of Trips', flt(frm.doc.total_trip), 0);
	row += get_row('Transfer Charges', flt(frm.doc.transfer_charges), 0, "+");
	row += get_row('Delivery Charges', flt(frm.doc.delivery_charges), 0, "+");
	row += get_row('Transportation Amount', flt(frm.doc.transportation_amount), 1);
	row += get_row('Unloading Amount', flt(frm.doc.unloading_amount), 0, "+");
	row += get_row('Transporter Trip Log Count', flt(frm.doc.within_warehouse_trip), 0);
	row += get_row('Within Warehouse Transportation Amt.', flt(frm.doc.within_warehouse_amount), 1, '+');
	row += get_row("Production Trip Count", flt(frm.doc.production_trip_count), 0);
	row += get_row('Production Transportation Amt.', flt(frm.doc.production_transport_amount), 1, '+');
	row += get_row('Gross Amount', flt(frm.doc.gross_amount), 1);
	row += get_row('POL Amount', flt(frm.doc.pol_amount), 0, "-");
	row += get_row('Net Amount', flt(frm.doc.net_payable), 1);
	row += get_row('Weighbridge Charges', flt(frm.doc.weighbridge_amount), 0, "-");
	row += get_row('Clearing Charges', flt(frm.doc.clearing_amount), 0, "-");
	row += get_row('Other Deductions, TDS & SD', flt(frm.doc.other_deductions), 0, "-");
	row += get_row('Payable Amount', flt(frm.doc.amount_payable), 1);
	
	$(cur_frm.fields_dict.total_html.wrapper).html('<table style="width: 100%; font-weight: bold;">'+row+'</table>');	
}
var get_row = function(label, value, with_border=0, suffix=""){
	var fmt_value = numberWithCommas(roundToTwo(flt(value)));
	var fmt_suffix= "";

	if(suffix){
		fmt_suffix = `(${suffix})`;
	}

	if(with_border){
		return `<tr>
				<td>${label}</td>
				<td align="right" style="border-top: 1px solid #8D99A6;border-bottom: 1px solid #8D99A6;">${fmt_value}</td>
				<td style="padding: 5px;">${fmt_suffix}</td></tr>`;
	}
	else{
		return `<tr><td>${label}</td><td align="right">${fmt_value}</td><td style="padding: 5px;">${fmt_suffix}</td></tr>`;
	}
}
function roundToTwo(num) {    
    return +(Math.round(num + "e+2")  + "e-2");
}

function numberWithCommas(x) {
    var parts = x.toString().split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return parts.join(".");
}
