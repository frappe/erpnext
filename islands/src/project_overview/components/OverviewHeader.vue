<script setup>
import { computed } from "vue";

import { useFormat } from "../format.js";
import { useActions } from "../host.js";

const props = defineProps({
	data: { type: Object, default: null },
	doc: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();
const actions = useActions();
const full = (date) => format.date(date, "D MMM YYYY");

const range = computed(() => {
	const { expected_start_date: start, expected_end_date: end } = props.doc;
	if (!start && !end) return "";
	if (!end) return __("From {0}", [full(start)]);
	if (!start) return __("Until {0}", [full(end)]);
	const same_year = window.moment(start).year() === window.moment(end).year();
	return format.date(start, same_year ? "D MMM" : "D MMM YYYY") + " – " + full(end);
});

const items = computed(() => {
	const data = props.data;
	if (data?.summary?.all_cancelled) return [];
	if (data?.delivery) {
		return [data.delivery.status === "Cancelled" ? cancelled(data.delivery) : delivered(data.delivery)];
	}
	const list = [];
	const milestone = data?.summary?.has_tasks && data.milestone;
	if (milestone && (milestone.next || milestone.all_met)) list.push(next_milestone(milestone));
	if (range.value) list.push({ text: range.value });
	return list;
});

function delivered({ finished_on, planned_end, days_late }) {
	const item = {
		icon: "lucide-circle-check",
		label: finished_on ? __("Completed {0}", [full(finished_on)]) : __("Completed"),
	};
	if (days_late != null) {
		let schedule = __("On time");
		if (days_late > 0) schedule = format.days_late(days_late);
		else if (days_late < 0) schedule = format.days_early(-days_late);
		item.note = schedule + " · " + __("planned {0}", [full(planned_end)]);
		item.note_error = days_late > 0;
	}
	return item;
}

function cancelled({ percent_complete }) {
	const notes = [__("{0}% complete", [format.number(percent_complete, percent_complete % 1 ? 1 : 0)])];
	if (range.value) notes.push(__("planned {0}", [range.value]));
	return { icon: "lucide-circle-x", label: __("Cancelled"), note: notes.join(" · ") };
}

function next_milestone({ next, all_met }) {
	const item = {
		icon: "lucide-flag",
		prefix: __("Next Milestone"),
		label: next ? next.subject : __("All milestones met"),
		onClick: () =>
			next
				? actions.open_task(next.task)
				: actions.open_list("Task", { project: props.doc.name, is_milestone: 1 }),
	};
	if (next?.due_date) {
		item.note = due_text(next);
		item.note_error = next.days_left < 0;
	}
	return item;
}

function due_text({ due_date, days_left }) {
	let relative = __("in {0} days", [days_left]);
	if (days_left < 0) relative = format.days_late(-days_left);
	else if (days_left === 0) relative = __("today");
	else if (days_left === 1) relative = __("tomorrow");
	return format.date(due_date, "D MMM") + " · " + relative;
}
</script>

<template>
	<div
		v-if="items.length"
		class="flex flex-wrap items-center justify-end gap-x-3 gap-y-1.5 text-sm text-ink-gray-5"
	>
		<template v-for="(item, index) in items" :key="index">
			<span v-if="index" class="h-3.5 w-px bg-outline-gray-2" aria-hidden="true" />
			<span class="flex items-center gap-1.5">
				<span v-if="item.icon" :class="item.icon" class="size-4" aria-hidden="true" />
				<span v-if="item.text">{{ item.text }}</span>
				<span v-if="item.prefix">{{ item.prefix }}</span>
				<button
					v-if="item.onClick"
					type="button"
					class="font-medium text-ink-gray-8 hover:underline"
					@click="item.onClick"
				>
					{{ item.label }}
				</button>
				<span v-else-if="item.label" class="font-medium text-ink-gray-8">{{ item.label }}</span>
				<span v-if="item.note" :class="item.note_error ? 'text-ink-red-7' : 'text-ink-gray-7'">
					{{ item.note }}
				</span>
			</span>
		</template>
	</div>
</template>
