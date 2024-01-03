<script setup>
import { inject, watch, shallowRef, computed } from "vue";
import CatalogItemGroupTree from "./CatalogItemGroupTree.vue";

const props = defineProps({
	node: {
		type: Object,
		default: null,
	},
});

const bus = inject("bus");
const tree = shallowRef(null);

function emitFilter(name) {
	const filters = [["Item", "item_group", "descendants of (inclusive)", name, false]];
	bus.emit("setFilters", filters);
}

async function getTree() {
	const groups = await frappe.db.get_list("Item Group", {
		fields: ["parent_item_group", "name"],
	});
	const id_field = "name";
	const parent_field = "parent_item_group";
	const title_field = "name";
	const tmp_tree = {};
	const register_node = (id, values = null) => {
		let node = tmp_tree[id];
		if (!node) {
			node = tmp_tree[id] = { children: [] };
		}
		Object.assign(node, values);
		return node;
	};
	for (const grp of groups) {
		const parent_id = String(grp[parent_field] || "");
		const name = grp[id_field];
		const title = grp[title_field] || name;
		const parent = register_node(parent_id);
		parent.children.push(register_node(name, { name, title }));
	}
	return tmp_tree[""];
}

const sortedChildren = computed(() => {
	if (!tree.value?.children?.length) {
		return null;
	}
	const array = [...tree.value.children];
	array.sort((x, y) => {
		const x1 = +(x.children.length || 0);
		const y1 = +(y.children.length || 0);
		if (x1 != y1) {
			return y1 - x1;
		}
		return x.title?.localeCompare(y.title);
	});
	return array;
});

watch(
	() => props.node,
	async () => {
		if (props.node) {
			tree.value = props.node;
		} else {
			tree.value = await getTree();
		}
	},
	{ immediate: true }
);
</script>

<template>
	<div v-if="!tree">
		Loading...
	</div>
	<details v-else-if="tree.name && sortedChildren?.length" open>
		<summary>
			<button class="btn btn-xs btn-text-default" @click="emitFilter(tree.name)">
				<span v-html="frappe.utils.icon('filter', 'sm')" style="margin-right: 2px" />
				<span>{{ tree.title || tree.name }}</span>
			</button>
		</summary>
		<div
			style="
				padding-inline-start: 6px;
				margin-inline-start: 6px;
				border-inline-start: 1px solid white;
			"
		>
			<CatalogItemGroupTree :node="child" v-for="child in sortedChildren" :key="child.name" />
		</div>
	</details>
	<div v-else-if="tree.name">
		<button class="btn btn-xs btn-text-default" @click="emitFilter(tree.name)">
			<span v-html="frappe.utils.icon('filter', 'sm')" style="margin-right: 2px" />
			<span>{{ tree.title || tree.name }}</span>
		</button>
	</div>
	<template v-else>
		<CatalogItemGroupTree :node="child" v-for="child in sortedChildren" :key="child.name" />
	</template>
</template>
