<script setup>
import { computed } from "vue";
import { Tooltip } from "frappe-ui";

const props = defineProps({
	no: [Number, String],
	icon: String,
	title: String,
	subtitle: String,
	status: { type: String, default: "waiting" },
	badge: Object,
});

const CIRCLE = {
	waiting: "border border-outline-gray-3 text-ink-gray-5",
	active: "border-2 border-outline-gray-8 text-ink-gray-9",
	done: "border border-outline-gray-2 text-ink-gray-5",
};
const BOX = {
	red: "border-2 border-outline-red-4 bg-surface-red-1",
	amber: "border-2 border-outline-amber-4",
	blue: "border-2 border-outline-blue-4",
	gray: "border border-outline-gray-3",
	green: "border border-outline-green-4 bg-surface-green-3 text-ink-green-6",
};

const circle = computed(() => CIRCLE[props.status]);
const checked = computed(() => props.status === "done" || props.badge?.theme === "green");
const box = computed(() => (checked.value ? BOX.green : BOX[props.badge?.theme] ?? BOX.gray));
</script>

<template>
	<div class="flex h-14 items-center gap-3 px-3">
		<div
			class="flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium tabular-nums"
			:class="circle"
		>
			{{ no }}
		</div>
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-1.5">
				<span
					v-if="icon"
					class="size-3.5 shrink-0 text-ink-gray-5"
					:class="icon"
					aria-hidden="true"
				/>
				<p
					class="truncate text-base font-medium"
					:class="status === 'waiting' ? 'text-ink-gray-5' : 'text-ink-gray-8'"
				>
					{{ title }}
				</p>
			</div>
			<p class="truncate text-sm text-ink-gray-5">{{ subtitle }}</p>
		</div>
		<Tooltip v-if="badge" :text="badge.label">
			<span
				class="flex size-5 shrink-0 items-center justify-center rounded-[5px]"
				:class="box"
				:aria-label="badge.label"
				role="img"
			>
				<span v-if="checked" class="lucide-check size-3.5" aria-hidden="true" />
			</span>
		</Tooltip>
	</div>
</template>
