erpnext.utils.CRMActivities = class CRMActivities {
	constructor(opts) {
		$.extend(this, opts);
	}

	refresh() {
		var me = this;
		$(this.open_activities_wrapper).empty();
		let cur_form_footer = this.form_wrapper.find(".form-footer");

		// all activities
		if (!$(this.all_activities_wrapper).find(".form-footer").length) {
			this.all_activities_wrapper.empty();
			$(cur_form_footer).appendTo(this.all_activities_wrapper);

			// remove frappe-control class to avoid absolute position for action-btn
			$(this.all_activities_wrapper).removeClass("frappe-control");
			// hide new event button
			$(".timeline-actions").find(".btn-default").hide();
			// hide new comment box
			$(".comment-box").hide();
			// show only communications by default
			$($(".timeline-content").find(".nav-link")[0]).tab("show");
		}

		// open activities
		frappe.call({
			method: "erpnext.crm.utils.get_open_activities",
			args: {
				ref_doctype: this.frm.doc.doctype,
				ref_docname: this.frm.doc.name,
			},
			callback: (r) => {
				if (!r.exc) {
					var activities_html = frappe.render_template("crm_activities", {
						tasks: r.message.tasks,
						events: r.message.events,
					});

					$(activities_html).appendTo(me.open_activities_wrapper);

					$(".open-tasks")
						.find(".completion-checkbox")
						.on("click", function () {
							me.update_status(this, "ToDo");
						});

					$(".open-events")
						.find(".completion-checkbox")
						.on("click", function () {
							me.update_status(this, "Event");
						});

					me.create_task();
					me.create_event();
				}
			},
		});
	}

	create_task() {
		let me = this;
		let _create_task = () => {
			const args = {
				doc: me.frm.doc,
				frm: me.frm,
				title: __("New Task"),
			};
			let composer = new frappe.views.InteractionComposer(args);
			composer.dialog.get_field("interaction_type").set_value("ToDo");
			// hide column having interaction type field
			$(composer.dialog.get_field("interaction_type").wrapper).closest(".form-column").hide();
			// hide summary field
			$(composer.dialog.get_field("summary").wrapper).closest(".form-section").hide();
		};
		$(".new-task-btn").click(_create_task);
	}

	create_event() {
		let me = this;
		let _create_event = () => {
			const args = {
				doc: me.frm.doc,
				frm: me.frm,
				title: __("New Event"),
			};
			let composer = new frappe.views.InteractionComposer(args);
			composer.dialog.get_field("interaction_type").set_value("Event");
			$(composer.dialog.get_field("interaction_type").wrapper).hide();
		};
		$(".new-event-btn").click(_create_event);
	}

	async update_status(input_field, doctype) {
		let completed = $(input_field).prop("checked") ? 1 : 0;
		let docname = $(input_field).attr("name");
		if (completed) {
			await frappe.db.set_value(doctype, docname, "status", "Closed");
			this.refresh();
		}
	}
};

erpnext.utils.CRMNotes = class CRMNotes {
	constructor(opts) {
		$.extend(this, opts);
	}

	refresh() {
		var me = this;
		this.notes_wrapper.find(".notes-section").remove();

		let notes = this.frm.doc.notes || [];
		notes.sort(function (a, b) {
			return new Date(b.added_on) - new Date(a.added_on);
		});

		let notes_html = frappe.render_template("crm_notes", {
			notes: notes,
		});
		$(notes_html).appendTo(this.notes_wrapper);

		this.add_note();

		$(".notes-section")
			.find(".edit-note-btn")
			.on("click", function () {
				me.edit_note(this);
			});

		$(".notes-section")
			.find(".delete-note-btn")
			.on("click", function () {
				me.delete_note(this);
			});
	}

	add_note() {
		let me = this;
		let _add_note = () => {
			var d = new frappe.ui.Dialog({
				title: __("Add a Note"),
				fields: [
					{
						label: "Note",
						fieldname: "note",
						fieldtype: "Text Editor",
						reqd: 1,
						enable_mentions: true,
					},
				],
				primary_action: function () {
					var data = d.get_values();
					frappe.call({
						method: "add_note",
						doc: me.frm.doc,
						args: {
							note: data.note,
						},
						freeze: true,
						callback: function (r) {
							if (!r.exc) {
								me.frm.refresh_field("notes");
								me.refresh();
							}
							d.hide();
						},
					});
				},
				primary_action_label: __("Add"),
			});
			d.show();
		};
		$(".new-note-btn").click(_add_note);
	}

	edit_note(edit_btn) {
		var me = this;
		let row = $(edit_btn).closest(".comment-content");
		let row_id = row.attr("name");
		let row_content = $(row).find(".content").html();
		if (row_content) {
			var d = new frappe.ui.Dialog({
				title: __("Edit Note"),
				fields: [
					{
						label: "Note",
						fieldname: "note",
						fieldtype: "Text Editor",
						default: row_content,
					},
				],
				primary_action: function () {
					var data = d.get_values();
					frappe.call({
						method: "edit_note",
						doc: me.frm.doc,
						args: {
							note: data.note,
							row_id: row_id,
						},
						freeze: true,
						callback: function (r) {
							if (!r.exc) {
								me.frm.refresh_field("notes");
								me.refresh();
								d.hide();
							}
						},
					});
				},
				primary_action_label: __("Done"),
			});
			d.show();
		}
	}

	delete_note(delete_btn) {
		var me = this;
		let row_id = $(delete_btn).closest(".comment-content").attr("name");
		frappe.call({
			method: "delete_note",
			doc: me.frm.doc,
			args: {
				row_id: row_id,
			},
			freeze: true,
			callback: function (r) {
				if (!r.exc) {
					me.frm.refresh_field("notes");
					me.refresh();
				}
			},
		});
	}
};
