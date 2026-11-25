<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { List } from "frappe-ui/list";

import AssigneeStack from "../project_overview/components/AssigneeStack.vue";
import EmptyState from "../project_overview/components/EmptyState.vue";
import GroupCard from "./components/GroupCard.vue";
import PhaseMeta from "./components/PhaseMeta.vue";
import TaskListHeader from "./components/TaskListHeader.vue";
import TaskRows from "./components/TaskRows.vue";
import { grid, visible_columns } from "./lib/columns.js";
import { DEFAULT_SORT, matches_search, next_sort, sorter } from "./lib/tasks.js";
import { create_host_events } from "./host.js";
import { provideTasks, useTaskEdits } from "./lib/context.js";
import {
	FOLDED_STATUSES,
	finished_phases,
	is_card_parent,
	parent_groups,
	status_groups,
} from "./lib/groups.js";

const props = defineProps({
	doctype: { type: String, default: "Project" },
	name: { type: String, default: null },
	doc: { type: Object, default: () => ({}) },
	is_new: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
	// set by the form's Tasks tab, which loads the tasks and holds the toolbar
	tasks: { type: Object, default: null },
	failed: { type: Boolean, default: false },
	search: { type: String, default: "" },
	// "none", "status" or "parent", from the toolbar's Group menu
	group_by: { type: String, default: "none" },
});

const __ = window.__;
const element = ref(null);
const send = create_host_events(element);

// the island stays mounted when another Project opens
const data = computed(() => (props.tasks?.project === props.name ? props.tasks : null));
const loading = computed(() => !props.failed && !data.value);

const { view, edit } = useTaskEdits(() => props.tasks, send);

// what the rows' chips need: which fields can be changed in place, their options, and the people
// already on this project's tasks, whom the assignee picker offers first
provideTasks({
	send,
	edit,
	editable: computed(() => data.value?.editable || []),
	options: computed(() => data.value?.options || {}),
	people: computed(() => [...new Set((data.value?.tasks || []).flatMap((task) => task.assigned_to || []))]),
});

// the list's own width, which the form's sidebar and the window both change
const width = ref(1200);
let resize_observer;
onMounted(() => {
	resize_observer = new ResizeObserver(([entry]) => (width.value = entry.contentRect.width));
	resize_observer.observe(element.value);
});
onBeforeUnmount(() => resize_observer?.disconnect());

const columns = computed(() => visible_columns(data.value?.fields || [], width.value));
const list_columns = computed(() => grid(columns.value));

const sort = ref({ ...DEFAULT_SORT });
const sort_by = (field) => (sort.value = next_sort(sort.value, field));
// another set of rows, which starts again from the first batch; an edit keeps the rows shown
const view_key = computed(
	() => `${props.group_by}|${props.search}|${sort.value.field}|${sort.value.dir}|${props.name}`
);

// every task with the edits still being saved, parent tasks included
const all = computed(() => (data.value ? data.value.tasks.map(view) : []));
const search_text = computed(() => props.search.trim().toLowerCase());
const searching = computed(() => Boolean(search_text.value));

// Grouped by parent task, a top-level parent task is its card's header, so it isn't a row as well;
// a parent task under another one is a row in that card. Without that grouping every task is a
// row, so a parent task can still be found, opened and changed.
const rows = computed(() => {
	if (!data.value) return [];
	return all.value
		.filter((task) => props.group_by !== "parent" || !is_card_parent(task))
		.sort(sorter(sort.value, data.value.options));
});
const work = computed(() => rows.value.filter((task) => matches_search(task, search_text.value)));

const groups = computed(() => {
	if (props.group_by === "status") return status_groups(work.value, data.value?.options.status);
	if (props.group_by === "parent") return parent_groups(all.value, rows.value, search_text.value);
	return [];
});
// grouped by parent task, a search can match a card's parent task and none of its rows
const no_match = computed(
	() => searching.value && (props.group_by === "parent" ? !groups.value.length : !work.value.length)
);

