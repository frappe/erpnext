// Onload
//-------------------------------
cur_frm.cscript.onload = function(doc,dt,dn){
  if(!doc.return_date) set_multiple(dt,dn,{return_date:get_today()});
  doc.delivery_note_no = '';
  doc.purchase_receipt_no = '';
  doc.sales_invoice_no = '';
  doc.return_type ='';
  refresh_many(['delivery_note_no', 'sales_invoice_no', 'purchase_receipt_no', 'return_type']);
}

// Link field query
//--------------------------------
cur_frm.fields_dict.delivery_note_no.get_query = function(doc) {
  return 'SELECT DISTINCT `tabDelivery Note`.name FROM `tabDelivery Note` WHERE `tabDelivery Note`.docstatus = 1 AND `tabDelivery Note`.%(key)s LIKE "%s" ORDER BY `tabDelivery Note`.name desc LIMIT 50';
}

cur_frm.fields_dict.sales_invoice_no.get_query = function(doc) {
  return 'SELECT DISTINCT `tabReceivable Voucher`.name FROM `tabReceivable Voucher` WHERE `tabReceivable Voucher`.docstatus = 1 AND `tabReceivable Voucher`.%(key)s LIKE "%s" ORDER BY `tabReceivable Voucher`.name desc LIMIT 50';
}

cur_frm.fields_dict.purchase_receipt_no.get_query = function(doc) {
  return 'SELECT DISTINCT `tabPurchase Receipt`.name FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.docstatus = 1 AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.name desc LIMIT 50';
}

// Hide/unhide based on return type
//----------------------------------
cur_frm.cscript.return_type = function(doc, cdt, cdn) {
  hide_field(['purchase_receipt_no', 'delivery_note_no', 'sales_invoice_no', 'return_details', 'Get Items', 'Make Excise Invoice', 'Make Stock Entry', 'Make Debit Note', 'Make Credit Note']);
  if(doc.return_type == 'Sales Return')
    unhide_field(['delivery_note_no', 'sales_invoice_no', 'Get Items', 'return_details', 'Make Credit Note', 'Make Stock Entry', 'Make Excise Invoice']);
  else if(doc.return_type == 'Purchase Return')
    unhide_field(['purchase_receipt_no', 'Get Items', 'return_details', 'Make Debit Note', 'Make Stock Entry', 'Make Excise Invoice']);

  cur_frm.cscript.clear_fields(doc);
}

// Create item table
//-------------------------------
cur_frm.cscript['Get Items'] = function(doc, cdt, cdn) {
  flag = 0
  if(doc.return_type == 'Sales Return') {
    if (doc.delivery_note_no && doc.sales_invoice_no) {
      msgprint("You can not enter both Delivery Note No and Sales Invoice No. Please enter any one.");
      flag = 1;
    } else if (!doc.delivery_note_no && !doc.sales_invoice_no) {
      msgprint("Please enter Delivery Note No or Sales Invoice No to proceed");
      flag = 1;
    }
  } else if (doc.return_type == 'Purchase Return' && !doc.purchase_receipt_no) {
    msgprint("Please enter Purchase Receipt No to proceed");
    flag = 1;
  }
  if (!flag)
    $c_obj(make_doclist(doc.doctype, doc.name),'pull_item_details','', function(r, rt) {
      refresh_many(['return_details', 'cust_supp', 'cust_supp_name', 'cust_supp_address']);
    });
}

// Clear fields
//-------------------------------
cur_frm.cscript.clear_fields = function(doc) {
  doc.purchase_receipt_no, doc.delivery_note_no, doc.sales_invoice_no = '', '', '';
  var cl = getchildren('Return Detail', doc.name, 'return_details')
  if(cl.length) $c_obj(make_doclist(doc.doctype, doc.name),'clear_return_table','', function(r, rt) {refresh_field('return_details')});
  refresh_many(['delivery_note_no', 'sales_invoice_no', 'purchase_receipt_no', 'return_details']);
}

