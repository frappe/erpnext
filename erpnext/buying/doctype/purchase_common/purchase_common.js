// Preset
// ------
// cur_frm.cscript.tname - Details table name
// cur_frm.cscript.fname - Details fieldname
var tname = cur_frm.cscript.tname;
var fname = cur_frm.cscript.fname;


cur_frm.cscript.get_default_schedule_date = function(doc) {
    var ch = getchildren( tname, doc.name, fname);
    if (flt(ch.length) > 0){
      $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_schedule_date', '', function(r, rt) { refresh_field(fname); });
    }
}

/*
// ======================== Supplier =================================================
cur_frm.cscript.supplier = function(doc, cdt, cdn) {
  if(doc.supplier) get_server_fields('get_supplier_details', doc.supplier,'', doc, cdt, cdn, 1);
}

*/


// ======================== Conversion Rate ==========================================
cur_frm.cscript.conversion_rate = function(doc,cdt,cdn) {
  cur_frm.cscript.calc_amount( doc, 1);
}

//==================== Item Code Get Query =======================================================
// Only Is Purchase Item = 'Yes' and Items not moved to trash are allowed.
cur_frm.fields_dict[fname].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
  return 'SELECT tabItem.name, tabItem.description FROM tabItem WHERE tabItem.is_purchase_item="Yes" AND (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND tabItem.%(key)s LIKE "%s" LIMIT 50'
}

//==================== Get Item Code Details =====================================================
cur_frm.cscript.item_code = function(doc,cdt,cdn) {
  var d = locals[cdt][cdn];
  if (d.item_code) {
    temp = "{'item_code':'"+(d.item_code?d.item_code:'')+"', 'warehouse':'"+(d.warehouse?d.warehouse:'')+"'}"
    get_server_fields('get_item_details', temp, fname, doc, cdt, cdn, 1);
  }
}

//==================== Update Stock Qty ==========================================================
cur_frm.cscript.update_stock_qty = function(doc,cdt,cdn){
  d = locals[cdt][cdn]
  // Step 1:=> Check if qty , uom, conversion_factor
  if (d.qty && d.uom && d.conversion_factor){
    // Step 2:=> Set stock_qty = qty * conversion_factor
    d.stock_qty = flt(flt(d.qty) * flt(d.conversion_factor));
    // Step 3:=> Refer stock_qty field a that particular row.
    refresh_field('stock_qty' , d.name,fname);
  }
}

//==================== Purchase UOM Get Query =======================================================
//cur_frm.fields_dict[fname].grid.get_field("uom").get_query = function(doc, cdt, cdn) {
//  var d = locals[this.doctype][this.docname];
//  return 'SELECT `tabUOM Conversion Detail`.`uom` FROM `tabUOM Conversion Detail` WHERE `tabUOM Conversion Detail`.`parent` = "' + d.item_code + '" AND `tabUOM Conversion Detail`.uom LIKE "%s"'
//}


//==================== UOM ======================================================================
cur_frm.cscript.uom = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if (d.item_code && d.uom) {
    call_back = function(doc, cdt, cdn){
      //refresh_field('purchase_rate', d.name, fname);
      //refresh_field('qty' , d.name, fname);
      //refresh_field('conversion_factor' , d.name, fname);
      //var doc = locals[cdt][cdn];
      cur_frm.cscript.calc_amount(doc, 2);
    }
    str_arg = {'item_code':d.item_code, 'uom':d.uom, 'stock_qty':flt(d.stock_qty), 'qty': flt(d.qty)}
    // Updates Conversion Factor, Qty and Purchase Rate
    get_server_fields('get_uom_details',JSON.stringify(str_arg), fname, doc,cdt,cdn,1, call_back);
    // don't make mistake of calling update_stock_qty() the get_uom_details returns stock_qty as per conversion factor properly
  }
}


//==================== Conversion factor =========================================================
cur_frm.cscript.conversion_factor = function(doc, cdt, cdn) {
  cur_frm.cscript.uom(doc, cdt, cdn);
}

