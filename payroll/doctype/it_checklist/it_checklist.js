cur_frm.cscript.onload=function(doc,cdt,cdn){

  if(doc.employee && doc.__islocal ==1){
    cur_frm.cscript.employee(doc,cdt,cdn);
  }
  if(doc.rent_acc == "Yes") unhide_field('ann_rent');
}

// when user select an employee corresponding basic, gross income and pf is set.
cur_frm.cscript.employee = function(doc,cdt,cdn){
  var mydoc=doc;
  $c('runserverobj', args={'method':'set_values','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
      function(r, rt) {
        var doc = locals[mydoc.doctype][mydoc.name];
       
        if(r.message){
        doc.hra_count = r.message;
        refresh_field('hra_count')
        }
        refresh_many(['employee','employee_name','basic','gross_income','pf']);
        
      }
    );
}

cur_frm.fields_dict['employee'].get_query = function(doc,dt,dn) {
   return 'SELECT tabEmployee.name FROM tabEmployee WHERE tabEmployee.status = "Active" AND tabEmployee.docstatus !=2 AND tabEmployee.name LIKE "%s" ORDER BY tabEmployee.name DESC LIMIT 50'
}

//---------------------------------------------------------
//if rent accomodation is yes then unhide annual rent paid else unhide.
cur_frm.cscript.rent_acc = function(doc,cdt,cdn){
  doc.ann_rent = 0
  if(doc.rent_acc == 'Yes')
    unhide_field('ann_rent');
  else
    hide_field('ann_rent');
  refresh_field('ann_rent');
}

//---------------------------------------------------------
//On done button click check for all values filled or not, and accordingly add records in child tables

cur_frm.cscript['Done']=function(doc,cdt,cdn){
  var mydoc=doc;

  if(doc.employee && doc.fiscal_year && doc.metro && doc.sr_citizen && doc.part_sr_citizen && doc.basic && doc.gross_income){
    if((doc.rent_acc == "Yes" && doc.ann_rent) || (doc.rent_acc == "No")){
        
        $c('runserverobj', args={'method':'set_tables', 'arg': doc.hra_count, 'docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
        function(r, rt) {
          var doc = locals[mydoc.doctype][mydoc.name];
          refresh_many(['edu_cess','tax_tot_income','net_tot_tax_income','tax_per_month','applicable_from','rem_months']);
          refresh_many(['exe_declaration_details','oth_inc_decl_details','chap_via_decl_details','invest_80_decl_details']);
          }
        );
      
    }
    
    else if(doc.rent_acc == "Yes" && !doc.ann_rent)
      alert("Please enter annual rent");
  }
  else
    alert("please fill up all data");
}


//---------------------------------------------------------
//change event of actual amount1 field (exemption declaration detail table) : check for values of actual amount & maximum limit, and accordingly do actions.
cur_frm.cscript.actual_amount1= function(doc,cdt,cdn){
  
  var cl = getchildren('Declaration Detail', doc.name, 'exe_declaration_details');
  for(var c=0; c<cl.length; c++) {
    if(cl[c].name == cdn){
      if(((flt(cl[c].actual_amount1) <= flt(cl[c].max_limit1)) || (flt(cl[c].actual_amount1) == 0)) || ((cl[c].particulars1 != 'House Rent Allowance') && (flt(cl[c].max_limit1) == 0.00)) || ((cl[c].particulars1 == 'House Rent Allowance') && (flt(cl[c].max_limit1) != 0.00) && (flt(cl[c].actual_amount1) <= flt(cl[c].max_limit1)))){
        cl[c].eligible_amount1 =cl[c].actual_amount1
        cl[c].modified_amount1 =cl[c].actual_amount1
      } 
      else {
        
        cl[c].eligible_amount1 =cl[c].max_limit1
        cl[c].modified_amount1 =cl[c].max_limit1
      } 
     
      refresh_field('exe_declaration_details'); 
    }
  }
 
}



//---------------------------------------------------------
////change event of actual amount2 field (Other Income declaration detail table) : check for values of actual amount & maximum limit, and accordingly do actions.
cur_frm.cscript.actual_amount2= function(doc,cdt,cdn){
  var cl = getchildren('Other Income Detail', doc.name, 'oth_inc_decl_details');
  for(var c=0; c<cl.length; c++) {
    if(cl[c].name == cdn){
      if((flt(cl[c].actual_amount2) <= flt(cl[c].max_limit2)) || flt((cl[c].actual_amount2) ==0) || !(cl[c].max_limit2)){
        cl[c].eligible_amount2 =cl[c].actual_amount2
        cl[c].modified_amount2 =cl[c].actual_amount2
          
      } 
      else {
        cl[c].eligible_amount2 =cl[c].max_limit2
        cl[c].modified_amount2 =cl[c].max_limit2
      } 
    
    
      refresh_field('oth_inc_decl_details');
    }
  }
}

//---------------------------------------------------------
//change event of actual amount3 field (Chapter VI A declaration detail table) : check for values of actual amount & maximum limit, and accordingly do actions.
cur_frm.cscript.actual_amount3= function(doc,cdt,cdn){
  

  var cl = getchildren('Chapter VI A Detail', doc.name, 'chap_via_decl_details');
  for(var c=0; c<cl.length; c++) {
    if(cl[c].name == cdn){
      if((flt(cl[c].actual_amount3) <= flt(cl[c].max_limit3)) || flt((cl[c].actual_amount3) ==0) || !(cl[c].max_limit3)){
        cl[c].eligible_amount3 =cl[c].actual_amount3
        cl[c].modified_amount3 =cl[c].actual_amount3
          
      } 
      else {
        cl[c].eligible_amount3 =cl[c].max_limit3
        cl[c].modified_amount3 =cl[c].max_limit3
      } 
    
      refresh_field('chap_via_decl_details');
    }
  }
}

//---------------------------------------------------------
//change event of actual amount4 field (Invest 80 declaration detail table) : check for values of actual amount & maximum limit, and accordingly do actions.
cur_frm.cscript.actual_amount4= function(doc,cdt,cdn){
  
  var cl = getchildren('Invest 80 Declaration Detail', doc.name, 'invest_80_decl_details');
  for(var c=0; c<cl.length; c++) {
    if(cl[c].name == cdn){
      if((flt(cl[c].actual_amount4) <= flt(cl[c].max_limit4)) || flt((cl[c].actual_amount4) ==0) || !(cl[c].max_limit4)){
        cl[c].eligible_amount4 =cl[c].actual_amount4
        cl[c].modified_amount4 =cl[c].actual_amount4
          
      } 
      else {
        cl[c].eligible_amount4 =cl[c].max_limit4
        cl[c].modified_amount4 =cl[c].max_limit4
      } 
   
      refresh_field('invest_80_decl_details');
    }
  }  
}
cur_frm.cscript.refresh=function(doc,cdt,cdn){

}