// Make Stock Entry
//-------------------------------
cur_frm.cscript['Make Stock Entry'] = function(doc, cdt, cdn) {
  var cl = getchildren('Return Detail', doc.name, 'return_details');
  if (!cl.length)
    msgprint("Item table can not be blank. Please click on 'Get Items'.");
  else if (!cur_frm.cscript.validate_returned_qty(cl)) {
    se = cur_frm.cscript.map_parent_fields(doc,cdt,cdn);
    cur_frm.cscript.map_child_fields(cl, se);
    loaddoc('Stock Entry', se.name);
  }
}

// Validate returned qty
//---------------------------
cur_frm.cscript.validate_returned_qty = function(cl) {
  flag = 0
  for(var i = 0; i<cl.length; i++){
    if(cl[i].returned_qty > cl[i].qty) {
      msgprint("Returned Qty can not be greater than qty. Please check for item: " + cl[i].item_code);
      flag = 1
    }
  }
  return flag
}


// map parent fields of stock entry
//----------------------------------
cur_frm.cscript.map_parent_fields = function(doc, cdt, cdn) {
  var se = LocalDB.create('Stock Entry');
  se = locals['Stock Entry'][se];
  se.posting_date = dateutil.obj_to_str(new Date());
  se.transfer_date = dateutil.obj_to_str(new Date());
  se.fiscal_year = sys_defaults.fiscal_year;
  se.purpose = doc.return_type;
  se.remarks = doc.return_type + ' of ' + (doc.delivery_note_no || doc.sales_invoice_no || doc.purchase_receipt_no);
  if(doc.return_type == 'Sales Return'){
    se.delivery_note_no = doc.delivery_note_no;
    se.sales_invoice_no = doc.sales_invoice_no;
    se.customer = doc.cust_supp_name;
    se.customer_name = doc.cust_supp_name;
    se.customer_address = doc.cust_supp_address;
  }
  else if(doc.return_type == 'Purchase Return'){
    se.purchase_receipt_no = doc.purchase_receipt_no;
    se.supplier = doc.cust_supp_name;
    se.supplier_name = doc.cust_supp_name;
    se.supplier_address = doc.cust_supp_address;
  }
  return se
}

// map child fields of stock entry
//---------------------------------
cur_frm.cscript.map_child_fields = function(cl, se) {
  for(var i = 0; i<cl.length; i++){
    if (cl[i].returned_qty) {
      var d1 = LocalDB.add_child(se, 'Stock Entry Detail', 'mtn_details');
      d1.detail_name = cl[i].detail_name;
      d1.item_code = cl[i].item_code;
      d1.description = cl[i].description;
      d1.transfer_qty = cl[i].returned_qty;
      d1.qty = cl[i].returned_qty;
      d1.stock_uom = cl[i].uom;
      d1.uom = cl[i].uom;
      d1.conversion_factor = 1;
      d1.incoming_rate = cl[i].rate;
      d1.serial_no = cl[i].serial_no;
      d1.batch_no = cl[i].batch_no;
    }
  }
}

// Make excise voucher
//-------------------------------
cur_frm.cscript['Make Excise Invoice'] = function(doc) {
  var excise = LocalDB.create('Journal Voucher');
  excise = locals['Journal Voucher'][excise];
  excise.voucher_type = 'Excise Voucher';
  loaddoc('Journal Voucher',excise.name);
}
// Make debit note
//------------------------------
cur_frm.cscript['Make Debit Note'] = function(doc) {
  cur_frm.cscript.make_jv(doc, 'Debit Note');
}
// Make credit note
//------------------------------
cur_frm.cscript['Make Credit Note'] = function(doc) {
  cur_frm.cscript.make_jv(doc, 'Credit Note');
}

// Make JV
//--------------------------------
cur_frm.cscript.make_jv = function(doc, dr_or_cr) {
  var jv = LocalDB.create('Journal Voucher');
  jv = locals['Journal Voucher'][jv];
  
  jv.voucher_type = dr_or_cr;
  jv.company = sys_defaults.company;
  jv.fiscal_year = sys_defaults.fiscal_year;
  jv.is_opening = 'No';
  jv.posting_date = dateutil.obj_to_str(new Date());
  jv.voucher_date = dateutil.obj_to_str(new Date());

  loaddoc('Journal Voucher',jv.name);
}
