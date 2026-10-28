<script setup>
import { Button, Dialog } from "frappe-ui";
import { List, ListCell, ListRow } from "frappe-ui/list";
import { useHost } from "@framework/ui/island";

import { form_route, list_route } from "../costing.js";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const open = defineModel("open", { type: Boolean, default: false });

const __ = window.__;
const format = useFormat();
const host = useHost();

function go(route) {
	open.value = false;
	host.navigate?.(route);
}

const show_timesheets = () =>
	go(
		list_route("Timesheet", {
			"Timesheet Detail.project": props.view.project,
			"Timesheet Detail.costing_rate": 0,
			docstatus: 1,
		})
	);

const actions = [
	{ label: __("Close"), onClick: ({ close }) => close() },
	{ label: __("Show affected timesheets"), variant: "solid", onClick: show_timesheets },
];
</script>

<template>
	<Dialog v-model:open="open" :title="__('Missing costing rates')" :actions="actions">
		<div class="space-y-4">
			<p class="text-p-sm text-ink-gray-6">
				{{
					view.rate_gaps.estimate
						? __("{0} h were saved with a costing rate of zero, about {1} of labour.", [
								format.number(view.rate_gaps.hours),
								format.short(view.rate_gaps.estimate),
						  ])
						: __("{0} h were saved with a costing rate of zero.", [
								format.number(view.rate_gaps.hours),
						  ])
				}}
			</p>
			<List :columns="['minmax(0,1fr)', 'auto']" :row-height="56">
				<ListRow v-for="activity in view.rate_gaps.activities" :key="activity.name ?? ''">
					<ListCell>
						<div class="min-w-0">
							<p class="truncate text-sm text-ink-gray-8">
								{{ activity.name || __("No activity type") }}
							</p>
							<p class="truncate text-xs text-ink-gray-5">
								{{ __("{0} h on {1} rows", [format.number(activity.hours), activity.rows]) }}
								·
								{{
									activity.name
										? __("no Activity Cost and no default rate on the Activity Type")
										: __("rows without an activity type get no rate lookup")
								}}
							</p>
						</div>
					</ListCell>
					<ListCell class="justify-end">
						<Button
							v-if="activity.name"
							size="sm"
							:label="__('Set rate')"
							@click="go(form_route('Activity Type', activity.name))"
						/>
					</ListCell>
				</ListRow>
			</List>
			<p class="text-p-xs text-ink-gray-5">
				{{
					__(
						"A rate applies to timesheets saved after it is set. Submitted timesheets keep a zero rate until they are cancelled and amended."
					)
				}}
			</p>
		</div>
	</Dialog>
</template>