// finished groups start folded, each time the grouping or the project changes; a search opens all
const folded = ref(new Set());
watch(
	() => [props.group_by, data.value?.project],
	() => {
		folded.value = new Set(props.group_by === "parent" ? finished_phases(groups.value) : FOLDED_STATUSES);
	},
	{ immediate: true }
);
const is_open = (group) => searching.value || !folded.value.has(group.key);
function toggle(group) {
	const next = new Set(folded.value);
	next.has(group.key) ? next.delete(group.key) : next.add(group.key);
	folded.value = next;
}
const add_to = (group) => send("tasks-new-task", { defaults: group.defaults });
</script>

<template>
	<div ref="element" class="flex flex-col gap-3 pb-8" :aria-busy="loading">
		<p v-if="is_new" class="text-base text-ink-gray-5">
			{{ __("Save the project first to add and view its tasks.") }}
		</p>

		<template v-else>
			<div v-if="loading" class="space-y-4 pt-2">
				<div v-for="i in 8" :key="i" class="flex items-center gap-6">
					<div class="h-4 flex-1 animate-pulse rounded-1 bg-surface-gray-2" />
					<div class="h-4 w-20 animate-pulse rounded-1 bg-surface-gray-2 max-lg:hidden" />
					<div class="h-4 w-16 animate-pulse rounded-1 bg-surface-gray-2 max-lg:hidden" />
					<div class="h-4 w-24 animate-pulse rounded-1 bg-surface-gray-2" />
				</div>
			</div>

			<EmptyState
				v-else-if="props.failed"
				icon="lucide-circle-alert"
				:title="__('Could not load tasks')"
			/>

			<EmptyState
				v-else-if="!data.tasks.length"
				icon="lucide-list-checks"
				:title="__('No tasks yet')"
				:actions="
					data.can_create
						? [
								{
									label: __('Add task'),
									icon: 'lucide-plus',
									onClick: () => send('tasks-new-task'),
								},
						  ]
						: []
				"
			/>

			<EmptyState
				v-else-if="no_match"
				icon="lucide-search-x"
				:title="__('No tasks match this search')"
				:actions="[{ label: __('Clear search'), onClick: () => send('tasks-clear-search') }]"
			/>

			<!-- grouped: one column header above a card per group; the border's 1px is matched -->
			<template v-else-if="groups.length">
				<List :columns="list_columns" class="list-row-px-3 px-px">
					<TaskListHeader :columns="columns" :sort="sort" @sort="sort_by" />
				</List>
				<GroupCard
					v-for="group in groups"
					:key="group.key"
					:label="group.label"
					:expanded="is_open(group)"
					:has_rows="group.items.length > 0"
					:can_add="group.can_add && data.can_create"
					@toggle="toggle(group)"
					@add="add_to(group)"
				>
					<template v-if="group.phase" #meta>
						<PhaseMeta :phase="group.phase" :done="group.done" :total="group.total" />
					</template>
					<template v-if="group.people?.length" #end>
						<span class="max-sm:hidden"><AssigneeStack :users="group.people" /></span>
					</template>
					<List :columns="list_columns" :row-height="40" class="list-row-px-3">
						<TaskRows
							:tasks="group.items"
							:columns="columns"
							:indent="20"
							:view_key="view_key"
							:first="20"
						/>
					</List>
				</GroupCard>
				<p v-if="data.truncated" class="text-sm text-ink-gray-5">
					{{ __("Showing the first {0} tasks.", [data.tasks.length]) }}
				</p>
			</template>

			<template v-else>
				<List :columns="list_columns" :row-height="40" class="-mx-3 list-row-px-3">
					<TaskListHeader :columns="columns" :sort="sort" @sort="sort_by" />
					<TaskRows :tasks="work" :columns="columns" :view_key="view_key" />
				</List>
				<p v-if="data.truncated" class="text-sm text-ink-gray-5">
					{{ __("Showing the first {0} tasks.", [data.tasks.length]) }}
				</p>
			</template>
		</template>
	</div>
</template>