//==================== stock qty ======================================================================
cur_frm.cscript.stock_qty = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if(d.uom && d.qty){
    d.conversion_factor = flt(d.stock_qty)/flt(d.qty);
    refresh_field('conversion_factor', d.name, fname);
  }
}

//==================== Warehouse ================================================================
cur_frm.cscript.warehouse = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  if (d.item_code && d.warehouse) {
    str_arg = "{'item_code':'" +  (d.item_code?d.item_code:'') + "', 'warehouse':'" + (d.warehouse?d.warehouse:'') + "'}"
    get_server_fields('get_bin_details', str_arg, fname, doc, cdt, cdn, 1);
  }  
}

//=================== Quantity ===================================================================
cur_frm.cscript.qty = function(doc, cdt, cdn) {
  var d = locals[cdt][cdn];
  // Step 1: => Update Stock Qty 
  cur_frm.cscript.update_stock_qty(doc,cdt,cdn);
  // Step 2: => Calculate Amount
  cur_frm.cscript.calc_amount(doc, 2);
}


//=================== Purchase Rate ==============================================================
cur_frm.cscript.purchase_rate = function(doc, cdt, cdn) {
  // Calculate Amount
  cur_frm.cscript.calc_amount(doc, 2);
}

//==================== Import Rate ================================================================
cur_frm.cscript.import_rate = function(doc, cdt, cdn) {
  // Calculate Amount
  cur_frm.cscript.calc_amount(doc, 1);
}


//====================== Calculate Amount  ============================================================
/*cur_frm.cscript.calc_amount = function(doc, n) {
  // Set defaults
  doc = locals[doc.doctype][doc.name] 
  if (! doc.conversion_rate) doc.conversion_rate = 1;
  if(!n) n=0;
  var net_total = 0;
  var net_total_import = 0;
  
  var cl = getchildren(tname, doc.name, fname);
  
  for(var i=0;i<cl.length;i++) 
  {
    if(n == 1){ 
      set_multiple(tname, cl[i].name, {'purchase_rate': flt(doc.conversion_rate) * flt(cl[i].import_rate) }, fname);
      set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(doc.conversion_rate) * flt(cl[i].import_rate))}, fname);
      set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) * flt(cl[i].import_rate))}, fname);
    }
    if(n == 2){
      set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(cl[i].purchase_rate)), 'import_rate': flt(flt(cl[i].purchase_rate) / flt(doc.conversion_rate)) }, fname);
      set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *  flt(cl[i].purchase_rate) / flt(doc.conversion_rate))}, fname);
    }
    net_total += flt(flt(cl[i].qty) * flt(cl[i].purchase_rate));
    net_total_import += flt(flt(cl[i].qty) * flt(cl[i].import_rate));
  }
  doc.net_total = flt(net_total) ;
  doc.net_total_import = flt(net_total_import) ;
  refresh_field('net_total');
  refresh_field('net_total_import');
}  */

//==================== check if item table is blank ==============================================
var is_item_table = function(doc,cdt,cdn) {
  // Step 1 :=>Get all childrens/ rows from Detail Table
  var cl = getchildren(tname, doc.name, fname);
  // Step 2 :=> If there are no rows then set validated = false, I hope this will stop further execution of code.
  if (cl.length == 0) {
    alert("There is no item in table"); validated = false;
  }
}

//==================== Validate ====================================================================
cur_frm.cscript.validate = function(doc, cdt, cdn) {
  // Step 1:=> check if item table is blank
  is_item_table(doc,cdt,cdn);
  // Step 2:=> Calculate Amount
  cur_frm.cscript.calc_amount(doc, 1);
}



/*cur_frm.cscript.other_fname = "purchase_tax_details";
other_charges ===> purchase_tax_details
RV Tax Detail ===> Purchase Tax Detail
cur_frm.cscript.recalc ===> cur_frm.cscript.calc_amount
export ===> import
other_charges_total ===> total_tax
Other Charges Calculation  ===> Tax Calculation*/

// **************** RE-CALCULATE VALUES ***************************

