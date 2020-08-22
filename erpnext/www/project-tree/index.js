frappe.ready(() => {
	let $wrapper = document.getElementsByClassName("layout-main-section");

	frappe.call({
		method: "erpnext.projects.page.project_tree.project.get_meta",
		callback: function(r) {
			new WebProjectTree({
				doctype: "Project",
				parent: $wrapper[0],
				project: r.message.project,
				task: r.message.task
			});
		}
	})
});

class WebProjectTree extends erpnext.projects.ProjectTree {
	constructor(opts) {
		super(opts);
		Object.assign(this, opts);
		this.show();
	}

	setup_defaults() {
		this.page_title = __("Project");

		this.meta = this.project;
		this.task_meta = this.task;

		this.task_fields = [];
		this.task_columns = [];

		this.start = 0;
		this.data = [];
		this.settings = {};

		this.get_settings("Project", "listview_settings");
		this.get_settings("Task", "task_listview_settings");

		this.menu_items = [];

		this.fields = [];
		this.filters = [];
		this.sort_by = 'modified';
		this.sort_order = 'desc';
	}

	set_title(title) {
		let title_el = $(document.getElementsByClassName("title-text")[0]);
		title_el.html(__(title));
	}

	setup_list_wrapper() {
		this.$frappe_list = $('<div class="frappe-list">').appendTo(this.parent);
	}

	comment_when(datetime, mini) {
		var timestamp = datetime;
		return '<span class="frappe-timestamp '
			+ (mini ? " mini" : "") + '" data-timestamp="' + datetime
			+ '" title="' + timestamp + '">'
			+ this.prettyDate(datetime, mini) + '</span>';
	}

	convert_to_user_tz(date) {
		return new Date((date || "").replace(/-/g, "/").replace(/[TZ]/g, " ").replace(/\.[0-9]*/, ""));
	}

	get_avatar() {
		return `<span class="avatar avatar-small avatar-empty"></span>`;
	}

	get_tasks() {
		this.$result.on('click', '.project-list-row-container', (e) => {
			this.set_title("Task Tree");
			this.fetch_tasks(unescape(e.currentTarget.getAttribute("data-name")));
		});
	}

	get_projects() {
		this.$frappe_list.on('click', '.btn-prev', () => {
			this.set_title("Project");
			this.remove_previous_button();
			this.render_header(this.columns, true);
			this.fetch_projects();
		})
	}

	refresh() {
		this.fetch_projects();
	}

	fetch_projects() {
		frappe.call(this.get_call_args([["Project", "show_in_portal", "=", 1]])).then(r => {
			// render
			this.render_header(this.columns, true);
			this.prepare_data(r);
			this.toggle_result_area();
			this.render();
		});
	}

	fetch_tasks(project) {
		let filters = [
			["Task", "project", "=", project],
			["Task", "show_in_portal", "=", 1]
		];

		frappe.call(this.get_task_call_args(filters)).then(r => {
			// render
			this.render_header(this.task_columns, true);
			this.prepare_data(r);
			this.toggle_result_area();
			this.render("Task", true);
			this.render_previous_button();
		});
	}

	get_task_call_args(filters) {
		return {
			method: "erpnext.projects.page.project_tree.project.get_tasks_for_portal",
			args: {
				params: {
					doctype: "Task",
					fields: this.get_task_fields(),
					filters: filters,
					with_comment_count: true,
					user: frappe.session.user,
					page_length: this.page_length,
					ignore_permissions: true
				}
			}
		};
	}

	get_call_args(filters) {
		return {
			method: "erpnext.projects.page.project_tree.project.get_projects_data",
			args: {
				params: {
					doctype: "Project",
					fields: this.get_fields(),
					filters: filters || this.get_filters_for_args(),
					with_comment_count: true,
					page_length: this.page_length,
					start: this.start,
					ignore_permissions: true
				}
			}
		};
	}

	get_fields_in_list_view(doctype, meta) {
		return meta.fields.filter(df => {
			return frappe.model.is_value_type(df.fieldtype) && (
				df.in_list_view
			) || (
				df.fieldtype === 'Currency'
				&& df.options
				&& !df.options.includes(':')
			) || (
				df.fieldname === 'status'
			);
		});
	}

	get_open_button() {
		return ``;
	}

	get_add_child_button() {
		return ``;
	}

	_add_task_field(fieldname) {
		if (!fieldname) return;
		let doctype = "Task";

		if (typeof fieldname === 'object') {
			// df is passed
			const df = fieldname;
			fieldname = df.fieldname;
			doctype = df.parent;
		}

		if (!this.task_fields) this.task_fields = [];

		if (!this.is_valid(this.task_meta.fields, fieldname)) {
			return;
		}

		this.task_fields.push([fieldname, doctype]);
	}

	_add_field(fieldname, doctype) {
		if (!fieldname) return;

		if (!doctype) doctype = this.doctype;

		if (typeof fieldname === 'object') {
			// df is passed
			const df = fieldname;
			fieldname = df.fieldname;
			doctype = df.parent;
		}

		if (!this.fields) this.fields = [];

		if (!this.is_valid(this.meta.fields, fieldname)) {
			return;
		}

		this.fields.push([fieldname, doctype]);
	}

	is_valid(fields, fieldname) {
		return (frappe.model.std_fields_list.includes(fieldname)
			|| fields.find(el => el.fieldname == fieldname) || fieldname === '_seen');
	}

	get_df(doctype, fieldname) {
		let meta = doctype === "Project" ? this.meta : this.task_meta;
		return meta.fields.find(el => el.fieldname === fieldname);
	}

	toggle_result_area() {
		this.$result.toggle(this.data.length > 0);
		this.$no_result.toggle(this.data.length == 0);
		this.$no_result_prev.toggle(this.data.length == 0);
	}

	get_subject_link(doc, subject, escaped_subject) {
		if (doc.doctype === 'Project') {
			return `<span class="ellipsis" title="${escaped_subject}" data-doctype="${doc.doctype}" data-name="${doc.name}">
				${subject}
			</span>`;
		} else {
			return `<a href ="/tasks?name=${doc.name}" class="ellipsis" title="${escaped_subject}" data-doctype="${doc.doctype}" data-name="${doc.name}">
				${subject}
			</a>`;
		}
	}

	setup_page() {}

	set_stats() {}

	setup_filter_area() {}

	setup_sort_selector() {}

	setup_paging_area() {}
}

frappe.datetime.refresh_when = function() {};