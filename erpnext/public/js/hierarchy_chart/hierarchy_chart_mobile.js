erpnext.HierarchyChartMobile = class {
	/* Options:
		- doctype
		- wrapper: wrapper for the hierarchy view
		- method:
			- to get the data for each node
			- this method should return id, name, title, image, and connections for each node
	*/
	constructor(doctype, wrapper, method) {
		this.page = wrapper.page;
		this.method = method;
		this.doctype = doctype;

		this.page.main.css({
			'min-height': '300px',
			'max-height': '600px',
			'overflow': 'auto',
			'position': 'relative'
		});
		this.page.main.addClass('frappe-card');

		this.nodes = {};
		this.setup_node_class();
	}

	setup_node_class() {
		let me = this;
		this.Node = class {
			constructor({
				id, parent, parent_id, image, name, title, expandable, connections, is_root // eslint-disable-line
			}) {
				// to setup values passed via constructor
				$.extend(this, arguments[0]);

				this.expanded = 0;

				me.nodes[this.id] = this;
				me.make_node_element(this);
				me.setup_node_click_action(this);
				me.setup_edit_node_action(this);
			}
		};
	}

	make_node_element(node) {
		let node_card = frappe.render_template('node_card', {
			id: node.id,
			name: node.name,
			title: node.title,
			image: node.image,
			parent: node.parent_id,
			connections: node.connections,
			is_mobile: true
		});

		node.parent.append(node_card);
		node.$link = $(`[id="${node.id}"]`);
		node.$link.addClass('mobile-node');
	}

	show() {
		let me = this;
		if ($(`[data-fieldname="company"]`).length) return;

		let company = this.page.add_field({
			fieldtype: 'Link',
			options: 'Company',
			fieldname: 'company',
			placeholder: __('Select Company'),
			default: frappe.defaults.get_default('company'),
			only_select: true,
			reqd: 1,
			change: () => {
				me.company = undefined;

				if (company.get_value() && me.company != company.get_value()) {
					me.company = company.get_value();

					// svg for connectors
					me.make_svg_markers();

					if (me.$sibling_group)
						me.$sibling_group.remove();

					// setup sibling group wrapper
					me.$sibling_group = $(`<div class="sibling-group mt-4 mb-4"></div>`);
					me.page.main.append(me.$sibling_group);

					me.setup_hierarchy();
					me.render_root_nodes();
				}
			}
		});

		company.refresh();
		$(`[data-fieldname="company"]`).trigger('change');
	}

	make_svg_markers() {
		$('#arrows').remove();

		this.page.main.prepend(`
			<svg id="arrows" width="100%" height="100%">
				<defs>
					<marker id="arrowhead-active" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="6" markerHeight="6" orient="auto" fill="var(--blue-500)">
						<path d="M 0 0 L 10 5 L 0 10 z"></path>
					</marker>
					<marker id="arrowhead-collapsed" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="6" markerHeight="6" orient="auto" fill="var(--blue-300)">
						<path d="M 0 0 L 10 5 L 0 10 z"></path>
					</marker>

					<marker id="arrowstart-active" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="8" markerHeight="8" orient="auto" fill="var(--blue-500)">
						<circle cx="4" cy="4" r="3.5" fill="white" stroke="var(--blue-500)"/>
					</marker>
					<marker id="arrowstart-collapsed" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="8" markerHeight="8" orient="auto" fill="var(--blue-300)">
						<circle cx="4" cy="4" r="3.5" fill="white" stroke="var(--blue-300)"/>
					</marker>
				</defs>
				<g id="connectors" fill="none">
				</g>
			</svg>`);
	}

	setup_hierarchy() {
		$(`#connectors`).empty();
		if (this.$hierarchy)
			this.$hierarchy.remove();

		if (this.$sibling_group)
			this.$sibling_group.empty();

		this.$hierarchy = $(
			`<ul class="hierarchy-mobile">
				<li class="root-level level"></li>
			</ul>`);

		this.page.main.append(this.$hierarchy);
	}

	render_root_nodes() {
		let me = this;

		frappe.call({
			method: me.method,
			args: {
				company: me.company
			},
		}).then(r => {
			if (r.message.length) {
				let root_level = me.$hierarchy.find('.root-level');
				root_level.empty();

				$.each(r.message, (_i, data) => {
					return new me.Node({
						id: data.id,
						parent: root_level,
						parent_id: undefined,
						image: data.image,
						name: data.name,
						title: data.title,
						expandable: true,
						connections: data.connections,
						is_root: true
					});
				});
			}
		});
	}

	expand_node(node) {
		const is_same_node = (this.selected_node && this.selected_node.id === node.id);
		this.set_selected_node(node);
		this.show_active_path(node);

		if (this.$sibling_group) {
			const sibling_parent = this.$sibling_group.find('.node-group').attr('data-parent');
			if (node.parent_id !== undefined && node.parent_id != sibling_parent)
				this.$sibling_group.empty();
		}

		if (!is_same_node) {
			// since the previous/parent node collapses, all connections to that node need to be rebuilt
			// rebuild outgoing connections of parent
			this.refresh_connectors(node.parent_id, node.id);

			// rebuild incoming connections of parent
			let grandparent = $(`[id="${node.parent_id}"]`).attr('data-parent');
			this.refresh_connectors(grandparent, node.parent_id);
		}

		if (node.expandable && !node.expanded) {
			return this.load_children(node);
		}
	}

	collapse_node() {
		let node = this.selected_node;
		if (node.expandable && node.$children) {
			node.$children.hide();
			node.expanded = 0;

			// add a collapsed level to show the collapsed parent
			// and a button beside it to move to that level
			let node_parent = node.$link.parent();
			node_parent.prepend(
				`<div class="collapsed-level d-flex flex-row"></div>`
			);

			node_parent
				.find('.collapsed-level')
				.append(node.$link);

			frappe.run_serially([
				() => this.get_child_nodes(node.parent_id, node.id),
				(child_nodes) => this.get_node_group(child_nodes, node.parent_id),
				(node_group) => node_parent.find('.collapsed-level').append(node_group),
				() => this.setup_node_group_action()
			]);
		}
	}

	show_active_path(node) {
		// mark node parent on active path
		$(`[id="${node.parent_id}"]`).addClass('active-path');
	}

	load_children(node) {
		frappe.run_serially([
			() => this.get_child_nodes(node.id),
			(child_nodes) => this.render_child_nodes(node, child_nodes)
		]);
	}

	get_child_nodes(node_id, exclude_node=null) {
		let me = this;
		return new Promise(resolve => {
			frappe.call({
				method: this.method,
				args: {
					parent: node_id,
					company: me.company,
					exclude_node: exclude_node
				}
			}).then(r => resolve(r.message));
		});
	}

	render_child_nodes(node, child_nodes) {
		if (!node.$children) {
			node.$children = $('<ul class="node-children"></ul>')
				.hide()
				.appendTo(node.$link.parent());

			node.$children.empty();

			if (child_nodes) {
				$.each(child_nodes, (_i, data) => {
					this.add_node(node, data);
					$(`[id="${data.id}"]`).addClass('active-child');

					setTimeout(() => {
						this.add_connector(node.id, data.id);
					}, 250);
				});
			}
		}

		node.$children.show();
		node.expanded = 1;
	}

	add_node(node, data) {
		var $li = $('<li class="child-node"></li>');

		return new this.Node({
			id: data.id,
			parent: $li.appendTo(node.$children),
			parent_id: node.id,
			image: data.image,
			name: data.name,
			title: data.title,
			expandable: data.expandable,
			connections: data.connections,
			children: undefined
		});
	}

	add_connector(parent_id, child_id) {
		const parent_node = document.querySelector(`#${parent_id}`);
		const child_node = document.querySelector(`#${child_id}`);

		const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

		let connector = undefined;

		if ($(`[id="${parent_id}"]`).hasClass('active')) {
			connector = this.get_connector_for_active_node(parent_node, child_node);
		} else if ($(`[id="${parent_id}"]`).hasClass('active-path')) {
			connector = this.get_connector_for_collapsed_node(parent_node, child_node);
		}

		path.setAttribute('d', connector);
		this.set_path_attributes(path, parent_id, child_id);

		document.getElementById('connectors').appendChild(path);
	}

	get_connector_for_active_node(parent_node, child_node) {
		// we need to connect the bottom left of the parent to the left side of the child node
		let pos_parent_bottom = {
			x: parent_node.offsetLeft + 20,
			y: parent_node.offsetTop + parent_node.offsetHeight
		};
		let pos_child_left = {
			x: child_node.offsetLeft - 5,
			y: child_node.offsetTop + child_node.offsetHeight / 2
		};

		let connector =
			"M" +
			(pos_parent_bottom.x) + "," + (pos_parent_bottom.y) + " " +
			"L" +
			(pos_parent_bottom.x) + "," + (pos_child_left.y - 10) + " " +
			"a10,10 1 0 0 10,10 " +
			"L" +
			(pos_child_left.x) + "," + (pos_child_left.y);

		return connector;
	}

	get_connector_for_collapsed_node(parent_node, child_node) {
		// we need to connect the bottom left of the parent to the top left of the child node
		let pos_parent_bottom = {
			x: parent_node.offsetLeft + 20,
			y: parent_node.offsetTop + parent_node.offsetHeight
		};
		let pos_child_top = {
			x: child_node.offsetLeft + 20,
			y: child_node.offsetTop
		};

		let connector =
			"M" +
			(pos_parent_bottom.x) + "," + (pos_parent_bottom.y) + " " +
			"L" +
			(pos_child_top.x) + "," + (pos_child_top.y);

		return connector;
	}

	set_path_attributes(path, parent_id, child_id) {
		path.setAttribute("data-parent", parent_id);
		path.setAttribute("data-child", child_id);
		const parent = $(`[id="${parent_id}"]`);

		if (parent.hasClass('active')) {
			path.setAttribute("class", "active-connector");
			path.setAttribute("marker-start", "url(#arrowstart-active)");
			path.setAttribute("marker-end", "url(#arrowhead-active)");
		} else if (parent.hasClass('active-path')) {
			path.setAttribute("class", "collapsed-connector");
		}
	}

	set_selected_node(node) {
		// remove .active class from the current node
		if (this.selected_node)
			this.selected_node.$link.removeClass('active');

		// add active class to the newly selected node
		this.selected_node = node;
		node.$link.addClass('active');
	}

	setup_node_click_action(node) {
		let me = this;
		let node_element = $(`[id="${node.id}"]`);

		node_element.click(function() {
			let el = undefined;

			if (node.is_root) {
				el = $(this).detach();
				me.$hierarchy.empty();
				$(`#connectors`).empty();
				me.add_node_to_hierarchy(el, node);
			} else if (node_element.is(':visible') && node_element.hasClass('active-path')) {
				me.remove_levels_after_node(node);
				me.remove_orphaned_connectors();
			} else {
				el = $(this).detach();
				me.add_node_to_hierarchy(el, node);
				me.collapse_node();
			}

			me.expand_node(node);
		});
	}

	setup_edit_node_action(node) {
		let node_element = $(`[id="${node.id}"]`);
		let me = this;

		node_element.find('.btn-edit-node').click(function() {
			frappe.set_route('Form', me.doctype, node.id);
		});
	}

	setup_node_group_action() {
		let me = this;

		$('.node-group').on('click', function() {
			let parent = $(this).attr('data-parent');
			if (parent === 'undefined') {
				me.setup_hierarchy();
				me.render_root_nodes();
			} else {
				me.expand_sibling_group_node(parent);
			}
		});
	}

	add_node_to_hierarchy(node_element, node) {
		this.$hierarchy.append(`<li class="level"></li>`);
		node_element.removeClass('active-child active-path');
		this.$hierarchy.find('.level:last').append(node_element);

		let node_object = this.nodes[node.id];
		node_object.expanded = 0;
		node_object.$children = undefined;
		this.nodes[node.id] = node_object;
	}

	get_node_group(nodes, parent, collapsed=true) {
		let limit = 2;
		const display_nodes = nodes.slice(0, limit);
		const extra_nodes = nodes.slice(limit);

		let html = display_nodes.map(node =>
			this.get_avatar(node)
		).join('');

		if (extra_nodes.length === 1) {
			let node = extra_nodes[0];
			html += this.get_avatar(node);
		} else if (extra_nodes.length > 1) {
			html = `
				${html}
				<span class="avatar avatar-small">
					<div class="avatar-frame standard-image avatar-extra-count"
						title="${extra_nodes.map(node => node.name).join(', ')}">
						+${extra_nodes.length}
					</div>
				</span>
			`;
		}

		if (html) {
			const $node_group =
				$(`<div class="node-group card cursor-pointer" data-parent=${parent}>
					<div class="avatar-group right overlap">
						${html}
					</div>
				</div>`);

			if (collapsed)
				$node_group.addClass('collapsed');

			return $node_group;
		}

		return null;
	}

	get_avatar(node) {
		return `<span class="avatar avatar-small" title="${node.name}">
			<span class="avatar-frame" src=${node.image} style="background-image: url(${node.image})"></span>
		</span>`;
	}

	expand_sibling_group_node(parent) {
		let node_object = this.nodes[parent];
		let node = node_object.$link;

		node.removeClass('active-child active-path');
		node_object.expanded = 0;
		node_object.$children = undefined;
		this.nodes[node.id] = node_object;

		// show parent's siblings and expand parent node
		frappe.run_serially([
			() => this.get_child_nodes(node_object.parent_id, node_object.id),
			(child_nodes) => this.get_node_group(child_nodes, node_object.parent_id, false),
			(node_group) => {
				if (node_group)
					this.$sibling_group.empty().append(node_group);
			},
			() => this.setup_node_group_action(),
			() => this.reattach_and_expand_node(node, node_object)
		]);
	}

	reattach_and_expand_node(node, node_object) {
		var el = node.detach();

		this.$hierarchy.empty().append(`
			<li class="level"></li>
		`);
		this.$hierarchy.find('.level').append(el);
		$(`#connectors`).empty();
		this.expand_node(node_object);
	}

	remove_levels_after_node(node) {
		let level = $(`[id="${node.id}"]`).parent().parent().index();

		level = $('.hierarchy-mobile > li:eq('+ level + ')');
		level.nextAll('li').remove();

		let node_object = this.nodes[node.id];
		let current_node = level.find(`#${node.id}`).detach();
		current_node.removeClass('active-child active-path');

		node_object.expanded = 0;
		node_object.$children = undefined;

		level.empty().append(current_node);
	}

	remove_orphaned_connectors() {
		let paths = $('#connectors > path');
		$.each(paths, (_i, path) => {
			const parent = $(path).data('parent');
			const child = $(path).data('child');

			if ($(`[id="${parent}"]`).length && $(`[id="${child}"]`).length)
				return;

			$(path).remove();
		});
	}

	refresh_connectors(node_parent, node_id) {
		if (!node_parent) return;

		$(`path[data-parent="${node_parent}"]`).remove();
		this.add_connector(node_parent, node_id);
	}
};
