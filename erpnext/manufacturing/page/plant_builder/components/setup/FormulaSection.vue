<script setup>
import { computed, inject, ref } from "vue";
import { Badge, Button, Dropdown, TextInput } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import DeskControl from "../DeskControl.vue";
import { __ } from "../../lib/api";
import { MATERIAL_TONES, STORAGE_OPTIONS, SWATCH, isPackingModel } from "../../lib/machines";
import { READ_ONLY, machineModelOf } from "../../lib/plant";
import { fmt, num, round } from "../../lib/format";

const props = defineProps({ doc: Object, data: { type: Object, default: () => ({}) } });
const readOnly = inject(READ_ONLY, ref(false));

const materials = computed(() => props.doc.materials);
const balanceRow = computed(() => materials.value.find((row) => row.is_balance_item));
const weightUom = computed(() => props.data.item?.weight_uom || "");
const factorOf = (row) => num(props.data.weight_factors?.[row.item_code]);
const weightOf = (row) => (factorOf(row) ? num(row.qty) / factorOf(row) : 0);
const totalWeight = computed(() => materials.value.reduce((sum, row) => sum + weightOf(row), 0));
const percentageOf = (row) => (totalWeight.value ? round((weightOf(row) / totalWeight.value) * 100, 3) : 0);
const uomOf = (row) => props.data.items?.[row.item_code]?.stock_uom || "";

function setPercentage(row, value) {
	const batchWeight = num(props.data.formula_weight) || totalWeight.value;
	if (!factorOf(row) || !batchWeight || num(value) === percentageOf(row)) return;
	row.qty = round((num(value) / 100) * batchWeight * factorOf(row), 3);
}

const summary = computed(() => ({
	label: `${fmt(round(totalWeight.value))} ${weightUom.value}`.trim(),
	theme: balanceRow.value && num(balanceRow.value.qty) <= 0 ? "red" : "gray",
}));

const stageOptions = computed(() =>
	props.doc.stages
		.map((stage, i) => ({ stage, label: String(i + 1), value: String(i + 1) }))
		.filter(({ stage }) => !isPackingModel(machineModelOf(stage, props.data.machines || {})))
		.map(({ label, value }) => ({ label, value }))
);
const showStage = computed(() => stageOptions.value.length > 1);
const columns = computed(() =>
	showStage.value
		? "grid-cols-[1.25rem_minmax(0,1fr)_3.5rem_6.5rem_4.5rem_1.75rem]"
		: "grid-cols-[1.25rem_minmax(0,1fr)_7rem_4.5rem_1.75rem]"
);
const stageOf = (row) => String(row.stage_row_id || 1);
const setStage = (row, value) => (row.stage_row_id = Number(value) || 1);

const setBalance = (row) => materials.value.forEach((m) => (m.is_balance_item = m === row ? 1 : 0));
const remove = (row) => materials.value.splice(materials.value.indexOf(row), 1);
const rowMenu = (row) => [
	{
		group: __("Storage"),
		options: STORAGE_OPTIONS.map((option) => ({
			label: __(option.label),
			icon: row.storage === option.value ? "lucide-check" : undefined,
			onClick: () => (row.storage = option.value),
		})),
	},
	{
		group: __("Formula"),
		options: [
			{ label: __("Use as Balance"), icon: "lucide-scale", onClick: () => setBalance(row) },
			{ label: __("Remove"), icon: "lucide-trash-2", onClick: () => remove(row) },
		],
	},
];
const add = () =>
	materials.value.push({
		item_code: "",
		qty: 0,
		is_balance_item: materials.value.length ? 0 : 1,
		stage_row_id: 1,
		storage: "Tank",
	});
</script>

<template>
	<section class="space-y-3">
		<SectionHead
			:title="__('Formula')"
			:description="
				__(
					'Raw materials for one batch and the stage that takes each one. Type a quantity or a share of the batch weight.'
				)
			"
		>
			<Badge
				v-if="materials.length && weightUom"
				:label="summary.label"
				:theme="summary.theme"
				variant="subtle"
			/>
		</SectionHead>
		<div
			v-if="materials.length"
			class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
		>
			<div class="grid h-8 items-center gap-2 px-2 text-xs text-ink-gray-5" :class="columns">
				<span />
				<span>{{ __("Raw Material") }}</span>
				<span v-if="showStage">{{ __("Stage") }}</span>
				<span class="text-right">{{ __("Quantity") }}</span>
				<span class="text-right">%</span>
				<span />
			</div>
			<div
				v-for="(row, i) in materials"
				:key="row.name || i"
				class="grid h-11 items-center gap-2 px-2"
				:class="columns"
			>
				<span
					class="size-4 rounded-full border border-outline-gray-3"
					:class="SWATCH[MATERIAL_TONES[i % MATERIAL_TONES.length]]"
					:title="__(row.storage || 'Tank')"
				/>
				<DeskControl v-model="row.item_code" options="Item" :filters="{ is_stock_item: 1 }" />
				<DeskControl
					v-if="showStage"
					:model-value="stageOf(row)"
					fieldtype="Select"
					:options="stageOptions"
					@update:model-value="setStage(row, $event)"
				/>
				<span
					v-if="row.is_balance_item"
					class="truncate text-right text-sm tabular-nums text-ink-gray-6"
					:title="__('Balance item')"
				>
					{{ fmt(row.qty) }} {{ uomOf(row) }}
				</span>
				<TextInput
					v-else
					v-model="row.qty"
					type="number"
					size="sm"
					class="[&_input]:bg-surface-base [&_input]:text-right"
					:title="uomOf(row)"
				>
					<template v-if="uomOf(row)" #suffix>
						<span class="text-xs text-ink-gray-5">{{ uomOf(row) }}</span>
					</template>
				</TextInput>
				<span v-if="row.is_balance_item" class="text-right text-sm tabular-nums text-ink-gray-6">
					{{ fmt(percentageOf(row)) }}
				</span>
				<TextInput
					v-else
					:model-value="percentageOf(row)"
					type="number"
					size="sm"
					class="[&_input]:bg-surface-base [&_input]:text-right"
					:disabled="!factorOf(row)"
					@update:model-value="setPercentage(row, $event)"
				/>
				<Dropdown v-if="!readOnly" :options="rowMenu(row)">
					<Button variant="ghost" size="sm" icon="lucide-ellipsis" :aria-label="__('More')" />
				</Dropdown>
			</div>
		</div>
		<div class="flex items-center gap-3">
			<Button v-if="!readOnly" icon-left="lucide-plus" :label="__('Add Material')" @click="add" />
			<p class="min-w-0 truncate text-xs text-ink-gray-5">
				<template v-if="balanceRow">
					{{
						__("{0} tops the batch up to the weight the formula needs", [
							data.items?.[balanceRow.item_code]?.item_name || __("The balance item"),
						])
					}}
				</template>
				<template v-else>{{
					__("No balance item, so the quantities must make the batch exactly")
				}}</template>
			</p>
		</div>
	</section>
</template>
