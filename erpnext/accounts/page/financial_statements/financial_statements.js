pscript['onload_Financial Statements'] = function() {
	
	// header and toolbar
	var h = new PageHeader('fs_header','Financial Statements','Profit & Loss and Balance Sheet Builder across multiple years');
	//$y(h.toolbar_area,{padding:'8px'});
	
	var dv = $a(h.toolbar_area,'div','',{margin:'4px 0px'});
	
	var t = make_table(dv,1,4,'640px', [], {padding:'4px', width:'160px'});
	
	var sel = $a($td(t,0,0),'select','',{width:'160px'});
	sel.id = 'stmt_type';
	
	var sel = $a($td(t,0,1),'select','',{width:'160px'});
	sel.id = 'stmt_company';
	
	var sel = $a($td(t,0,2),'select','',{width:'160px'});
	sel.id = 'stmt_period';

	var sel = $a($td(t,0,3),'select','',{width:'160px'});
	sel.id = 'stmt_fiscal_year';

	h.add_button('Create',function(){ pscript.stmt_new(); },0,'ui-icon-document');
	h.add_button('Print', function(){ _p.go($i('print_html').innerHTML); }, 0, 'ui-icon-print');
/*	
	var btn = $a($td(t,1,0),'button');
	btn.onclick = function(){ pscript.stmt_new(); }
	btn.innerHTML = 'Create';
	
	var btn = $a($td(t,1,1),'button');
	btn.onclick = function(){ alert('print'); }
	btn.innerHTML = 'Print';

  //Button to create new
  var btn = $a('stmt_new', 'button');
  btn.onclick = function() { pscript.stmt_new(); }
  btn.innerHTML = 'Create';*/

  // select for statement
  add_sel_options($i('stmt_type'), ['Select Statement...','Balance Sheet','Profit & Loss']);

  // select for companies
  add_sel_options($i('stmt_company'), ['Loading Companies...']);


  // load companies
  $c_obj('MIS Control','get_comp','', function(r,rt) {    
    // company
    empty_select($i('stmt_company'));
    add_sel_options($i('stmt_company'), add_lists(['Select Company...'], r.message.company), 'Select Company...');


    // period
    empty_select($i('stmt_period'));
    //add_sel_options($i('stmt_period'), add_lists(['Select Period...'], r.message.period), 'Select period...');
    add_sel_options($i('stmt_period'), add_lists(['Select Period...'], ['Annual', 'Quarterly', 'Monthly']), 'Select period...');
    
    // fiscal-year
    empty_select($i('stmt_fiscal_year'));
    add_sel_options($i('stmt_fiscal_year'), add_lists(['Select Year...'], r.message.fiscal_year), 'Select fiscal year...');
  });

}

pscript.stmt_new = function(stmt,company_name,level,period,year) {
    
  $i('stmt_tree').innerHTML = 'Refreshing....';
  $i('stmt_tree').style.display = 'block';
  
  var arg = {
  	statement:sel_val($i('stmt_type'))
  	,company:sel_val($i('stmt_company'))
  	,period:sel_val($i('stmt_period'))
  	,year:sel_val($i('stmt_fiscal_year'))
  }

  $c_obj('MIS Control', 'get_statement', docstring(arg), function(r,rt) {
      var nl = r.message;
      var t = $i('stmt_tree');
      var stmt_type = sel_val($i('stmt_type'));
      t.innerHTML = '';
      var tab = $a($a(t, 'div'),'table','stmt_table');
      tab.style.tableLayout = 'fixed';
      tab.style.width = '100%';
      
      $i('stmt_title1').innerHTML = sel_val($i('stmt_company'));
      $i('stmt_title2').innerHTML = sel_val($i('stmt_type')) + ' - ' +  sel_val($i('stmt_fiscal_year'));
      for(i=0;i<nl.length;i++) {
        tab.insertRow(i);
        
        tab.rows[i].style.height = '20px';
        
        // heads
        var per = tab.rows[i].insertCell(0);
 //       var acc_width = (sel_val($i('stmt_period'))=='Monthly')? 12 : 20;
 //       per.style.width = acc_width+'%';
        per.style.width = '150px';
        per.innerHTML = pscript.space_reqd(nl[i][0])+cstr(nl[i][1]);
        per.className = 'stmt_level' + nl[i][0];
        
        // Make Title Bold
        if(nl[i][0] == 0 || nl[i][0] == 1 || nl[i][0] == 4){
          per.innerHTML = (pscript.space_reqd(nl[i][0])+cstr(nl[i][1])+'').bold();
          per.style.fontSize = '12px';
        }

        for(j=2;j<nl[i].length;j++){
          var per = tab.rows[i].insertCell(j-1);
//          per.style.width = (100-acc_width)/(nl[i].length-2) +'%';
          per.style.width = '150px';
          per.style.textAlign = "right";
          per.className = 'stmt_level' + nl[i][0];
          if (i==0) {
            per.style.fontSize = '14px';
            per.style.textAlign = "right";
          }
          if (nl[i][0]==5) {
            if(flt(nl[i][j])<0.0) per.style.color = "RED";
            else per.style.color = "GREEN";
          }
          if(nl[i][0] != 0){
            if(nl[i][j]) {
              if (i==0) per.innerHTML = (nl[i][j]+'').bold();
              else if(nl[i][0] == 1 || nl[i][0] == 4) per.innerHTML = (cstr(fmt_money(nl[i][j]))+'').bold();
              else per.innerHTML = fmt_money(nl[i][j])
            } else
              per.innerHTML = '-';
          }
        }
      }
    
  });	
  $i('stmt_tree').style.display = 'block';  
}

//printing statement
pscript.print_statement = function(){
  print_go($i('print_html').innerHTML);
}

//determine space to be given
pscript.space_reqd = function(val){
  if(val == 1) return '  ';
  else if(val == 2) return '     ';
  else if(val == 3) return '        ';
  else return '';  
}