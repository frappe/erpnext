<script setup>
import { computed } from "vue";
import { __ } from "../../lib/api";
import { fmt, fmtDuration, timeOf } from "../../lib/format";

const props = defineProps({ activity: Object, names: { type: Object, default: () => ({}) } });

const continued = computed(
	() => new Set((props.activity?.logs || []).map((log) => `${log.job_card}|${log.employee}|${log.to_time}`))
);

function logEvents(log) {
	const who = props.names[log.employee] || log.employee || __("Someone");
	const isContinued = continued.value.has(`${log.job_card}|${log.employee}|${log.from_time}`);
	const events = isContinued
		? []
		: [
				{
					time: log.from_time,
					icon: "lucide-play",
					title: __("{0} started {1}", [who, log.operation]),
					detail: log.job_card,
				},
		  ];
	if (log.completed_qty)
		events.push({
			time: log.to_time,
			icon: "lucide-circle-check",
			title: __("{0} done", [fmt(log.completed_qty)]),
			detail: who,
		});
	if (log.process_loss_qty)
		events.push({
			time: log.to_time,
			icon: "lucide-circle-x",
			title: __("{0} lost · {1}", [fmt(log.process_loss_qty), log.loss_reason || ""]),
			detail: who,
		});
	if (log.pause_reason)
		events.push({
			time: log.to_time,
			icon: "lucide-pause",
			title: __("Paused · {0}", [__(log.pause_reason)]),
			detail: who,
		});
	return events;
}

const items = computed(() => {
	if (!props.activity?.logs) return [];
	const downtime = (props.activity.downtime || []).map((row) => ({
		time: row.to_time || row.from_time,
		icon: "lucide-octagon-x",
		title: __("Downtime · {0}", [__(row.stop_reason || "")]),
		detail: `${fmtDuration((row.downtime || 0) * 60)} · ${row.name}`,
	}));
	return [...props.activity.logs.flatMap(logEvents), ...downtime]
		.filter((row) => row.time)
		.sort((a, b) => String(b.time).localeCompare(String(a.time)))
		.slice(0, 30);
});
</script>

<template>
	<section class="space-y-2">
		<h3 class="text-base font-semibold text-ink-gray-8">{{ __("Today on this machine") }}</h3>
		<ol v-if="items.length" class="space-y-3 rounded-5 border border-outline-gray-2 p-4">
			<li v-for="(row, i) in items" :key="i" class="flex gap-3">
				<span class="w-12 shrink-0 pt-0.5 text-sm tabular-nums text-ink-gray-5">{{
					timeOf(row.time)
				}}</span>
				<span class="mt-0.5 size-4 shrink-0 text-ink-gray-5" :class="row.icon" aria-hidden="true" />
				<div class="min-w-0">
					<p class="text-sm text-ink-gray-8">{{ row.title }}</p>
					<p v-if="row.detail" class="text-p-xs text-ink-gray-5">{{ row.detail }}</p>
				</div>
			</li>
		</ol>
		<p
			v-else
			class="rounded-5 border border-dashed border-outline-gray-2 px-4 py-6 text-center text-sm text-ink-gray-5"
		>
			{{ __("No activity yet today") }}
		</p>
	</section>
</template>
