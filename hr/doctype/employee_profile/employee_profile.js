cur_frm.cscript.onload = function(doc, cdt, cdn){
  $c('runserverobj', args={'method':'cal_tot_exp','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
function(r, rt) { refresh_many(['year','months']); });
}

//===========================================================

cur_frm.cscript.employee = function(doc, cdt, cdn){
  $c('runserverobj', args={'method':'get_doj','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
function(r, rt) { refresh_many(['employee_name','date_of_joining']); });
}

//===========================================================

cur_frm.cscript.country1 = function(doc, cdt, cdn) {
  var mydoc=doc;
  $c('runserverobj', args={'method':'check_state','arg':doc.country1, 'docs':compress_doclist([doc])},
    function(r,rt){

      if(r.message) {
        var doc = locals[mydoc.doctype][mydoc.name];
        doc.state1 = '';
        get_field(doc.doctype, 'state1' , doc.name).options = r.message;
        refresh_field('state1');
      }
    }  
  );
}

//===========================================================
cur_frm.cscript.country2 = function(doc, cdt, cdn) {
  var mydoc=doc;
  $c('runserverobj', args={'method':'check_state', 'arg':doc.country2,'docs':compress_doclist([doc])},
    function(r,rt){

      if(r.message) {
        var doc = locals[mydoc.doctype][mydoc.name];
        doc.state2 = '';
        get_field(doc.doctype, 'state2' , doc.name).options = r.message;
        refresh_field('state2');
      }
    }  
  );
}