
/*
 *	erpnext/utilities/page/kb_common/kb_common.js
 */
KBItemToolbar=function(args,kb){$.extend(this,args);var me=this;this.make=function(){this.wrapper=$a(this.parent,'div','',{});this.line1=$a(this.wrapper,'div','',{color:'#888',fontSize:'11px',margin:'7px 0px'});this.make_timestamp();this.make_answers();if(this.with_tags)
this.make_tags();this.setup_del();}
this.make_timestamp=function(){this.line1.innerHTML=repl('By %(name)s | %(when)s',{name:wn.utils.full_name(this.det.first_name,this.det.last_name),when:wn.datetime.comment_when(this.det.modified)});if(has_common(user_roles,['Administrator','System Manager'])){this.line1.innerHTML+=' | <a style="cursor:pointer;"\
    class="del-link">delete</a>';}}
this.make_answers=function(){if(this.doctype=='Question'){if(this.det.answers==0){this.line1.innerHTML+=' | no answers';}else if(this.det.answers==1){this.line1.innerHTML+=' | 1 answer';}else{this.line1.innerHTML+=' | '+this.det.answers+' answers';}}}
this.make_tags=function(){this.line1.innerHTML+=' | '
this.tags_area=$a(this.line1,'span','kb-tags')
this.tags=new TagList(this.tags_area,this.det._user_tags&&(this.det._user_tags.split(',')),this.doctype,this.det.name,0,kb.set_tag_filter)}
this.setup_del=function(){$(this.line1).find('.del-link').click(function(){console.log(1);this.innerHTML='deleting...';this.disabled=1;$c_page('utilities','questions','delete',{dt:me.doctype,dn:me.det.name},function(r,rt){kb.list.run()});});}
this.make();}
EditableText=function(args){$.extend(this,args);var me=this;me.$w=$(repl('<div class="ed-text">\
  <div class="ed-text-display %(disp_class)s"></div>\
  <a class="ed-text-edit" style="cursor: pointer; float: right; margin-top: -16px;">[edit]</a>\
  <textarea class="ed-text-input %(inp_class)s hide"></textarea>\
  <div class="help hide"><br>Formatted as <a href="#markdown-reference"\
    target="_blank">markdown</a></div>\
  <button class="btn btn-small btn-info hide ed-text-save">Save</button>\
  <a class="ed-text-cancel hide" style="cursor: pointer;">Cancel</a>\
 </div>',args)).appendTo(me.parent);this.set_display=function(txt){me.$w.find('.ed-text-display').html(wn.markdown(txt));me.text=txt;}
this.set_display(me.text);if(me.height)me.$w.find('.ed-text-input').css('height',me.height);me.$w.find('.ed-text-edit').click(function(){me.$w.find('.ed-text-input').val(me.text);me.show_as_input();})
me.$w.find('.ed-text-save').click(function(){var v=me.$w.find('.ed-text-input').val();if(!v){msgprint('Please write something!');return;}
var btn=this;$(btn).set_working();$c_page('utilities','question_view','update_item',{dt:me.dt,dn:me.dn,fn:me.fieldname,text:v},function(r){$(btn).done_working();if(r.exc){msgprint(r.exc);return;}
me.set_display(v);me.show_as_text();});})
me.$w.find('.ed-text-cancel').click(function(){me.show_as_text();})
this.show_as_text=function(){me.$w.find('.ed-text-display, .ed-text-edit').toggle(true);me.$w.find('.ed-text-input, .ed-text-save, .ed-text-cancel, .help').toggle(false);}
this.show_as_input=function(){me.$w.find('.ed-text-display, .ed-text-edit').toggle(false);me.$w.find('.ed-text-input, .ed-text-save, .ed-text-cancel, .help').toggle(true);}}