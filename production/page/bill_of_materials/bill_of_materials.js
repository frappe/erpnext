pscript['onload_Bill of Materials'] = function() {
	
	// header and toolbar
	var h = new PageHeader('bom_header','Bill of Materials','BOM gives the breakdown of cost for product');
	
	var dv = $a(h.toolbar_area,'div','',{margin:'4px 0px'});
	
	var tbl = make_table(dv, 1,3,'480px',[],{padding:'4px', width:'160px'});
	
	var sel = $a($td(tbl,0,0),'select','',{width:'160px'});
	sel.id = 'bom_item_group';
	
	var sel = $a($td(tbl,0,1),'select','',{width:'160px'});
	sel.id = 'bom_item_code'; sel.innerHTML = 'Select Item Code...'; sel.disabled = 1;
	
	var sel = $a($td(tbl,0,2),'select','',{width:'160px'});
	sel.id = 'bom_bom_no'; sel.innerHTML = 'Select Bom No...'; sel.disabled = 1;
	
	h.add_button('Calculate Cost', function(){ pscript.bom_calculate_cost(pscript.bom_no); },1,'ui-icon-calculator');
	h.add_button('Refresh', function(){ pscript.bom_refresh(); },0,'ui-icon-refresh');
        h.add_button('Collapse All', function(){pscript.collapse_all();},0,'');
	
  // select for Item Group
    //$i('bom_item_group').style.width = '180px';
   // $i('bom_item_code').style.width = '110px';
   // $i('bom_bom_no').style.width = '150px';
    $i('bom_tree').innerHTML = 'Please Select Item Group';
    add_sel_options($i('bom_item_group'), ['Loading ...    ']);

    $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'get_item_group'}, function(r,rt) {
      pscript.item_group = r.message.split('~~~');
      empty_select($i('bom_item_group'));
//      add_sel_options($i('bom_item_group'), add_lists([' '], pscript.item_group), ' ');
      add_sel_options($i('bom_item_group'), add_lists(['Select Item Group...'], pscript.item_group), 'Select Item Group...');
      $i('bom_item_group').onchange = function() {
		
         //$i('bom_item_code').innerHTML = '';
        // $i('bom_bom_no').innerHTML = '';
         $i('bom_head_op').innerHTML = '';
         $i('bom_head_it').innerHTML = '';
         $i('bom_tree').innerHTML = 'Please Select Item Code';
         pscript.bom_select_item_code(sel_val(this)); 
      }
    });	
}

pscript.bom_select_item_code = function(item_group) {

  //select for Item Code	

    add_sel_options($i('bom_item_code'), ['Loading ... ']);

    $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'get_item_code', 'arg':item_group}, function(r,rt) {
      pscript.item_code = r.message.split('~~~');
      empty_select($i('bom_item_code'));
      add_sel_options($i('bom_item_code'), add_lists(['Select Item Code...'], pscript.item_code), 'Select Item Code...');
	  if(sel_val($i('bom_item_code')) == 'Select Item Group...'){
		$i('bom_item_code').disabled = 1;
		$i('bom_bom_no').disabled = 1;
	  }
	  else{ $i('bom_item_code').disabled = 0; }
	  
      $i('bom_item_code').onchange = function() {
        // $i('bom_bom_no').innerHTML = '';
         $i('bom_head_op').innerHTML = '';
         $i('bom_head_it').innerHTML = '';
         $i('bom_tree').innerHTML = 'Please Select BOM NO.'; 
         pscript.bom_select_bom_no(sel_val(this));
      }
    });	
  
}

