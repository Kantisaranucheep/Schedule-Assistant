/**
 * Frontend Component Tests for FilterBar
 * 
 * Test ID Format: FE-FB-XXX
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FilterBar from '@/app/components/FilterBar';
import { EventMap, EventCategory } from '@/app/types';

// Mock categories
const mockCategories: EventCategory[] = [
  { id: 'cat-1', name: 'Work', color: '#e74c3c' },
  { id: 'cat-2', name: 'Personal', color: '#3498db' },
  { id: 'cat-3', name: 'Meeting', color: '#2ecc71' },
];

// Mock events
const mockEvents: EventMap = {
  '2026-04-15': [
    {
      id: 'evt-1',
      title: 'Work Meeting',
      color: '#e74c3c',
      kind: 'event',
      allDay: false,
      startMin: 540,
      endMin: 600,
    },
  ],
};

describe('FilterBar', () => {
  const mockOnFilterChange = jest.fn();
  const mockOnAddEvent = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderFilterBar = (props = {}) => {
    return render(
      <FilterBar
        events={mockEvents}
        categories={mockCategories}
        onFilterChange={mockOnFilterChange}
        onAddEvent={mockOnAddEvent}
        {...props}
      />
    );
  };

  describe('FE-FB-001: Basic Rendering', () => {
    it('renders search input', () => {
      renderFilterBar();
      
      expect(screen.getByPlaceholderText('Search events...')).toBeInTheDocument();
    });

    it('renders filter button', () => {
      renderFilterBar();
      
      expect(screen.getByTitle('Filter')).toBeInTheDocument();
    });

    it('renders add event button', () => {
      renderFilterBar();
      
      expect(screen.getByTitle('Add Event')).toBeInTheDocument();
    });
  });

  describe('FE-FB-002: Search Functionality', () => {
    it('updates search text on input', async () => {
      renderFilterBar();
      
      const searchInput = screen.getByPlaceholderText('Search events...');
      fireEvent.change(searchInput, { target: { value: 'meeting' } });

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({ searchText: 'meeting' })
        );
      });
    });

    it('clears search text', async () => {
      renderFilterBar();
      
      const searchInput = screen.getByPlaceholderText('Search events...');
      fireEvent.change(searchInput, { target: { value: 'test' } });
      fireEvent.change(searchInput, { target: { value: '' } });

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenLastCalledWith(
          expect.objectContaining({ searchText: '' })
        );
      });
    });
  });

  describe('FE-FB-003: Filter Panel', () => {
    it('opens filter panel on click', () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);

      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    it('closes filter panel on Apply click', () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const applyButton = screen.getByText('Apply');
      fireEvent.click(applyButton);

      expect(screen.queryByText('Filters')).not.toBeInTheDocument();
    });

    it('displays type filter options', () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);

      expect(screen.getByText('All')).toBeInTheDocument();
      expect(screen.getByText('Event')).toBeInTheDocument();
      expect(screen.getByText('Task')).toBeInTheDocument();
    });
  });

  describe('FE-FB-004: Type Filter', () => {
    it('filters by event type', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const eventButton = screen.getByText('Event');
      fireEvent.click(eventButton);

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({ kindFilter: 'event' })
        );
      });
    });

    it('filters by task type', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const taskButton = screen.getByText('Task');
      fireEvent.click(taskButton);

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({ kindFilter: 'task' })
        );
      });
    });
  });

  describe('FE-FB-005: Category Filter', () => {
    it('displays all categories', () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);

      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.getByText('Personal')).toBeInTheDocument();
      expect(screen.getByText('Meeting')).toBeInTheDocument();
    });

    it('selects category on click', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const workCategory = screen.getByText('Work');
      fireEvent.click(workCategory);

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({ selectedCategories: ['cat-1'] })
        );
      });
    });

    it('toggles category selection', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const workCategory = screen.getByText('Work');
      fireEvent.click(workCategory); // Select
      fireEvent.click(workCategory); // Deselect

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenLastCalledWith(
          expect.objectContaining({ selectedCategories: [] })
        );
      });
    });
  });

  describe('FE-FB-006: Date Range Filter', () => {
    it('sets from date', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const dateInputs = screen.getAllByRole('textbox', { hidden: true });
      // Date inputs are type="date", find them by type
      const fromDateInput = document.querySelector('input[type="date"]');
      if (fromDateInput) {
        fireEvent.change(fromDateInput, { target: { value: '2026-04-01' } });
      }

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({ fromDate: expect.any(String) })
        );
      });
    });
  });

  describe('FE-FB-007: Location Filter', () => {
    it('filters by location', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      const locationInput = screen.getByPlaceholderText('Filter by location...');
      fireEvent.change(locationInput, { target: { value: 'Office' } });

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({ locationFilter: 'Office' })
        );
      });
    });
  });

  describe('FE-FB-008: Reset Filters', () => {
    it('resets all filters on Reset click', async () => {
      renderFilterBar();
      
      const filterButton = screen.getByTitle('Filter');
      fireEvent.click(filterButton);
      
      // Set some filters first
      const taskButton = screen.getByText('Task');
      fireEvent.click(taskButton);
      
      const resetButton = screen.getByText('Reset');
      fireEvent.click(resetButton);

      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenLastCalledWith({
          searchText: '',
          kindFilter: 'all',
          locationFilter: '',
          fromDate: '',
          toDate: '',
          selectedCategories: [],
        });
      });
    });
  });

  describe('FE-FB-009: Add Event Button', () => {
    it('calls onAddEvent when add button is clicked', () => {
      renderFilterBar();
      
      const addButton = screen.getByTitle('Add Event');
      fireEvent.click(addButton);

      expect(mockOnAddEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe('FE-FB-010: Active Filter Badge', () => {
    it('shows active filter indicator when filters are applied', async () => {
      renderFilterBar();
      
      const searchInput = screen.getByPlaceholderText('Search events...');
      fireEvent.change(searchInput, { target: { value: 'test' } });

      await waitFor(() => {
        // The filter button should have visual indication when filters are active
        const filterButton = screen.getByTitle('Filter');
        expect(filterButton.className).toContain('btn-dark');
      });
    });
  });
});
