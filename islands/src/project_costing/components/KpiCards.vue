<script setup>
import { Tooltip } from "frappe-ui";
import { NumberCard } from "frappe-ui/charts";

// Each item: label, value, and optionally sub (the grey caption) and hint (the ⓘ tooltip).
defineProps({
	items: { type: Array, required: true },
});

const COLUMNS = { 2: "lg:grid-cols-2", 3: "lg:grid-cols-3", 5: "lg:grid-cols-5" };
</script>

<template>
	<div class="grid grid-cols-2 gap-5" :class="COLUMNS[items.length] || 'lg:grid-cols-4'">
		<NumberCard v-for="item in items" :key="item.label" :title="item.label" :value="item.value">
			<template v-if="item.hint" #title-suffix>
				<Tooltip :text="item.hint">
					<span class="lucide-info size-[1em] text-ink-gray-4" role="img" :aria-label="item.hint" />
				</Tooltip>
			</template>
			<template v-if="item.sub" #caption>
				<span class="text-ink-gray-5">{{ item.sub }}</span>
			</template>
		</NumberCard>
	</div>
</template>
