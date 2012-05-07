
/*
 *	lib/js/legacy/widgets/print_query.js
 */
_p.PrintQuery=function(){this.args={};}
_p.PrintQuery.prototype.show_dialog=function(args){this.args=args;var me=this;if(!this.dialog){var d=new Dialog(400,300,"Print");d.make_body([['Data','Max rows','Blank to print all rows'],['Data','Rows per page'],['Button','Go'],]);d.widgets['Go'].onclick=function(){d.hide();me.render(cint(d.widgets['Max rows'].value),cint(d.widgets['Rows per page'].value))}
d.onshow=function(){this.widgets['Rows per page'].value='35';this.widgets['Max rows'].value='500';}
this.dialog=d;}
this.dialog.show();}
_p.PrintQuery.prototype.render=function(max_rows,page_len){var me=this;var args=me.args;if(cint(max_rows)!=0)args.query+=' LIMIT 0,'+cint(max_rows);if(!args.query)return;var callback=function(r,rt){if(!r.values){return;}
if(!page_len)page_len=r.values.length;if(r.colnames&&r.colnames.length)
args.colnames=args.has_index?add_lists(['Sr'],r.colnames):r.colnames;if(r.colwidths&&r.colwidths.length)
args.colwidths=args.has_index?add_lists(['25px'],r.colwidths):r.colwidths;if(r.coltypes)
args.coltypes=args.has_index?add_lists(['Data'],r.coltypes):r.coltypes;if(args.coltypes){for(var i in args.coltypes)
if(args.coltypes[i]=='Link')args.coltypes[i]='Data';}
if(args.colwidths){var tw=0;for(var i=0;i<args.colwidths.length;i++)tw+=cint(args.colwidths[i]?args.colwidths[i]:100);for(var i=0;i<args.colwidths.length;i++)args.colwidths[i]=cint(cint(args.colwidths[i]?args.colwidths[i]:100)/tw*100)+'%';}
var has_heading=args.colnames?1:0;if(!args.has_headings)has_heading=0;var tl=[]
for(var st=0;st<r.values.length;st=st+page_len){tl.push(me.build_table(r,st,page_len,has_heading,args.rb))}
var html='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
+'<html><head>'
+'<title>'+args.title+'</title>'
+'<style>'+_p.def_print_style_body+_p.def_print_style_other+'</style>'
+'</head><body>'
+(r.header_html?r.header_html:'')
+tl.join('\n<div style="page-break-after: always;"></div>\n')
+(r.footer_html?r.footer_html:'')
+'</body></html>';_p.preview(html);}
var out_args=copy_dict(args);if(args.is_simple){out_args.simple_query=args.query;delete out_args.query;}
if(args.filter_values)
out_args.filter_values=args.filter_values;$c('webnotes.widgets.query_builder.runquery',out_args,callback);}
_p.PrintQuery.prototype.build_table=function(r,start,page_len,has_heading,rb){var div=document.createElement('div');if(!r.page_template){var head=$a(div,'div',null,{fontSize:'20px',fontWeight:'bold',margin:'16px 0px',borderBottom:'1px solid #CCC',paddingBottom:'8px'});head.innerHTML=args.title;}
var m=start+page_len;if(m>r.values.length)m=r.values.length
var t=make_table(div,m+has_heading-start,r.values[0].length+args.has_index,'100%',null);t.className='simpletable';if(args.colwidths)
$y(t,{tableLayout:'fixed'});if(has_heading){for(var i=0;i<args.colnames.length;i++){$td(t,0,i).innerHTML=args.colnames[i].bold();if(args.colwidths&&args.colwidths[i]){$w($td(t,0,i),args.colwidths[i]);}}}
for(var ri=start;ri<m;ri++){if(args.has_index)
$td(t,ri+has_heading-start,0).innerHTML=ri+1;for(var ci=0;ci<r.values[0].length;ci++){if(ri-start==0&&args.colwidths&&args.colwidths[i]){$w($td(t,0,i),args.colwidths[i]);}
var c=$td(t,ri+has_heading-start,ci+args.has_index)
c.div=$a(c,'div','',{whiteSpace:'normal'});$s(c.div,r.values[ri][ci],args.coltypes?args.coltypes[ci+args.has_index]:null);}}
if(r.style){for(var i=0;i<r.style.length;i++){$yt(t,r.style[i][0],r.style[i][1],r.style[i][2]);}}
if(rb&&rb.aftertableprint){rb.aftertableprint(t);}
if(r.page_template)return repl(r.page_template,{table:div.innerHTML});else return div.innerHTML;}