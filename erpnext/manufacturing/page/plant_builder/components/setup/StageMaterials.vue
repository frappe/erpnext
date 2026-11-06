<script setup>
import { computed, inject, ref } from "vue";
import { Button, Dropdown, TextInput } from "frappe-ui";
import DeskControl from "../DeskControl.vue";
import { __ } from "../../lib/api";
import { MATERIAL_TONES, STORAGE_OPTIONS, SWATCH } from "../../lib/machines";
import { READ_ONLY } from "../../lib/plant";
import { num, round } from "../../lib/format";

const props = defineProps({
	doc: Object,
	data: { type: Object, default: () => ({}) },
	stageNo: Number,
	packingNo: { type: Number, default: 0 },
	stageOptions: { type: Array, default: () => [] },
});
const readOnly = inject(READ_ONLY, ref(false));

const all = computed(() => props.doc.materials);
const packing = computed(() => props.doc.packing_materials);
const isPacking = computed(() => props.stageNo === props.packingNo);
const batch = computed(() => num(props.doc.batch_size) || 1);
const stageOf = (row) => num(row.stage_row_id) || 1;
const materials = computed(() =>
	isPacking.value ? packing.value : all.value.filter((row) => stageOf(row) === props.stageNo)
);
const balanceRow = computed(() => materials.value.find((row) => row.is_balance_item));
const factorOf = (row) => num(props.data.weight_factors?.[row.item_code]);
const weightOf = (row) => (factorOf(row) ? num(row.qty) / factorOf(row) : 0);
const totalWeight = computed(() => all.value.reduce((sum, row) => sum + weightOf(row), 0));
const percentageOf = (row) => (totalWeight.value ? round((weightOf(row) / totalWeight.value) * 100, 3) : 0);
const uomOf = (row) => props.data.items?.[row.item_code]?.stock_uom || "";
const toneOf = (row) =>
	isPacking.value
		? "bg-surface-gray-3"
		: SWATCH[MATERIAL_TONES[all.value.indexOf(row) % MATERIAL_TONES.length]];

const draft = ref(null);
const shown = (row, field, value) =>
	draft.value?.row === row && draft.value.field === field ? draft.value.text : value;
function edit(row, field, text, apply) {
	draft.value = { row, field, text };
	if (text !== "" && Number.isFinite(Number(text))) apply(row, num(text));
}
const stopEditing = () => (draft.value = null);

const qtyOf = (row) => {
	if (isPacking.value) return round(num(row.qty_per_unit) * batch.value, 3);
	return round(num(row.qty), 3);
};
function setQty(row, value) {
	if (isPacking.value) row.qty_per_unit = value / batch.value;
	else row.qty = value;
}

function setPercentage(row, value) {
	const others = totalWeight.value - weightOf(row);
	const hasBalance = all.value.some((m) => m.is_balance_item && m !== row);
	if (!factorOf(row) || value < 0 || (!hasBalance && value >= 100)) return;
	const batchWeight = num(props.data.formula_weight) || totalWeight.value;
	const weight = hasBalance ? (value / 100) * batchWeight : (value / (100 - value)) * others;
	row.qty = round(weight * factorOf(row), 6);
}

const columns = computed(() =>
	isPacking.value
		? "grid-cols-[1rem_minmax(0,1fr)_8rem_1.75rem]"
		: "grid-cols-[1rem_minmax(0,1fr)_8rem_3.5rem_1.75rem]"
);

const setBalance = (row, on) => all.value.forEach((m) => (m.is_balance_item = on && m === row ? 1 : 0));
function remove(row) {
	const rows = isPacking.value ? packing.value : all.value;
	rows.splice(rows.indexOf(row), 1);
}

function moveTo(row, stageNo) {
	if (!isPacking.value && stageNo !== props.packingNo) {
		row.stage_row_id = stageNo;
		return;
	}
	remove(row);
	if (isPacking.value) {
		all.value.push({
			item_code: row.item_code,
			qty: num(row.qty_per_unit) * batch.value,
			is_balance_item: 0,
			stage_row_id: stageNo,
			storage: "Tank",
		});
	} else {
		packing.value.push({ item_code: row.item_code, qty_per_unit: num(row.qty) / batch.value });
	}
}

