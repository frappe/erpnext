<script setup>
import { computed } from "vue";
import { NumberCard } from "frappe-ui/charts";

import { useFormat } from "../format.js";
import { useActions } from "../host.js";

const props = defineProps({
	data: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	project: { type: String, required: true },
});

const __ = window.__;
const format = useFormat();
const actions = useActions();

const cards = computed(() => {
	const stats = props.data?.stats;
	const delivery = stats && props.data.delivery;
	const cancelled = delivery?.status === "Cancelled";
	let labels = [__("Open Tasks"), __("Overdue"), __("Hours Logged")];
	if (cancelled) labels = [__("Tasks Delivered"), __("Hours Logged")];
	else if (delivery) labels = [__("Tasks Delivered"), __("On Time"), __("Hours Logged")];

	const failed = () => ({ value: "—", caption: __("Could not load tasks"), caption_error: true });
	let list = labels.map(() => (props.loading ? { loading: true } : failed()));
	const hours = stats?.hours && hours_card(stats);
	if (cancelled) list = [delivered_card(delivery), hours];
	else if (delivery) list = [delivered_card(delivery), on_time_card(delivery), hours];
	else if (stats) list = [open_tasks_card(stats), overdue_card(stats), hours];

	list.forEach((card, index) => card && (card.label = labels[index]));
	list = list.filter(Boolean);
	if (stats && props.data.unbilled) list.push(unbilled_card(props.data.unbilled));
	return list;
});

function open_tasks_card({ open_tasks: { count, due_soon, due_soon_days } }) {
	let caption = __("None open");
	if (count) {
		caption = due_soon
			? __("{0} due in the next {1} days", [due_soon, due_soon_days])
			: __("None due in the next {0} days", [due_soon_days]);
	}
	return { value: format.number(count), caption, onClick: () => actions.open_task_list() };
}

function overdue_card({ overdue: { count, oldest_days_late, tasks } }) {
	return {
		value: format.number(count),
		color: count ? "var(--ink-red-7)" : undefined,
		caption: count ? __("Oldest {0}", [format.days_late(oldest_days_late)]) : __("Nothing overdue"),
		// by name, as a due-date filter can't leave out tasks still awaiting review
		onClick: count ? () => actions.open_list("Task", { name: ["in", tasks] }) : null,
	};
}

function delivered_card({ total, completed, cancelled, open }) {
	const notes = [];
	if (cancelled) notes.push(__("{0} cancelled", [cancelled]));
	if (open) notes.push(__("{0} still open", [open]));
	return {
		value: __("{0} of {1}", [format.number(completed), format.number(total)]),
		caption: notes.length ? notes.join(" · ") : __("All tasks completed"),
		onClick: () => actions.open_list("Task", { project: props.project, status: "Completed" }),
	};
}

function on_time_card({ rated, late }) {
	if (!rated) return { value: "—", caption: __("No Expected End Dates to compare") };
	let caption = __("Every task finished on time");
	if (late) caption = late === 1 ? __("1 task finished late") : __("{0} tasks finished late", [late]);
	return {
		value: Math.round(((rated - late) / rated) * 100) + "%",
		caption,
		onClick: () => actions.open_list("Task", { project: props.project, status: "Completed" }),
	};
}

function hours_card({ hours: { logged, expected } }) {
	let caption = __("No Expected Time to compare");
	if (expected && logged > expected) {
		caption = __("{0} over {1} expected", [format.hours(logged - expected), format.hours(expected)]);
	} else if (expected) {
		caption = __("{0}% of {1} expected", [Math.round((logged / expected) * 100), format.hours(expected)]);
	}
	return {
		value: format.hours(logged),
		caption,
		onClick: () => actions.open_list("Timesheet", { project: props.project, docstatus: 1 }),
	};
}

function unbilled_card({ amount, hours, currency }) {
	let caption = __("All billable time invoiced");
	if (amount) {
		caption =
			hours == null
				? __("Billable time not invoiced")
				: __("{0} of billable time not invoiced", [format.hours(hours)]);
	}
	return {
		label: __("Unbilled"),
		value: format.money(amount, currency),
		caption,
		onClick: () =>
			actions.open_list("Timesheet", {
				"Timesheet Detail.project": props.project,
				"Timesheet Detail.is_billable": 1,
				"Timesheet Detail.sales_invoice": ["is", "not set"],
				docstatus: 1,
			}),
	};
}

const COLUMNS = { 2: "lg:grid-cols-2", 3: "lg:grid-cols-3" };
</script>

<template>
	<div class="grid grid-cols-2 gap-4" :class="COLUMNS[cards.length] || 'lg:grid-cols-4'">
		<component
			:is="card.onClick ? 'button' : 'div'"
			v-for="card in cards"
			:key="card.label"
			:type="card.onClick ? 'button' : undefined"
			class="block rounded-lg text-start"
			:class="
				card.onClick &&
				'transition hover:bg-surface-gray-1 focus-visible:ring-2 focus-visible:ring-outline-gray-3'
			"
			@click="card.onClick?.()"
		>
			<NumberCard
				class="h-full"
				:title="card.label"
				:value="card.value"
				:color="card.color"
				:loading="card.loading"
			>
				<template v-if="card.caption" #caption>
					<span :class="card.caption_error ? 'text-ink-red-7' : 'text-ink-gray-5'">{{
						card.caption
					}}</span>
				</template>
			</NumberCard>
		</component>
	</div>
</template>
