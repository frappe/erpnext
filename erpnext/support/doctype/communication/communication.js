cur_frm.cscript.refresh = function(doc, dt, dn) {
	if(!doc.islocal) {
		var field_list = ['lead', 'customer', 'supplier', 'contact', 'opportunity',
			'quotation', 'support_ticket'];
		var hide_list = [];
		$.each(field_list, function(i, v) {
			if(!doc[v]) hide_list.push(v);
		});
		
		if(hide_list.length < field_list.length) hide_field(hide_list);
	}
}


cur_frm.cscript.make_communication_body = function() {
	var communication_wrapper = cur_frm.fields_dict.communication_html.wrapper;
	communication_wrapper.innerHTML = '';
	cur_frm.communication_html = $a(communication_wrapper, 'div');
}

cur_frm.cscript.render_communication_list = function(doc, dt, dn) {
	var ListView = wn.views.ListView.extend({
		init: function(doclistview) {
			this._super(doclistview);
			this.fields = this.fields.concat([
				"`tabCommunication`.communication_date",
				"`tabCommunication`.category",
				"`tabCommunication`.subject",
				"`tabCommunication`.content"
			]);
			this.order_by = "`tabCommunication`.communication_date desc";
		},

		prepare_data: function(data) {
			this._super(data);
			data.creation = wn.datetime.str_to_user(data.communication_date);

			data.content = cstr(data.subject) + " | " + cstr(data.content);

			if(data.content && data.content.length > 50) {
				data.content = '<span title="'+data.content+'">' +
					data.description.substr(0,50) + '...</span>';
			}

		},

		columns: [
			{width: '3%', content: 'docstatus'},
			{width: '15%', content: 'name'},
			{width: '15%', content: 'category'},
			{width: '55%', content: 'content'},
			{width: '12%', content:'communication_date',
				css: {'text-align': 'right', 'color':'#777'}}		
		],
	});
	
	cur_frm.cscript.render_list(doc, 'Communication', cur_frm.communication_html,
		ListView, function(doctype) {
			var new_doc = LocalDB.create(doctype);
			new_doc = locals[doctype][new_doc];
			new_doc[doc.doctype.toLowerCase()] = doc.name;
			loaddoc(new_doc.doctype, new_doc.name);
		});
}


// Render List
cur_frm.cscript.render_list = function(doc, doctype, wrapper, ListView,
		new_doc_constructor) {
	wn.model.with_doctype(doctype, function(r) {
		if(r && r['403']) {
			return;
		}
		var RecordListView = wn.views.RecordListView.extend({
			default_docstatus: ['0', '1', '2'],
			default_filters: [
				[doctype, doc.doctype.toLowerCase(), '=', doc.name],
			],
			new_doc_constructor: new_doc_constructor || null,
		});
		var record_list_view = new RecordListView(doctype, wrapper, ListView);
	});
}



// Transaction List related functions
cur_frm.cscript.render_list2 = function(parent, doc, doctype, args) {
	$(parent).css({ 'padding-top': '10px' });
	cur_frm.transaction_list = new wn.ui.Listing({
		parent: parent,
		page_length: 10,
		get_query: function() {
			return cur_frm.cscript.get_query_list({
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
			render_html = cur_frm.cscript.render_list_row(data, args, doctype);
			$(wrapper).html(render_html);
		},
	});
	cur_frm.transaction_list.run();
}

cur_frm.cscript.render_list_row = function(data, args, doctype) {
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

cur_frm.cscript.get_query_list = function(args) {
	var query = repl("\
		select %(fields)s from `tab%(doctype)s` \
		where %(parent)s = '%(parent_name)s' \
		order by modified desc", args);
	return query;
}