cur_frm.cscript['Re-Calculate Values'] = function(doc, cdt, cdn) {
  cur_frm.cscript['Calculate Tax'](doc,cdt,cdn);
}

cur_frm.cscript['Calculate Tax'] = function(doc, cdt, cdn) {
  var other_fname  = cur_frm.cscript.other_fname;

  var cl = getchildren('Purchase Tax Detail', doc.name, other_fname, doc.doctype);
  for(var i = 0; i<cl.length; i++){
    cl[i].total_tax_amount = 0;
    cl[i].total_amount = 0;
    cl[i].tax_amount = 0;                    // this is done to calculate other charges
    cl[i].total = 0;
    if(in_list(['On Previous Row Amount','On Previous Row Total'],cl[i].charge_type) && !cl[i].row_id){
      alert("Please Enter Row on which amount needs to be calculated for row : "+cl[i].idx);
      validated = false;
    }
  }
  if(doc.doctype != 'Payable Voucher') cur_frm.cscript.calc_amount(doc, 1);
  else if(doc.doctype == 'Payable Voucher') cur_frm.cscript.calc_total(doc);
}



cur_frm.cscript.get_item_wise_tax_detail = function( doc, rate, cl, i, tax, t) {
  doc = locals[doc.doctype][doc.name];
  var detail = '';
  detail = cl[i].item_code + " : " + cstr(rate) + NEWLINE;
  return detail;
}

  //if(cur_frm.cscript.custom_recalc)cur_frm.cscript.custom_recalc(doc);



cur_frm.cscript.amount = function(doc, cdt, cdn) {
  cur_frm.cscript.calc_amount(doc, 3);
}


//====================== Calculate Amount for PO and PR not for PV  ============================================================
cur_frm.cscript.calc_amount = function(doc, n) {
  // Set defaults
  doc = locals[doc.doctype][doc.name]
  var other_fname  = cur_frm.cscript.other_fname;
  if(!flt(doc.conversion_rate)) { doc.conversion_rate = 1; refresh_field('conversion_rate'); }
  if(!n) n=0;
  var net_total = 0;
  var net_total_import = 0;
  
  var cl = getchildren(tname, doc.name, fname);
  
  for(var i=0;i<cl.length;i++) 
  {
    if(n == 1){ 
      set_multiple(tname, cl[i].name, {'purchase_rate': flt(doc.conversion_rate) * flt(cl[i].import_rate) }, fname);
      set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(doc.conversion_rate) * flt(cl[i].import_rate))}, fname);
      set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) * flt(cl[i].import_rate))}, fname);
    }
    if(n == 2){
      set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(cl[i].purchase_rate)), 'import_rate': flt(flt(cl[i].purchase_rate) / flt(doc.conversion_rate)) }, fname);
      set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *  flt(cl[i].purchase_rate) / flt(doc.conversion_rate))}, fname);
    }
    if(n == 3){
      set_multiple(tname, cl[i].name, {'purchase_rate': flt(flt(cl[i].amount) / flt(cl[i].qty)) }, fname);
      set_multiple(tname, cl[i].name, {'import_rate': flt(flt(cl[i].purchase_rate) / flt(doc.conversion_rate))}, fname); 
      set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *  flt(cl[i].purchase_rate) / flt(doc.conversion_rate))}, fname);
    }
    if (n != 3){
      net_total += flt(flt(cl[i].qty) * flt(cl[i].purchase_rate));
      net_total_import += flt(flt(cl[i].qty) * flt(cl[i].import_rate));
    }
    else if(n == 3){
      net_total += flt(cl[i].amount);
      net_total_import += flt(cl[i].amount) / flt(doc.conversion_rate);
    }
    //update stock uom
    cur_frm.cscript.update_stock_qty(doc, tname, cl[i].name);
  }
  doc.net_total = flt(net_total) ;
  doc.net_total_import = flt(net_total_import) ;
  refresh_field('net_total');
  refresh_field('net_total_import');
  
  cur_frm.cscript.val_cal_charges(doc, cdt, cdn, tname, fname, other_fname);
}