pscript.bom_select_bom_no = function(item_code) {

  //select for BOM NO
    
    add_sel_options($i('bom_bom_no'), ['Loading ...     ']);
	
    $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'get_bom_no', 'arg':item_code}, function(r,rt) {
      var bom_list = r.message.split('~~~');
      empty_select($i('bom_bom_no'));
	  empty_select($i('bom_bom_no'));
      add_sel_options($i('bom_bom_no'), add_lists(['Select Bom No...'], bom_list), 'Select Bom No...');
	  if(sel_val($i('bom_item_code')) == 'Select Item Code...'){
		$i('bom_bom_no').disabled = 1;
	  }
	  else{
		$i('bom_bom_no').disabled = 0;
	  }
	  
      $i('bom_bom_no').onchange = function() { 
         $i('bom_head_op').innerHTML = '';
         $i('bom_head_it').innerHTML = '';
         $i('bom_tree').innerHTML = 'Loading...';
         pscript.show_bom(); }
    });	
}

// Refresh Function
pscript.bom_refresh = function() {
  $i('bom_head_op').innerHTML = '';
  $i('bom_head_it').innerHTML = '';
  $i('bom_tree').innerHTML = 'Refreshing....';
  pscript.show_bom();
}

//Calculate Cost Function
pscript.bom_calculate_cost = function() {
  $i('bom_head_op').innerHTML = '';
  $i('bom_head_it').innerHTML = '';
  $i('bom_tree').innerHTML = ' Calculating Cost...';
  $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'calculate_cost', 'arg':pscript.bom_no}, function(r,rt) {
      var calculated = r.message;
      if (calculated == 'calculated') {pscript.show_bom();}
      else  {$i('bom_tree').innerHTML = "Sorry it's taking too long try next time....";}
  });	
}

pscript.collapse_all = function(){
  alert("In");
  pscript.bom_tree.collapseall()
}

pscript.show_bom = function () {
  pscript.item_code = $i('bom_item_code').value;
  pscript.bom_no = $i('bom_bom_no').value;
 // $i('bom_refresh').innerHTML = '';
  //$i('bom_refresh').innerHTML = "<input type='button' value='Refresh' onClick='javascript:pscript.bom_refresh()' />";
  //$i('bom_calculate_cost').innerHTML = "<input type='button' value='Calculate Cost' onClick='javascript:pscript.bom_calculate_cost(pscript.bom_no)' />";
  if (pscript.item_code == "") {
    alert("Please Enter Item Code");
    return;
  }
  if (pscript.bom_no == "") {
    alert("Please Enter BOM No");
    return;
  }
  $ds('bom_head_op');
  $ds('bom_head_it');
  $ds('bom_tree');
  pscript.bom_onexp = function(node) {
    //alert("Server Call")
    if(!node.expanded_once) {
      $ds(node.loading_div);
      if (!node.is_item){
        // We will get List Of Items and BOM for particular Operation
        data = "{'op_no':'" + node.text[1] +"','bom_no':'" + node.text[3] +"'}";
        $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'get_item_bom', 'arg':data}, 
        function(r,rt) {
          $dh(node.loading_div);
          var nl = r.message;
          for(var i=0; i<nl.length; i++) {
            if (nl[i][8] == 1) {
              pscript.bom_tree.addNode(node,$i('bom_head_op'), nl[i], 'images/icons/box.png', null, null);
            }
            else {
              pscript.bom_tree.addNode(node,$i('bom_head_op'), nl[i], 'images/icons/package.png', null, pscript.bom_onexp);
            }
         }
        });
      } else {
        //alert("bom_no:%s"%node.text[2])
        //We will get List Of Operations for particular Item and BOM
        $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'get_operations', 'arg':node.text[3]},
          function(r,rt) {
            $dh(node.loading_div);
            var nl = r.message;
            for(var i=0; i<nl.length; i++) {
              pscript.bom_tree.addNode(node, $i('bom_head_op'), nl[i], 'images/icons/folder.png', null, pscript.bom_onexp);
            }
          }
        );
      }
    }
  }
  // First this function will execute and we will get list of operations
  $c('runserverobj', args={'doctype':'BOM Control', 'docname':'BOM Control', 'method':'get_operations', 'arg':pscript.bom_no}, function(r,rt) {
    var nl = r.message;
    
    $i('bom_tree').innerHTML = '';
    var t = new Tree($i('bom_tree'),$i('bom_head_op'),$i('bom_head_it'));

    pscript.bom_tree = t;
    pscript.bom_curnode = null;

    for(var i=0; i<nl.length; i++) {
      t.addNode(null, $i('bom_head_op'), nl[i], 'images/icons/folder.png', null, pscript.bom_onexp);
    }
  });    
}


