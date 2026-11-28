<script setup>
import { ref, watch } from "vue";
import { Button, Dialog, TextInput } from "frappe-ui";
import { __, call } from "../../lib/api";

const open = defineModel("open");
const props = defineProps({ jobCard: Object });
const emit = defineEmits(["done"]);

const checklist = ref(null);
const readings = ref({});
const saving = ref(false);

watch(open, async (isOpen) => {
	if (!isOpen) return;
	checklist.value = await call("get_quality_inspection_checklist", { job_card: props.jobCard.name });
	readings.value = Object.fromEntries(
		checklist.value.parameters.map((row) => [
			row.specification,
			{ status: "Accepted", reading_value: "" },
		])
	);
});

const rangeOf = (row) =>
	row.numeric ? __("Acceptable range {0} to {1}", [row.min_value, row.max_value]) : row.value;

async function submit() {
	saving.value = true;
	try {
		const rows = Object.entries(readings.value).map(([specification, reading]) => ({
			specification,
			...reading,
		}));
		const result = await call("submit_quality_inspection", {
			job_card: props.jobCard.name,
			readings: JSON.stringify(rows),
		});
		open.value = false;
		emit("done", result);
	} finally {
		saving.value = false;
	}
}
</script>

<template>
	<Dialog v-model:open="open" :title="__('Quality Inspection')" size="xl">
		<div v-if="checklist" class="space-y-4">
			<p class="text-p-sm text-ink-gray-6">
				{{ __("Inspect {0} before you complete {1}.", [checklist.item_code, jobCard.name]) }}
			</p>
			<div
				v-for="row in checklist.parameters"
				:key="row.specification"
				class="flex flex-wrap items-center gap-3 rounded-4 border border-outline-gray-2 p-3"
			>
				<div class="min-w-0 flex-1">
					<p class="text-base text-ink-gray-8">{{ row.specification }}</p>
					<p v-if="rangeOf(row)" class="text-sm text-ink-gray-5">{{ rangeOf(row) }}</p>
				</div>
				<TextInput
					v-if="row.numeric || row.formula_based_criteria"
					v-model="readings[row.specification].reading_value"
					type="number"
					size="lg"
					class="w-32"
					:aria-label="__('Reading for {0}', [row.specification])"
				/>
				<template v-else>
					<Button
						size="lg"
						:variant="readings[row.specification].status === 'Accepted' ? 'solid' : 'outline'"
						theme="green"
						:label="__('Pass')"
						@click="readings[row.specification].status = 'Accepted'"
					/>
					<Button
						size="lg"
						:variant="readings[row.specification].status === 'Rejected' ? 'solid' : 'outline'"
						theme="red"
						:label="__('Fail')"
						@click="readings[row.specification].status = 'Rejected'"
					/>
				</template>
			</div>
			<div class="flex justify-end gap-2">
				<Button size="lg" :label="__('Cancel')" @click="open = false" />
				<Button
					size="lg"
					variant="solid"
					:label="__('Submit Inspection')"
					:loading="saving"
					@click="submit"
				/>
			</div>
		</div>
	</Dialog>
</template>