//======== Function was broken away from cur_frm.cscript.calc_amount as PV has fieldname 'rate' instead of 'purchase_rate'===========
cur_frm.cscript.val_cal_charges = function(doc, cdt, cdn, tname, fname, other_fname){

  doc = locals[doc.doctype][doc.name]
  if(flt(doc.net_total) > 0) {
    var cl = getchildren('Purchase Tax Detail', doc.name, other_fname,doc.doctype);
    for(var i = 0; i<cl.length; i++){
      cl[i].total_tax_amount = 0;
      cl[i].total_amount = 0;
      cl[i].tax_amount = 0;                    // this is done to calculate other charges
      cl[i].total = 0;
      cl[i].item_wise_tax_detail = "";
      if(in_list(['On Previous Row Amount','On Previous Row Total'],cl[i].charge_type) && !cl[i].row_id){
        alert("Please Enter Row on which amount needs to be calculated for row : "+cl[i].idx);
        validated = false;
      }
    }
    cur_frm.cscript.calc_other_charges(doc , tname , fname , other_fname); // calculate other charges
  }
  cur_frm.cscript.calc_doc_values(doc, cdt, cdn, tname, fname, other_fname); // calculates total amounts

  refresh_many(['net_total','grand_total','rounded_total','grand_total_import','rounded_total_import','in_words','in_words_import','purchase_tax_details','total_tax','other_charges_added', 'other_charges_deducted','net_total_import','other_charges_added_import','other_charges_deducted_import']);

}


