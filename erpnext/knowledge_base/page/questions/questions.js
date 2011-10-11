pscript.onload_questions = function() {
	var w = page_body.pages['questions'];
	
	var tab = make_table(w, 1, 2, '100%', ['75%', '25%'], {});
	var body = $a($td(tab,0,0),'div','layout_wrapper');

	new PageHeader(body, 'Knowledge Base');

	// kb
	var kb = new KnowledgeBase(body);
	
	// sidebar
	$y($td(tab, 0, 1), {paddingTop:'53px'});
	this.sidebar = new wn.widgets.PageSidebar($td(tab, 0, 1), {
		sections: [
			{
				title: 'Top Tags',
				render: function(body) {
					new wn.widgets.TagCloud(body, 'Question', function(tag) { kb.set_tag_filter(tag) });
				}				
			}
		]
	});
	set_title('Knowledge Base');
}

// knowledge base object
// has a box for search or ask a question
// and list of top rated search results
//
function KnowledgeBase(w) {
	var me = this;
	this.sort_by = 'modified';
	this.tag_filter_dict = {};
	
	this.make_search_bar = function() {
		this.search = $a($a(w,'div','kb-search-wrapper'), 'textarea');

		$(this.search).add_default_text('Enter keywords or a new Question');
		
		var div = $a(w,'div','kb-btn-wrapper');
		$btn(div, 'Search', function() { me.run() }, {fontSize:'14px'});
		$btn(div, 'Ask', function() { me.ask() }, {fontSize:'14px'});
	}
	
	// ask a new question
	this.ask = function() {
		if(this.search.value==$(this.search).attr('default_text')) {
			msgprint('Please enter some text'); return;
		}
		this.suggest();
	}
	
	// suggest a few users who can answer
	this.suggest = function() {
		this.dialog = new wn.widgets.Dialog({
			title: 'Suggest a users',
			width: 400,
			fields: [
				{fieldtype:'HTML', options:'Optional: Suggest a few users who can help you answer this question<br>'},
				{fieldtype:'Link', fieldname:'profile1', label:'1st User',options:'Profile'},
				{fieldtype:'Link', fieldname:'profile2', label:'2nd User',options:'Profile'},
				{fieldtype:'Link', fieldname:'profile3', label:'3rd User',options:'Profile'},
				{fieldtype:'Button', fieldname:'ask', label:'Add the Question'}
			]
		});
		this.dialog.fields_dict.ask.input.onclick = function() {
			me.dialog.hide();
			me.add_question(values(me.dialog.get_values()));
		}
		this.dialog.show();
	}
	
	// add a new question to the database
	this.add_question = function(suggest_list) {
		$c_page('knowledge_base', 'questions', 'add_question', {
			question: this.search.value,
			suggest: suggest_list
		}, function(r,rt) {
			$(me.search).val('').blur();
			me.run();
		})
	}
	
	// where tags that filter will be displayed
	this.make_tag_filter_area = function() {
		this.tag_filters = $a(w, 'div', 'kb-tag-filter-area');
		$a(this.tag_filters,'span','',{marginRight:'4px',color:'#442'}, '<i>Showing for:</i>');
		this.tag_area = $a(this.tag_filters, 'span');
	}
	
	// make a list of questions
	this.make_list = function() {
		this.make_tag_filter_area();
		this.list_area = $a(w, 'div', '', {marginRight:'13px'})
		this.no_result = $a(w, 'div','help_box',{display:'none'},'No questions asked yet! Be the first one to ask')

		this.list = new wn.widgets.Listing({
			parent: this.list_area,
			no_results_message: 'No questions found. Ask a new question!',
			as_dict: 1,
			get_query: function() {
				
				// filter by search string
				var v = me.search.value==$(me.search).attr('default_text') ? '' : me.search.value;
				cond = v ? (' and t1.question like "%'+v+'%"') : '';
				
				// filter by tags
				if(me.tag_filter_dict) {
					for(f in me.tag_filter_dict) {
						cond += ' and t1.`_user_tags` like "%' + f + '%"'
					}
				}
				return repl('select t1.name, t1.owner, t1.question, t1.points, t1.modified, t1._user_tags, '
				+'t1._users_voted, t2.first_name, t2.last_name '
				+'from tabQuestion t1, tabProfile t2 '
				+'where t1.docstatus!=2 '
				+'and t1.owner = t2.name'
				+'%(cond)s order by t1.modified desc', {user:user, cond: cond})
			},
			render_row: function(parent, data, listing) {
				new KBQuestion(parent, data, me);
			}
		});
		
		this.list.run();

	}

	// add a tag filter to the search in the
	// main page
	this.set_tag_filter = function(tag) {

		// check if exists
		if(in_list(keys(me.tag_filter_dict), tag.label)) return;

		// create a tag in filters
		var filter_tag = new SingleTag({
			parent: me.tag_area,
			label: tag.label,
			dt: 'Question',
			color: tag.color
		});

		// remove tag from filters
		filter_tag.remove = function(tag_remove) {
			$(tag_remove.body).fadeOut();
			delete me.tag_filter_dict[tag_remove.label];

			// hide everything?
			if(!keys(me.tag_filter_dict).length) {
				$(me.tag_filters).slideUp(); // hide
			}

			// run
			me.run();
		}

		// add to dict
		me.tag_filter_dict[tag.label] = filter_tag;
		$ds(me.tag_filters);

		// run
		me.run();
	}	
	this.run = function() {
		this.list.run();
	}

	this.make_search_bar();
	this.make_list();
	
}

// single kb question
// "question
//  points | tag list"

KBQuestion = function(parent, det, kb) {
	
	this.make = function() {
		this.wrapper = $a(parent, 'div', 'kb-question-wrapper');
		this.q_area = $a($a(this.wrapper, 'div'), 'h3', 'kb-questions link_type', {display:'inline', textDecoration:'none'}, det.question);

		this.q_area.onclick = function() {
			var q = this;
			window.location.href = '#!question-view/' + q.id;
			//loadpage('question-view', function() { pscript.question_view(q.id, q.txt) })
		}
		
		this.q_area.id = det.name; this.q_area.txt = det.question;

		new KBItemToolbar({
			parent: this.wrapper,
			det: det,
			with_tags: 1,
			doctype: 'Question'
		}, kb)
		
	}
	

	this.make()
}

$import(knowledge_base/page/kb_common/kb_common.js);