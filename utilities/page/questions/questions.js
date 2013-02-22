// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

pscript.onload_questions = function(wrapper) {
	body = $(wrapper).find('.layout-main-section').get(0);
	
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.layout-appframe'));
	wrapper.appframe.add_home_breadcrumb();
	wrapper.appframe.add_breadcrumb(wn.modules["Knowledge Base"].icon);
	wrapper.appframe.title('Knowledge Base');
	
	// kb
	var kb = new KnowledgeBase(body);
	
	wn.model.with_doctype("Question", function() {
		this.sidebar_stats = new wn.views.SidebarStats({
			doctype: "Question",
			stats: ["_user_tags"],
			parent: $(wrapper).find('.questions-tags'),
			set_filter: function(fieldname, label) {
				kb.set_filter(fieldname, label);
				//me.set_filter(fieldname, label);
			}
		});	
	})
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
		this.search = $(w).find('.kb-search-wrapper textarea').get(0);
		
		$(w).find('.btn.search').click(function() {
			me.run();
		})
		$(w).find('.btn.ask').click(function() {
			me.ask();
		})
	}
	
	// ask a new question
	this.ask = function() {
		if(this.search.value==$(this.search).attr('default_text')) {
			msgprint('Please enter some text'); return;
		}
		this.add_question([]);
	}
	
	// suggest a few users who can answer
	this.suggest = function() {
		this.dialog = new wn.ui.Dialog({
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
		$c_page('utilities', 'questions', 'add_question', {
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

		this.list = new wn.ui.Listing({
			parent: this.list_area,
			no_results_message: 'No questions found. Ask a new question!',
			appframe: wn.pages.questions.appframe,
			as_dict: 1,
			method: 'utilities.page.questions.questions.get_questions',
			get_args: function() {
				var args = {};
				if(me.search.value) {
					args.search_text = me.search.value;
				}
				if(me.tag_filter_dict) {
					args.tag_filters = keys(me.tag_filter_dict);
				}
				return args
			},
			render_row: function(parent, data, listing) {
				new KBQuestion(parent, data, me);
			}
		});
		
		this.list.run();

	}

	this.set_filter = function(fieldname, label) {
		this.set_tag_filter({label:label});
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
		this.q_area = $a($a(this.wrapper, 'div'), 'h3', 
			'kb-questions link_type', {display:'inline', textDecoration:'none'}, det.question);
		if(det.answers==0) {
			$(this.q_area).addClass('un-answered')
		}

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

wn.require('app/js/kb_common.js');
