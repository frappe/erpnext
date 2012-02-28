// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

pscript['onshow_Sales Browser'] = function(){
  wn.require('lib/js/legacy/widgets/tree.js');

	var route = decodeURIComponent(location.hash);
	if(route.indexOf('/')!=-1) {
		var chart_type = route.split('/')[1];
		new SalesBrowser().set_val(chart_type)
		return;
	}

  var parent = $i('tr_body');
  parent.innerHTML = 'Please select your chart: '
  var sel = $a(parent,'select');
  add_sel_options(sel, ['Territory', 'Customer Group', 'Item Group', 'Sales Person'], 'Territory');
  var btn = $btn(parent, 'Go', function() { new SalesBrowser().set_val(sel_val(sel)) }, {marginTop:'8px'});
}

//================================= SalesBrowser Class ======================================
SalesBrowser = function(){
  
  this.make_body = function(){
  
    $i('tr_header').innerHTML = '';
    $i('tr_body').innerHTML = '';
    //make header
    var desc = this.sel;
    var me = this;
    var h = new PageHeader($i('tr_header'),desc);
    h.add_button('New '+this.sel, function() { me.set_dialog(1); }, 0, 'ui-icon-plus', 1);
    h.add_button('Refresh', function() { me.refresh_tree(); }, 0, 'ui-icon-refresh');

    var div_body = $a($i('tr_body'),'div');
    var tr_main_grid = make_table(div_body,1,2,'100%',['60%','40%'],{width: "100%", tableLayout: "fixed", borderCollapse: "collapse", border:"0px", padding:"4px 4px 4px 4px"});
    
    $y($td(tr_main_grid,0,0),{border: "1px solid #dddddd", padding: "8px", width: "60%"});   
    this.tree_area = $a($td(tr_main_grid,0,0),'div');

    $y($td(tr_main_grid,0,1),{border: "1px solid #DDD"});   
    this.detail_area = $a($td(tr_main_grid,0,1),'div');
    
    this.make_tree_body(this.tree_area);  
    this.refresh_tree();
  }
  
  this.set_val = function(b){
    var me = this;
    me.sel = b;  
    me.make_body();
  }
}

//=================================================================================================================================
SalesBrowser.prototype.make_tree_body = function(parent){

  //this.tab2 =make_table(this.wrapper,1,2,'100%',['60%','40%']);
  this.make_tree();
  this.make_rgt_sect();
  
}

//=================================================================================================================================
SalesBrowser.prototype.make_rgt_sect=function(){
  //var d = $a($td(this.tab2,0,1),'div','',{border:'1px solid #000'});

  this.rgt_tab =make_table(this.detail_area,4,1,'','',{padding:"4px",spacing:"4px"});
  this.dtl = $a($td(this.rgt_tab,0,0),'div');
  this.btn = $a($td(this.rgt_tab,1,0),'div','span');
  this.help = $a($td(this.rgt_tab,2,0),'div');
  this.help.innerHTML = "Note: Explore and click on the tree node to see details."

  this.set_btn();
}
//=================================================================================================================================
SalesBrowser.prototype.set_btn = function(){
  var me = this;
  this.edit_btn = $btn(this.btn,'Edit',function(){ me.set_dialog(2); });

  this.trash_btn = $btn(this.btn,'Trash',null);
  this.trash_btn.onclick = function(){
    var check = confirm("Are you sure you want to trash "+me.cur_node.rec.name+" node?");
    
    if(check){
      var arg = [me.cur_node.rec.name, me.sel];
      $c_obj('Sales Browser Control','trash_record',arg.join(','),function(r,rt){      me.refresh_tree();});

    }
  }
}

