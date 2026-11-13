<script setup>
import { computed, ref } from "vue";
import { Avatar, Button, ItemListRow, Tooltip } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";

import EmptyState from "./EmptyState.vue";
import InfoTip from "./InfoTip.vue";
import { avatarTheme } from "../colors.js";
import { person, useActions } from "../host.js";

const MAX_ROWS = 5;

const props = defineProps({
	data: { type: Object, required: true },
});

const __ = window.__;
const actions = useActions();

const info = __(
	"A task shared by several people counts for each of them. Group tasks are left out, as their subtasks carry the work."
);

const view = computed(() => {
	if (props.data.delivery) {
		const completed = props.data.completed_by_assignee;
		return {
			title: __("Completed by Assignee"),
			rows: completed?.rows,
			count: (row) => __("{0} completed", [row.completed]),
			note: (row) => (row.late ? __("{0} late", [row.late]) : ""),
			empty: __("No completed tasks"),
			open: (row) => actions.open_list("Task", { name: ["in", row.tasks] }),
		};
	}
	let rows = props.data.workload?.rows;
	const cut = rows && rows.length > MAX_ROWS;
	if (cut) {
		const unassigned = rows.find((row) => !row.user);
		rows = unassigned ? [...rows.slice(0, MAX_ROWS - 1), unassigned] : rows.slice(0, MAX_ROWS);
	}
	return {
		title: __("Open Tasks by Assignee"),
		rows,
		cut,
		count: (row) => __("{0} open", [row.open]),
		note: (row) => (row.overdue ? __("{0} overdue", [row.overdue]) : ""),
		empty: __("No open tasks"),
		open: (row) => actions.open_task_list({ name: ["in", row.tasks] }),
	};
});

const people = computed(() =>
	(view.value.rows || []).map((row) => ({ row, ...(row.user ? person(row.user) : {}) }))
);
const active = ref(null);
</script>

<template>
	<ChartCard class="min-h-[220px]">
		<ChartContainer
			:title="view.title"
			:error="view.rows ? null : __('Could not load tasks')"
			:empty="Boolean(view.rows) && !people.length"
		>
			<template #title-suffix><InfoTip :text="info" /></template>
			<template v-if="view.cut" #actions>
				<Tooltip :text="__('Open Task List')">
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-arrow-up-right"
						:aria-label="__('Open Task List')"
						@click="actions.open_task_list({ is_group: 0 })"
					/>
				</Tooltip>
			</template>
			<template #error>
				<span class="text-sm-medium text-ink-red-7">{{ __("Could not load tasks") }}</span>
			</template>
			<template #empty>
				<EmptyState icon="lucide-users" :title="view.empty" />
			</template>

			<div class="-mx-2.5 flex flex-col">
				<ItemListRow
					v-for="(item, index) in people"
					:key="item.user || 'unassigned'"
					as="button"
					type="button"
					size="md"
					class="text-start focus-visible:outline-none"
					:active="active === index"
					@mouseenter="active = index"
					@mouseleave="active = null"
					@focus="active = index"
					@blur="active = null"
					@click="view.open(item.row)"
				>
					<template #prefix>
						<Avatar
							v-if="item.user"
							size="lg"
							:label="item.fullname"
							:image="item.image"
							:theme="avatarTheme(item.fullname)"
						/>
						<span
							v-else
							class="flex size-7 items-center justify-center rounded-full border border-dashed border-outline-gray-4 text-base text-ink-gray-5"
							:title="__('Unassigned')"
							aria-hidden="true"
						>
							?
						</span>
					</template>
					<span class="block truncate" :class="item.user ? 'text-ink-gray-8' : 'text-ink-gray-5'">
						{{ item.user ? item.fullname : __("Unassigned") }}
					</span>
					<span class="block text-sm text-ink-gray-5">
						{{ view.count(item.row) }}
						<template v-if="view.note(item.row)">
							· <span class="text-ink-red-7">{{ view.note(item.row) }}</span>
						</template>
					</span>
				</ItemListRow>
			</div>
		</ChartContainer>
	</ChartCard>
</template>
