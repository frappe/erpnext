//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  // 
}

/*cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}*/

// For customizing print

cur_frm.pformat.other_charges= function(doc){
  //function to make row of table
  var make_row = function(title,val,bold){
    var bstart = '<b>'; var bend = '</b>';
    return '<tr><td style="width:50%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
     +'<td style="width:25%;text-align:right;">'+doc.currency+'</td>'
     +'<td style="width:25%;text-align:right;">'+val+'</td>'
     +'</tr>'
  }

  function convert_rate(val){
    var new_val = flt(val)/flt(doc.conversion_rate);
    return new_val;
  }
  out ='';
  if (!doc.print_without_amount) {
    var cl = getchildren('RV Tax Detail',doc.name,'other_charges');

    // outer table  
    var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 60%"></td><td>';
    
    // main table
    out +='<table class="noborder" style="width:100%">'+make_row('Net Total',fmt_money(convert_rate(doc.net_total)),1);

    // add rows
    if(cl.length){
      for(var i=0;i<cl.length;i++){
        if(fmt_money(convert_rate(cl[i].tax_amount))!=0)
          out += make_row(cl[i].description,fmt_money(convert_rate(cl[i].tax_amount)),0);
      }
    }
  
    // grand total
    out +=make_row('Grand Total',fmt_money(doc.grand_total_export),1) +make_row('Rounded Total',fmt_money(doc.rounded_total_export),1)
    if(doc.in_words_export){
      out +='</table></td></tr>';
      out += '<tr><td colspan = "2">';
      out += '<table><tr><td style="width:25%;"><b>In Words</b></td>'
      out+= '<td style="width:50%;">'+doc.in_words_export+'</td></tr>'
    }
    out +='</table></td></tr></table></div>';   
  }
  return out;
}

cur_frm.cscript.charge_type = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(d.idx == 1 && (d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total')){
    alert("You cannot select Charge Type as 'On Previous Row Amount' or 'On Previous Row Total' for first row");
    d.charge_type = '';
  }
  validated = false;
  refresh_field('charge_type',d.name,'other_charges');
  cur_frm.cscript.row_id(doc, cdt, cdn);
  cur_frm.cscript.rate(doc, cdt, cdn);
  cur_frm.cscript.tax_amount(doc, cdt, cdn);
}

cur_frm.cscript.row_id = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.row_id){
    alert("Please select Charge Type first");
    d.row_id = '';
  }
  else if((d.charge_type == 'Actual' || d.charge_type == 'On Net Total') && d.row_id) {
    alert("You can Enter Row only if your Charge Type is 'On Previous Row Amount' or ' Previous Row Total'");
    d.row_id = '';
  }
  else if((d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total') && d.row_id){
    if(d.row_id >= d.idx){
      alert("You cannot Enter Row no. greater than or equal to current row no. for this Charge type");
      d.row_id = '';
    }
  }
  validated = false;
  refresh_field('row_id',d.name,'other_charges');
}

/*---------------------- Get rate if account_head has account_type as TAX or CHARGEABLE-------------------------------------*/

cur_frm.fields_dict['other_charges'].grid.get_field("account_head").get_query = function(doc,cdt,cdn) {
  return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND (tabAccount.account_type = "Tax" OR tabAccount.account_type = "Chargeable") AND tabAccount.company = "'+doc.company+'" AND  tabAccount.name LIKE "%s"'
}

//--------------------filter other charges master company-wise-----------------------------------------
/*
cur_frm.fields_dict.charge.get_query = function(doc) {
  return 'SELECT DISTINCT `tabOther Charges`.name FROM `tabOther Charges` WHERE `tabOther Charges`.company = "'+doc.company+'" AND `tabOther Charges`.company is not NULL AND `tabOther Charges`.name LIKE "%s" ORDER BY `tabOther Charges`.name LIMIT 50';
}
*/

cur_frm.cscript.account_head = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.account_head){
    alert("Please select Charge Type first");
    validated = false;
    d.account_head = '';
  }
  else if(d.account_head && d.charge_type) {
    arg = "{'charge_type' : '" + d.charge_type +"', 'account_head' : '" + d.account_head + "'}";
    get_server_fields('get_rate', arg, 'other_charges', doc, cdt, cdn, 1);
  }
  refresh_field('account_head',d.name,'other_charges');
}

cur_frm.cscript.rate = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.rate) {
    alert("Please select Charge Type first");
    d.rate = '';
  }
  validated = false;
  refresh_field('rate',d.name,'other_charges');
}

cur_frm.cscript.tax_amount = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(!d.charge_type && d.tax_amount){
    alert("Please select Charge Type first");
    d.tax_amount = '';
  }
  else if(d.charge_type && d.tax_amount) {
    alert("You cannot directly enter Amount and if your Charge Type is Actual enter your amount in Rate");
    d.tax_amount = '';
  }
  validated = false;
  refresh_field('tax_amount',d.name,'other_charges');
}
