<script setup>
import { computed } from "vue";
import { Badge, Button } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import AssigneeStack from "./AssigneeStack.vue";
import { useActions } from "../host.js";

const props = defineProps({
	data: { type: Object, required: true },
});

const __ = window.__;
const moment = window.moment;
const actions = useActions();

// frappe-ui badges have no orange
const REASONS = {
	Overdue: { label: __("Overdue"), theme: "red" },
	Blocked: { label: __("Blocked"), theme: "amber" },
	Unassigned: { label: __("Unassigned"), theme: "gray" },
	"Due Soon": { label: __("Due Soon"), theme: "blue" },
};
const STATUSES = {
	Open: { label: __("Open"), theme: "gray" },
	Working: { label: __("Working"), theme: "blue" },
	"Pending Review": { label: __("Pending Review"), theme: "violet" },
};

const section = computed(() => {
	const { delivery } = props.data;
	if (delivery) {
		return {
			list: props.data.loose_ends,
			title: __("Loose Ends"),
			subtitle:
				delivery.status === "Cancelled"
					? __("Tasks still open on this cancelled project")
					: __("Tasks still open on this completed project"),
			badge_label: __("Status"),
			badges: STATUSES,
		};
	}
	const list = props.data.needs_attention;
	return {
		list,
		title: __("Needs Attention"),
		subtitle:
			list && __("Overdue, blocked, unassigned, or due in the next {0} days", [list.due_soon_days]),
		badge_label: __("Reason"),
		badges: REASONS,
	};
});

const badge = (reason) => section.value.badges[reason] || { label: __(reason), theme: "gray" };

const due_text = (due_date) => {
	if (!due_date) return "";
	const due = moment(due_date);
	return due.format(due.year() === moment().year() ? "D MMM" : "D MMM YYYY");
};
const delay_text = (days) => {
	if (!days) return "";
	return days === 1 ? __("1 day") : __("{0} days", [days]);
};

// leave modifier clicks to the browser, so they open a new tab
function open_link(event, task) {
	if (event.metaKey || event.ctrlKey || event.shiftKey) return;
	event.preventDefault();
	actions.open_task(task);
}
</script>

<template>
	<section v-if="section.list?.total !== 0" class="flex flex-col gap-3">
		<div class="flex items-end justify-between gap-2">
			<div class="min-w-0">
				<div class="text-base font-semibold text-ink-gray-8">{{ section.title }}</div>
				<div v-if="section.list" class="mt-0.5 text-sm text-ink-gray-5">{{ section.subtitle }}</div>
			</div>
			<Button
				size="sm"
				variant="ghost"
				icon-right="lucide-arrow-up-right"
				:label="__('Task List')"
				@click="actions.open_task_list()"
			/>
		</div>

		<p v-if="!section.list" class="text-sm text-ink-red-7">{{ __("Could not load tasks") }}</p>
		<div v-else class="-mx-1 overflow-x-auto px-1">
			<div class="min-w-[600px]">
				<List
					class="list-row-px-3"
					:columns="['minmax(10rem,1fr)', '104px', '112px', '80px', '80px']"
					:row-height="44"
				>
					<ListHeader>
						<ListHeaderCell>{{ __("Task") }}</ListHeaderCell>
						<ListHeaderCell>{{ section.badge_label }}</ListHeaderCell>
						<ListHeaderCell>{{ __("Assigned To") }}</ListHeaderCell>
						<ListHeaderCell class="justify-end">{{ __("Due Date") }}</ListHeaderCell>
						<ListHeaderCell class="justify-end">{{ __("Delayed By") }}</ListHeaderCell>
					</ListHeader>
					<ListRow
						v-for="row in section.list.tasks"
						:key="row.task"
						:href="actions.task_link(row.task)"
						@click="open_link($event, row.task)"
					>
						<ListCell>
							<span class="truncate text-sm text-ink-gray-8">{{ row.subject }}</span>
						</ListCell>
						<ListCell>
							<Badge
								size="sm"
								:label="badge(row.reason).label"
								:theme="badge(row.reason).theme"
							/>
						</ListCell>
						<ListCell>
							<AssigneeStack :users="row.assigned_to" />
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-8">{{
								due_text(row.due_date)
							}}</span>
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-8">{{
								delay_text(row.days_late)
							}}</span>
						</ListCell>
					</ListRow>
				</List>
			</div>
		</div>
	</section>
</template>
