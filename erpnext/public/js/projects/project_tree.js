frappe.provide('frappe.views');
frappe.provide("erpnext.projects");

erpnext.projects.ProjectTree = class Projects extends frappe.views.BaseList {
	constructor(opts) {
		super(opts);
		this.show();
		window.cur_list = this;
	}

	setup_defaults() {
		super.setup_defaults();

		this.task_meta = frappe.get_meta("Task");

		this.task_fields = [];
		this.task_columns = [];
		this.get_settings("Project", "listview_settings");
		this.get_settings("Task", "task_listview_settings");

		this.menu_items = [];
	}

	setup_page() {
		this.$page = $(this.parent);
		this.page && this.page.page_form.removeClass('row').addClass('flex');
		this.setup_page_head();
	}

	setup_page_head() {
		this.set_title("Projects");
		this.set_menu_items("Project");
		this.set_breadcrumbs();
	}

	set_menu_items(doctype) {

		const bulk_delete = () => {
			return {
				label: __('Delete'),
				action: () => {
					const docnames = this.get_checked_items(true).map(docname => docname.toString());
					frappe.confirm(__('Delete {0} items permanently?', [docnames.length]),
						() => {
							frappe.call({
								method: 'frappe.desk.reportview.delete_items',
								freeze: true,
								args: {
									items: docnames,
									doctype: doctype
								}
							}).then((r) => {
								let failed = r.message;
								if (!failed) failed = [];

								if (failed.length && !r._server_messages) {
									frappe.throw(__('Cannot delete {0}', [failed.map(f => f.bold()).join(', ')]));
								}

								if (failed.length < docnames.length) {
									frappe.utils.play_sound('delete');
								}

								this.refresh();
							});
						});
				},
				standard: true,
			};
		};

		if (frappe.user.has_role('System Manager')) {
			this.menu_items.push({
				label: __('Project Settings'),
				action: () => this.show_list_settings("Project", this.listview_settings),
				standard: true
			});

			this.menu_items.push({
				label: __('Task Settings'),
				action: () => this.show_list_settings("Task", this.task_listview_settings),
				standard: true
			});
		}

		// bulk delete
		if (frappe.model.can_delete(doctype)) {
			this.menu_items.push(bulk_delete());
		}

		this.page && this.menu_items.map(item => {
			const $item = this.page.add_menu_item(item.label, item.action, item.standard, item.shortcut);
			if (item.class) {
				$item && $item.addClass(item.class);
			}
		});
	}

	show_list_settings(doctype, settings) {
		frappe.model.with_doctype(doctype, () => {
			new frappe.views.ListSettings({
				listview: this,
				doctype: doctype,
				settings: settings,
				meta: frappe.get_meta(doctype)
			});
		});
	}

	refresh_columns() {
		this.show();
	}

	set_title(title) {
		this.page && this.page.set_title(title);
	}

	setup_view() {
		this.columns = this.setup_columns("Project", this.meta, this.listview_settings);
		this.task_columns = this.setup_columns("Task", this.task_meta, this.task_listview_settings);

		this.render_header(this.columns);
		this.render_skeleton();
		this.setup_events();
	}

	setup_fields() {
		super.setup_fields();

		this.set_task_fields();
		this.build_task_fields();
	}

	set_task_fields() {
		let fields = [].concat(
			frappe.model.std_fields_list,
			this.get_fields_in_list_view("Task", this.task_meta),
			[this.meta.title_field, this.meta.image_field],
			(this.settings.add_fields || []),
			this.meta.track_seen ? '_seen' : null,
			this.sort_by,
			'enabled',
			'disabled',
			'color'
		);

		fields.forEach(f => this._add_task_field(f));

		this.task_fields.forEach(f => {
			const df = frappe.meta.get_docfield(f[1], f[0]);
			if (df && df.fieldtype === 'Currency' && df.options && !df.options.includes(':')) {
				this._add_field(df.options);
			}
		});
	}

	build_task_fields() {
		// fill in missing doctype
		this.task_fields = this.task_fields.map(f => {
			if (typeof f === 'string') {
				f = [f, this.doctype];
			}
			return f;
		});
		// remove null or undefined values
		this.task_fields = this.task_fields.filter(Boolean);
		// de-duplicate
		this.task_fields = this.task_fields.uniqBy(f => f[0] + f[1]);
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

		const is_valid_field = frappe.model.std_fields_list.includes(fieldname)
			|| frappe.meta.has_field(doctype, fieldname)
			|| fieldname === '_seen';

		if (!is_valid_field) {
			return;
		}

		this.task_fields.push([fieldname, doctype]);
	}

	get_df(doctype, fieldname) {
		return frappe.meta.get_docfield(doctype, fieldname);
	}

	setup_columns(doctype, meta, list_view_settings) {
		// setup columns for list view
		let columns = [];

		// 1st column: title_field or name
		if (meta.title_field) {
			columns.push({
				type: 'Subject',
				df: this.get_df(doctype, meta.title_field)
			});
		} else {
			columns.push({
				type: 'Subject',
				df: {
					label: __('Name'),
					fieldname: 'name'
				}
			});
		}

		// 2nd column: Status indicator
		if (frappe.has_indicator(doctype)) {
			// indicator
			columns.push({
				type: 'Status'
			});
		}

		const fields_in_list_view = this.get_fields_in_list_view(doctype, meta);
		// Add rest from in_list_view docfields
		columns = columns.concat(
			fields_in_list_view
				.filter(df => {
					if (frappe.has_indicator(doctype) && df.fieldname === 'status') {
						return false;
					}
					if (!df.in_list_view) {
						return false;
					}
					return df.fieldname !== meta.title_field;
				})
				.map(df => ({
					type: 'Field',
					df
				}))
		);

		if (list_view_settings && list_view_settings.fields) {
			columns = this.reorder_listview_fields(columns, list_view_settings.fields);
		}

		// limit max to 8 columns if no total_fields is set in List View Settings
		// Screen with low density no of columns 4
		// Screen with medium density no of columns 6
		// Screen with high density no of columns 8
		let total_fields = 6;

		if (window.innerWidth <= 1366) {
			total_fields = 4;
		} else if (window.innerWidth >= 1920) {
			total_fields = 8;
		}

		if (list_view_settings && list_view_settings.total_fields) {
			total_fields = parseInt(list_view_settings.total_fields);
		}

		return columns.slice(0, total_fields);
	}

	reorder_listview_fields(columns, fields) {
		let fields_order = [];
		fields = JSON.parse(fields);

		// title_field is fixed
		fields_order.push(columns[0]);
		columns.splice(0, 1);

		for (let fld in fields) {
			for (let col in columns) {
				let field = fields[fld];
				let column =columns[col];

				if (column.type == "Status" && field.fieldname == "status_field") {
					fields_order.push(column);
					break;
				} else if (column.type == "Field" && field.fieldname === column.df.fieldname) {
					fields_order.push(column);
					break;
				}
			}
		}

		return fields_order;
	}

	get_fields_in_list_view(doctype, meta) {
		return meta.fields.filter(df => {
			return frappe.model.is_value_type(df.fieldtype) && (
				df.in_list_view
				&& frappe.perm.has_perm(doctype, df.permlevel, 'read')
			) || (
				df.fieldtype === 'Currency'
				&& df.options
				&& !df.options.includes(':')
			) || (
				df.fieldname === 'status'
			);
		});
	}

	render_skeleton() {
		const $row = this.get_list_row_html_skeleton('<div><input type="checkbox" /></div>');
		this.$result.append($row);
	}

	set_fields() {
		let fields = [].concat(
			frappe.model.std_fields_list,
			this.get_fields_in_list_view("Project", this.meta),
			[this.meta.title_field, this.meta.image_field],
			(this.settings.add_fields || []),
			this.meta.track_seen ? '_seen' : null,
			this.sort_by,
			'enabled',
			'disabled',
			'color'
		);

		fields.forEach(f => this._add_field(f));

		this.fields.forEach(f => {
			const df = frappe.meta.get_docfield(f[1], f[0]);
			if (df && df.fieldtype === 'Currency' && df.options && !df.options.includes(':')) {
				this._add_field(df.options);
			}
		});
	}

	get_task_fields() {
		// convert [fieldname, Doctype] => tabDoctype.fieldname
		return this.task_fields.map(f => frappe.model.get_full_column_name(f[0], f[1]));
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
					start: this.start
				}
			}
		};
	}

	get_task_call_args(filters) {
		return {
			method: "erpnext.projects.page.project_tree.project.get_tasks",
			args: {
				params: {
					doctype: "Task",
					fields: this.get_task_fields(),
					filters: filters,
					with_comment_count: true,
					page_length: this.page_length,
				}
			}
		};
	}

	setup_side_bar() {}

	get_settings(doctype, attr) {
		return frappe.call({
			method: "frappe.desk.listview.get_list_settings",
			args: {
				doctype: doctype
			},
			async: false
		}).then(doc => this[attr] = doc.message || {});
	}

	setup_events() {
		this.get_tasks();
		this.setup_check_events();
		this.setup_open_doc();
		this.setup_task_tree_dropdown();
		this.setup_create_new_task();
		this.get_projects();
		this.setup_expand_all_rows();
		this.setup_collapse_all_rows();
	}

	setup_task_tree_dropdown() {
		this.$result.on('click', '.btn-action', (e) => {
			let el = e.currentTarget;
			let $el = $(el);
			$el.find(".octicon").removeClass("octicon-chevron-right").addClass("octicon-chevron-down");

			let target = unescape(el.getAttribute("data-name"));
			this.render_task(target, $el);
		});
	}

	render_task(task, $el, expand_all) {
		let $row = this.$result.find(`.list-rows[data-name="${task}"]`);
		if (!$row || (!$row.length)) return;

		if (!$el) {
			$el = $row.find(".octicon").removeClass("octicon-chevron-right").addClass("octicon-chevron-down");
		}

		let list = $row.find(`.nested-list-row-container`);
		let $list = $(list);
		let level = parseInt($row[0].getAttribute("data-level")) + 1;
		let $result = $(`<div class="nested-result">`);

		$list.toggleClass("hide");

		if ($list[0].classList.contains("hide")) {
			$list.find(`.nested-result`).remove();
			$el.find(".octicon").removeClass("octicon-chevron-down").addClass("octicon-chevron-right");
		}

		frappe.call(this.get_task_call_args([["Task", "parent_task", "=", task]])).then(r => {
			// render
			this.prepare_data(r);

			list.append($result);
			this.data.map((doc, i) => {
				doc._idx = i;
				doc.doctype = 'Task';
				$result.append(this.get_task_list_row_html(doc, level));
			});

			if (expand_all) {
				this.$result.find(".expand-all").click();
			}
		});
	}

	setup_open_doc() {
		this.$result.on('click', '.btn-open', (e) => {
			e.stopPropagation();
			let el = e.currentTarget;
			let doctype = unescape(el.getAttribute("data-doctype"));
			let name = unescape(el.getAttribute("data-name"));
			frappe.set_route("Form", doctype, name);
		});
	}

	setup_create_new_task() {
		this.$result.on('click', '.create-new', (e) => {
			let parent = unescape(e.currentTarget.getAttribute("data-name"));
			let project = unescape(e.currentTarget.getAttribute("data-project"));
			let task = frappe.model.get_new_doc("Task");
			task["project"] = project;
			task["parent_task"] = parent;

			frappe.ui.form.make_quick_entry("Task", null, null, task);
		});
	}

	get_projects() {
		this.$frappe_list.on('click', '.btn-prev', () => {
			this.filter_area.clear(false);
			this.set_title("Project");
			this.remove_previous_button();
			this.render_header(this.columns, true);
			this.filter_area.refresh_filters(this.meta);
			this.fetch_projects();
		});
	}

	fetch_projects() {
		frappe.call(this.get_call_args([])).then(r => {
			// render
			this.render_header(this.columns, true);
			this.prepare_data(r);
			this.toggle_result_area();
			this.render();
		});
	}

	get_tasks() {
		this.$result.on('click', '.project-list-row-container', (e) => {
			this.filter_area.clear(false);
			this.set_title("Task Tree");
			this.filter_area.refresh_filters(this.task_meta);
			this.fetch_tasks(unescape(e.currentTarget.getAttribute("data-name")));
		});
	}

	fetch_tasks(project) {
		if (project) {
			this.filter_area.add([["Task", "project", "=", project]], false);
		}

		let filters = this.get_filters_for_args();
		filters.push(["Task", "parent_task", "=", '']);

		frappe.call(this.get_task_call_args(filters)).then(r => {
			// render
			this.render_header(this.task_columns, true);
			this.prepare_data(r);

			this.render("Task", true, project);
			this.render_previous_button();
		});
	}

	setup_expand_all_rows() {
		this.$result.on('click', '.expand-all', () => {
			let task_list = this.$result.find(".octicon-chevron-right").parent();
			this.toggle_expand_collapse_button('expand');

			if (!task_list) return
			task_list.map((i, task) => {
				let task_name = task.getAttribute("data-name");
				if (task_name) {
					this.render_task(task_name, null, true);
				}
			});
		});
	}

	setup_collapse_all_rows() {
		this.$result.on('click', '.collapse-all', () => {
			let task_list = this.$result.find(".octicon-chevron-down").parent();
			this.toggle_expand_collapse_button('collapse');

			if (!task_list) return
			task_list.map((i, task) => {
				let task_name = task.getAttribute("data-name")
				let $row = this.$result.find(`.list-rows[data-name="${task_name}"]`);
				let list = $row.find(`.nested-list-row-container`);
				let $list = $(list);
				$list.toggleClass("hide");

				if ($list.length && $list[0].classList.contains("hide")) {
					$list.find(`.nested-result`).remove();
					$row.find(".octicon").removeClass("octicon-chevron-down").addClass("octicon-chevron-right");
				}
			});

		});
	}

	toggle_expand_collapse_button(action) {
		let hide = (action == 'expand') ? '.expand-all': '.collapse-all';
		let show = (action == 'expand') ? '.collapse-all': '.expand-all';

		this.$result.find(hide).hide();
		this.$result.find(show).show();
	}

	render(doctype, is_task=false, project=null) {
		// clear rows
		this.$result.find('.list-row-container').remove();
		if (this.data.length > 0) {
			// append rows
			this.$result.append(
				this.data.map((doc, i) => {
					doc._idx = i;
					doc.doctype = doctype || this.doctype;

					if (is_task && project) {
						doc.project = project;
					}

					return is_task ? this.get_task_list_row_html(doc, 0) : this.get_list_row_html(doc);
				}).join('')
			);
		}
	}

	setup_no_result_area() {
		this.$no_result = $(`
			<div class="no-result text-muted flex justify-center align-center">
				${this.get_no_result_message()}
			</div>
		`).hide();
		this.$no_result_prev = $(this.get_previous_header_html()).hide();

		this.$frappe_list.append(this.$no_result_prev);
		this.$frappe_list.append(this.$no_result);
	}

	toggle_result_area() {
		this.$result.toggle(this.data.length > 0);
		this.$paging_area.toggle(this.data.length > 0);
		this.$no_result.toggle(this.data.length == 0);
		this.$no_result_prev.toggle(this.data.length == 0);

		const show_more = (this.start + this.page_length) <= this.data.length;
		this.$paging_area.find('.btn-more')
			.toggle(show_more);
	}

	setup_filter_area() {
		this.filter_area = new erpnext.projects.CustomFilterArea(this);

		if (this.filters && this.filters.length > 0) {
			return this.filter_area.set(this.filters);
		}
	}

	get_list_row_html(doc) {
		return this.get_list_row_html_skeleton(this.get_left_html(this.columns, doc), this.get_right_html(doc), doc);
	}

	get_task_list_row_html(doc, level) {
		return this.get_task_list_row_html_skeleton(this.get_left_html(this.task_columns, doc, level), this.get_right_html(doc, true), doc, level);
	}

	get_list_row_html_skeleton(left = '', right = '', doc = {}) {
		return `
			<div class="list-row-container project-list-row-container" tabindex="1" data-doctype="Project" data-name="${escape(doc.name)}">
				<div class="level list-row small">
					<div class="level-left ellipsis">
						${left}
					</div>
					<div class="level-right text-muted ellipsis">
						${right}
					</div>
				</div>
			</div>
		`;
	}

	get_task_list_row_html_skeleton(left = '', right = '', doc = {}, level) {
		return `
		<div class="list-rows" data-doctype="Task" data-name="${escape(doc.name)}" data-level="${level}">
			<div class="list-row-container" tabindex="1">
				<div class="level list-row small">
					<div class="level-left ellipsis">
						${left}
					</div>
					<div class="level-right text-muted ellipsis">
						${right}
					</div>
				</div>
			</div>
			<div class="nested-list-row-container hide">
			</div>
		</div>
		`;
	}

	get_left_html(columns, doc, level) {
		return columns.map(col => this.get_column_html(col, columns, doc, level)).join('');
	}

	get_right_html(doc, create_new=false) {
		return this.get_meta_html(doc, create_new);
	}

	get_column_html(col, columns, doc, level) {
		if (col.type === 'Status') {
			return `
				<div class="list-row-col hidden-xs ellipsis">
					${this.get_indicator_html(doc)}
				</div>
			`;
		}

		const df = col.df || {};
		const label = df.label;
		const fieldname = df.fieldname;
		const value = doc[fieldname] || '';

		const format = () => {
			if (df.fieldtype === 'Code') {
				return value;
			} else if (df.fieldtype === 'Percent') {
				return `<div class="progress level" style="margin: 0px;">
						<div class="progress-bar progress-bar-success" role="progressbar"
							aria-valuenow="${value}"
							aria-valuemin="0" aria-valuemax="100" style="width: ${Math.round(value)}%;">
						</div>
					</div>`;
			} else {
				return frappe.format(value, df, null, doc);
			}
		};

		const field_html = () => {
			let html;
			let _value;
			// listview_setting formatter
			if (this.settings.formatters && this.settings.formatters[fieldname]) {
				_value = this.settings.formatters[fieldname](value, df, doc);
			} else {
				let strip_html_required = df.fieldtype == 'Text Editor'
					|| (df.fetch_from && ['Text', 'Small Text'].includes(df.fieldtype));
				if (strip_html_required) {
					_value = strip_html(value);
				} else {
					_value = typeof value === 'string' ? frappe.utils.escape_html(value) : value;
				}
			}

			if (df.fieldtype === 'Image') {
				html = df.options ?
					`<img src="${doc[df.options]}" style="max-level: 30px; max-width: 100%;">` :
					`<div class="missing-image small">
						<span class="octicon octicon-circle-slash"></span>
					</div>`;
			} else if (df.fieldtype === 'Select') {
				html = `<span class="filterable indicator ${frappe.utils.guess_colour(_value)} ellipsis"
					data-filter="${fieldname},=,${value}">
					${__(_value)}
				</span>`;
			} else if (df.fieldtype === 'Link') {
				html = `<a class="filterable text-muted ellipsis"
					data-filter="${fieldname},=,${value}">
					${_value}
				</a>`;
			} else if (['Text Editor', 'Text', 'Small Text', 'HTML Editor'].includes(df.fieldtype)) {
				html = `<span class="text-muted ellipsis">
					${_value}
				</span>`;
			} else {
				html = `<a class="filterable text-muted ellipsis"
					data-filter="${fieldname},=,${value}">
					${format()}
				</a>`;
			}

			return `<span class="ellipsis"
				title="${__(label)}: ${escape(_value)}">
				${html}
			</span>`;
		};

		const class_map = {
			Subject: 'list-subject level',
			Field: 'hidden-xs'
		};
		const css_class = [
			'list-row-col ellipsis',
			class_map[col.type],
			frappe.model.is_numeric_field(df) ? 'text-right' : ''
		].join(' ');

		const html_map = {
			Subject: this.get_subject_html(columns, doc, level),
			Field: field_html()
		};
		const column_html = html_map[col.type];

		return `
			<div class="${css_class}">
				${column_html}
			</div>
		`;
	}

	get_subject_html(columns, doc, level) {
		let user = frappe.session.user;
		let subject_field = columns[0].df;
		let value = doc[subject_field.fieldname] || doc.name;
		let subject = strip_html(value.toString());
		let escaped_subject = frappe.utils.escape_html(subject);

		const liked_by = JSON.parse(doc._liked_by || '[]');
		let heart_class = liked_by.includes(user) ? 'liked-by' : 'text-extra-muted not-liked';

		const seen = JSON.parse(doc._seen || '[]').includes(user) ? '' : 'bold';

		const subject_link = this.get_subject_link(doc, subject, escaped_subject);

		let html = doc.doctype == 'Task' && doc.expandable ? `<a class="btn btn-action btn-xs"
			data-doctype="Task" data-name="${escape(doc.name)}" style="width: 20px;">
				<i class="octicon octicon-chevron-right" />
			</a>` : ``;


		let subject_html = `
			<input class="level-item list-row-checkbox hidden-xs" type="checkbox" data-name="${escape(doc.name)}">
			<span class="level-item" style="margin-bottom: 1px;">
				<i class="octicon octicon-heart like-action ${heart_class}"
					data-name="${doc.name}" data-doctype="${doc.doctype}"
					data-liked-by="${encodeURI(doc._liked_by) || '[]'}">
				</i>
				<span class="likes-count">
					${ liked_by.length > 99 ? __("99") + '+' : __(liked_by.length || '')}
				</span>
			</span>
			<span class="level-item ${seen} ellipsis" title="${escaped_subject}" style="padding-left: ${20*level}px;">
				<span class="level-item" style="margin-bottom: 1px;"">
					${html}
				</span>
				${subject_link}
			</span>
		`;

		return subject_html;
	}

	get_subject_link(doc, subject, escaped_subject) {
		if (doc.doctype === 'Project') {
			return `<span class="ellipsis" title="${escaped_subject}" data-doctype="${doc.doctype}" data-name="${doc.name}">
				${subject}
			</span>`;
		} else {
			return `<a href ="desk#Form/Task/${doc.name}" class="ellipsis" title="${escaped_subject}" data-doctype="${doc.doctype}" data-name="${doc.name}">
				${subject}
			</a>`;
		}
	}

	get_indicator_html(doc) {
		const indicator = frappe.get_indicator(doc, this.doctype);
		if (indicator) {
			return `<span class="indicator ${indicator[1]} filterable"
				data-filter='${indicator[2]}'>
				${__(indicator[0])}
			<span>`;
		}
		return '';
	}

	get_indicator_dot(doc) {
		const indicator = frappe.get_indicator(doc, this.doctype);
		if (!indicator) return '';
		return `<span class='indicator ${indicator[1]}' title='${__(indicator[0])}'></span>`;
	}

	get_avatar(last_assignee) {
		return `<span class="filterable"
				data-filter="_assign,like,%${last_assignee}%">
				${frappe.avatar(last_assignee)}
			</span>`
	}

	get_meta_html(doc, create_new) {
		let html = '';

		if (create_new && doc.is_group) {
			html += this.get_add_child_button(doc);
		}

		if (doc.doctype == 'Project') {
			html += this.get_open_button(doc);
		}

		const modified = this.comment_when(doc.modified, true);

		const last_assignee = JSON.parse(doc._assign || '[]').slice(-1)[0];
		const assigned_to = last_assignee ?
			this.get_avatar(last_assignee) :
			`<span class="avatar avatar-small avatar-empty"></span>`;

		const comment_count =
			`<span class="${!doc._comment_count ? 'text-extra-muted' : ''} comment-count">
				<i class="octicon octicon-comment-discussion"></i>
				${doc._comment_count > 99 ? "99+" : doc._comment_count}
			</span>`;

		html += `
			<div class="level-item hidden-xs list-row-activity">
				${modified}
				${assigned_to}
				${comment_count}
			</div>
			<div class="level-item visible-xs text-right">
				${this.get_indicator_dot(doc)}
			</div>
		`;

		return html;
	}

	get_open_button(doc) {
		return `
				<div class="level-item hidden-xs" style="margin-left: 5px;">
					<button class="btn btn-open btn-default btn-xs"
						data-doctype="${escape(doc.doctype)}" data-name="${escape(doc.name)}">
						${__("Open")}
					</button>
				</div>
			`;
	}

	get_add_child_button(doc) {
		return `
				<div class="level-item hidden-xs">
					<button class="btn create-new btn-default btn-xs"
						data-name="${escape(doc.name)}" data-project="${escape(doc.project)}">
						${__("Add Child")}
					</button>
				</div>
			`;
	}

	render_header(columns, refresh_header) {
		if (refresh_header) {
			this.$result.find('.list-row-head').remove();
		}

		if (this.$result.find('.list-row-head').length === 0) {
			// append header once
			this.$result.prepend(this.get_header_html(columns));
		}
	}

	render_previous_button() {
		if (this.$result.find('.list-row-previous-head').length === 0) {
			// append header once
			this.$result.prepend(this.get_previous_header_html());
		}
	}

	remove_previous_button() {
		this.$result.find('.list-row-previous-head').remove();
	}

	get_header_html(columns) {
		const subject_field = columns[0].df;

		let subject_html = `
			<input class="level-item list-check-all hidden-xs" type="checkbox" title="${__("Select All")}">
			<span class="level-item list-liked-by-me">
				<i class="octicon octicon-heart text-extra-muted" title="${__("Likes")}"></i>
			</span>
			<span class="level-item">${__(subject_field.label)}</span>
		`;

		const $columns = columns.map(col => {
			let classes = [
				'list-row-col ellipsis',
				col.type == 'Subject' ? 'list-subject level' : 'hidden-xs',
				frappe.model.is_numeric_field(col.df) ? 'text-right' : ''
			].join(' ');

			return `
				<div class="${classes}">
					${col.type === 'Subject' ? subject_html : `
					<span>${__(col.df && col.df.label || col.type)}</span>`}
				</div>
			`;
		}).join('');

		return this.get_header_html_skeleton($columns, '<span class="list-count"></span>');
	}

	get_previous_header_html() {
		return `
			<header class="level list-row list-row-head text-muted small">
				<a class="btn btn-prev btn-xs">
					<i class="octicon octicon-chevron-left" />
					<span style="margin-left: 5px">Projects</span>
				</a>
				<button class="btn btn-xs expand-all btn-default" style="float: right">
					${__('Expand All')}</button>
				<button class="btn btn-xs collapse-all btn-default" style="float: right; display: none">
					${__('Collapse All')}</button>
			</header>
		`;
	}

	on_row_checked() {
		this.$list_head_subject = this.$list_head_subject || this.$result.find('header .list-header-subject');
		this.$checkbox_actions = this.$checkbox_actions || this.$result.find('header .checkbox-actions');

		this.$checks = this.$result.find('.list-row-checkbox:checked');

		this.$list_head_subject.toggle(this.$checks.length === 0);
		this.$checkbox_actions.toggle(this.$checks.length > 0);

		if (this.$checks.length === 0) {
			this.$list_head_subject.find('.list-check-all').prop('checked', false);
		} else {
			this.$checkbox_actions.find('.list-header-meta').html(
				__('{0} items selected', [this.$checks.length])
			);
			this.$checkbox_actions.show();
			this.$list_head_subject.hide();
		}
	}

	get_checked_items(only_docnames) {
		const docnames = Array.from(this.$checks || [])
			.map(check => cstr(unescape($(check).data().name)));

		if (only_docnames) return docnames;

		return this.data.filter(d => docnames.includes(d.name));
	}

	get_header_html_skeleton(left = '', right = '') {
		return `
			<header class="level list-row list-row-head text-muted small">
				<div class="level-left list-header-subject">
					${left}
				</div>
				<div class="level-left checkbox-actions">
					<div class="level list-subject">
						<input class="level-item list-check-all hidden-xs" type="checkbox" title="${__("Select All")}">
						<span class="level-item list-header-meta"></span>
					</div>
				</div>
				<div class="level-right">
					${right}
				</div>
			</header>
		`;
	}

	setup_check_events() {
		this.$result.on('change', 'input[type=checkbox]', e => {
			const $target = $(e.currentTarget);
			e.stopPropagation();

			if ($target.is('.list-header-subject .list-check-all')) {
				const $check = this.$result.find('.checkbox-actions .list-check-all');
				$check.prop('checked', $target.prop('checked'));
				$check.trigger('change');
			} else if ($target.is('.checkbox-actions .list-check-all')) {
				const $check = this.$result.find('.list-header-subject .list-check-all');
				$check.prop('checked', $target.prop('checked'));

				this.$result.find('.list-row-checkbox')
					.prop('checked', $target.prop('checked'));
			}

			this.on_row_checked();
		});

		this.$result.on('click', '.list-row-checkbox', e => {
			const $target = $(e.currentTarget);
			e.stopPropagation()

			// shift select checkboxes
			if (e.shiftKey && this.$checkbox_cursor && !$target.is(this.$checkbox_cursor)) {
				const name_1 = this.$checkbox_cursor.data().name;
				const name_2 = $target.data().name;
				const index_1 = this.data.findIndex(d => d.name === name_1);
				const index_2 = this.data.findIndex(d => d.name === name_2);
				let [min_index, max_index] = [index_1, index_2];

				if (min_index > max_index) {
					[min_index, max_index] = [max_index, min_index];
				}

				let docnames = this.data.slice(min_index + 1, max_index).map(d => d.name);
				const selector = docnames.map(name => `.list-row-checkbox[data-name="${name}"]`).join(',');
				this.$result.find(selector).prop('checked', true);
			}

			this.$checkbox_cursor = $target;
		});
	}

	comment_when(datetime, mini) {
		var timestamp = frappe.datetime.str_to_user ?
			frappe.datetime.str_to_user(datetime) : datetime;
		return '<span class="frappe-timestamp '
			+ (mini ? " mini" : "") + '" data-timestamp="' + datetime
			+ '" title="' + timestamp + '">'
			+ this.prettyDate(datetime, mini) + '</span>';
	}

	convert_to_user_tz(date) {
		date = frappe.datetime.convert_to_user_tz(date);
		return new Date((date || "").replace(/-/g, "/").replace(/[TZ]/g, " ").replace(/\.[0-9]*/, ""));
	}

	prettyDate(date, mini) {
		if (!date) return '';

		if (typeof (date) == "string") {
			date = this.convert_to_user_tz(date);
		}

		let diff = (((new Date()).getTime() - date.getTime()) / 1000);
		let day_diff = Math.floor(diff / 86400);

		if (isNaN(day_diff) || day_diff < 0) return '';

		if (mini) {
			// Return short format of time difference
			if (day_diff == 0) {
				if (diff < 60) {
					return __("now");
				} else if (diff < 3600) {
					return __("{0} m", [Math.floor(diff / 60)]);
				} else if (diff < 86400) {
					return __("{0} h", [Math.floor(diff / 3600)]);
				}
			} else {
				if (day_diff < 7) {
					return __("{0} d", [day_diff]);
				} else if (day_diff < 31) {
					return __("{0} w", [Math.ceil(day_diff / 7)]);
				} else if (day_diff < 365) {
					return __("{0} M", [Math.ceil(day_diff / 30)]);
				} else {
					return __("{0} y", [Math.ceil(day_diff / 365)]);
				}
			}
		} else {
			// Return long format of time difference
			if (day_diff == 0) {
				if (diff < 60) {
					return __("just now");
				} else if (diff < 120) {
					return __("1 minute ago");
				} else if (diff < 3600) {
					return __("{0} minutes ago", [Math.floor(diff / 60)]);
				} else if (diff < 7200) {
					return __("1 hour ago");
				} else if (diff < 86400) {
					return __("{0} hours ago", [Math.floor(diff / 3600)]);
				}
			} else {
				if (day_diff == 1) {
					return __("yesterday");
				} else if (day_diff < 7) {
					return __("{0} days ago", [day_diff]);
				} else if (day_diff < 14) {
					return __("1 week ago");
				} else if (day_diff < 31) {
					return __("{0} weeks ago", [Math.ceil(day_diff / 7)]);
				} else if (day_diff < 62) {
					return __("1 month ago");
				} else if (day_diff < 365) {
					return __("{0} months ago", [Math.ceil(day_diff / 30)]);
				} else if (day_diff < 730) {
					return __("1 year ago");
				} else {
					return __("{0} years ago", [Math.ceil(day_diff / 365)]);
				}
			}
		}
	}
};

