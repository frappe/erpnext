pscript['onload_question-view'] = function() {
//
	var w = page_body.pages['question-view'];
	w.className = 'layout_wrapper';
	new PageHeader(w, 'Knowledge Base');
	w.link = $ln($a(w, 'div'), '< Back to all questions', function() { loadpage('questions'); })
	w.body = $a(w, 'div', 'qv-body');

}

pscript['refresh_question-view'] = function() {
	// href
	var qid = window.location.hash.split('/')[1];
	if(qid) {
		pscript.question_view(qid);
	}
}

pscript.question_view = function(qid, qtext) {
	var w = page_body.pages['question-view'];
	new KBQuestionView(w, qid, qtext);
}

KBQuestionView = function(w, qid, qtext) {
	var me = this;
	
	w.body.innerHTML = '';
	w.question_area = $a(w.body, 'div', 'social qv-question-wrapper');
	w.answer_area = $a(w.body, 'div', 'social qv-answer-wrapper');
	w.add_answer_link = $a(w.body, 'div', '', {margin:'3px 0px'});
	w.add_answer_area = $a(w.body, 'div', 'qv-add-answer');
	
	this.make_question = function() {
		new EditableText({
			parent: w.question_area,
			dt: 'Question',
			dn: qid,
			fieldname: 'question',
			text: qtext,
			inp_class: 'qv-input',
			disp_class: 'qv-text'
		});

		// show tags
	}
	
	// answer list
	this.make_answer_list = function() {
		this.ans_list = new KBAnswerList({
			parent: w.answer_area,
			qid: qid
		})
	}
	
	// check if users has answered 
	// (if no) then add a box to add a new answer
	this.make_add_answer = function() {
		$c_page('knowledge_base', 'question_view', 'has_answered', qid, function(r, rt) {
			if(r.message=='No') {
				me.make_answer_box_link();
			}
		});
	}
	
	// add a link to open add answer
	this.make_answer_box_link = function() {
		$a(w.add_answer_link, 'span', 'link_type', null, '+ Add your answer', 
			function() { 
				$dh(w.add_answer_link);
				me.make_answer_box();
			});
	}
	
	// answer box
	// text area + add button
	this.make_answer_box = function() {
		$ds(w.add_answer_area);
		$a(w.add_answer_area, 'h3', '', {}, 'Add Your Answer')
		this.input = $a(w.add_answer_area, 'textarea');
		wn.tinymce.add_simple(this.input);
		
		this.btn = $btn($a(w.add_answer_area, 'div'), 'Post', function() {
			var v = wn.tinymce.get_value(me.input);
			if(!v) { msgprint('Write something!'); return; }
			me.btn.set_working();
			$c_page('knowledge_base', 'question_view', 'add_answer', {qid: qid, answer:v}, 
				function(r, rt) {
					me.btn.done_working();
					me.ans_list.list.run();
					$dh(w.add_answer_area);
				}
			);
		});
	}
	
	this.setup = function() {
		if(qtext) {
			this.make();
		}
		else {
			$c_page('knowledge_base', 'question_view', 'get_question', qid, function(r, rt) {
				qtext = r.message;
				me.make();
			});
		}
	}
	
	this.make = function() {
		set_title(qtext);
		this.make_question();
		this.make_answer_list();
		this.make_add_answer();		
	}
	
	this.setup();
}


// kb answer list
KBAnswerList = function(args) {
	var me = this;
	$.extend(this, args);
	
	this.make_list = function() {
	
		this.list = new wn.widgets.Listing({
			parent: me.parent,
			as_dict: 1,
			no_results_message: 'No answers yet, be the first one to answer!',
			render_row: function(body, data) {
				new KBAnswer(body, data)
			},
			get_query: function() {
				return repl("SELECT t1.name, t1.owner, t1.answer, t1.points, t1._users_voted, t2.first_name, "
					+"t2.last_name, t1.modified from tabAnswer t1, tabProfile t2 "
					+"where question='%(qid)s' and t1.owner = t2.name "
					+"order by t1.points desc, t1.modified desc", {qid: me.qid})
			}
		});
		
		this.list.run();
		
	}
	
	this.make_list();
	
}

// kb answer
// answer
// by xxx | on xxx
// points yyy
KBAnswer = function(body, data) {
	body.className = 'qv-answer';
	new EditableText({
		parent: body,
		dt: 'Answer',
		dn: data.name,
		fieldname: 'answer',
		text: data.answer,
		inp_class: 'qv-ans-input',
		disp_class: 'qv-ans-text',
		rich_text: 1
	});	
	
	var div = $a(body, 'div', '', {})
	new KBItemToolbar({
		parent: div,
		det: data,
		with_tags: 0,
		doctype: 'Answer'
	}, null)
	
}


$import(knowledge_base/page/kb_common/kb_common.js);