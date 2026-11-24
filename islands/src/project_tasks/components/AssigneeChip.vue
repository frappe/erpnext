<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, MultiSelect } from "frappe-ui";

import { avatarTheme } from "../../project_overview/colors.js";
import { person } from "../../project_overview/host.js";
import { change_assignees, search_users } from "../lib/api.js";
import { useTasks } from "../lib/context.js";
import RowAvatars from "./RowAvatars.vue";

const props = defineProps({
	task: { type: Object, required: true },
});

// A long list has a picker per row; each is built the first time its row's avatars are clicked,
// and opens straight away.
const active = ref(false);
const open = ref(false);
function activate() {
	active.value = true;
	open.value = true;
}

const __ = window.__;
const tasks = useTasks();
const me = window.frappe?.session?.user;

const assigned = computed(() => props.task.assigned_to || []);
// as in desk: anyone who can read a task assigns people to it, but taking someone else off it
// needs write access
const can_remove = (user) => user === me || props.task.can_write;

// people found by search; their names come from the search, as desk may not know them yet
const query = ref("");
const found = ref([]);
const searching = ref(false);
let search_seq = 0;
let search_timer = null;
watch(query, (text) => {
	clearTimeout(search_timer);
	if (!text.trim()) {
		found.value = [];
		searching.value = false;
		return;
	}
	searching.value = true;
	search_timer = setTimeout(async () => {
		const seq = ++search_seq;
		const results = await search_users(text.trim());
		if (seq !== search_seq) return;
		found.value = results || [];
		searching.value = false;
	}, 200);
});
const on_open = (open) => open && (query.value = "");

function option(user, label) {
	const who = person(user);
	return {
		label: label || who.fullname,
		value: user,
		image: who.image,
		disabled: assigned.value.includes(user) && !can_remove(user),
	};
}

// people already on this project's tasks first, then everyone else the search finds
const options = computed(() => {
	const text = query.value.trim().toLowerCase();
	const on_project = [...new Set([...assigned.value, ...tasks.people.value])]
		.map((user) => option(user))
		.filter((item) => !text || item.label.toLowerCase().includes(text) || item.value.includes(text));
	const known = new Set(on_project.map((item) => item.value));
	const others = found.value
		.filter((result) => !known.has(result.value) && !assigned.value.includes(result.value))
		.map((result) => option(result.value, result.label || result.description));
	return [
		{ group: __("On this project"), options: on_project },
		...(others.length ? [{ group: __("Others"), options: others }] : []),
	];
});

function update(values) {
	const { task } = props;
	const add = values.filter((user) => !assigned.value.includes(user));
	const remove = assigned.value.filter((user) => !values.includes(user) && can_remove(user));
	if (!add.length && !remove.length) return;
	const next = [...assigned.value.filter((user) => !remove.includes(user)), ...add];
	tasks.edit(task, { assigned_to: next }, () => change_assignees(task, add, remove));
}

const label = computed(() =>
	assigned.value.length
		? __("Assigned to {0}", [assigned.value.map((user) => person(user).fullname).join(", ")])
		: __("Assign")
);
</script>

<template>
	<MultiSelect
		v-if="active"
		v-model:open="open"
		v-model:query="query"
		:model-value="assigned"
		:options="options"
		:filterable="false"
		:loading="searching"
		:placeholder="__('Assign')"
		@update:model-value="update"
		@update:open="on_open"
	>
		<template #trigger>
			<button
				type="button"
				class="relative flex items-center rounded-full"
				:aria-label="label"
				:title="label"
			>
				<RowAvatars v-if="assigned.length" :users="assigned" />
				<span v-else class="lucide-circle-user-round size-5 text-ink-gray-4" aria-hidden="true" />
			</button>
		</template>
		<template #item-prefix="{ item }">
			<Avatar size="xs" :label="item.label" :image="item.image" :theme="avatarTheme(item.label)" />
		</template>
		<!-- no Clear all / Select all: people are added and taken off one at a time -->
		<template #footer><span /></template>
	</MultiSelect>
	<button
		v-else
		type="button"
		class="relative flex items-center rounded-full"
		:aria-label="label"
		:title="label"
		aria-haspopup="listbox"
		@click="activate"
	>
		<RowAvatars v-if="assigned.length" :users="assigned" />
		<span v-else class="lucide-circle-user-round size-5 text-ink-gray-4" aria-hidden="true" />
	</button>
</template>
