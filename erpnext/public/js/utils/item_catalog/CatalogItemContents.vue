<script setup>
import { inject, ref } from "vue";
import { fetchItemDetails } from "./common";

const frm = inject("frm");
const item = inject("item");

const details = ref(null);

fetchItemDetails(item.name, frm, (info) => { details.value = info });
</script>

<template>
	<div class="d-flex justify-content-between px-2">
		<template v-if="details">
			<div v-html="frappe.format(details.price_list_rate, { fieldtype: 'Currency' }, frm.doc)" />
			<div class="d-flex" style="gap: 0.25em;" v-if="details.actual_qty">
				<div v-html="frappe.format(details.actual_qty, { fieldtype: 'Int' }, frm.doc)" />
				<span>&times;</span>
				<div v-html="frappe.format(details.stock_uom, { fieldtype: 'Link', options: 'UOM' }, frm.doc)" />
			</div>
		</template>
		<template v-else>
			<span class="text-muted">
				{{ __("Loading") }}
			</span>
		</template>
	</div>
</template>
