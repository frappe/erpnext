<script setup>
import { computed } from "vue";
import { FormControl } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import DeskControl from "../DeskControl.vue";
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
			<DeskControl v-model="doc.company" options="Company" :label="__('Company')" :disabled="isSaved" />
		</div>
		<DeskControl
			v-model="doc.production_item"
			options="Item"
			:label="__('Finished Good')"
			:filters="{ is_stock_item: 1, has_variants: 0 }"
			:description="doc.production_item ? weightText : ''"
		/>
		<div class="grid grid-cols-2 gap-3">
			<FormControl v-model="doc.batch_size" type="number" :label="__('Batch Size')" />
			<FormControl v-model="doc.formula_tolerance" type="number" :label="__('Formula Tolerance (%)')" />
		</div>
		<div class="grid grid-cols-2 gap-3">
			<DeskControl
				v-model="doc.warehouse"
				options="Warehouse"
				:label="__('Raw Material Store')"
				:filters="warehouseFilters"
				:disabled="isSaved && !!doc.warehouse"
			/>
			<DeskControl
				v-model="doc.fg_warehouse"
				options="Warehouse"
				:label="__('Finished Goods Warehouse')"
				:filters="warehouseFilters"
			/>
		</div>
	</section>
</template>
