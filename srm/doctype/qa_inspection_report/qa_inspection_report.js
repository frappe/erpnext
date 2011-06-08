cur_frm.cscript.item_code = function(doc, cdt, cdn) {
  if (doc.item_code)
    get_server_fields('get_purchase_receipt_item_details','','',doc,cdt,cdn,1);
}

cur_frm.cscript.inspection_type = function(doc, cdt, cdn) {
  if(doc.inspection_type == 'Incoming'){
    doc.delivery_note_no = '';
    hide_field('delivery_note_no');    
    unhide_field('purchase_receipt_no');
  }
  else if(doc.inspection_type == 'Outgoing'){
    doc.purchase_receipt_no = '';
    unhide_field('delivery_note_no');
    hide_field('purchase_receipt_no');

  }
  else {
    doc.purchase_receipt_no = '';
    doc.delivery_note_no = '';    
    hide_field('purchase_receipt_no');
    hide_field('delivery_note_no');
  }
}

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;