erpnext.projects.CustomFilterArea = class CustomFilterArea extends frappe.ui.FilterArea {

	refresh_filters(meta) {
		this.list_view.page.clear_fields();
		this.list_view.current_doctype = meta.name;
		// this.$filter_list_wrapper.remove();

		let existing_list = $(this.list_view.parent).find(".filter-list");

		if (existing_list) {
			existing_list.remove();
		}

		this.list_view.doctype = meta.name;
		// this.standard_filters_wrapper = this.list_view.page.page_form;
		// this.$filter_list_wrapper = $('<div class="filter-list">').appendTo(this.list_view.$frappe_list);
		this.$filter_list_wrapper = $('<div class="filter-list">').prependTo(this.list_view.$frappe_list);

		this.make_standard_filters(meta);
		this.make_filter_list(meta.name);
		this.clear(false);
	}

	make_standard_filters(meta) {
		if (!meta) {
			meta = this.list_view.meta;
		}

		let fields = [
			{
				fieldtype: 'Data',
				label: 'Name',
				condition: 'like',
				fieldname: 'name',
				onchange: () => this.refresh_list_view()
			}
		];

		const doctype_fields = meta.fields;
		const title_field = meta.title_field;

		fields = fields.concat(doctype_fields.filter(
			df => (df.fieldname === title_field) || (df.in_standard_filter && frappe.model.is_value_type(df.fieldtype))
		).map(df => {
			let options = df.options;
			let condition = '=';
			let fieldtype = df.fieldtype;
			if (['Text', 'Small Text', 'Text Editor', 'HTML Editor', 'Data', 'Code', 'Read Only'].includes(fieldtype)) {
				fieldtype = 'Data';
				condition = 'like';
			}
			if (df.fieldtype == "Select" && df.options) {
				options = df.options.split("\n");
				if (options.length > 0 && options[0] != "") {
					options.unshift("");
					options = options.join("\n");
				}
			}
			let default_value = (fieldtype === 'Link') ? frappe.defaults.get_user_default(options) : null;
			if (['__default', '__global'].includes(default_value)) {
				default_value = null;
			}
			return {
				fieldtype: fieldtype,
				label: __(df.label),
				options: options,
				fieldname: df.fieldname,
				condition: condition,
				default: default_value,
				onchange: () => this.refresh_list_view(),
				ignore_link_validation: fieldtype === 'Dynamic Link',
				is_filter: 1,
			};
		}));

		fields.map(df => this.list_view.page.add_field(df));
	}

	make_filter_list(doctype) {
		if (!doctype) {
			doctype = this.list_view.doctype;
		}

		this.filter_list = new frappe.ui.FilterGroup({
			base_list: this.list_view,
			parent: this.$filter_list_wrapper,
			doctype: doctype,
			default_filters: [],
			on_change: () => this.refresh_list_view()
		});
	}

	refresh_list_view() {
		if (this.trigger_refresh) {
			if (this.list_view.doctype == "Task") {
				this.list_view.fetch_tasks();
				return;
			}

			this.list_view.start = 0;
			this.list_view.refresh();
			this.list_view.on_filter_change();
		}
	}
}