//=====================================================
SalesBrowser.prototype.set_dialog = function(f){

 
  if(this.sel == 'Territory')
    new MakeDialog('Territory','territory',f,this);            //Territory Dialog
  if(this.sel == 'Customer Group')
    new MakeDialog('Customer Group','customer_group',f,this);  //Customer Group Dialog  
  if(this.sel == 'Item Group')
    new MakeDialog('Item Group','item_group',f,this);   //Item Group Dialog
  if(this.sel == 'Sales Person')
    new MakeDialog('Sales Person','sales_person',f,this);//Sales Person Dialog 
  
}
//=====================================================Make Tree============================================================================
SalesBrowser.prototype.make_tree = function() {
  var me = this;

  this.tree = new Tree(this.tree_area, '100%');
  
  //---------------------------------------------------------------------------------------------------------------------------------
  // on click
  this.tree.std_onclick = function(node) {
      
      me.cur_node = node;
      if(node.rec.name =='All Customer Groups' || node.rec.name =='All Sales Persons' || node.rec.name =='All Item Groups' || node.rec.name =='All Territories'){
        //$di(me.add_btn);

        $dh(me.edit_btn);
        $dh(me.trash_btn);
      }
      else{
        //$di(me.add_btn);
        //if(node.has_children == false)
          //$dh(me.add_btn);

        $di(me.edit_btn);
        $di(me.trash_btn);

      }
      me.make_details();
	  
  }
  //---------------------------------------------------------------------------------------------------------------------------------
  // on expand
  this.tree.std_onexp = function(node) {

    if(node.expanded_once)return;
    $di(node.loading_div);

    var callback = function(r,rt) {

      $dh(node.loading_div);
      var n = me.tree.allnodes[r.message.parent];
      var cl = r.message.cl;

      for(var i=0;i<cl.length;i++) {
        var imgsrc=null;
        var has_children = true;

        if(cl[i].is_group=='No') {
          var imgsrc = 'lib/images/icons/page.png';
          has_children = false;
        }
        var t = me.tree.addNode(n, cl[i].name, imgsrc,me.tree.std_onclick, has_children ? me.tree.std_onexp : null);
        t.rec = cl[i];
        t.parent_account = r.message.parent;
        t.has_children = has_children;
      }

    }
    var arg = [node.rec.name, me.sel];
    $c_obj('Sales Browser Control','get_record_list',arg.join(','),callback);
  }
  
 
}

//=================================================================================================================================
SalesBrowser.prototype.make_details = function(){
  var me = this;
  var callback = function(r,rt){

    me.dtl.innerHTML = "";
    //me.dtl_tab = make_table(me.dtl,3,2,'','',{tableLayout:'fixed',borderCollapse: 'collapse'})
    
    var h = $a(me.dtl,'h3','',{padding:'4px', margin:'0px',backgroundColor:'#EEEEEE',borderBottom:'1px solid #AAAAAA'});
    $(h).html(r.message.name);
    
    var d = $a(me.dtl,'div');
    me.dtl_tab = make_table(me.dtl,3,2,'','',{tableLayout:'fixed',borderCollapse: 'collapse',padding:'4px'})
    $td(me.dtl_tab,0,0).innerHTML="Parent";
    if(r.message.parent != '')
      $td(me.dtl_tab,0,1).innerHTML=": "+r.message.parent;
    else
      $td(me.dtl_tab,0,1).innerHTML=": ----";    
    $td(me.dtl_tab,1,0).innerHTML="Has Child Node";
    $td(me.dtl_tab,1,1).innerHTML=": "+r.message.is_group;
   

    me.open_doc = $a(me.dtl,'div','link_type',{paddingTop:'14px'});
    me.open_doc.innerHTML = "Click here to open "+r.message.name;
    
    me.open_doc.onclick = function(){
      loaddoc(me.sel,r.message.name );
    }
  }

  var arg = [this.cur_node.rec.name, this.sel];
  
  $c_obj('Sales Browser Control','get_record',arg.join(','),callback);

}
//=================================================================================================================================
SalesBrowser.prototype.refresh_tree=function(){

  this.tree_area.innerHTML = '';
  this.dtl.innerHTML = '';  
  this.first_level_node();    //set root
  //hide add, edit, trash buttons
  //$dh(this.add_btn);
  $dh(this.edit_btn);
  $dh(this.trash_btn);
  


}

