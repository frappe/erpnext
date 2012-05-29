// common partner functions
// =========================


// make history list body
// -----------------------
cur_frm.cscript.make_hl_body = function(){
	cur_frm.fields_dict['history_html'].wrapper.innerHTML = '';
	cur_frm.history_html = $a(cur_frm.fields_dict['history_html'].wrapper,'div');
}


// make history
// -------------
cur_frm.cscript.make_history = function(doc,dt,dn){
	cur_frm.history_html.innerHTML = '';
	cur_frm.cscript.make_history_list(cur_frm.history_html,doc);
}

// make history list
// ------------------
cur_frm.cscript.make_history_list = function(parent,doc){

	var sel = $a(parent,'select');
	
	var ls = ['Select Transaction..'];
	for(d in cur_frm.history_dict){
		ls.push(d);
	}
	
	add_sel_options(sel,ls,'Select..');
	
	var body = $a(parent,'div');
	body.innerHTML = '<div class="help_box">Please select a transaction type to see History</div>';
	
	sel.body = body;
	sel.doc = doc;
	
	sel.onchange = function(){
		for(d in cur_frm.history_dict){
			if(sel_val(this) == d){
				this.body.innerHTML = '';
				eval(cur_frm.history_dict[d]);
				return;
			}
			else{
				// pass
			}
		}
	}
}

// run list
// ---------
cur_frm.cscript.run_list = function(lst,parent,q,q_max,doc,dn,nm){
	
	parent.innerHTML = '';
	$dh(parent);
	
	lst.doc = doc;
	lst.dn = dn;
	lst.nm = nm;
	lst.page_len = 10;
	
	lst.get_query = function(){
		this.query = q;
		this.query_max = q_max;
	}
	
	lst.make(parent);
	lst.run();
	
	lst.onrun = function(){
		$ds(parent);
		if(!this.has_data()){
			parent.innerHTML = '';
			var dv = $a(parent,'div','help_box');
			$a(dv,'span').innerHTML = "No " + this.dn + " found. ";
			
			var lbl = 'Create the <b>first</b> ' + this.dn + ' for ' + this.doc.name;
			var sp = $a(dv,'span');
			sp.nm = this.nm;
			$(sp).html(lbl).addClass('link_type').click(function(){ newdoc(this.nm); });
		}
	}
}


// get sates on country trigger
// -----------------------------
cur_frm.cscript.get_states=function(doc,dt,dn){
   $c('runserverobj', args={'method':'check_state', 'docs':compress_doclist([doc])},
    function(r,rt){
      if(r.message) {
        set_field_options('state', r.message);
      }
    }  
  );

}

cur_frm.cscript.country = function(doc, dt, dn) {
  cur_frm.cscript.get_states(doc, dt, dn);
}

// territory help - cutsomer + sales partner
// -----------------------------------------
cur_frm.cscript.TerritoryHelp = function(doc,dt,dn){
  var call_back = function(){

    var sb_obj = new SalesBrowser();        
    sb_obj.set_val('Territory');
  }
  loadpage('Sales Browser',call_back);
}

// get query select Territory
// ---------------------------
if(cur_frm.fields_dict['territory']){
	cur_frm.fields_dict['territory'].get_query = function(doc,dt,dn) {
		return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"  ORDER BY  `tabTerritory`.`name` ASC LIMIT 50';
	}
}


// Transaction History related functions
cur_frm.cscript.render_transaction_history = function(parent, doc, doctype, args) {
	$(parent).css({ 'padding-top': '10px' });
	cur_frm.transaction_list = new wn.ui.Listing({
		parent: parent,
		page_length: 10,
		get_query: function() {
			return cur_frm.cscript.get_query_transaction_history({
				parent: doc.doctype.toLowerCase(),
				parent_name: doc.name,
				doctype: doctype,
				fields: (function() {
					var fields = [];
					for(var i in args) {
						fields.push(args[i].fieldname);
					}
					return fields.join(", ");
				})(),
			});
		},
		as_dict: 1,
		no_result_message: repl('No %(doctype)s created for this %(parent)s', 
								{ doctype: doctype, parent: doc.doctype }),
		render_row: function(wrapper, data) {
			render_html = cur_frm.cscript.render_transaction_history_row(data, args, doctype);
			$(wrapper).html(render_html);
		},
	});
	cur_frm.transaction_list.run();
}

cur_frm.cscript.render_transaction_history_row = function(data, args, doctype) {
	var content = [];
	var currency = data.currency;
	for (var a in args) {
		for (var d in data) {
			if (args[a].fieldname === d && args[a].fieldname !== 'currency') {
				if (args[a].type === 'Link') {
					data[d] = repl('<a href="#!Form/%(doctype)s/%(name)s">\
						%(name)s</a>', { doctype: doctype, name: data[d]});
				} else if (args[a].type === 'Currency') {
					data[d] = currency + " " + fmt_money(data[d]);
				} else if (args[a].type === 'Percentage') {
					data[d] = flt(data[d]) + '%';
				} else if (args[a].type === 'Date') {
					data[d] = wn.datetime.only_date(data[d]);
				}
				if (args[a].style == undefined) {
					args[a].style = '';
				}
				data[d] = repl('\
					<td width="%(width)s" title="%(title)s" style="%(style)s">\
					%(content)s</td>',
					{
						content: data[d],
						width: args[a].width,
						title: args[a].label,
						style: args[a].style,
					});
				content.push(data[d]);
				break;
			}
		}
	}
	content = content.join("\n");
	return '<table><tr>' + content + '</tr></table>';
}

cur_frm.cscript.get_query_transaction_history = function(args) {
	var query = repl("\
		select %(fields)s from `tab%(doctype)s` \
		where %(parent)s = '%(parent_name)s' \
		order by modified desc", args);
	return query;
}