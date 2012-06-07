cur_frm.cscript.refresh = function(doc, dt, dn) {
	if(!doc.__islocal) {
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
	$(cur_frm.communication_html).css({
		'min-height': '275px',
	});
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

			// replace double quote with blank string
			data.content = cstr(data.subject).replace(/"/gi, '')
				+ " | " + cstr(data.content).replace(/"/gi, '');

			if(data.content && data.content.length > 50) {
				data.content = '<span title="'+data.content+'">' +
					data.content.substr(0,50) + '...</span>';
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
cur_frm.cscript.render_list = function(doc, doctype, wrapper, ListView, make_new_doc) {
	wn.model.with_doctype(doctype, function(r) {
		if((r && r['403']) || wn.boot.profile.all_read.indexOf(doctype)===-1) {
			return;
		}
		var RecordListView = wn.views.RecordListView.extend({
			default_docstatus: ['0', '1', '2'],
			default_filters: [
				[doctype, doc.doctype.toLowerCase(), '=', doc.name],
			],
		});
		
		if (make_new_doc) {
			RecordListView = RecordListView.extend({
				make_new_doc: make_new_doc,
			});
		}
		
		var record_list_view = new RecordListView(doctype, wrapper, ListView);
	});
}