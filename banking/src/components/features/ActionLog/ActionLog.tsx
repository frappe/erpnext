import { Button } from '@/components/ui/button'
import { Dialog, DialogTrigger } from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { HistoryIcon } from 'lucide-react'
import { useState } from 'react'
import { useHotkeys } from 'react-hotkeys-hook'
import ActionLogDialog from './ActionLogDialog'

const ActionLog = () => {
	const [isOpen, setIsOpen] = useState(false)

	useHotkeys('meta+z', () => {
		setIsOpen(true)
	}, {
		enabled: true,
		enableOnFormTags: false,
		preventDefault: true
	})

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<Tooltip>
				<TooltipTrigger asChild>
					<DialogTrigger asChild>
						<Button variant={'outline'} isIconButton size='md'>
							<HistoryIcon />
						</Button>
					</DialogTrigger>
				</TooltipTrigger>
				<TooltipContent>
					{_("Reconciliation History")}
				</TooltipContent>
			</Tooltip>
			{isOpen && (
				<ActionLogDialog onClose={() => setIsOpen(false)} />
			)}
		</Dialog>
	)
}

export default ActionLog
