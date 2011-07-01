pscript['onload_Sales Dashboard'] = function() {
  var h = new PageHeader('pt_header','Sales Dashboard');
  
  pscript.make_filters(); 
  $dh(pscript.mnt_div);
  $dh(pscript.mnt_div1);
  //pscript.dx_axis = [];
  
  if($.jqplot) pscript.all_onchnge();
  else
    // import the library
    $c_js('jquery/jquery.jqplot.min.js', pscript.all_onchnge);
}
//=======================================================================
pscript.make_filters = function(){
  this.tab = make_table('pt_filters', 2, 4, '800px', ['200px','200px','200px','200px'], {padding: '2px'});
  pscript.fiscal_year();
  pscript.report_type();
  pscript.item_grp();
  pscript.month_lst();
}
//=======================================================================

pscript.fiscal_year=function(){
  var me = this;
  $td(this.tab,0,0).innerHTML = "Select Year";
  this.sel_fy = $a($td(this.tab,1,0), 'select', null, {width:'120px'});
  $c_obj('Plot Control', 'get_fiscal_year', '', function(r,rt){
    if(r.message)  fy_lst = r.message;
    else  fy_lst = [];
    empty_select(me.sel_fy);
    add_sel_options(me.sel_fy,fy_lst);
    me.sel_fy.value = sys_defaults.fiscal_year;
  });
  
}

//=======================================================================

pscript.report_type=function(){
  $td(this.tab,0,1).innerHTML = "Select Report";
  this.sel_rpt = $a($td(this.tab,1,1), 'select', null, {width:'120px'});
  rpt_lst = ['Monthly','Weekly']; 
  add_sel_options(this.sel_rpt,rpt_lst);
}

//=======================================================================

pscript.item_grp=function(){
  var me = this;
  
  $td(this.tab,0,2).innerHTML = "Select Item Group";
  
  this.sel_grp = $a($td(this.tab,1,2), 'select', null, {width:'120px'});
  $c_obj('Plot Control', 'get_item_groups', '', function(r,rt){
    
    itg_lst = r.message;
    itg_lst.push('All');
    
    empty_select(me.sel_grp);
    add_sel_options(me.sel_grp, itg_lst.reverse());
  });
  
}

//=======================================================================

