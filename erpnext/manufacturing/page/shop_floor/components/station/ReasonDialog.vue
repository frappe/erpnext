<script setup>
import { computed, ref, watch } from "vue";
import { Button, Dialog, TextInput } from "frappe-ui";
import NumberStepper from "./NumberStepper.vue";
import { __ } from "../../lib/api";

const open = defineModel("open");
const props = defineProps({
	title: String,
	hint: String,
	reasons: { type: Array, default: () => [] },
	withQty: Boolean,
	maxQty: { type: Number, default: 0 },
	action: String,
	theme: { type: String, default: "gray" },
});
const emit = defineEmits(["confirm"]);

const reason = ref("");
const other = ref("");
const qty = ref(1);

watch(open, (isOpen) => {
	if (!isOpen) return;
	reason.value = "";
	other.value = "";
	qty.value = 1;
});

const chosen = computed(() => (reason.value === "__other" ? other.value.trim() : reason.value));
const qtyError = computed(() => props.withQty && (qty.value <= 0 || qty.value > props.maxQty));

function confirm() {
	emit("confirm", chosen.value, qty.value);
	open.value = false;
}
</script>

<template>
	<Dialog v-model:open="open" :title="title" size="lg">
		<div class="space-y-5">
			<p v-if="hint" class="text-p-sm text-ink-gray-6">{{ hint }}</p>
			<div v-if="withQty" class="space-y-1.5">
				<p class="text-sm text-ink-gray-6">{{ __("Quantity") }}</p>
				<NumberStepper v-model="qty" :label="__('Quantity')" :invalid="qtyError" />
				<p v-if="qtyError" class="text-p-sm text-ink-red-5">
					{{ __("Enter a quantity between 1 and {0}.", [maxQty]) }}
				</p>
			</div>
			<div class="grid grid-cols-2 gap-2">
				<Button
					v-for="row in reasons"
					:key="row"
					size="lg"
					class="justify-start"
					:variant="reason === row ? 'solid' : 'outline'"
					:label="__(row)"
					@click="reason = row"
				/>
				<Button
					size="lg"
					class="justify-start"
					:variant="reason === '__other' ? 'solid' : 'outline'"
					:label="__('Other')"
					@click="reason = '__other'"
				/>
			</div>
			<TextInput
				v-if="reason === '__other'"
				v-model="other"
				size="lg"
				:placeholder="__('Describe the reason')"
				:aria-label="__('Reason')"
			/>
			<div class="flex justify-end gap-2">
				<Button size="lg" :label="__('Cancel')" @click="open = false" />
				<Button
					size="lg"
					variant="solid"
					:theme="theme"
					:label="action"
					:disabled="!chosen || qtyError"
					@click="confirm"
				/>
			</div>
		</div>
	</Dialog>
</template>
