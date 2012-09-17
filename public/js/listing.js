
/*
 *	lib/js/legacy/widgets/listing.js
 */
list_opts={cell_style:{padding:'3px 2px'},alt_cell_style:{},head_style:{height:'20px',overflow:'hidden',verticalAlign:'middle',fontWeight:'bold',padding:'1px',fontSize:'13px'},head_main_style:{padding:'0px'},hide_export:1,hide_print:1,hide_refresh:0,hide_rec_label:0,show_calc:1,show_empty_tab:0,no_border:1,append_records:1,table_width:null};function Listing(head_text,no_index,no_loading){this.start=0;this.page_len=20;this.filters_per_line=7;this.cell_idx=0;this.head_text=head_text?head_text:'Result';this.keyword='records';this.no_index=no_index;this.underline=1;this.no_rec_message='No Result';this.show_cell=null;this.show_result=null;this.colnames=null;this.colwidths=null;this.coltypes=null;this.coloptions=null;this.filters={};this.sort_list={};this.sort_order_dict={};this.sort_heads={};this.is_std_query=false;this.server_call=null;this.no_loading=no_loading;this.opts=copy_dict(list_opts);}
Listing.prototype.make=function(parent){var me=this;this.wrapper=parent;this.filter_wrapper=$a(parent,'div','srs_filter_wrapper');this.filter_area=$a(this.filter_wrapper,'div','srs_filter_area');$dh(this.filter_wrapper);this.btn_area=$a(parent,'div','',{margin:'8px 0px'});this.body_area=$a(parent,'div','srs_body_area');if(!this.opts.hide_rec_label)
this.rec_label=$a(this.body_area,'div','',{margin:'4px 0px',color:'#888'});this.results=$a($a(this.body_area,'div','srs_results_area'),'div');this.fetching_area=$a(this.body_area,'div','',{height:'120px',background:'url("images/lib/ui/square_loading.gif") center no-repeat',display:'none'});this.show_no_records=$a(this.body_area,'div','',{margin:'200px 0px',textAlign:'center',fontSize:'14px',color:'#888',display:'none'});this.show_no_records.innerHTML='No Result';if(this.opts.show_empty_tab)
this.make_result_tab();this.bottom_div=$a(this.body_area,'div','',{paddingTop:'8px'});this.make_toolbar();}
Listing.prototype.make_toolbar=function(){var me=this;this.buttons={};var make_btn=function(label,icon,onclick,bold){var btn=$btn(me.btn_area,label,onclick,{marginRight:'4px'});if(bold)$y(btn,{fontWeight:'bold'});me.buttons[label]=btn;}
if(!this.opts.hide_refresh){make_btn('Refresh','ui-icon-refresh',function(btn){me.start=0;me.run();},1);}
if(this.opts.show_new){make_btn('New ','ui-icon-document',function(){new_doc(me.dt);},1);}
if(this.opts.show_report){make_btn('Report Builder','ui-icon-clipboard',function(){loadreport(me.dt,null,null,null,1);},0);}
if(!this.opts.hide_export){make_btn('Export','ui-icon-circle-arrow-e',function(){me.do_export();});}
if(this.opts.show_calc){make_btn('Calc','ui-icon-calculator',function(){me.do_calc();});$dh(me.buttons['Calc'])}
this.loading_img=$a(this.btn_area,'img','',{display:'none',marginBottom:'-2px'});this.loading_img.src='images/lib/ui/button-load.gif';if(!keys(this.buttons).length)
$dh(this.btn_area);}
Listing.prototype.do_calc=function(){show_calc(this.result_tab,this.colnames,this.coltypes,0)}
Listing.prototype.add_filter=function(label,ftype,options,tname,fname,cond){if(!this.filter_area){alert('[Listing] make() must be called before add_filter');}
var me=this;if(!this.filter_set){var h=$a(this.filter_area,'div','',{fontSize:'14px',fontWeight:'bold',marginBottom:'4px'});h.innerHTML='Filter your search';this.filter_area.div=$a(this.filter_area,'div');this.perm=[[1,1],]
this.filters={};}
$ds(this.filter_wrapper);if((!this.inp_tab)||(this.cell_idx==this.filters_per_line)){this.inp_tab=$a(this.filter_area.div,'table','',{width:'100%',tableLayout:'fixed'});this.inp_tab.insertRow(0);for(var i=0;i<this.filters_per_line;i++){this.inp_tab.rows[0].insertCell(i);}
this.cell_idx=0;}
var c=this.inp_tab.rows[0].cells[this.cell_idx];this.cell_idx++;$y(c,{width:cint(100/this.filters_per_line)+'%',textAlign:'left',verticalAlign:'top'});var d1=$a(c,'div','',{fontSize:'11px',marginBottom:'2px'});d1.innerHTML=label;if(ftype=='Link')d1.innerHTML+=' <img src="images/lib/icons/link.png" style="margin-bottom:-5px" title="Link">';var d2=$a(c,'div');if(in_list(['Text','Small Text','Code','Text Editor','Read Only'],ftype))
ftype='Data';if(ftype=='Select'&&!in_list(options.split('\n'),''))options='\n'+options
var inp=make_field({fieldtype:ftype,'label':label,'options':options,no_buttons:1},'',d2,this,0,1);inp.not_in_form=1;inp.report=this;inp.df.single_select=1;inp.parent_cell=c;inp.parent_tab=this.input_tab;$y(inp.wrapper,{width:'95%'});inp.refresh();inp.tn=tname;inp.fn=fname;inp.condition=ftype=='Data'?'like':cond;var me=this;inp.onchange=function(){me.start=0;}
this.filters[label]=inp;this.filter_set=1;}
Listing.prototype.remove_filter=function(label){var inp=this.filters[label];inp.parent_tab.rows[0].deleteCell(inp.parent_cell.cellIndex);delete this.filters[label];}
Listing.prototype.remove_all_filters=function(){for(var k in this.filters)this.remove_filter(k);$dh(this.filter_wrapper);}
Listing.prototype.add_sort=function(ci,fname){this.sort_list[ci]=fname;}
Listing.prototype.has_data=function(){return this.n_records;}
Listing.prototype.set_default_sort=function(fname,sort_order){this.sort_order=sort_order;this.sort_order_dict[fname]=sort_order;this.sort_by=fname;if(this.sort_heads[fname])
this.sort_heads[fname].set_sorting_as(sort_order);}
Listing.prototype.set_sort=function(cell,ci,fname){var me=this;$y(cell.sort_cell,{width:'18px'});cell.sort_img=$a(cell.sort_cell,'img');cell.fname=fname;$dh(cell.sort_img);cell.set_sort_img=function(order){var t='images/icons/sort_desc.gif';if(order=='ASC'){t='images/icons/sort_asc.gif';}
this.sort_img.src=t;}
cell.set_sorting_as=function(order){me.sort_order=order;me.sort_by=this.fname
me.sort_order_dict[this.fname]=order;this.set_sort_img(order)
if(me.cur_sort){$y(me.cur_sort,{backgroundColor:"#FFF"});$dh(me.cur_sort.sort_img);}
me.cur_sort=this;$y(this,{backgroundColor:"#DDF"});$di(this.sort_img);}
$y(cell.label_cell,{color:'#44A',cursor:'pointer'});cell.set_sort_img(me.sort_order_dict[fname]?me.sort_order_dict[fname]:'ASC');cell.onmouseover=function(){$di(this.sort_img);}
cell.onmouseout=function(){if(this!=me.cur_sort)
$dh(this.sort_img);}
cell.onclick=function(){this.set_sorting_as((me.sort_order_dict[fname]=='ASC')?'DESC':'ASC');me.run();}
this.sort_heads[fname]=cell;}
Listing.prototype.do_export=function(){this.build_query();var me=this;me.cn=[];if(this.no_index)
me.cn=this.colnames;else{for(var i=1;i<this.colnames.length;i++)
me.cn.push(this.colnames[i]);}
var q=export_query(this.query,function(query){export_csv(query,me.head_text,null,1,null,me.cn);});}
Listing.prototype.build_query=function(){if(this.get_query)this.get_query(this);if(!this.query){alert('No Query!');return;}
if(!this.prefix)this.prefix='tab';var cond=[];for(var i in this.filters){var f=this.filters[i];var val=f.get_value();var c=f.condition;if(!c)c='=';if(val&&c.toLowerCase()=='like')val+='%';if(f.tn&&val&&!in_list(['All','Select...',''],val))
cond.push(repl(' AND `%(prefix)s%(dt)s`.%(fn)s %(condition)s "%(val)s"',{prefix:this.prefix,dt:f.tn,fn:f.fn,condition:c,val:val}));}
if(cond){this.query+=NEWLINE+cond.join(NEWLINE)
if(this.query_max)
this.query_max+=NEWLINE+cond.join(NEWLINE)}
if(this.group_by)
this.query+=' '+this.group_by+' ';if(this.sort_by&&this.sort_order){this.query+=NEWLINE+' ORDER BY `'+this.sort_by+'` '+this.sort_order;}
if(this.show_query)msgprint(this.query);}
Listing.prototype.set_rec_label=function(total,cur_page_len){if(this.opts.hide_rec_label)
return;else if(total==-1)
this.rec_label.innerHTML='Fetching...'
else if(total>0)
this.rec_label.innerHTML=repl('Total %(total)s %(keyword)s. Showing %(start)s to %(end)s',{total:total,start:cint(this.start)+1,end:cint(this.start)+cint(cur_page_len),keyword:this.keyword});else if(total==null)
this.rec_label.innerHTML=''
else if(total==0)
this.rec_label.innerHTML=this.no_rec_message;}
Listing.prototype.run=function(run_callback){this.build_query();var q=this.query;var me=this;if(this.max_len&&this.start>=this.max_len)this.start-=this.page_len;q+=' LIMIT '+this.start+','+this.page_len;var call_back=function(r,rt){$dh(me.loading_img);me.max_len=r.n_values;if(r.values&&r.values.length){me.n_records=r.values.length;var nc=r.values[0].length;if(me.colwidths)nc=me.colwidths.length-(me.no_index?0:1);if(me.opts.append_records&&me.start!=0){me.append_rows(r.values.length);}else{me.clear_tab();if(!me.show_empty_tab){me.remove_result_tab();me.make_result_tab(r.values.length);}}
me.refresh(r.values.length,nc,r.values,r.n_values);me.total_records=r.n_values;me.set_rec_label(r.n_values,r.values.length);}else{me.n_records=0;me.set_rec_label(0);me.clear_tab();if(!me.opts.append_records){if(me.show_empty_tab){me.clear_tab();}else{me.remove_result_tab();me.make_result_tab(0);if(me.opts.show_no_records_label){$ds(me.show_no_records);}}}}
$ds(me.results);if(run_callback)run_callback();if(me.onrun)me.onrun();}
$dh(me.show_no_records);this.set_rec_label(-1);$di(this.loading_img);if(this.server_call){this.server_call(this,call_back);}else{args={query_max:(this.query_max?this.query_max:'')}
if(this.is_std_query)args.query=q;else args.simple_query=q;if(this.opts.formatted)args.formatted=1;$c('webnotes.widgets.query_builder.runquery',args,call_back,null,this.no_loading);}}
Listing.prototype.remove_result_tab=function(){if(!this.result_tab)return;this.result_tab.parentNode.removeChild(this.result_tab);delete this.result_tab;}
Listing.prototype.reset_tab=function(){this.remove_result_tab();this.make_result_tab();}
Listing.prototype.make_result_tab=function(nr){if(this.result_tab)return;if(!this.colwidths)alert("Listing: Must specify column widths");var has_headrow=this.colnames?1:0;if(nr==null)nr=this.page_len;nr+=has_headrow;var nc=this.colwidths.length;var t=make_table(this.results,nr,nc,(this.opts.table_width?this.opts.table_width:'100%'),this.colwidths,{padding:'0px'});t.className='srs_result_tab';this.result_tab=t;$y(t,{borderCollapse:'collapse'});if(this.opts.table_width){$y(this.results,{overflowX:'auto'});$y(t,{tableLayout:'fixed'});}
if(has_headrow){this.make_headings(t,nr,nc);if(this.sort_by&&this.sort_heads[this.sort_by]){this.sort_heads[this.sort_by].set_sorting_as(this.sort_order);}}
this.set_table_style();if(this.opts.no_border==1){$y(t,{border:'0px'});}
this.result_tab=t;}
Listing.prototype.set_table_style=function(){var t=this.result_tab;for(var ri=(this.colnames?1:0);ri<t.rows.length;ri++){for(var ci=0;ci<t.rows[ri].cells.length;ci++){if(this.opts.cell_style)$y($td(t,ri,ci),this.opts.cell_style);if(this.opts.alt_cell_style&&(ri%2))$y($td(t,ri,ci),this.opts.alt_cell_style);if(this.opts.show_empty_tab&&!$td(t,ri,ci).innerHTML)$td(t,ri,ci).innerHTML='&nbsp;';}}}
Listing.prototype.append_rows=function(nr){for(var i=0;i<nr;i++){append_row(this.result_tab);}
this.set_table_style();}
Listing.prototype.clear_tab=function(){$dh(this.results);if(this.result_tab){var nr=this.result_tab.rows.length;var nc=this.result_tab.rows[0].cells.length;for(var ri=(this.colnames?1:0);ri<nr;ri++)
for(var ci=0;ci<nc;ci++)
$td(this.result_tab,ri,ci).innerHTML=(this.opts.show_empty_tab?'&nbsp;':'');}}
Listing.prototype.clear=function(){this.rec_label.innerHTML='';this.clear_tab();}
Listing.prototype.refresh_calc=function(){if(!this.opts.show_calc)return;if(has_common(this.coltypes,['Currency','Int','Float'])){$di(this.buttons['Calc']);}else{$dh(this.buttons['Calc']);}}
Listing.prototype.refresh=function(nr,nc,d,n_values){this.refresh_more_button(nr,n_values);this.refresh_calc();if(this.show_result)
this.show_result();else{if(nr){var start=this.result_tab.rows.length-nr;for(var ri=start;ri<start+nr;ri++){var c0=$td(this.result_tab,ri,0);if(!this.no_index){c0.innerHTML=cint(this.start)+cint(ri-start)+1;}
for(var ci=0;ci<nc;ci++){var c=$td(this.result_tab,ri,ci+(this.no_index?0:1));if(c){c.innerHTML='';if(this.show_cell)this.show_cell(c,ri-start,ci,d);else this.std_cell(c,ri-start,ci,d);}}}}}}
Listing.prototype.refresh_more_button=function(nr,n_values){var me=this;if(this.more_btn){$dh(this.more_btn);}
if((this.start+nr)==this.max_len||(!this.max_len&&nr<this.page_len)){}else if(nr){if(!this.more_btn){$y(this.bottom_div,{margin:'8px 0px 16px 0px',textAlign:'center'});this.more_btn=$btn(this.bottom_div,'Show more results...',function(){me.start=me.start+me.page_len;me.more_btn.set_working();me.run(function(){me.more_btn.done_working();});},{fontSize:'14px'},0,1);$y(this.more_btn.loading_img,{marginBottom:'0px'});}
$di(this.more_btn);}}
Listing.prototype.make_headings=function(t,nr,nc){for(var ci=0;ci<nc;ci++){var tmp=make_table($td(t,0,ci),1,2,'100%',['','0px'],this.opts.head_style);$y(tmp,{tableLayout:'fixed',borderCollapse:'collapse'});$y($td(t,0,ci),this.opts.head_main_style);$td(t,0,ci).sort_cell=$td(tmp,0,1);$td(t,0,ci).label_cell=$td(tmp,0,0);$td(tmp,0,1).style.padding='0px';$td(tmp,0,0).innerHTML=this.colnames[ci]?this.colnames[ci]:'&nbsp;';if(this.sort_list[ci])this.set_sort($td(t,0,ci),ci,this.sort_list[ci]);var div=$a($td(t,0,ci),'div');$td(t,0,ci).style.borderBottom='1px solid #CCC';if(this.coltypes&&this.coltypes[ci]&&in_list(['Currency','Float','Int'],this.coltypes[ci]))$y($td(t,0,ci).label_cell,{textAlign:'right'})}}
Listing.prototype.std_cell=function(cell,ri,ci,d){var has_headrow=this.colnames?1:0;cell.div=$a(cell,'div');$s(cell.div,d[ri][ci],this.coltypes?this.coltypes[ci+(this.no_index?0:1)]:null,this.coloptions?this.coloptions[ci+(this.no_index?0:1)]:null);}