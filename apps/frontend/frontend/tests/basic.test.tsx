import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'

describe('Simple Test', () => {
    it('renders a heading', () => {
        // This is a  test that just asserts true is true to verify the runner works
        expect(true).toBe(true)
    })

    it('checks math', () => {
        expect(1 + 1).toBe(2)
    })
})
