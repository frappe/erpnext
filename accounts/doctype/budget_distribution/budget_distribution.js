// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(doc.__islocal){
    var callback1 = function(r,rt){
      refresh_field('budget_distribution_details');
    }
    
    return $c('runserverobj',args={'method' : 'get_months', 'docs' : 
		wn.model.compress(make_doclist(doc.doctype, doc.name))},callback1);
  }
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
	cur_frm.toggle_display('distribution_id', doc.__islocal);
}