//
// Tree
//

function Tree(parent,head_op,head_it) {
  this.container = parent;
  this.heading = head_op;
  this.nodes = {};
  this.all_nodes = [];
  
  var me = this;
  
  this.body = $a(parent, 'div');
  this.hopbody = $a(head_op, 'div');
  this.hitbody = $a(head_it, 'div');

  // columns
  this.col_details = [
     ['340px','Opn No', 'Opn Descr','Item Code', 'Description',1,2]
    ,['150px','BOM' , 'BOM', 3]
    ,['80px', 'Workstn', 'Qty', 4]
    ,['45px', 'Hr Rate','Stock UOM',5]
    ,['45px', 'Time','Scrap',6]
    ,['50px', 'Mat Cost','Rate',7]
    ,['45px', 'Op Cost','',8]
    ,['50px', 'Tot Cost','',9]
    ,['25px', 'Refresh']
  ]
  
  // Operation  header
  this.hopbody_tab = $a(this.hopbody, 'table');
  $y(this.hopbody_tab, {borderCollapse:'collapse', tableLayout:'fixed'})
  
  var r0 = this.hopbody_tab.insertRow(0);
  for(var i=0; i<this.col_details.length; i++) {
    var c = r0.insertCell(i);
    c.style.width = this.col_details[i][0];
    c.style.padding = '2px';
    c.style.border = '1px solid #DDD';
   if (i > 0 && this.col_details[i][1] != 'Refresh') c.innerHTML = this.col_details[i][1];
  }
  this.hopbody_label = $a(r0.cells[0], 'div');
  var hopbody_nodetab = $a(this.hopbody_label, 'table');
  $y(hopbody_nodetab, {borderCollapse:'collapse', tableLayout:'fixed'})
  
  var r0 = hopbody_nodetab.insertRow(0);
  var c = r0.insertCell(0); c.style.width = '16px';  
  var c = r0.insertCell(1); c.style.width = '20px'; c.innerHTML = "<img src='images/icons/wrench.png' />";
  var c = r0.insertCell(2); c.style.width = '80px'; c.innerHTML = this.col_details[0][1];
  l=340-116;
  var c = r0.insertCell(3); c.style.width = l+'px'; c.innerHTML = this.col_details[0][2];
  
  // Item Header
  this.hitbody_tab = $a(this.hitbody, 'table');
  $y(this.hitbody_tab, {borderCollapse:'collapse', tableLayout:'fixed'})
  
  var r0 = this.hitbody_tab.insertRow(0);
  for(var i=0; i<this.col_details.length; i++) {
    var c = r0.insertCell(i);
    c.style.width = this.col_details[i][0];
    c.style.padding = '2px';
    c.style.border = '1px solid #DDD';
	if (i > 0 && this.col_details[i][1] != 'Refresh') c.innerHTML = this.col_details[i][2];
  }
  this.hitbody_label = $a(r0.cells[0], 'div');
  var hitbody_nodetab = $a(this.hitbody_label, 'table');
  $y(hitbody_nodetab, {borderCollapse:'collapse', tableLayout:'fixed'})
  
  var r0 = hitbody_nodetab.insertRow(0);
  var c = r0.insertCell(0); c.style.width = '16px'; 
  var c = r0.insertCell(1); c.style.width = '20px'; c.innerHTML = "<img src='images/icons/package.png' />";
  var c = r0.insertCell(2); c.style.width = '100px'; c.innerHTML = this.col_details[0][3];
  l=350-136;
  var c = r0.insertCell(3); c.style.width = l+'px'; c.innerHTML = this.col_details[0][4];
  
  this.addNode = function(parent, head_op, label, imagesrc, onclick, onexpand) {
    var t = new TreeNode(me, parent, head_op, label, imagesrc, onclick, onexpand);
   	if(!parent) {
      me.nodes[label]=t; // add to roots
    } else {
      parent.nodes[label] = t; // add to the node
    }
    
    this.all_nodes.push(t);
		
    // note: this will only be for groups
    if(onexpand)t.create_expimage();
    t.expanded_once = false;

    return t;
    
  }
  
  this.deleteNode = function(node) {
    node.container.remove(node);

  }
  var me = this;

  this.collapseall = function() {
    //alert("collapseall")
    for(n in me.nodes) {
      if (me.nodes[n].expimage){
        l = me.nodes[n].get_list_of_child_nodes()  
        for (var i=0; i < l.length; i++ )  l[i].collapse(l[i]);
      }
    }
  }
}

