<script setup>
import { computed, inject } from "vue";
import { Button } from "frappe-ui";
import { __, call, setRoute } from "../../lib/api";
import { machineOf } from "../../lib/machines";
import { fmt, fmtTimer, num, plural, round } from "../../lib/format";

const run = inject("run");
const state = computed(() => run.state.value);
const order = computed(() => state.value.work_order);

const kpis = computed(() => {
	const charged = num(order.value.charged_weight);
	const good = num(order.value.produced_qty);
	const yieldPercentage = charged
		? round(((good * state.value.plan.weight_per_unit) / charged) * 100, 1)
		: 0;
	return [
		{ label: __("Good {0}", [plural(order.value.stock_uom).toLowerCase()]), value: fmt(good) },
		{ label: __("Process Loss"), value: fmt(order.value.process_loss_qty) },
		{ label: __("Overall Yield"), value: `${fmt(yieldPercentage)}%` },
	];
});

const batchesOf = (entry, finished) =>
	entry.items.filter((row) => !!row.is_finished_item === finished).flatMap((row) => row.batch_ids);

const chain = computed(() => {
	const entries = state.value.entries;
	const materials = new Set(state.value.plan.materials.map((row) => row.item_code));
	const rawBatches = entries
		.filter((entry) => entry.purpose === "Material Transfer for Manufacture")
		.flatMap((entry) => entry.items.filter((row) => materials.has(row.item_code)))
		.flatMap((row) => row.batch_ids);
	const raw = {
		title: __("Raw material batches"),
		meta: [...new Set(rawBatches)].join(", ") || __("Not batch tracked"),
		icon: "lucide-boxes",
	};
	const steps = state.value.stages.map((stage) => {
		const batches = entries
			.filter((row) => row.purpose === "Manufacture" && stage.job_cards.includes(row.job_card))
			.flatMap((entry) => batchesOf(entry, true));
		const parts = [
			[...new Set(batches)].join(", "),
			`${fmt(stage.output.completed_qty)} ${stage.output.uom}`,
			stage.lot > 1 ? __("{0} lots", [stage.lot]) : "",
			fmtTimer(Math.floor(stage.worked_seconds || 0)),
		];
		const { icon } = machineOf(stage.machine_model);
		return { title: stage.output.item_name, meta: parts.filter(Boolean).join(" · "), icon };
	});
	return [raw, ...steps];
});

async function runAnother() {
	setRoute("run", await call("repeat_work_order", { work_order: order.value.name }));
}
</script>

<template>
	<div class="space-y-4 rounded-5 border border-outline-gray-2 p-4">
		<div class="flex items-center gap-2">
			<span class="lucide-circle-check size-4 text-ink-green-5" aria-hidden="true" />
			<p class="flex-1 truncate text-base-semibold text-ink-gray-8">
				{{ __("Work Order completed in {0}", [fmtTimer(run.elapsed.value)]) }}
			</p>
		</div>
		<div class="grid grid-cols-3 divide-x divide-outline-gray-2">
			<div v-for="kpi in kpis" :key="kpi.label" class="px-3 first:pl-0">
				<p class="truncate text-xs text-ink-gray-5">{{ kpi.label }}</p>
				<p class="mt-1 text-lg-semibold tabular-nums text-ink-gray-9">{{ kpi.value }}</p>
			</div>
		</div>
		<div>
			<p class="mb-2 text-sm text-ink-gray-5">{{ __("Batch genealogy") }}</p>
			<div v-for="(node, i) in chain" :key="node.title + i" class="relative flex gap-3">
				<div class="flex flex-col items-center">
					<div
						class="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
					>
						<span class="size-3.5" :class="node.icon" aria-hidden="true" />
					</div>
					<div v-if="i < chain.length - 1" class="w-px flex-1 bg-surface-gray-4" />
				</div>
				<div class="min-w-0 flex-1 pb-3">
					<p class="truncate text-sm text-ink-gray-8">{{ node.title }}</p>
					<p class="truncate text-xs tabular-nums text-ink-gray-5" :title="node.meta">
						{{ node.meta }}
					</p>
				</div>
			</div>
		</div>
		<Button
			icon-left="lucide-rotate-ccw"
			:label="__('Run Another Batch')"
			class="w-full"
			@click="runAnother"
		/>
	</div>
</template>
