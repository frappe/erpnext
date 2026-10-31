<script setup>
import { computed } from "vue";
import { Badge, Button, Dropdown, Select, TextInput } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import LinkField from "../LinkField.vue";
import { __ } from "../../lib/api";
import { MATERIAL_TONES, STORAGE_OPTIONS, SWATCH } from "../../lib/machines";
import { balancePercentage } from "../../lib/plant";
import { fmt } from "../../lib/format";

const props = defineProps({ doc: Object });

const materials = computed(() => props.doc.materials);
const balanceRow = computed(() => materials.value.find((row) => row.is_balance_item));
const rest = computed(() => balancePercentage(props.doc));
const summary = computed(() => {
	if (balanceRow.value) {
		const label = `${balanceRow.value.item_name || __("Balance")} ${fmt(rest.value)}%`;
		return { label, theme: rest.value > 0 ? "gray" : "red" };
	}
	const total = 100 - rest.value;
	return { label: __("Total {0}%", [fmt(total)]), theme: Math.abs(rest.value) < 0.001 ? "green" : "red" };
});

const setBalance = (row) => materials.value.forEach((m) => (m.is_balance_item = m === row ? 1 : 0));
const remove = (row) => materials.value.splice(materials.value.indexOf(row), 1);
const rowMenu = (row) => [
	{ label: __("Use as Balance"), icon: "lucide-scale", onClick: () => setBalance(row) },
	{ label: __("Remove"), icon: "lucide-trash-2", onClick: () => remove(row) },
];
const add = () =>
	materials.value.push({
		item_code: "",
		percentage: 5,
		is_balance_item: materials.value.length ? 0 : 1,
		storage: "Tank",
	});
</script>

<template>
	<section class="space-y-3">
		<SectionHead
			:title="__('Formula')"
			:description="
				__('Raw materials charged into the first stage, as a percentage of the batch weight.')
			"
		>
			<Badge :label="summary.label" :theme="summary.theme" variant="subtle" />
		</SectionHead>
		<div
			v-if="materials.length"
			class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
		>
			<div
				class="grid h-8 grid-cols-[1.25rem_minmax(0,1fr)_5.5rem_4.5rem_1.75rem] items-center gap-2 px-2 text-xs text-ink-gray-5"
			>
				<span />
				<span>{{ __("Raw Material") }}</span>
				<span>{{ __("Storage") }}</span>
				<span class="text-right">%</span>
				<span />
			</div>
			<div
				v-for="(row, i) in materials"
				:key="row.name || i"
				class="grid h-11 grid-cols-[1.25rem_minmax(0,1fr)_5.5rem_4.5rem_1.75rem] items-center gap-2 px-2"
			>
				<span
					class="size-4 rounded-full border border-outline-gray-3"
					:class="SWATCH[MATERIAL_TONES[i % MATERIAL_TONES.length]]"
				/>
				<LinkField v-model="row.item_code" doctype="Item" :filters="{ is_stock_item: 1 }" />
				<Select v-model="row.storage" :options="STORAGE_OPTIONS" size="sm" />
				<span
					v-if="row.is_balance_item"
					class="text-right text-sm tabular-nums text-ink-gray-6"
					:title="__('Balance item')"
				>
					{{ fmt(rest) }}
				</span>
				<TextInput
					v-else
					v-model="row.percentage"
					type="number"
					size="sm"
					class="[&_input]:bg-surface-base [&_input]:text-right"
				/>
				<Dropdown :options="rowMenu(row)">
					<Button variant="ghost" size="sm" icon="lucide-ellipsis" :aria-label="__('More')" />
				</Dropdown>
			</div>
		</div>
		<div class="flex items-center gap-3">
			<Button icon-left="lucide-plus" :label="__('Add Material')" @click="add" />
			<p class="min-w-0 truncate text-xs text-ink-gray-5">
				<template v-if="balanceRow">
					{{
						__("{0} tops the formula up to 100%", [
							balanceRow.item_name || __("The balance item"),
						])
					}}
				</template>
				<template v-else>{{
					__("No balance item, so the percentages must add up to 100%")
				}}</template>
			</p>
		</div>
	</section>
</template>
