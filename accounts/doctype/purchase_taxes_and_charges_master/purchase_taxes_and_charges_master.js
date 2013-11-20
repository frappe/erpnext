// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// 

//--------- ONLOAD -------------
wn.require("app/js/controllers/accounts.js");

cur_frm.cscript.onload = function(doc, cdt, cdn) {
   
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   cur_frm.set_footnote(wn.markdown(cur_frm.meta.description));
}

cur_frm.pformat.purchase_tax_details= function(doc){
 
  //function to make row of table
  var make_row = function(title,val,bold){
    var bstart = '<b>'; var bend = '</b>';
    return '<tr><td style="width:50%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
     +'<td style="width:25%;text-align:right;"></td>'
     +'<td style="width:25%;text-align:right;">'+format_currency(val, doc.currency)+'</td>'
     +'</tr>'
  }

  function convert_rate(val){
    var new_val = flt(val)/flt(doc.conversion_rate);
    return new_val;
  }

  var cl = getchildren('Purchase Taxes and Charges',doc.name,'purchase_tax_details');

  // outer table  
  var out='<div><table class="noborder" style="width:100%">\
		<tr><td style="width: 60%"></td><td>';
  
  // main table
  out +='<table class="noborder" style="width:100%">'
		+make_row('Net Total',convert_rate(doc.net_total),1);

  // add rows
  if(cl.length){
    for(var i=0;i<cl.length;i++){
      out += make_row(cl[i].description,convert_rate(cl[i].tax_amount),0);
    }
  }
  
  // grand total
  out +=make_row('Grand Total',doc.grand_total_import,1)
  if(doc.in_words_import){
    out +='</table></td></tr>';
    out += '<tr><td colspan = "2">';
    out += '<table><tr><td style="width:25%;"><b>In Words</b></td>';
    out+= '<td style="width:50%;">'+doc.in_words_import+'</td></tr>';
  }
  out +='</table></td></tr></table></div>';   
  return out;
}

cur_frm.cscript.add_deduct_tax = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.category && d.add_deduct_tax){
    alert(wn._("Please select Category first"));
    d.add_deduct_tax = '';
  }
  else if(d.category != 'Total' && d.add_deduct_tax == 'Deduct') {
	console.log([d.category, d.add_deduct_tax]);
    msgprint(wn._("You cannot deduct when category is for 'Valuation' or 'Valuation and Total'"));
    d.add_deduct_tax = '';
  }

}

cur_frm.cscript.charge_type = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.category && d.charge_type){
    alert(wn._("Please select Category first"));
    d.charge_type = '';
  }  
  else if(d.idx == 1 && (d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total')){
    alert(wn._("You cannot select Charge Type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"));
    d.charge_type = '';
  }
  else if((d.category == 'Valuation' || d.category == 'Valuation and Total') && (d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total')){
    alert(wn._("You cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for valuation. You can select only 'Total' option for previous row amount or previous row total"))
    d.charge_type = '';
  }
  validated = false;
  refresh_field('charge_type',d.name,'purchase_tax_details');

  cur_frm.cscript.row_id(doc, cdt, cdn);
  cur_frm.cscript.rate(doc, cdt, cdn);
  cur_frm.cscript.tax_amount(doc, cdt, cdn);
}


cur_frm.cscript.row_id = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.row_id){
    alert(wn._("Please select Charge Type first"));
    d.row_id = '';
  }
  else if((d.charge_type == 'Actual' || d.charge_type == 'On Net Total') && d.row_id) {
    alert(wn._("You can Enter Row only if your Charge Type is 'On Previous Row Amount' or ' Previous Row Total'"));
    d.row_id = '';
  }
  else if((d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total') && d.row_id){
    if(d.row_id >= d.idx){
      alert(wn._("You cannot Enter Row no. greater than or equal to current row no. for this Charge type"));
      d.row_id = '';
    }
  }
  validated = false;
  refresh_field('row_id',d.name,'purchase_tax_details');
}

cur_frm.set_query("account_head", "purchase_tax_details", function(doc) {
	return {
		query: "controllers.queries.tax_account_query",
    	filters: {
			"account_type": ["Tax", "Chargeable", "Expense Account"],
			"debit_or_credit": "Debit",
			"company": doc.company
		}
	}
});

cur_frm.fields_dict['purchase_tax_details'].grid.get_field("cost_center").get_query = function(doc) {
  return {
    filters: {
      'company': doc.company,
      'group_or_ledger': "Ledger"
    }
  }
}

cur_frm.cscript.rate = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.rate) {
    alert(wn._("Please select Charge Type first"));
    d.rate = '';
  }
  validated = false;
  refresh_field('rate',d.name,'purchase_tax_details');
}

cur_frm.cscript.tax_amount = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.tax_amount){
    alert(wn._("Please select Charge Type first"));
    d.tax_amount = '';
  }
  else if(d.charge_type && d.tax_amount) {
    alert(wn._("You cannot directly enter Amount and if your Charge Type is Actual enter your amount in Rate"));
    d.tax_amount = '';
  }
  validated = false;
  refresh_field('tax_amount',d.name,'purchase_tax_details');
}
