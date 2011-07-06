cur_frm.cscript.onload = function(doc,dt,dn){
  if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
  if(!doc.leave_transaction_type) set_multiple(dt,dn,{leave_transaction_type:'Allocation'});

}


// Validation For To Date
// ================================================================================================
cur_frm.cscript.to_date = function(doc, cdt, cdn) {
  $c('runserverobj', args={'method':'to_date_validation','docs':compress_doclist([doc])},
    function(r, rt) {
    var doc = locals[cdt][cdn];
    if (r.message) {
      alert("To date cannot be before from date");
      doc.to_date = '';
      refresh_field('to_date');
    }
    }
  ); 
}

// Allocation Type
// ================================================================================================
cur_frm.cscript.allocation_type = function (doc, cdt, cdn){
  doc.no_of_days = '';
  refresh_field('no_of_days');
}