// ******************************* OTHER CHARGES *************************************
cur_frm.cscript.calc_other_charges = function(doc , tname , fname , other_fname) {
  doc = locals[doc.doctype][doc.name];
  // make display area
  // ------------------

  
  cur_frm.fields_dict['Tax Calculation'].disp_area.innerHTML = '<b style="padding: 8px 0px;">Calculation Details for Other Charges and Landed cost:</b>';
  var cl = getchildren(tname, doc.name, fname);
  var tax = getchildren('Purchase Tax Detail', doc.name, other_fname,doc.doctype);
  // make display table
  // ------------------
  var otc = make_table(cur_frm.fields_dict['Tax Calculation'].disp_area, cl.length + 1, tax.length + 1, '90%',[],{border:'1px solid #AAA',padding:'2px'});
  $y(otc,{marginTop:'8px'});
  
  var tax_desc = {}; var tax_desc_rates = []; var net_total = 0;
  
  
  for(var i=0;i<cl.length;i++) {
    var item_tax = 0;
    if(doc.doctype != 'Payable Voucher') net_total += flt(flt(cl[i].qty) * flt(cl[i].purchase_rate));
    else if(doc.doctype == 'Payable Voucher') net_total += flt(flt(cl[i].qty) * flt(cl[i].rate));

    var prev_total = flt(cl[i].amount);
    if(cl[i].item_tax_rate)
      var check_tax = eval('var a='+cl[i].item_tax_rate+';a');        //to get in dictionary
    
    // Add Item Code in new Row 
    //--------------------------
    $td(otc,i+1,0).innerHTML = cl[i].item_code;
    
    var tax = getchildren('Purchase Tax Detail', doc.name, other_fname,doc.doctype);
    var total = net_total;
    for(var t=0;t<tax.length;t++){
 
      var account = tax[t].account_head;
      $td(otc,0,t+1).innerHTML = account?account:'';
      //Check For Rate
      if(cl[i].item_tax_rate && check_tax[account]!=null)  {rate = flt(check_tax[account]);}
      else               // if particular item doesn't have particular rate it will take other charges rate
        rate = flt(tax[t].rate);
      //Check For Rate and get tax amount
      var tax_amount = cur_frm.cscript.check_charge_type_and_get_tax_amount(doc,tax,t, cl[i], rate);
      
      //enter item_wise_tax_detail i.e. tax rate on each item
      
      item_wise_tax_detail = cur_frm.cscript.get_item_wise_tax_detail( doc, rate, cl, i, tax, t);
      
      
      if(tax[t].add_deduct_tax == 'Add'){
        // this is calculation part for all types
        if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
        tax[t].total_amount = flt(tax_amount.toFixed(2));     //stores actual tax amount in virtual field
        tax[t].total_tax_amount = flt(prev_total.toFixed(2));      //stores total amount in virtual field
        tax[t].tax_amount += flt(tax_amount.toFixed(2));       
        var total_amount = flt(tax[t].tax_amount);
        total_tax_amount = flt(tax[t].total_tax_amount) + flt(total_amount);
        if(tax[t].category != "For Valuation"){
          set_multiple('Purchase Tax Detail', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':total_amount, 'total':flt(total)+flt(tax[t].tax_amount)/*_tax_amount)*/}, other_fname);
          prev_total += flt(tax[t].total_amount);
          total += flt(tax[t].tax_amount);  // for adding total to previous amount       
        }
        else{
          set_multiple('Purchase Tax Detail', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':total_amount, 'total':flt(total)/*_tax_amount)*/}, other_fname);
          prev_total = prev_total;
        }
        //prev_total += flt(tax[t].total_amount);   // for previous row total

        if(tax[t].charge_type == 'Actual')
          $td(otc,i+1,t+1).innerHTML = fmt_money(tax[t].total_amount);
        else
          $td(otc,i+1,t+1).innerHTML = '('+fmt_money(rate) + '%) ' +fmt_money(tax[t].total_amount);

        if (tax[t].category != "For Total"){
          item_tax += tax[t].total_amount;
        }
      }
      else if(tax[t].add_deduct_tax == 'Deduct'){
        // this is calculation part for all types
        if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
        tax[t].total_amount = flt(tax_amount.toFixed(2));     //stores actual tax amount in virtual field
        tax[t].total_tax_amount = flt(prev_total.toFixed(2));      //stores total amount in virtual field
        tax[t].tax_amount += flt(tax_amount.toFixed(2));
        var total_amount = flt(tax[t].tax_amount);
        total_tax_amount = flt(tax[t].total_tax_amount) - flt(total_amount);
        if(tax[t].category != "For Valuation"){
          set_multiple('Purchase Tax Detail', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'tax_amount':total_amount, 'total':flt(total)-flt(tax[t].tax_amount)/*_tax_amount)*/}, other_fname);
          prev_total -= flt(tax[t].total_amount); 
          total -= flt(tax[t].tax_amount);  // for adding total to previous amount       
        }
        else{
          set_multiple('Purchase Tax Detail', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'tax_amount':total_amount, 'total':flt(total)/*_tax_amount)*/}, other_fname);
          prev_total = prev_total;
        }
        //prev_total += flt(tax[t].total_amount);   // for previous row total

        if(tax[t].charge_type == 'Actual')
          $td(otc,i+1,t+1).innerHTML = fmt_money(tax[t].total_amount);
        else
          $td(otc,i+1,t+1).innerHTML = '('+fmt_money(rate) + '%) ' +fmt_money(tax[t].total_amount);

        if (tax[t].category != "For Total"){
          item_tax -= tax[t].total_amount;
        }
      }      
      
      
    }
    set_multiple(tname, cl[i].name, {'item_tax_amount': item_tax }, fname);
  }
}




