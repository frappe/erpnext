// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exercise Type', {
	refresh: function(frm) {
		let wrapper = frm.fields_dict.steps_html.wrapper;

		frm.ExerciseEditor = new erpnext.ExerciseEditor(frm, wrapper);
	}
});

erpnext.ExerciseEditor = Class.extend({
	init: function(frm, wrapper) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.make(frm, wrapper);
	},

	make: function(frm, wrapper) {
		$(this.wrapper).empty();

		this.exercise_toolbar = $('<p>\
		<button class="btn btn-default btn-add btn-xs" style="margin-left: 10px;"></button>').appendTo(this.wrapper);

		this.exercise_cards = $('<div class="exercise-cards"></div>').appendTo(this.wrapper);

		this.row = $('<div class="exercise-row"></div>').appendTo(this.wrapper);

		let me = this;

		this.exercise_toolbar.find(".btn-add")
			.html(__('Add'))
			.on("click", function() {
				me.show_add_card_dialog(frm);
			});

		if (frm.doc.steps_table && frm.doc.steps_table.length > 0) {
			this.make_cards(frm);
			this.make_buttons(frm);
		}
	},

	make_cards: function(frm) {
		var me = this;
		$(me.exercise_cards).empty();

		$.each(frm.doc.steps_table, function(i, step) {
			$(repl(`
				<div class="exercise-col col-sm-4" id="%(col_id)s">
					<div class="card h-100 exercise-card" id="%(card_id)s">
						<div class="card-body exercise-card-body">
							<img src=%(image_src)s class="card-img-top" alt="...">
							<h4 class="card-title">%(title)s</h4>
							<p class="card-text text-truncate">%(description)s</p>
						</div>
						<div class="card-footer">
							<button class="btn btn-default btn-xs btn-edit" data-id="%(id)s"><i class="fa fa-pencil" aria-hidden="true"></i></button>
							<button class="btn btn-default btn-xs btn-del" data-id="%(id)s"><i class="fa fa-trash" aria-hidden="true"></i></button>
						</div>
					</div>
			</div>`, {image_src: step.image, title: step.title, description: step.description, col_id: "col-"+i, card_id: "card-"+i, id: i})).appendTo(me.row);
		});
	},

	make_buttons: function(frm) {
		let me = this;
		$('.btn-edit').on('click', function() {
			let id = $(this).attr('data-id');
			me.show_edit_card_dialog(frm, id);
		});

		$('.btn-del').on('click', function() {
			let id = $(this).attr('data-id');
			$('#card-'+id).addClass("zoom-out");

			setTimeout(() => {
				// not using grid_rows[id].remove because
				// grid_rows is not defined when the table is hidden
				frm.doc.steps_table.pop(id);
				frm.refresh_field('steps_table');
				$('#col-'+id).remove();
				frm.dirty();
			}, 300);
		});
	},

	show_add_card_dialog: function(frm) {
		let me = this;
		let d = new frappe.ui.Dialog({
			title: __('Add Exercise Step'),
			fields: [
				{
					"label": "Title",
					"fieldname": "title",
					"fieldtype": "Data",
					"reqd": 1
				},
				{
					"label": "Attach Image",
					"fieldname": "image",
					"fieldtype": "Attach Image"
				},
				{
					"label": "Step Description",
					"fieldname": "step_description",
					"fieldtype": "Long Text"
				}
			],
			primary_action: function() {
				let data = d.get_values();
				let i = 0;
				if (frm.doc.steps_table) {
					i = frm.doc.steps_table.length;
				}
				$(repl(`
					<div class="exercise-col col-sm-4" id="%(col_id)s">
						<div class="card h-100 exercise-card" id="%(card_id)s">
							<div class="card-body exercise-card-body">
								<img src=%(image_src)s class="card-img-top" alt="...">
								<h4 class="card-title">%(title)s</h4>
								<p class="card-text text-truncate">%(description)s</p>
							</div>
							<div class="card-footer">
								<button class="btn btn-default btn-xs btn-edit" data-id="%(id)s"><i class="fa fa-pencil" aria-hidden="true"></i></button>
								<button class="btn btn-default btn-xs btn-del" data-id="%(id)s"><i class="fa fa-trash" aria-hidden="true"></i></button>
							</div>
						</div>
					</div>`, {image_src: data.image, title: data.title, description: data.step_description, col_id: "col-"+i, card_id: "card-"+i, id: i})).appendTo(me.row);
				let step = frappe.model.add_child(frm.doc, 'Exercise Type Step', 'steps_table');
				step.title = data.title;
				step.image = data.image;
				step.description = data.step_description;
				me.make_buttons(frm);
				frm.refresh_field('steps_table');
				d.hide();
			},
			primary_action_label: __('Add')
		});
		d.show();
	},

	show_edit_card_dialog: function(frm, id) {
		let new_dialog = new frappe.ui.Dialog({
			title: __("Edit Exercise Step"),
			fields: [
				{
					"label": "Title",
					"fieldname": "title",
					"fieldtype": "Data",
					"reqd": 1
				},
				{
					"label": "Attach Image",
					"fieldname": "image",
					"fieldtype": "Attach Image"
				},
				{
					"label": "Step Description",
					"fieldname": "step_description",
					"fieldtype": "Long Text"
				}
			],
			primary_action: () => {
				let data = new_dialog.get_values();
				$('#card-'+id).find('.card-title').html(data.title);
				$('#card-'+id).find('img').attr('src', data.image);
				$('#card-'+id).find('.card-text').html(data.step_description);

				frm.doc.steps_table[id].title = data.title;
				frm.doc.steps_table[id].image = data.image;
				frm.doc.steps_table[id].description = data.step_description;
				refresh_field('steps_table');
				frm.dirty();
				new_dialog.hide();
			},
			primary_action_label: __("Edit"),
		});

		new_dialog.set_values({
			title: frm.doc.steps_table[id].title,
			image: frm.doc.steps_table[id].image,
			step_description: frm.doc.steps_table[id].description
		});
		new_dialog.show();
	}
});