//=============================== make first level node ================================================
SalesBrowser.prototype.first_level_node = function(){

  var me = this;
  var callback = function(r,rt) {

    var cl = r.message.cl;

    for(var i=0;i<cl.length;i++) {
      var imgsrc=null;
      var has_children = true;

      if(cl[i].is_group=='No') {
        var imgsrc = 'lib/images/icons/page.png';
        has_children = false;
      }
     me.tree_area.innerHTML = ''; 
     if(me.tree) {

        me.tree.innerHTML = '';
        me.tree.body.innerHTML = '';
        
        me.make_tree();
      }

      var t = me.tree.addNode(null, cl[i].name, imgsrc,me.tree.std_onclick, has_children ? me.tree.std_onexp : null);
      t.rec ={};
      t.rec.name = cl[i].name;
      t.has_children = has_children;
    }
  }

  $c_obj('Sales Browser Control','get_fl_node',this.sel,callback);

}

//========================================= Dialog Section ===================================================================
//--------------------------------------------------------------------------------------------------------------------------------
//========================================================================
MakeDialog=function(label,field_name,n,cls_obj){

  var new_head = 'Create A New '+label;

  this.label = label;

  this.lbl_rec = label+' Name';
  this.field_name = field_name;
  this.n = n;
  this.cls_obj=cls_obj;
  //-----------------------------------------------
 
  this.main_dialog = new Dialog(400,300,new_head);      
  this.set_dg_fields();
  this.set_dg_values();
  //-----------------------------------------------
  this.new_main_dialog = this.main_dialog;
  
  this.new_main_dialog.show();

}
//=================================================================================================================================
MakeDialog.prototype.set_dg_fields = function(){

  var bd_lst = [];
  bd_lst.push(['HTML','Heading'],['Data',this.lbl_rec],['Select','Parent'],['Select','Has Child Node']);
  if(this.cls_obj.sel == 'Sales Person')
    bd_lst.push(['HTML','','All nodes are allowed in transaction.']);
  else
    bd_lst.push(['HTML','','Only leaf nodes are allowed in transaction.']);
  if(this.n==1)
    bd_lst.push(['Button','Create']);
  
  if(this.n==2){
    bd_lst.push(['Button','Update']);
    this.set_edit_fields();
  }  

  this.main_dialog.make_body(bd_lst);
  
  //-----------------------------------------------
}


//==================================================================================================================================== 
MakeDialog.prototype.set_edit_fields=function(){
  var me = this;
  var callback = function(r,rt){
    
    me.main_dialog.widgets[me.lbl_rec].value = r.message.name;
    
    add_sel_options(me.main_dialog.widgets['Parent'], r.message.parent_lst,r.message.parent);    
    me.main_dialog.widgets['Has Child Node'].value = r.message.is_group;
  }

  var arg = [this.cls_obj.cur_node.rec.name, this.cls_obj.sel];
  
  $c_obj('Sales Browser Control','get_record',arg.join(','),callback);
}
//======================================= Validation - fields entered or not =================================================
MakeDialog.prototype.validate = function(){

  if(!this.main_dialog.widgets[this.lbl_rec].value) {
      err_msg1 ='Please enter '+this.label +' Name' 
      alert(err_msg1); 
      return 1;
    }
    if(!this.main_dialog.widgets['Parent'].value){
      alert('Please enter Parent Name' );
      return 1;
    }
}
//==================================================================================================================================== 
MakeDialog.prototype.set_dg_values = function(){
  if(this.n==1){
    var me = this;
    var callback = function(r,rt){
      me.main_dialog.widgets[me.lbl_rec].disabled = 0;
      me.main_dialog.widgets['Parent'].disabled = 0;

      add_sel_options(me.main_dialog.widgets['Parent'],r.message);
      //add_sel_options(this.main_dialog.widgets['Parent'], [this.cls_obj.cur_node.rec.name]);
      me.btn_onclick('Create',me.cls_obj);
    }
  
    $c_obj('Sales Browser Control','get_parent_lst',this.cls_obj.sel,callback);

  }  
  if(this.n == 2){
    this.main_dialog.widgets[this.lbl_rec].disabled = 1;
    this.main_dialog.widgets['Parent'].disabled = 0;
    this.btn_onclick('Update');
    this.old_value = sel_val(this.main_dialog.widgets['Parent']);
  }

  add_sel_options(this.main_dialog.widgets['Has Child Node'], ['Yes','No'], 'No');

}

