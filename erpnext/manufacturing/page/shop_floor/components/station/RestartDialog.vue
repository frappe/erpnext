<script setup>
import { ref, watch } from "vue";
import { Button, Dialog, FormControl } from "frappe-ui";
import { __ } from "../../lib/api";

const open = defineModel("open");
const props = defineProps({ workstation: Object });
const emit = defineEmits(["confirm"]);

const reason = ref("");
const remarks = ref("");
watch(open, (isOpen) => {
	if (!isOpen) return;
	reason.value = props.workstation.stop_reasons.includes("Machine malfunction")
		? "Machine malfunction"
		: "";
	remarks.value = "";
});

function confirm() {
	emit("confirm", reason.value, remarks.value);
	open.value = false;
}
</script>

<template>
	<Dialog v-model:open="open" :title="__('Restart {0}', [workstation.name])" size="lg">
		<div class="space-y-4">
			<p class="text-p-sm text-ink-gray-6">
				{{
					__(
						"Restarting makes a Downtime Entry for the time the machine was stopped and resumes its job."
					)
				}}
			</p>
			<FormControl
				v-model="reason"
				type="select"
				size="lg"
				:label="__('Stop Reason')"
				:options="workstation.stop_reasons.map((value) => ({ label: __(value), value }))"
				required
			/>
			<FormControl
				v-model="remarks"
				type="textarea"
				:label="__('Remarks')"
				:description="__('What was wrong and what was fixed.')"
			/>
			<div class="flex justify-end gap-2">
				<Button size="lg" :label="__('Cancel')" @click="open = false" />
				<Button
					size="lg"
					variant="solid"
					icon-left="lucide-rotate-cw"
					:label="__('Restart Machine')"
					:disabled="!reason"
					@click="confirm"
				/>
			</div>
		</div>
	</Dialog>
</template>
