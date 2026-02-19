import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MonthNavigation from '../../app/components/MonthNavigation';

describe('MonthNavigation', () => {
    it('renders with title and buttons', () => {
        const onPrev = jest.fn();
        const onNext = jest.fn();
        render(<MonthNavigation onPrev={onPrev} onNext={onNext} title="January 2023" />);

        expect(screen.getByText('January 2023')).toBeInTheDocument();
        expect(screen.getByText('<')).toBeInTheDocument();
        expect(screen.getByText('>')).toBeInTheDocument();
    });

    it('calls onPrev when prev button clicked', () => {
        const onPrev = jest.fn();
        const onNext = jest.fn();
        render(<MonthNavigation onPrev={onPrev} onNext={onNext} title="January 2023" />);

        fireEvent.click(screen.getByText('<'));
        expect(onPrev).toHaveBeenCalledTimes(1);
    });

    it('calls onNext when next button clicked', () => {
        const onPrev = jest.fn();
        const onNext = jest.fn();
        render(<MonthNavigation onPrev={onPrev} onNext={onNext} title="January 2023" />);

        fireEvent.click(screen.getByText('>'));
        expect(onNext).toHaveBeenCalledTimes(1);
    });
});
