
pscript.onload_people=function(){make_customer_tab($i('crm_home'));}
function make_customer_tab(parent){new DocColumnView('Customers',parent,['Customer Group','Customer','Contact'],{'Customer Group':{show_fields:['name'],create_fields:['name'],search_fields:['name'],next_col:'Customer'},'Customer':{show_fields:['name','customer_name'],create_fields:['name','customer_name'],search_fields:['customer_name'],filter_by:['Customer Group','customer_group'],next_col:'Contact'},'Contact':{show_fields:['name','first_name','last_name'],create_fields:['name','first_name','last_name'],search_fields:['first_name','last_name'],conditions:['is_customer=1'],filter_by:['Customer','customer']},})}
function DocColumnView(title,parent,items,opts){this.columns={};this.items=items;this.page_head=new PageHeader(parent,title);this.make_columns(items.length,parent);for(var i=0;i<items.length;i++){var c=opts[items[i]];this.columns[items[i]]=new List2(this,$td(this.tab,0,i),items[i],c);}
this.columns[items[0]].run();}
DocColumnView.prototype.make_columns=function(n,parent){var cl=[];for(var i=0;i<n;i++){cl.push(cint(100/n)+'%')}
this.tab=make_table(parent,1,n,'100%',cl)
this.tab.className='dcv-tab';}
DocColumnView.prototype.refresh=function(){this.columns[this.items[0]].run();}
function List2(dcv,parent,doctype,opts){this.dcv=dcv;this.doctype=doctype;this.opts=opts;this.dtl=get_doctype_label(doctype);this.make_body(parent);this.selected_item=null;}
List2.prototype.make_body=function(parent){this.make_toolbar(parent);this.make_search(parent);this.make_message(parent);this.make_list(parent);this.clear();}
List2.prototype.make_toolbar=function(parent){var me=this;this.head=$a(parent,'div','list2-head');$gr(this.head,'#EEE','#CCC');var t=make_table(this.head,1,2,'100%',['60%','40%'],{verticalAlign:'middle'});var span=$a($td(t,0,0),'span','',{cssFloat:'left'},this.dtl);var refresh_icon=$a($td(t,0,0),'div','wn-icon ic-playback_reload',{marginLeft:'7px',cssFloat:'left'});refresh_icon.onclick=function(){me.run();}
this.btn=$btn($td(t,0,1),'+ New',function(){me.make_new();},{fontWeight:'bold',cssFloat:'right'},'green');}
List2.prototype.make_search=function(parent){var me=this;this.searchbar=$a(parent,'div','list2-search');this.search_inp=$a_input(this.searchbar,'text');this.search_btn=$a(this.searchbar,'img','',{cursor:'pointer',marginLeft:'8px',marginBottom:'-3px'});this.search_btn.src='images/icons/magnifier.png';this.search_btn.onclick=function(){me.run();}}
List2.prototype.make_message=function(parent){this.clear_message=$a(parent,'div','help_box',{margin:'4px',display:'none'},(this.opts.filter_by?('Select '+get_doctype_label(this.opts.filter_by[0])+' to see list'):''));this.no_result_message=$a(parent,'div','help_box',{margin:'4px',display:'none'},'No '+this.dtl+' created yet!');}
List2.prototype.make_new=function(){var me=this;newdoc(this.doctype,function(dn){if(me.opts.filter_by){var val=me.dcv.columns[me.opts.filter_by[0]].get_selected();if(val)
locals[me.doctype][dn][me.opts.filter_by[1]]=val;}});}
List2.prototype.clear=function(){$dh(this.lst_area);$ds(this.clear_message)
$dh(this.no_result_message);this.clear_next();}
List2.prototype.show_list=function(){$ds(this.lst_area);$dh(this.clear_message)
$dh(this.no_result_message);}
List2.prototype.show_no_result=function(){if(!this.search_inp.value){$dh(this.lst_area);$dh(this.clear_message);$ds(this.no_result_message);}}
List2.prototype.clear_next=function(){if(this.opts.next_col&&this.dcv.columns[this.opts.next_col])this.dcv.columns[this.opts.next_col].clear();}
List2.prototype.make_list=function(parent){var me=this;this.lst_area=$a(parent,'div','list2-list-area');this.lst=new Listing('Profiles',1);this.lst.opts.hide_refresh=1;this.lst.opts.cell_style={padding:'0px'};this.lst.colwidths=['100%'];this.lst.get_query=function(){var q=me.build_query();this.query=q[0];this.query_max=q[1];}
this.lst.make(this.lst_area);this.lst.show_cell=function(cell,ri,ci,d){new List2Item(cell,d[ri],me);}
this.lst.onrun=function(){me.show_list();me.clear_next();if(!me.lst.has_data())me.show_no_result();}}
List2.prototype.run=function(){$dh(this.lst.results);this.lst.run();}
List2.prototype.build_query=function(){var args={fields:this.opts.show_fields.join(', '),doctype:this.doctype,cond:''}
var cl=this.build_search_conditions();cl=this.add_filter_condition(cl);if(cl.length)args.cond=' AND '+cl.join(' AND ');var query=repl('SELECT %(fields)s FROM `tab%(doctype)s` WHERE docstatus < 2 %(cond)s',args)
var query_max=repl('SELECT COUNT(*) FROM `tab%(doctype)s` WHERE docstatus < 2 %(cond)s',args)
return[query,query_max]}
List2.prototype.build_search_conditions=function(){var cl=new Array();if(this.opts.conditions){for(var i=0;i<this.opts.conditions.length;i++)cl.push(this.opts.conditions);}
if(this.search_inp.value&&this.search_inp.value!='Search'){for(var i=0;i<this.opts.search_fields.length;i++){cl.push(repl('`%(field)s` LIKE "%(txt)s"',{field:this.opts.search_fields[i],txt:'%'+this.search_inp.value+'%'}));}}
return cl;}
List2.prototype.add_filter_condition=function(cl){if(this.opts.filter_by){cl.push(repl('`%(filter)s` = "%(val)s"',{filter:this.opts.filter_by[1],val:this.dcv.columns[this.opts.filter_by[0]].get_selected()}));}
return cl;}
List2.prototype.get_selected=function(){if(this.selected_item)return this.selected_item.det[0];else return'';}
List2Item=function(cell,det,list2){this.det=det;this.list2=list2;this.make_body(cell);this.show_text();this.show_more_info();}
List2Item.prototype.make_body=function(cell){var me=this;this.body=$a(cell,'div','list2-item-div')
if(me.list2.opts.next_col){this.make_with_icon();}else{this.content=this.body;}
this.body.onclick=function(){me.select();if(me.list2.opts.next_col)me.list2.dcv.columns[me.list2.opts.next_col].run();}}
List2Item.prototype.make_with_icon=function(){var t=make_table(this.body,1,2,'100%',['','18px'])
$y($td(t,0,1),{verticalAlign:'middle'})
var img=$a($td(t,0,1),'img');img.src='images/icons/control_play.png';this.content=$td(t,0,0);}
List2Item.prototype.show_text=function(){var me=this;this.label=$a(this.content,'div','list2-item-title','',this.det[0]);var span=$a(this.label,'span','link_type list2-edit-link','','[Edit]');span.onclick=function(){loaddoc(me.list2.doctype,me.det[0]);}}
List2Item.prototype.show_more_info=function(){var det=this.det;if(det.length>1){var l=[];for(var i=1;i<det.length;i++){if(det[i]&&det[i]!=det[0])l.push(det[i]);}
if(l.length)
this.more_info=$a(this.content,'div','list2-item-more-info','',l.join(', '))}}
List2Item.prototype.select=function(){if(this.list2.selected_item)this.list2.selected_item.deselect();this.body.className='list2-item-div list2-item-selected';this.list2.selected_item=this;}
List2Item.prototype.deselect=function(){this.body.className='list2-item-div';}