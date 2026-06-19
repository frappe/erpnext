import {
	SettingsDialog,
	SettingsPanels,
	SettingsTabGroup,
	SettingsTabItem,
	SettingsTabs,
} from '@/components/ui/settings-dialog'
import _ from '@/lib/translate'
import { KeyboardIcon, Loader2Icon, SlidersVerticalIcon, ZapIcon } from 'lucide-react'
import { lazy, Suspense } from 'react'

const SettingsPanelsContent = lazy(() => import('./SettingsPanelsContent'))

const SettingsPanelsFallback = () => (
	<div className="flex flex-1 items-center justify-center min-h-full">
		<Loader2Icon className="size-6 animate-spin text-muted-foreground" />
	</div>
)

const SettingsDialogContent = ({ onClose }: { onClose: () => void }) => {
	return (
		<SettingsDialog defaultValue="preferences" onClose={onClose}>
			<SettingsTabs>
				<SettingsTabGroup header={_("Settings")}>
					<SettingsTabItem
						icon={<SlidersVerticalIcon />}
						label={_("Preferences")}
						value="preferences"
					/>
					<SettingsTabItem
						icon={<ZapIcon />}
						label={_("Matching Rules")}
						value="rules"
					/>
					<SettingsTabItem
						icon={<KeyboardIcon />}
						label={_("Keyboard Shortcuts")}
						value="keyboard-shortcuts"
					/>
				</SettingsTabGroup>
			</SettingsTabs>

			<SettingsPanels>
				<Suspense fallback={<SettingsPanelsFallback />}>
					<SettingsPanelsContent />
				</Suspense>
			</SettingsPanels>
		</SettingsDialog>
	)
}

export default SettingsDialogContent
