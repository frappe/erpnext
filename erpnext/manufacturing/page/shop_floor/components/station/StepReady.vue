<script setup>
import { computed } from "vue";
import { Button } from "frappe-ui";
import { __, openForm } from "../../lib/api";
import { fmt } from "../../lib/format";

const props = defineProps({ jobCard: Object, blocked: String });
defineEmits(["start"]);

const facts = computed(() => {
	const row = props.jobCard;
	return [
		[__("Quantity"), `${fmt(row.for_quantity)} ${row.stock_uom}`],
		[
			__("Done so far"),
			__("{0} done · {1} lost", [fmt(row.total_completed_qty), fmt(row.process_loss_qty)]),
		],
		[__("Ready to work on"), `${fmt(row.ready_qty)} ${row.stock_uom}`],
		[__("Operation"), __("{0} of {1}", [row.sequence_id || 1, row.operation_count || 1])],
	];
});
</script>

<template>
	<div class="space-y-5">
		<dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
			<div v-for="[label, value] in facts" :key="label">
				<dt class="text-sm text-ink-gray-5">{{ label }}</dt>
				<dd class="mt-0.5 text-lg text-ink-gray-8">{{ value }}</dd>
			</div>
		</dl>
		<div v-if="jobCard.items.length" class="space-y-1">
			<p class="text-sm text-ink-gray-5">{{ __("Materials") }}</p>
			<p v-for="item in jobCard.items" :key="item.item_code" class="text-base text-ink-gray-7">
				{{ item.item_name || item.item_code }} ·
				{{
					__("{0} of {1} {2} transferred", [
						fmt(item.transferred_qty),
						fmt(item.required_qty),
						item.uom,
					])
				}}
			</p>
		</div>
		<div
			v-if="jobCard.instructions?.description || jobCard.instructions?.work_instruction"
			class="space-y-1 rounded-4 bg-surface-gray-1 p-3"
		>
			<p v-if="jobCard.instructions.description" class="text-p-base text-ink-gray-7">
				{{ jobCard.instructions.description }}
			</p>
			<div
				v-if="jobCard.instructions.work_instruction"
				class="prose prose-sm text-ink-gray-7"
				v-html="jobCard.instructions.work_instruction"
			/>
		</div>
		<p v-if="blocked" class="text-p-sm text-ink-red-5">{{ blocked }}</p>
		<div class="flex flex-wrap gap-2">
			<Button
				v-if="jobCard.needs_transfer"
				size="lg"
				icon-left="lucide-arrow-down-to-line"
				:label="__('Open Job Card to transfer materials')"
				@click="openForm('Job Card', jobCard.name)"
			/>
			<Button
				size="lg"
				variant="solid"
				icon-left="lucide-play"
				:label="__('Start Job')"
				class="h-12 flex-1 text-lg"
				:disabled="!!blocked || jobCard.needs_transfer"
				@click="$emit('start')"
			/>
		</div>
	</div>
</template>
