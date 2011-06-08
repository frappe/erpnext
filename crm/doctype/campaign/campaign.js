$import(Tips Common)

//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
  cur_frm.cscript.get_tips(doc, cdt, cdn);
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
  cur_frm.cscript.get_tips(doc, cdt, cdn);
}