pscript.month_lst=function(){
  pscript.mnt_div1 = $a($td(this.tab,0,3));
  pscript.mnt_div1.innerHTML = "Select Month";
  pscript.mnt_div = $a($td(this.tab,1,3));
  this.sel_mnt = $a(pscript.mnt_div, 'select', null, {width:'120px'});
  mnt_lst = ['All','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; 
  add_sel_options(this.sel_mnt,mnt_lst);
}

//=======================================================================
pscript.all_onchnge = function(){
  pscript.report_change();
  pscript.fiscal_year_onchnage();
  pscript.month_onchange();
  pscript.item_grp_onchange();
  pscript.monthly();
}

//=======================================================================
pscript.report_change = function(){
  var me = this;
  this.sel_rpt.onchange = function(){
    
    $dh(pscript.mnt_div);
    $dh(pscript.mnt_div1);
    if(me.sel_rpt.value == 'Monthly'){
      
      pscript.monthly();
    }
    
    else if(me.sel_rpt.value == 'Weekly'){
      $ds(pscript.mnt_div); 
      $ds(pscript.mnt_div1);
      me.sel_mnt.value = 'All';
      pscript.get_x_dates();

    }
    
    else{
      me.sel_mnt.value = 'All';
      $i('plot_test').innerHTML = '';
    }
  }

}
//=======================================================================
pscript.fiscal_year_onchnage = function(){
  var me = this;
  this.sel_fy.onchange = function(){ 

    if(me.sel_rpt.value == 'Monthly'){
      
      me.sel_mnt.value = 'All';
      $dh(pscript.mnt_div); 
      $dh(pscript.mnt_div1);     
      pscript.monthly();
    }
    else if(me.sel_rpt.value == 'Weekly' && me.sel_mnt.value){
    
      pscript.get_x_dates();
      
    }
    
    else{
      me.sel_mnt.value = 'All';
      me.sel_rpt.value == '';
      $i('plot_test').innerHTML = '';
      
    }
  }

}
//=======================================================================
pscript.month_onchange = function(){
  this.sel_mnt.onchange = function(){
    pscript.get_x_dates();
    
  }
}
//=======================================================================

pscript.item_grp_onchange=function(){
  var me = this;
  this.sel_grp.onchange = function(){
  
    if(me.sel_rpt.value == 'Monthly'){
      
      me.sel_mnt.value = 'All';
      $dh(pscript.mnt_div); 
      $dh(pscript.mnt_div1);     
      pscript.monthly();
    }
    else if(me.sel_rpt.value == 'Weekly' && me.sel_mnt.value){
    
      pscript.get_x_dates();
      
    }
    
    else{
      me.sel_mnt.value = 'All';
      me.sel_rpt.value == '';
      $i('plot_test').innerHTML = '';
      
    }
  }
    
  }

//=======================================================================

pscript.get_x_dates=function(){
  
  if(this.sel_mnt.value !='All'){
    
    pscript.weekly();
  }
  else{ 
    
    $c_obj('Plot Control','yr_wk_dates',this.sel_fy.value,
      function(r,rt){
        
        pscript.dx_axis = r.message[0];
        
        pscript.x_axis = r.message[1];
        
        pscript.yearly();
      }
    );
    
  }
}

//=======================================================================
pscript.draw_graph1 = function(x_axis,line1,t) {
  
  t = t + " ("+sys_defaults.currency +")";
  $i('plot_test').innerHTML = '';
  // div plot_test contains the container div
  $.jqplot('plot_test',  [line1],{
    title:t,
    axesDefaults: {
      min:0  
    },
    
    axes:{ 
      xaxis:{ticks:x_axis}
    }
  });
}
//=======================================================================
pscript.monthly = function(){
  var callback = function(r,rt){
    x_axis = r.message.x_axis;
    msg_data = r.message.msg_data; 
    
    var line1 = [];
    for(var i=0; i<x_axis.length;i++){
      var f =0
      for(var j=0; j<msg_data.length;j++){
        if(msg_data[j] && x_axis[i]){
          if(x_axis[i][1] == msg_data[j][1])
          { 
            line1.push([i+1,flt(msg_data[j][0])]);
            f = 1
          }
          
        }
      }
      if(f == 0){
        line1.push([i+1,0]);
      }
    }
    pscript.draw_graph1(x_axis,line1,'Monthly Sales');
  }
  var val2 = '';
  if(this.sel_grp.value != 'All') val2 = this.sel_grp.value;
  $c_obj('Plot Control','get_monthwise_amount',[this.sel_fy.value,val2],callback);
}

//=======================================================================

pscript.weekly = function(){
  
  var callback = function(r,rt){
    
    x_axis =[[1,'Week1'],[2,'Week2'],[3,'Week3'],[4,'Week4'],[5,'Week5'],[6,'Week6']];
    var line1 = [];
    for(var i=0; i<x_axis.length;i++){
      var f = 0;
      for(var j=0; j<r.message.length;j++){
        if(r.message[j]){
          if(r.message[j][1] == x_axis[i][1]){ line1.push([i+1,flt(r.message[j][0])]); f=1;}}
      }
      if(f == 0){
        line1.push([i+1,0]);
      }
    }
    
    pscript.draw_graph1(x_axis,line1,'Weekly Sales');
  }
  dict_mnt={'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12};
  var val3 = '';
  if(this.sel_grp.value != 'All') val3 = this.sel_grp.value;
  $c_obj('Plot Control','get_weekwise_amount',[dict_mnt[this.sel_mnt.value],this.sel_fy.value,val3],callback);
}

//=======================================================================

pscript.yearly = function(){
  
  var callback = function(r,rt){
      
    var line1 = [];
    for(var i=0; i<pscript.x_axis.length;i++){
      var f = 0
      for(var j=0; j<r.message.length;j++){
        if(r.message[j]){

          if((r.message[j][1] == pscript.x_axis[i][1]) && (r.message[j][2] == pscript.x_axis[i][2])){ line1.push([pscript.x_axis[i][0],r.message[j][0]]); break; f =1;}
      }
      }
      if(f == 0){
        line1.push([pscript.x_axis[i][0],0]);
      }
    }
    
    pscript.draw_graph1(pscript.dx_axis,line1,'Year-Weekly Sales');
  }
  var val2 = '';
  if(this.sel_grp.value != 'All') val2 = this.sel_grp.value;
  
  
  $c_obj('Plot Control','get_year_weekwise_amount',[this.sel_fy.value,val2],callback);
} 