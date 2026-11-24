<script setup>
import { computed } from "vue";
import { ListCell, ListRow } from "frappe-ui/list";

import { long_date, short_date } from "../lib/dates.js";
import { useTasks } from "../lib/context.js";
import { is_done } from "../lib/tasks.js";
import AssigneeChip from "./AssigneeChip.vue";
import DueCell from "./DueCell.vue";
import PriorityChip from "./PriorityChip.vue";
import StatusChip from "./StatusChip.vue";

const props = defineProps({
	task: { type: Object, required: true },
	columns: { type: Array, required: true },
	// inside a group card, so titles line up with the card's label
	indent: { type: Number, default: 0 },
});

const __ = window.__;
const tasks = useTasks();
const open = computed(() => !is_done(props.task));
const progress = computed(() => Math.round(props.task.progress || 0));
</script>

<template>
	<!-- A row can't be a button and hold buttons, so a button stretched over the row opens the
	     task, and the controls after it sit above it with `relative`. -->
	<ListRow :value="task.name" class="rounded-4 hover:bg-surface-gray-1">
		<button
			type="button"
			class="absolute inset-0 rounded-4 focus-visible:focus-ring"
			:aria-label="__('Open {0}', [task.subject || task.name])"
			@click="tasks.send('tasks-open-task', { name: task.name })"
		/>
		<template v-for="column in columns" :key="column.field">
			<ListCell v-if="column.field === 'subject'">
				<span
					class="truncate text-base text-ink-gray-8"
					:style="indent ? { paddingInlineStart: `${indent}px` } : null"
					:title="`${task.subject} · ${task.name}`"
				>
					{{ task.subject }}
				</span>
			</ListCell>

			<ListCell v-else-if="column.field === 'status'">
				<StatusChip :task="task" />
			</ListCell>

			<ListCell v-else-if="column.field === 'priority'">
				<PriorityChip :task="task" />
			</ListCell>

			<ListCell v-else-if="column.field === 'exp_start_date'">
				<span
					v-if="task.exp_start_date"
					class="relative whitespace-nowrap text-base tabular-nums text-ink-gray-7"
					:title="long_date(task.exp_start_date)"
				>
					{{ short_date(task.exp_start_date) }}
				</span>
			</ListCell>

			<ListCell v-else-if="column.field === 'exp_end_date'">
				<DueCell :date="task.exp_end_date" :open="open" />
			</ListCell>

			<ListCell v-else-if="column.field === 'progress'" class="justify-end">
				<span
					class="text-base tabular-nums"
					:class="progress ? 'text-ink-gray-7' : 'text-ink-gray-4'"
				>
					{{ progress }}%
				</span>
			</ListCell>

			<!-- a gap after the right-aligned progress -->
			<ListCell v-else-if="column.field === 'assigned_to'" class="pl-6">
				<AssigneeChip :task="task" />
			</ListCell>
		</template>
	</ListRow>
</template>
