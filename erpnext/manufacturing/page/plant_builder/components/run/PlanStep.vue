<script setup>
import { computed, inject, ref, watch } from "vue";
import { Button, FormControl } from "frappe-ui";
import StepHeader from "./StepHeader.vue";
import { __ } from "../../lib/api";
import { fmt, num, plural, round } from "../../lib/format";

const run = inject("run");
const order = computed(() => run.state.value.work_order);
const plan = computed(() => run.state.value.plan);
const started = computed(() => order.value.docstatus === 1);
const unit = computed(() => plan.value.stock_uom || "");
const qty = ref(order.value.qty);
let timer = null;

watch(qty, (value) => {
	clearTimeout(timer);
	if (num(value) > 0 && num(value) !== num(order.value.qty))
		timer = setTimeout(() => run.setQty(num(value)), 600);
});

async function start() {
	clearTimeout(timer);
	if (num(qty.value) !== num(order.value.qty)) await run.setQty(num(qty.value));
	await run.start();
}

const overfull = computed(() =>
	plan.value.stages
		.filter((stage) => !stage.inputs.length)
		.map((stage) => ({
			stage,
			limit: num(run.state.value.plant.machines[stage.workstation]?.batch_capacity),
		}))
		.find(({ stage, limit }) => limit && stage.input_weight > limit)
);
const error = computed(() => {
	if (num(qty.value) < 1) return __("Make at least one {0}", [unit.value]);
	if (overfull.value) {
		const { stage, limit } = overfull.value;
		return __("{0} holds {1} {2}", [stage.workstation, fmt(limit), plan.value.weight_uom]);
	}
	return "";
});

const losses = computed(() =>
	plan.value.stages
		.filter((stage) => !stage.is_packing && stage.input_weight > stage.output_weight)
		.map((stage) => {
			const loss = stage.input_weight - stage.output_weight;
			return {
				label: stage.stage_name,
				value: `${fmt(round(loss))} ${plan.value.weight_uom} · ${fmt(
					round((loss / stage.input_weight) * 100, 1)
				)}%`,
			};
		})
);
const badge = computed(() =>
	started.value ? { label: __("Started"), theme: "green" } : { label: __("Not Started"), theme: "gray" }
);
const subtitle = computed(() =>
	started.value
		? `${fmt(order.value.qty)} ${plural(unit.value).toLowerCase()} · ${order.value.name}`
		: __("Pick a quantity and the formula scales")
);
</script>

<template>
	<div>
		<StepHeader
			:title="__('Plan the Batch')"
			:subtitle="subtitle"
			:status="started ? 'done' : 'active'"
			:badge="badge"
		/>
		<div v-if="!started" class="space-y-4 px-3 pb-4">
			<FormControl
				v-model="qty"
				type="number"
				:label="__('{0} to Make', [plural(unit)])"
				:error="error"
			/>
			<div v-if="losses.length">
				<p class="mb-1 text-sm text-ink-gray-5">{{ __("Process Loss") }}</p>
				<div class="space-y-1.5 rounded-4 bg-surface-gray-1 p-3">
					<div
						v-for="row in losses"
						:key="row.label"
						class="flex items-center justify-between gap-3 text-sm"
					>
						<span class="truncate text-ink-gray-6">{{ row.label }}</span>
						<span class="shrink-0 tabular-nums text-ink-gray-8">{{ row.value }}</span>
					</div>
				</div>
			</div>
			<div>
				<p class="mb-1 text-sm text-ink-gray-5">
					{{ __("Formula for {0} {1}", [fmt(round(plan.input_weight)), plan.weight_uom]) }}
				</p>
				<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
					<div
						class="grid h-8 grid-cols-[minmax(0,1fr)_3.5rem_6rem] items-center gap-2 px-3 text-xs text-ink-gray-5"
					>
						<span>{{ __("Raw Material") }}</span>
						<span class="text-right">%</span>
						<span class="text-right">{{ __("Quantity") }}</span>
					</div>
					<div
						v-for="row in plan.materials"
						:key="row.item_code"
						class="grid h-9 grid-cols-[minmax(0,1fr)_3.5rem_6rem] items-center gap-2 px-3"
					>
						<span class="flex min-w-0 items-center gap-1.5">
							<span class="truncate text-sm text-ink-gray-8" :title="row.item_name">{{
								row.item_name
							}}</span>
							<span v-if="row.is_balance_item" class="shrink-0 text-xs text-ink-gray-5">{{
								__("balance")
							}}</span>
						</span>
						<span class="text-right text-sm tabular-nums text-ink-gray-6">{{
							fmt(row.percentage)
						}}</span>
						<span class="text-right text-sm tabular-nums text-ink-gray-8">{{
							fmt(row.qty)
						}}</span>
					</div>
				</div>
			</div>
			<Button
				variant="solid"
				icon-left="lucide-play"
				:label="__('Start Work Order')"
				class="w-full"
				:loading="run.busy.value"
				:disabled="!!error"
				@click="start"
			/>
		</div>
	</div>
</template>