const rowMenu = (row) => [
	...(isPacking.value
		? []
		: [
				{
					group: __("Storage"),
					options: STORAGE_OPTIONS.map((option) => ({
						label: __(option.label),
						icon: row.storage === option.value ? "lucide-check" : undefined,
						onClick: () => (row.storage = option.value),
					})),
				},
		  ]),
	...(props.stageOptions.length
		? [
				{
					group: __("Move to Stage"),
					options: props.stageOptions.map((option) => ({
						label: option.label,
						onClick: () => moveTo(row, option.stageNo),
					})),
				},
		  ]
		: []),
	{
		group: __("Formula"),
		options: [
			...(isPacking.value
				? []
				: [
						row.is_balance_item
							? {
									label: __("Stop Using as Balance"),
									icon: "lucide-pencil",
									onClick: () => setBalance(row, false),
							  }
							: {
									label: __("Use as Balance"),
									icon: "lucide-scale",
									onClick: () => setBalance(row, true),
							  },
				  ]),
			{ label: __("Remove"), icon: "lucide-trash-2", onClick: () => remove(row) },
		],
	},
];

function add() {
	if (isPacking.value) {
		packing.value.push({ item_code: "", qty_per_unit: 1 });
		return;
	}
	all.value.push({
		item_code: "",
		qty: 0,
		is_balance_item: all.value.length ? 0 : 1,
		stage_row_id: props.stageNo,
		storage: "Tank",
	});
}
</script>

<template>
	<div v-if="materials.length || !readOnly" class="space-y-2">
		<p class="text-xs text-ink-gray-5">{{ __("Raw Materials") }}</p>
		<div
			v-if="materials.length"
			class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
		>
			<div class="grid h-8 items-center gap-2 px-2 text-xs text-ink-gray-5" :class="columns">
				<span />
				<span>{{ __("Item") }}</span>
				<span class="text-right">{{ __("Quantity") }}</span>
				<span v-if="!isPacking" class="text-right">%</span>
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
					:class="toneOf(row)"
					:title="isPacking ? '' : __(row.storage || 'Tank')"
				/>
				<DeskControl v-model="row.item_code" options="Item" :filters="{ is_stock_item: 1 }" />
				<TextInput
					:model-value="shown(row, 'qty', qtyOf(row))"
					type="number"
					size="sm"
					class="[&_input]:text-right"
					:class="{
						'[&_input]:bg-surface-base': !row.is_balance_item,
						'[&_input]:pr-12': uomOf(row),
					}"
					:disabled="!!row.is_balance_item"
					:title="row.is_balance_item ? __('Balance item') : uomOf(row)"
					@update:model-value="edit(row, 'qty', $event, setQty)"
					@blur="stopEditing"
				>
					<template v-if="uomOf(row)" #suffix>
						<span class="text-xs text-ink-gray-5">{{ uomOf(row) }}</span>
					</template>
				</TextInput>
				<TextInput
					v-if="!isPacking"
					:model-value="shown(row, 'percentage', percentageOf(row))"
					type="number"
					size="sm"
					class="[&_input]:text-right"
					:class="{ '[&_input]:bg-surface-base': !row.is_balance_item }"
					:disabled="!!row.is_balance_item || !factorOf(row)"
					@update:model-value="edit(row, 'percentage', $event, setPercentage)"
					@blur="stopEditing"
				/>
				<Dropdown v-if="!readOnly" :options="rowMenu(row)">
					<Button variant="ghost" size="sm" icon="lucide-ellipsis" :aria-label="__('More')" />
				</Dropdown>
			</div>
		</div>
		<p v-if="balanceRow" class="text-xs text-ink-gray-5">
			{{
				__(
					"{0} is the balance item. Its quantity is worked out so the batch makes the finished good weight after each stage's yield.",
					[data.items?.[balanceRow.item_code]?.item_name || __("The balance item")]
				)
			}}
		</p>
		<Button
			v-if="!readOnly"
			size="sm"
			icon-left="lucide-plus"
			:label="__('Add Raw Material')"
			@click="add"
		/>
	</div>
</template>
