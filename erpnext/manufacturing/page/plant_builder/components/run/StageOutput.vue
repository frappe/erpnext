<script setup>
import { computed, inject } from "vue";
import { Button, FormControl } from "frappe-ui";
import { __ } from "../../lib/api";
import { fmt, num, plural, round } from "../../lib/format";

const props = defineProps({ stage: Object, meta: Object });
const run = inject("run");
const local = run.local;
const plan = computed(() => run.state.value.plan);

const consumedWeight = computed(() =>
	props.stage.items
		.filter((row) => row.weight_factor)
		.reduce((sum, row) => sum + num(row.transferred_qty) / row.weight_factor, 0)
);
const packingSets = computed(() => {
	const perUnit = Object.fromEntries(
		(run.state.value.plant.doc.packing_materials || []).map((row) => [
			row.item_code,
			num(row.qty_per_unit),
		])
	);
	const sets = props.stage.items
		.filter((row) => perUnit[row.item_code])
		.map((row) => num(row.transferred_qty) / perUnit[row.item_code]);
	return sets.length ? Math.min(...sets) : Infinity;
});
const outputWeight = computed(() => {
	const factor = num(props.stage.output.weight_factor);
	return factor ? num(local.output[props.stage.idx]) / factor : null;
});
const unit = computed(() => plural(props.stage.output.uom || ""));
const outputLabel = computed(() =>
	props.meta.pack
		? __("Good {0}", [unit.value.toLowerCase()])
		: __("{0} Made ({1})", [props.stage.output.item_name, props.stage.output.uom])
);

const errors = computed(() => {
	const output = num(local.output[props.stage.idx]);
	if (output <= 0) return [__("Enter the quantity made")];
	const units = output + num(local.rejected[props.stage.idx]);
	if (props.meta.pack && units > packingSets.value + 0.001) {
		return [
			__("Only {0} sets of packing material were issued to the line", [fmt(round(packingSets.value))]),
		];
	}
	if (units > num(props.stage.output.planned_qty) + 0.001) {
		return [
			__("You cannot make more than {0} {1} from the materials that went in", [
				fmt(props.stage.output.planned_qty),
				props.stage.output.uom,
			]),
		];
	}
	return qualityErrors();
});

function qualityErrors() {
	const quality = props.stage.quality;
	if (!quality) return [];
	return quality.parameters
		.filter((p) => p.numeric)
		.map((p) => {
			const value = local.readings[props.stage.idx]?.[p.specification];
			if (value === "" || value == null) return __("Enter the {0} reading", [p.specification]);
			if (num(value) < num(p.min_value) || num(value) > num(p.max_value)) {
				return __("{0} is outside {1} to {2}. Adjust the batch and test again.", [
					p.specification,
					fmt(p.min_value),
					fmt(p.max_value),
				]);
			}
		})
		.filter(Boolean);
}

const facts = computed(() => {
	const output = num(local.output[props.stage.idx]);
	if (props.meta.pack) {
		const filled = (output + num(local.rejected[props.stage.idx])) * plan.value.weight_per_unit;
		return [
			[
				__("Filled into {0}", [unit.value.toLowerCase()]),
				`${fmt(round(filled))} ${plan.value.weight_uom}`,
			],
			[__("Left in the line"), `${fmt(round(consumedWeight.value - filled))} ${plan.value.weight_uom}`],
		];
	}
	const wentIn = [__("Went in"), `${fmt(round(consumedWeight.value))} ${plan.value.weight_uom}`];
	if (outputWeight.value === null) return [wentIn];
	const yieldPercentage = consumedWeight.value
		? round((outputWeight.value / consumedWeight.value) * 100, 1)
		: 0;
	return [
		wentIn,
		...(props.stage.output.uom !== plan.value.weight_uom
			? [[__("Made"), `${fmt(round(outputWeight.value))} ${plan.value.weight_uom}`]]
			: []),
		[
			__("Lost in this stage"),
			`${fmt(round(consumedWeight.value - outputWeight.value))} ${plan.value.weight_uom}`,
		],
		[__("Yield"), `${fmt(yieldPercentage)}%`],
	];
});
</script>

<template>
	<div class="space-y-4">
		<div :class="meta.pack ? 'grid grid-cols-2 gap-3' : 'space-y-4'">
			<FormControl v-model="local.output[stage.idx]" type="number" :label="outputLabel" />
			<FormControl
				v-if="meta.pack"
				v-model="local.rejected[stage.idx]"
				type="number"
				:label="__('Rejected {0}', [unit.toLowerCase()])"
			/>
			<template v-if="stage.quality">
				<FormControl
					v-for="parameter in stage.quality.parameters.filter((p) => p.numeric)"
					:key="parameter.specification"
					v-model="local.readings[stage.idx][parameter.specification]"
					type="number"
					:label="__('{0} Reading', [parameter.specification])"
					:description="
						__('Target is {0} to {1}', [fmt(parameter.min_value), fmt(parameter.max_value)])
					"
				/>
			</template>
		</div>
		<div class="space-y-1.5 rounded-4 bg-surface-gray-1 p-3">
			<div
				v-for="[label, value] in facts"
				:key="label"
				class="flex items-center justify-between gap-3 text-sm"
			>
				<span class="truncate text-ink-gray-6">{{ label }}</span>
				<span class="shrink-0 tabular-nums text-ink-gray-8">{{ value }}</span>
			</div>
		</div>
		<p v-for="error in errors" :key="error" class="text-p-sm text-ink-red-5">{{ error }}</p>
		<Button
			variant="solid"
			icon-left="lucide-package-check"
			class="w-full"
			:label="meta.action"
			:loading="run.busy.value"
			:disabled="errors.length > 0 || run.paused.value"
			@click="run.produce(stage)"
		/>
	</div>
</template>
