// question toolbar
// contains - voting widget / tag list and user info / timestamp
// By XXXXXX on YYYYY

KBItemToolbar = function(args, kb) {
	$.extend(this, args);
	var me = this;
	this.make = function() {
		this.wrapper = $a(this.parent, 'div', '', {});
		this.line1 = $a(this.wrapper, 'div', '', {color: '#888', fontSize:'11px', margin:'7px 0px'});
		this.line2 = $a(this.wrapper, 'div','',{marginBottom:'7px'});
		this.make_timestamp();
		this.make_vote();
		if(this.with_tags)
			this.make_tags();
	}
	
	this.make_timestamp = function() {
		this.line1.innerHTML = repl('By %(name)s | %(when)s', {
			name: wn.utils.full_name(this.det.first_name, this.det.last_name),
			when: wn.datetime.comment_when(this.det.modified)
		})
	}

	this.make_vote = function() {
		new KBPoints(this.line2, this.det.points, this.det._users_voted, this.doctype, this.det.name, this.det.owner);
		
	}
	
	this.make_tags = function() {
		this.tags_area = $a(this.line2, 'span', 'kb-tags')
		this.tags = new TagList(this.tags_area, 
			this.det._user_tags && (this.det._user_tags.split(',')), 
			this.doctype, this.det.name, 0, kb.set_tag_filter)		
	}

	this.make();
}


// kb points
// x points | Vote Up | Vote Down (if not voted and not guest)
KBPoints = function(parent, points, voted, dt, dn, owner) {
	var me = this;
	voted = voted ? voted.split(',') : [];

	this.wrapper = $a(parent, 'span', '', {fontSize: '11px', marginRight: '13px'});
	
	this.render_points = function(p) {
		if(!this.points_area)
			this.points_area = $a(this.wrapper, 'span');
		this.points_area.innerHTML = cint(p) + ' point' + (p>1 ? 's' : '');			
	}
	
	this.render_points(points);
	
	// vote up or down
	// if user has not already voted
	
	if(user!='Guest' && !in_list(voted, user) && user!=owner) {
		this.vote_up = $a(this.wrapper, 'img', 'images/ui/vote_up.gif', {margin:'0px 0px -2px 7px', cursor: 'pointer'});
		this.vote_down = $a(this.wrapper, 'img', 'images/ui/vote_down.gif', {margin:'0px 0px -3px 0px', cursor: 'pointer'});
		
		this.vote_up.title = 'Vote Up'; this.vote_down.title = 'Vote Down';
		
		var callback = function(r, rt) {
			if(r.exc) { msgprint(r.exc); return; }
			$dh(me.vote_up); $dh(me.vote_down);
			me.render_points(r.message);
		}
		
		this.vote_up.onclick = function() {
			$c_page('knowledge_base', 'questions', 'vote', {vote:'up', dn:dn, dt:dt}, callback);
		}
		this.vote_down.onclick = function() {
			$c_page('knowledge_base', 'questions', 'vote', {vote:'down', dn:dn, dt:dt}, callback);
		}
	}
}

// displays an editable text,
// needs parent, text, disp_class, inp_class
// dt, dn

EditableText = function(args) {
	$.extend(this, args);
	var me = this;
	
	this.display = $a(me.parent, 'div', me.disp_class, '', me.text);
	this.input = $a(me.parent, 'textarea', me.inp_class, {display:'none'});
	
	var div = $a(me.parent, 'div', '', {marginTop:'5px', height:'23px'});
	
	// edit text
	this.edit_btn = $a(div, 'span', '', {color:'#333', marginLeft:'-2px', cursor:'pointer', padding:'3px', backgroundColor:'#ddd', cssFloat: 'left'});
	$br(this.edit_btn, '3px')
	$a(this.edit_btn, 'div', 'wn-icon ic-pencil', {marginBottom:'-2px', cssFloat:'left'} );
	$a(this.edit_btn, 'span', 'link_type', {marginLeft:'3px', color:'#555', fontSize:'11px'}, 'Edit');

	this.edit_btn.onclick = function() {
		me.input.value = me.display.innerHTML;
		me.show_as_input();
	}
	
	// save button - save the new text
	// check if text is written
	this.save_btn = $btn(div, 'Save', function() {
		var v = me.rich_text ? wn.tinymce.get_value(me.input) : me.input.value;
		if(!v) {
			msgprint('Please write something!');
			return;
		}
		me.save_btn.set_working();
		$c_page('knowledge_base', 'question_view', 'update_item', {
				dt: me.dt, dn: me.dn, fn: me.fieldname, text: v
			}, 
			function(r, rt) {
				me.save_btn.done_working();
				if(r.exc) {msgprint(r.exc); return; }
				me.display.innerHTML = v;
				me.show_as_text();
			});
	}, {display: 'none'});

	// cancel button
	this.cancel_btn = $a(div, 'span', 'link_type', {color: '#555', display:'none'}, 'Cancel', {marginLeft:'7px'});
	this.cancel_btn.onclick = function() {
		me.show_as_text();		
	}

	this.show_as_text = function() {
		$ds(me.display); $ds(me.edit_btn);
		if(me.rich_text)
			wn.tinymce.remove(me.input);
		$dh(me.input); $dh(me.save_btn); $dh(me.cancel_btn);
				
	}

	this.show_as_input = function() {
		$ds(me.input); $ds(me.save_btn); $ds(me.cancel_btn); 
		$dh(me.edit_btn); $dh(me.display);
		if(me.rich_text)
			wn.tinymce.add_simple(me.input, '300px');
	}	

}