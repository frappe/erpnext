cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(doc.__islocal){
    var callback1 = function(r,rt){
      refresh_field('budget_distribution_details');
    }
    
    $c('runserverobj',args={'method' : 'get_months', 'docs' : compress_doclist([doc])},callback1);
  }
}