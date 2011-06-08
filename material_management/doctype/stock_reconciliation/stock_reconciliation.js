cur_frm.cscript.onload = function(doc, cdt, cdn) {
  cfn_set_fields(doc, cdt, cdn);
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  cfn_set_fields(doc, cdt, cdn);
}

var cfn_set_fields = function(doc, cdt, cdn) {
  refresh_field('remark');
  refresh_field('next_step');
  if (doc.docstatus == 0 && doc.next_step == 'Upload File and Save Document') 
    doc.next_step = 'Validate Data';
  
  if (! doc.file_list)
    doc.next_step = 'Upload File and Save Document'
  
  if (doc.next_step == 'Upload File and Save Document') {
    //alert("Upload File and Save Document");
    cur_frm.clear_tip();
    cur_frm.set_tip("Please Enter Reconciliation Date and Attach CSV File with Columns in Following Sequence:-");
    cur_frm.append_tip("Item Code , Warehouse , Qty , MAR");
    hide_field("Validate Data");
  }
  if (doc.next_step == 'Validate Data') {
    //alert("Validate Data");
    cur_frm.clear_tip();
    cur_frm.set_tip("Please Check Remarks");
    unhide_field("Validate Data");
  }
  if (doc.next_step == 'Submit Document') {
    //alert('Submit Document');
    cur_frm.clear_tip();
    cur_frm.set_tip("Please Submit the document.");
    hide_field("Validate Data");
  }
}