function TreeNode(tree, parent, head_op, label, imagesrc, onclick, onexpand) {
  
  var me = this;
  this.parent = parent;
  this.head = head_op;
  this.nodes = {};
  this.onclick = onclick;
  this.onexpand = onexpand;
  this.text = label;

  if(!parent) {
    var container = tree.body; 
  }
  else {
    var container = parent.body;
  }
  var h_container = tree.hopbody;
  
  var t = $a(container, "div");
  var ht = $a(h_container, "div");

  t.style.display = "none";
  ht.style.display = "none";
 
  this.node_area = $a(t, "div");
  this.node_area.style.cursor = 'pointer';
    
  this.loading_div = $a(container, "div");
  this.loading_div.innerHTML = 'Loading...';
  $dh(this.loading_div);

  // main table
  this.tab = $a(this.node_area, 'table');
  $y(this.tab, {borderCollapse:'collapse', tableLayout:'fixed'})
  
  var r0 = this.tab.insertRow(0);
  for(var i=0; i<tree.col_details.length; i++) {
    var c = r0.insertCell(i);
    c.style.width = tree.col_details[i][0];
    c.style.padding = '2px';
    c.style.border = '1px solid #DDD';
  }
  
  this.label = $a(r0.cells[0], 'div');
  
  var m=0;
  var tn = this;
   
  while(tn.parent){m+=16;tn=tn.parent;}
  this.label.style.marginLeft = m+'px';
  this.loading_div.style.marginLeft = m+40+'px';
  var l = 350 - m;
  this.body = $a(t, 'div'); // children will come here

  // make the node
  var nodetab = $a(this.label, 'table');
  $y(nodetab, {borderCollapse:'collapse', tableLayout:'fixed'})
  
  var r0 = nodetab.insertRow(0);
  var c = r0.insertCell(0); c.style.width = '16px';  
  var c = r0.insertCell(1); c.style.width = '20px';
  var c = r0.insertCell(2); c.style.width = '100px';
  l=l-136;
  
  var c = r0.insertCell(3); c.style.width = l+'px';
  // BOM - is it item or operation
  this.is_item = 1;
  if(label[0] == 'operation') {
    this.is_item = 0;
    imagesrc = 'images/icons/wrench.png';
  }
  
  if(!imagesrc) imagesrc = "images/icons/folder.png";
  this.usrimg = $a(nodetab.rows[0].cells[1], 'img');
  this.usrimg.src = imagesrc;


  //this.node_area.onmouseover = function() {this.style.backgroundColor = '#DEF';  }
  //this.node_area.onmouseout = function() { this.style.backgroundColor = '#FFF';  }

  this.create_expimage = function() {
    if(!me.expimage) {
      me.expimage = $a(nodetab.rows[0].cells[0], 'img');
      me.expimage.style.marginTop = "3px";
      me.expimage.src = "images/icons/plus.gif";
      me.expimage.onclick = me.toggle;
      me.expimage.node = me;
    }
  }
  
  this.get_list_of_child_nodes = function() {
    var main_l = [];
    for (n in me.nodes){
      if(!me.expimage){}
      else{
        var l = [];
        if (me.nodes[n].get_list_of_child_nodes()) l = me.nodes[n].get_list_of_child_nodes();
        for(var i=0 ; i < l.length; i ++){
          main_l.push(l[i]);
        }
        alert(1);
        main_l.push(me.nodes[n]);
        alert(2);
      }
    }
    return main_l
  }

 this.select = function() {
    me.show_selected();
    if(this.onclick)this.onclick(this);
  }
  this.show_selected = function() {
    if(pscript.bom_curnode)pscript.bom_curnode.deselect();
    me.tab.style.backgroundColor = '#DEF';
    if(me.is_item == 1) tree.hitbody_tab.style.backgroundColor = '#DEF';
    if(me.is_item == 0) tree.hopbody_tab.style.backgroundColor = '#DEF';
    me.tab.style.fontWeight = 'bold';
    pscript.bom_curnode = me;
    $ds(me.refresh);
  }

  this.deselect = function() {
    me.tab.style.fontWeight = 'normal';
    pscript.bom_curnode=null;
    me.tab.style.backgroundColor = '#FFF';
    tree.hopbody_tab.style.backgroundColor = '#FFF';
    tree.hitbody_tab.style.backgroundColor = '#FFF';
    $dh(me.refresh);
  }
   

  var expanded = 1;
  this.toggle = function(node) {
    //alert("toggle")
    if(!me.expimage)return;
    if(me.expanded)me.collapse(this.node);
    else me.expand(this.node);
  }
  this.collapse = function(node) {
    //alert("collapse")
    if(!node.expimage)return;
    node.body.style.display = 'none';
    if(node.expimage.src)node.expimage.src = "images/icons/plus.gif";
    node.expanded = 0;
  }
  this.expand = function(node) {
    //alert("expand")
    if(!node.expimage)return;
    if(node.onexpand)node.onexpand(node);
    node.body.style.display = 'block';
    if(node.expimage.src)node.expimage.src = "images/icons/minus.gif";
    node.expanded = 1;
    node.expanded_once = 1;
  }

  // BOM - Set values
  for(var i=0;i<tree.col_details.length; i++) {
    if ( i == 0) {
      if(this.is_item == 1) {
        var c = $a( nodetab.rows[0].cells[2], 'span', 'link_type');
        c.item_code = label[tree.col_details[i][5]]
        c.onclick = function() { loaddoc("Item", this.item_code); }
      }
      if(this.is_item == 0) var c = nodetab.rows[0].cells[2];
      var d = nodetab.rows[0].cells[3];
      c.innerHTML = label[tree.col_details[i][5]];
      d.innerHTML = label[tree.col_details[i][6]].substring(0,15) + '...';
    }
    if(i==1) {
      var c = $a(this.tab.rows[0].cells[i], 'div', 'link_type', {overflow:'hidden', width:'100%'});
      c.bom_no = label[tree.col_details[i][3]]
      c.onclick = function() { loaddoc("Bill Of Materials", this.bom_no); }
      c.innerHTML = label[tree.col_details[i][3]];
    }
    if(this.is_item == 1 && i > 1 && i < 6) {
      var c = this.tab.rows[0].cells[i];
      c.innerHTML = label[tree.col_details[i][3]];
    }
    if(this.is_item == 0 && i > 1 && tree.col_details[i][1] != 'Refresh') {
      var c = this.tab.rows[0].cells[i];
      c.innerHTML = label[tree.col_details[i][3]];
    }
    if(tree.col_details[i][1] == 'Refresh') {
      this.refresh = $a(this.tab.rows[0].cells[i], 'span', 'link_type');  
      this.refresh.onclick = function() {
        me.node = me
        if(me.node.expanded_once){
          me.node.body.innerHTML = '';
          me.node.expanded_once = 0
          me.expanded = 0
          me.toggle();
        }
        else {me.toggle()}
      }
      this.refresh.innerHTML = "<img src='images/icons/page_refresh.gif' />"
      $dh(this.refresh);
    }
  }

  this.tab.onclick= function(e) { me.select(); }
  this.tab.ondblclick = function(e) { me.select(); if(me.ondblclick)me.ondblclick(me); }
  t.style.display = "block";
  ht.style.display = "block";
}