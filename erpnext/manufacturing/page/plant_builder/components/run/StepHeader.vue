<script setup>
import { computed } from "vue";
import { Checkbox, Tooltip } from "frappe-ui";

const props = defineProps({
	icon: String,
	title: String,
	subtitle: String,
	status: { type: String, default: "waiting" },
	badge: Object,
});

const checked = computed(() => props.status === "done" || props.badge?.theme === "green");
</script>

<template>
	<div class="flex h-14 items-center gap-3 px-3">
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
			<span class="inline-flex">
				<Checkbox
					:model-value="checked"
					size="md"
					tabindex="-1"
					:aria-label="badge.label"
					@click.prevent
				/>
			</span>
		</Tooltip>
	</div>
</template>