//================================================================================================================================= 
//-----------------------------------------Dialog button onclick event----------------------------------------------
MakeDialog.prototype.btn_onclick=function(btn_name){
  var me = this;
  this.btn_name = btn_name;
  this.main_dialog.widgets[this.btn_name].onclick = function() {
  
    var callback=function(r,rt){
      if(r.message == 'true'){
        me.main_dialog.hide();
      }
      else{
        flag = me.validate();
        if(flag == 1) return;
           
        //---------------------------------------------------------  

        var arg2 = me.make_args();
        
        //create Sales Person -- server to Sales Browser Control
        if(me.btn_name == "Create")
          method_name = "add_node";
        else 
          method_name = "edit_node";       
           
        $c_obj('Sales Browser Control',method_name, docstring(arg2), function(r,rt) { 
          me.main_dialog.widgets[me.lbl_rec].value='';
          me.main_dialog.hide();
          /*if(me.btn_name == "Create"){
            me.cls_obj.cur_node.clear_child_nodes();
            me.cls_obj.dtl.innerHTML = '';  
            me.cls_obj.cur_node.expand();
          }
          else{
            me.cls_obj.refresh_tree();   
          }*/
          me.cls_obj.refresh_tree(); 
        });
      }
    }
    var arg1 = {'node_title':me.cls_obj.sel,'is_group':sel_val(me.main_dialog.widgets['Has Child Node']),'lft':0,'rgt':0,'nm':me.main_dialog.widgets[me.lbl_rec].value,'parent_nm':sel_val(me.main_dialog.widgets['Parent']),'action':me.btn_name};
    $c_obj('Sales Browser Control','mvalidate',docstring(arg1),callback);
  }
}
//=================================================================================================================================

MakeDialog.prototype.make_args = function(){
  var args ={};   //args making
  var nt = this.cls_obj.sel;
  var nm = this.main_dialog.widgets[this.lbl_rec].value;
  var pnm = sel_val(this.main_dialog.widgets['Parent']);
  var grp = sel_val(this.main_dialog.widgets['Has Child Node']);

  if(this.n==1)
    var old_prt ='';
  else if(this.n==2){
    if(this.old_value == sel_val(this.main_dialog.widgets['Parent']))
      var old_prt = '';
    else
      var old_prt = this.old_value;
  }
  
  if(this.cls_obj.sel == 'Territory')
    return {'node_title':nt,'territory_name':nm,'parent_territory':pnm,'is_group':grp,'old_parent':old_prt}

  else if(this.cls_obj.sel == 'Customer Group')
    return {'node_title':nt,'customer_group_name':nm,'parent_customer_group':pnm,'is_group':grp,'old_parent':old_prt}

  else if(this.cls_obj.sel == 'Item Group')
    return {'node_title':nt,'item_group_name':nm,'parent_item_group':pnm,'is_group':grp,'old_parent':old_prt}

  else if(this.cls_obj.sel == 'Sales Person')
    return {'node_title':nt,'sales_person_name':nm,'parent_sales_person':pnm,'is_group':grp,'old_parent':old_prt}

}