// ******* Calculation of total amounts of document (item amount + other charges)****************
cur_frm.cscript.calc_doc_values = function(doc, cdt, cdn, tname, fname, other_fname) {
  doc = locals[doc.doctype][doc.name];
  var net_total = 0; var total_tax = 0; var other_charges_added = 0; var other_charges_deducted = 0;
  var cl = getchildren(tname, doc.name, fname);
  for(var i = 0; i<cl.length; i++){
    net_total += flt(cl[i].amount);
  }
  var d = getchildren('Purchase Tax Detail', doc.name, other_fname,doc.doctype);
  for(var j = 0; j<d.length; j++){
    if(d[j].category != 'For Valuation'){
      
      if(d[j].add_deduct_tax == 'Add'){
        other_charges_added += flt(d[j].tax_amount);
        total_tax += flt(d[j].tax_amount);
      }
      if(d[j].add_deduct_tax == 'Deduct'){
        other_charges_deducted += flt(d[j].tax_amount);
        total_tax -= flt(d[j].tax_amount);
      }
    }
  }
  doc.net_total = flt(net_total);
  doc.total_tax = flt(total_tax);

  doc.other_charges_added = flt(other_charges_added);
  doc.other_charges_deducted = flt(other_charges_deducted);
  doc.grand_total = flt(flt(net_total) + flt(other_charges_added) - flt(other_charges_deducted));
  doc.rounded_total = Math.round(doc.grand_total);
  doc.net_total_import = flt(flt(net_total) / flt(doc.conversion_rate));
  doc.other_charges_added_import = flt(flt(other_charges_added) / flt(doc.conversion_rate));
  doc.other_charges_deducted_import = flt(flt(other_charges_deducted) / flt(doc.conversion_rate));
  doc.grand_total_import = flt(flt(doc.grand_total) / flt(doc.conversion_rate));
  doc.rounded_total_import = Math.round(doc.grand_total_import);

  if(doc.doctype == 'Payable Voucher'){
    var t_tds_tax = 0.0;
    
    doc.total_tds_on_voucher = flt(doc.ded_amount)
    // total amount to pay
    
    doc.total_amount_to_pay = flt(flt(net_total) + flt(other_charges_added) - flt(other_charges_deducted) - flt(doc.total_tds_on_voucher));
    
    // outstanding amount 
    if(doc.docstatus==0) doc.outstanding_amount = flt(doc.net_total) + flt(other_charges_added) - flt(other_charges_deducted) - flt(doc.total_tds_on_voucher) - flt(doc.total_advance);
    
    refresh_many(['net_total','total_taxes','grand_total','total_tds_on_voucher','total_amount_to_pay', 'outstanding_amount']);
  }
}


cur_frm.cscript.check_charge_type_and_get_tax_amount = function(doc, tax, t, cl, rate, print_amt) {
  doc = locals[doc.doctype][doc.name];

  var tax_amount = 0;
  if(tax[t].charge_type == 'Actual') {
    var value = flt(tax[t].rate) / flt(doc.net_total);   // this give the ratio in which all items are divided           
    return tax_amount = flt(value) * flt(cl.amount);
   }   
  else if(tax[t].charge_type == 'On Net Total') {
    return tax_amount = (flt(rate) * flt(cl.amount) / 100);
  }
  else if(tax[t].charge_type == 'On Previous Row Amount'){
    var row_no = (tax[t].row_id).toString();
    var row = (row_no).split("+");      // splits the values and stores in an array
    for(var r = 0;r<row.length;r++){
      var id = cint(row[r].replace(/^\s+|\s+$/g,""));
      tax_amount += (flt(rate) * flt(tax[id-1].total_amount) / 100);
    }
    var row_id = row_no.indexOf("/");
    if(row_id != -1) {
      rate = '';
      var row = (row_no).split("/");      // splits the values and stores in an array
      if(row.length>2) alert("You cannot enter more than 2 nos. for division");
      var id1 = cint(row[0].replace(/^\s+|\s+$/g,""));
      var id2 = cint(row[1].replace(/^\s+|\s+$/g,""));
      tax_amount = flt(tax[id1-1].total_amount) / flt(tax[id2-1].total_amount);
    }
    return tax_amount
  }
  else if(tax[t].charge_type == 'On Previous Row Total') {
    var row = cint(tax[t].row_id);
    if(tax[row-1].add_deduct_tax == 'Add'){
      return tax_amount = flt(rate) * (flt(tax[row-1].total_tax_amount)+flt(tax[row-1].total_amount)) / 100;
     }
    else if(tax[row-1].add_deduct_tax == 'Deduct'){
      return tax_amount = flt(rate) * (flt(tax[row-1].total_tax_amount)-flt(tax[row-1].total_amount)) / 100;
     }
  }
}
