/**
 * Frontend Component Tests for MonthGrid
 * 
 * Test ID Format: FE-MG-XXX
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MonthGrid from '@/app/components/MonthGrid';
import { Ev } from '@/app/types';

// Mock the minutesToLabel utility
jest.mock('@/app/utils', () => ({
  minutesToLabel: (min: number) => {
    const h = Math.floor(min / 60);
    const m = min % 60;
    const period = h >= 12 ? 'PM' : 'AM';
    const hour12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${hour12}:${m.toString().padStart(2, '0')} ${period}`;
  },
}));

// Helper to create test cell data
function createTestCell(overrides: Partial<{
  date: Date;
  muted: boolean;
  key: string;
  isToday: boolean;
  dayEvents: Ev[];
}> = {}) {
  return {
    date: new Date(2026, 3, 15), // April 15, 2026
    muted: false,
    key: '2026-04-15',
    isToday: false,
    dayEvents: [],
    ...overrides,
  };
}

// Helper to create test event data
function createTestEvent(overrides: Partial<Ev> = {}): Ev {
  return {
    id: `test-event-${Math.random().toString(36).substring(7)}`,
    title: 'Test Event',
    color: '#3498db',
    kind: 'event',
    allDay: false,
    startMin: 540, // 9:00 AM
    endMin: 600,   // 10:00 AM
    ...overrides,
  };
}

describe('MonthGrid', () => {
  const mockOnSelectDay = jest.fn();
  const mockSetViewMode = jest.fn();
  const mockOnViewEvent = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('FE-MG-001: Basic Rendering', () => {
    it('renders day headers', () => {
      const cells = [createTestCell()];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      expect(screen.getByText('Sunday')).toBeInTheDocument();
      expect(screen.getByText('Monday')).toBeInTheDocument();
      expect(screen.getByText('Tuesday')).toBeInTheDocument();
      expect(screen.getByText('Wednesday')).toBeInTheDocument();
      expect(screen.getByText('Thursday')).toBeInTheDocument();
      expect(screen.getByText('Friday')).toBeInTheDocument();
      expect(screen.getByText('Saturday')).toBeInTheDocument();
    });

    it('renders cell with date number', () => {
      const cells = [createTestCell({ date: new Date(2026, 3, 15) })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });

  describe('FE-MG-002: Event Display', () => {
    it('displays event title', () => {
      const event = createTestEvent({ title: 'Team Meeting' });
      const cells = [createTestCell({ dayEvents: [event] })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      expect(screen.getByText('Team Meeting')).toBeInTheDocument();
    });

    it('displays event time for non-all-day events', () => {
      const event = createTestEvent({ 
        title: 'Morning Meeting',
        startMin: 540, // 9:00 AM
        allDay: false,
      });
      const cells = [createTestCell({ dayEvents: [event] })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      expect(screen.getByText('9:00 AM')).toBeInTheDocument();
    });

    it('shows +N for more than 3 events', () => {
      const events = [
        createTestEvent({ id: '1', title: 'Event 1' }),
        createTestEvent({ id: '2', title: 'Event 2' }),
        createTestEvent({ id: '3', title: 'Event 3' }),
        createTestEvent({ id: '4', title: 'Event 4' }),
        createTestEvent({ id: '5', title: 'Event 5' }),
      ];
      const cells = [createTestCell({ dayEvents: events })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      expect(screen.getByText('+2')).toBeInTheDocument();
    });
  });

  describe('FE-MG-003: User Interactions', () => {
    it('calls onSelectDay and setViewMode when cell is clicked', () => {
      const cells = [createTestCell({ key: '2026-04-15' })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const cell = screen.getByText('15').closest('[role="button"]');
      fireEvent.click(cell!);

      expect(mockOnSelectDay).toHaveBeenCalledWith('2026-04-15');
      expect(mockSetViewMode).toHaveBeenCalledWith('day');
    });

    it('calls onViewEvent when event is clicked', () => {
      const event = createTestEvent({ id: 'evt-123', title: 'Click Me' });
      const cells = [createTestCell({ key: '2026-04-15', dayEvents: [event] })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const eventElement = screen.getByText('Click Me');
      fireEvent.click(eventElement);

      expect(mockOnViewEvent).toHaveBeenCalledWith('2026-04-15', event);
      // Event click should not trigger cell selection
      expect(mockOnSelectDay).not.toHaveBeenCalled();
    });

    it('supports keyboard navigation (Enter key)', () => {
      const cells = [createTestCell({ key: '2026-04-15' })];
      
      render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const cell = screen.getByText('15').closest('[role="button"]');
      fireEvent.keyDown(cell!, { key: 'Enter' });

      expect(mockOnSelectDay).toHaveBeenCalledWith('2026-04-15');
      expect(mockSetViewMode).toHaveBeenCalledWith('day');
    });
  });

  describe('FE-MG-004: Visual States', () => {
    it('applies muted styling for muted cells', () => {
      const cells = [createTestCell({ muted: true })];
      
      const { container } = render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const cell = container.querySelector('.bg-light.text-muted');
      expect(cell).toBeInTheDocument();
    });

    it('highlights today\'s cell', () => {
      const cells = [createTestCell({ isToday: true })];
      
      const { container } = render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const cell = container.querySelector('.bg-primary.bg-opacity-10');
      expect(cell).toBeInTheDocument();
    });
  });

  describe('FE-MG-005: Event Sorting', () => {
    it('sorts all-day events before timed events', () => {
      const timedEvent = createTestEvent({ 
        id: '1', 
        title: 'Timed Event', 
        startMin: 540,
        allDay: false,
      });
      const allDayEvent = createTestEvent({ 
        id: '2', 
        title: 'All Day Event', 
        allDay: true,
      });
      // Pass timed event first, but all-day should appear first
      const cells = [createTestCell({ dayEvents: [timedEvent, allDayEvent] })];
      
      const { container } = render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const eventElements = container.querySelectorAll('.text-truncate');
      expect(eventElements[0].textContent).toBe('All Day Event');
      expect(eventElements[1].textContent).toBe('Timed Event');
    });

    it('sorts tasks before regular events', () => {
      const regularEvent = createTestEvent({ 
        id: '1', 
        title: 'Regular Event',
        kind: 'event',
        startMin: 540,
      });
      const taskEvent = createTestEvent({ 
        id: '2', 
        title: 'Task',
        kind: 'task',
      });
      const cells = [createTestCell({ dayEvents: [regularEvent, taskEvent] })];
      
      const { container } = render(
        <MonthGrid
          cells={cells}
          onSelectDay={mockOnSelectDay}
          setViewMode={mockSetViewMode}
          onViewEvent={mockOnViewEvent}
        />
      );

      const eventElements = container.querySelectorAll('.text-truncate');
      expect(eventElements[0].textContent).toBe('Task');
      expect(eventElements[1].textContent).toBe('Regular Event');
    });
  });
});
