<script setup>
import { computed } from "vue";
import { Badge } from "frappe-ui";

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
	done: "bg-surface-green-2 text-ink-green-5",
};

const circle = computed(() => CIRCLE[props.status]);
</script>

<template>
	<div class="flex h-14 items-center gap-3 px-3">
		<div
			class="flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium tabular-nums"
			:class="circle"
		>
			<span v-if="status === 'done'" class="lucide-check size-3.5" aria-hidden="true" />
			<template v-else>{{ no }}</template>
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
		<Badge v-if="badge" :label="badge.label" :theme="badge.theme" variant="subtle" />
	</div>
</template>
