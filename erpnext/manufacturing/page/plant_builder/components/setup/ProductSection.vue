<script setup>
import { computed } from "vue";
import { FormControl } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import LinkField from "../LinkField.vue";
import { __ } from "../../lib/api";
import { fmt } from "../../lib/format";

const props = defineProps({ doc: Object, item: Object, isSaved: Boolean });

const warehouseFilters = computed(() => ({ company: props.doc.company, is_group: 0 }));
const weightText = computed(() => {
	const item = props.item;
	if (!item?.weight_per_unit) return __("Set Weight Per Unit on the item");
	return __("{0} {1} in each {2}", [fmt(item.weight_per_unit), item.weight_uom, item.stock_uom]);
});
</script>

<template>
	<section class="space-y-4">
		<SectionHead
			:title="__('Product')"
			:description="__('What leaves the plant and where its stock is kept.')"
		/>
		<div class="grid grid-cols-2 gap-3">
			<FormControl v-model="doc.floor_name" :label="__('Plant Name')" :disabled="isSaved" />
			<LinkField v-model="doc.company" doctype="Company" :label="__('Company')" :disabled="isSaved" />
		</div>
		<LinkField
			v-model="doc.production_item"
			doctype="Item"
			:label="__('Finished Good')"
			:filters="{ is_stock_item: 1, has_variants: 0 }"
			:description="doc.production_item ? weightText : ''"
		/>
		<div class="grid grid-cols-2 gap-3">
			<FormControl v-model="doc.batch_size" type="number" :label="__('Batch Size')" />
			<FormControl v-model="doc.formula_tolerance" type="number" :label="__('Formula Tolerance (%)')" />
		</div>
		<div class="grid grid-cols-2 gap-3">
			<LinkField
				v-model="doc.warehouse"
				doctype="Warehouse"
				:label="__('Raw Material Store')"
				:filters="warehouseFilters"
				:disabled="isSaved && !!doc.warehouse"
			/>
			<LinkField
				v-model="doc.fg_warehouse"
				doctype="Warehouse"
				:label="__('Finished Goods Warehouse')"
				:filters="warehouseFilters"
			/>
		</div>
	</section>
</template>
