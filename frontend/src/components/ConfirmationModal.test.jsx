import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ConfirmationModal from './ConfirmationModal'

const defaults = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    title: 'Potwierdź akcję',
    actionType: 'INCREASE_BUDGET',
    entity: 'Kampania Brand Search',
    beforeState: { Budżet: '50 PLN' },
    afterState: { Budżet: '60 PLN' },
    reason: 'Kampania ma headroom',
}

describe('ConfirmationModal', () => {
    it('renders nothing when isOpen is false', () => {
        const { container } = render(<ConfirmationModal {...defaults} isOpen={false} />)
        expect(container.innerHTML).toBe('')
    })

    it('renders title, entity, action type, before/after, and reason', () => {
        render(<ConfirmationModal {...defaults} />)

        expect(screen.getByText('Potwierdź akcję')).toBeInTheDocument()
        expect(screen.getByText('INCREASE_BUDGET')).toBeInTheDocument()
        expect(screen.getByText('Kampania Brand Search')).toBeInTheDocument()
        expect(screen.getByText(/50 PLN/)).toBeInTheDocument()
        expect(screen.getByText(/60 PLN/)).toBeInTheDocument()
        expect(screen.getByText(/Kampania ma headroom/)).toBeInTheDocument()
    })

    it('calls onConfirm when Potwierdź is clicked', () => {
        const onConfirm = vi.fn()
        render(<ConfirmationModal {...defaults} onConfirm={onConfirm} />)

        fireEvent.click(screen.getByText('Potwierdź'))
        expect(onConfirm).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when Anuluj is clicked', () => {
        const onClose = vi.fn()
        render(<ConfirmationModal {...defaults} onClose={onClose} />)

        fireEvent.click(screen.getByText('Anuluj'))
        expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when backdrop is clicked', () => {
        const onClose = vi.fn()
        const { container } = render(<ConfirmationModal {...defaults} onClose={onClose} />)

        // Backdrop is the first div inside the fixed overlay
        const backdrop = container.querySelector('.bg-black\\/60')
        fireEvent.click(backdrop)
        expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('disables both buttons when isLoading', () => {
        render(<ConfirmationModal {...defaults} isLoading={true} />)

        expect(screen.getByText('Wykonuję...')).toBeDisabled()
        expect(screen.getByText('Anuluj')).toBeDisabled()
    })

    it('renders without optional props', () => {
        render(
            <ConfirmationModal
                isOpen={true}
                onClose={vi.fn()}
                onConfirm={vi.fn()}
            />
        )

        expect(screen.getByText('Potwierdź akcję')).toBeInTheDocument()
        expect(screen.getByText('Potwierdź')).toBeEnabled()
    })
})
