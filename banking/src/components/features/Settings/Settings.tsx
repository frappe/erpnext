import { Button } from '@/components/ui/button'
import { Dialog, DialogTrigger } from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { SettingsIcon } from 'lucide-react'
import { useState } from 'react'
import { useHotkeys } from 'react-hotkeys-hook'
import SettingsDialogContent from './SettingsDialogContent'

const Settings = () => {
	const [isOpen, setIsOpen] = useState(false)

	useHotkeys('shift+meta+g', () => {
		setIsOpen(x => !x)
	}, {
		enabled: true,
		preventDefault: true,
		enableOnFormTags: false
	})

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<Tooltip>
				<TooltipTrigger asChild>
					<DialogTrigger asChild>
						<Button variant={'outline'} isIconButton size='md' aria-label={_("Settings")}>
							<SettingsIcon />
						</Button>
					</DialogTrigger>
				</TooltipTrigger>
				<TooltipContent>
					{_("Settings")}
				</TooltipContent>
			</Tooltip>
			{isOpen && (
				<SettingsDialogContent onClose={() => setIsOpen(false)} />
			)}
		</Dialog>
	)
}

export default Settings
