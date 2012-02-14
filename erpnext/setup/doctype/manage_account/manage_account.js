// Validate
cur_frm.cscript.validate = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt, cdn), 'get_defaults', '', function(r, rt){
    sys_defaults = r.message;
  });
}