// The Project form's Tasks tab: a desk toolbar above two views of the project's tasks.
// List: a Vue island; the tab loads the tasks once and hands them, with the search and grouping,
// to it. Board: the project's own Kanban Board, the same board its Kanban page shows.

const TASK_LIST = "erpnext.projects.doctype.project.project_tasks.get_project_task_list";
const PROJECT_BOARD = "erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists";
const SEARCH_DELAY = 150;
// how the list groups its tasks; none by default, so every task shows in one list
const GROUPS = {
	none: { label: () => __("None"), menu: () => __("No grouping"), icon: "list" },
	status: { label: () => __("Status"), menu: () => __("Status"), icon: "circle-dot" },
	parent: { label: () => __("Parent task"), menu: () => __("Parent task"), icon: "list-tree" },
};

frappe.ui.form.on("Project", {
	refresh(frm) {
		frm.tasks_tab ??= new erpnext.ProjectTasksTab(frm);
		frm.tasks_tab.refresh();
	},
	on_tab_change(frm) {
		frm.tasks_tab?.show();
	},
});

erpnext.ProjectTasksTab = class ProjectTasksTab {
	constructor(frm) {
		this.frm = frm;
		this.project = null;
		this.view = "list";
		this.tasks = null;
		this.failed = false;
		this.search = "";
		this.group_by = "none";
		// the board's swimlane field, or null
		this.lanes = null;
		this.board = null;
		// lets a late reply for an earlier load, or another project, be dropped
		this.load_seq = 0;
		this.board_seq = 0;
		// the island asks for these with events from inside its shadow root
		$(frm.wrapper).on("tasks-clear-search", () => this.set_search(""));
		// a save can change more than the field edited, such as progress on completion
		$(frm.wrapper).on("tasks-changed", () => this.load());
	}

	// on every form refresh: another project opened, or a task changed in a dialog
	refresh() {
		const { frm } = this;
		const can_read = frappe.model.can_read("Task");
		const shown = can_read && !frm.is_new();

		// each project opens on the plain list: no grouping, no search, not the board, whatever
		// the last project was left on
		const project = frm.is_new() ? null : frm.doc.name;
		if (this.project !== project) {
			this.project = project;
			this.view = "list";
			this.group_by = "none";
			this.tasks = null;
			this.failed = false;
			this.search = "";
			this.lanes = null;
			this.destroy_board();
		}

		frm.toggle_display("tasks_toolbar", shown);
		// a new project still shows the list's "save first" message
		frm.toggle_display("tasks_list", can_read && this.view === "list");
		frm.toggle_display("tasks_board", shown && this.view === "board");
		if (!shown) return;

		this.render_toolbar();
		this.push();
		this.show();
	}

	get is_active() {
		return this.frm.get_active_tab?.()?.df?.fieldname === "tasks_tab";
	}

	// tasks change on their own forms too, so each visit to the tab loads them again
	show() {
		if (!this.is_active) return;
		if (this.view === "board") this.show_board();
		else this.load();
	}

	// after a task changed somewhere the tab can't see, such as its dialog
	reload() {
		if (this.view === "board") this.board?.refresh();
		else this.load();
	}

	set_view(view) {
		if (view === this.view) return;
		this.view = view;
		this.frm.toggle_display("tasks_list", view === "list");
		this.frm.toggle_display("tasks_board", view === "board");
		this.render_toolbar();
		this.show();
	}

	// --- list ---

	load() {
		const project = this.frm.doc.name;
		if (!project || this.frm.is_new()) return Promise.resolve();
		const seq = ++this.load_seq;
		return frappe.xcall(TASK_LIST, { project }, "GET").then(
			(tasks) => {
				if (seq !== this.load_seq || project !== this.project) return;
				this.tasks = tasks;
				this.failed = false;
				this.push();
			},
			() => {
				if (seq !== this.load_seq || project !== this.project) return;
				this.failed = true;
				this.push();
			}
		);
	}

	// the island keeps these across the form's own prop updates, which merge into them
	push() {
		this.frm.get_field("tasks_list")?.island?.update({
			tasks: this.tasks,
			failed: this.failed,
			search: this.search,
			group_by: this.group_by,
		});
	}

	set_group_by(group_by) {
		this.group_by = group_by;
		this.render_group_menu();
		this.push();
	}

	// --- board ---

	async show_board() {
		if (this.board) {
			this.board.refresh();
			return;
		}
		const project = this.project;
		const seq = ++this.board_seq;
		const $wrapper = this.frm.get_field("tasks_board").$wrapper;
		let board_name;
		try {
			[board_name] = await Promise.all([
				frappe.xcall(PROJECT_BOARD, { project }),
				frappe.require("kanban.bundle.js"),
			]);
		} catch (error) {
			// desk has already shown the server's message
			if (seq === this.board_seq) {
				$wrapper.empty().append(
					frappe.ui.empty_state({
						icon: "circle-alert",
						title: __("Could not load the board"),
					})
				);
			}
			return;
		}
		// another project opened, or the list came back, while the board was on its way
		if (seq !== this.board_seq || project !== this.project || this.view !== "board") return;

		$wrapper.empty();
		// the board fills this and its columns scroll inside, as on the Kanban page
		const $container = $(`<div class="project-tasks-board"></div>`)
			.css({ height: "calc(100vh - 14rem)", minHeight: "26rem" })
			.appendTo($wrapper);
		this.board = new frappe.views.KanbanV2Embed({
			container: $container[0],
			board_name,
			filters: [["Task", "project", "=", project]],
		});
		this.board_filters();
		await this.board.ready;
		if (seq !== this.board_seq) return;
		if (this.lanes) await this.board.set_group_by(this.lanes);
		// its swimlane fields are known only once it has loaded
		this.render_group_menu();
	}

	destroy_board() {
		this.board_seq++;
		this.board?.destroy();
		this.board = null;
		this.frm.get_field("tasks_board")?.$wrapper.empty();
	}

	board_filters() {
		const text = this.search.trim();
		this.board?.set_filters(text ? [["Task", "subject", "like", `%${text}%`]] : []);
	}

	set_lanes(fieldname) {
		this.lanes = fieldname;
		this.board?.set_group_by(fieldname);
		this.render_group_menu();
	}

	// --- toolbar ---

	set_search(text) {
		this.search = text;
		if (this.$search && this.$search.val() !== text) this.$search.val(text);
		this.push();
		this.board_filters();
	}

	// List: Group by none, status or parent task. Board: swimlanes by a field the board offers.
	render_group_menu() {
		const dropdown =
			this.view === "board"
				? this.lanes_dropdown()
				: new frappe.ui.Dropdown({
						button: {
							label: __("Group: {0}", [GROUPS[this.group_by].label()]),
							icon: "rows-3",
						},
						options: Object.entries(GROUPS).map(([value, group]) => ({
							label: group.menu(),
							icon: group.icon,
							selected: value === this.group_by,
							onclick: () => this.set_group_by(value),
						})),
				  });
		this.$group.empty().append(dropdown.$trigger);
	}

	lanes_dropdown() {
		const fields = this.board?.group_by_options || [];
		const current = fields.find((field) => field.fieldname === this.lanes);
		return new frappe.ui.Dropdown({
			button: {
				label: __("Swimlanes: {0}", [current ? current.label : __("None")]),
				icon: "rows-3",
			},
			options: [
				{
					label: __("No swimlanes"),
					icon: "columns-3",
					selected: !current,
					onclick: () => this.set_lanes(null),
				},
				...fields.map((field) => ({
					label: field.label,
					selected: field.fieldname === this.lanes,
					onclick: () => this.set_lanes(field.fieldname),
				})),
			],
		});
	}

	render_toolbar() {
		const $wrapper = this.frm.get_field("tasks_toolbar").$wrapper;
		if (!this.$toolbar || !$.contains(document, this.$toolbar[0])) {
			this.$toolbar = $(`<div class="flex flex-wrap items-center gap-2 pb-3"></div>`).appendTo(
				$wrapper.empty()
			);
			this.$search = $(`<input type="text" class="form-control form-control-sm">`)
				.attr({ placeholder: __("Search tasks"), "aria-label": __("Search tasks") })
				.css("max-width", "12rem")
				.appendTo(this.$toolbar);
			this.$search.on(
				"input",
				frappe.utils.debounce(() => this.set_search(this.$search.val()), SEARCH_DELAY)
			);
			this.$group = $(`<div></div>`).appendTo(this.$toolbar);
			this.$actions = $(`<div class="flex items-center gap-2 ms-auto"></div>`).appendTo(this.$toolbar);
		}
		this.$search.val(this.search);
		this.render_group_menu();

		this.$actions.empty();
		if (this.view === "board") {
			frappe.ui
				.button({
					icon: "settings-2",
					variant: "ghost",
					tooltip: __("Board settings"),
					onclick: () => this.board?.open_settings(),
				})
				.appendTo(this.$actions);
		}
		new frappe.ui.TabButtons({
			label: __("View"),
			value: this.view,
			options: [
				{ label: __("List"), value: "list", icon_left: "list" },
				{ label: __("Board"), value: "board", icon_left: "square-kanban" },
			],
			on_change: (view) => this.set_view(view),
		}).$el.appendTo(this.$actions);
		if (frappe.model.can_create("Task")) {
			frappe.ui
				.button({
					label: __("Add task"),
					icon: "plus",
					onclick: () => this.frm.events.new_task(this.frm),
				})
				.appendTo(this.$actions);
		}
	}
};
