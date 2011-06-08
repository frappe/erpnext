cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  if(doc.send_to == 'Customer Group')
    unhide_field('customer_group_name');
  else
    hide_field('customer_group_name');
}

cur_frm.cscript.send_to = cur_frm.cscript.refresh;