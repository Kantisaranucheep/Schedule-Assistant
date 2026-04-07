/**
 * API Service Tests
 * 
 * Test ID Format: FE-API-XXX
 */

import { api, API_BASE_URL } from '@/app/services/api';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('API Service', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('FE-API-001: Base Configuration', () => {
    it('uses correct base URL', () => {
      expect(API_BASE_URL).toBe('http://localhost:8000');
    });
  });

  describe('FE-API-002: GET Requests', () => {
    it('makes GET request with correct headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });

      await api.get('/test');

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/test`,
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('returns parsed JSON response', async () => {
      const mockData = { id: 1, name: 'Test' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await api.get('/test');

      expect(result).toEqual(mockData);
    });

    it('throws error on failed request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(api.get('/nonexistent')).rejects.toThrow();
    });
  });

  describe('FE-API-003: POST Requests', () => {
    it('makes POST request with body', async () => {
      const postData = { title: 'New Event' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...postData, id: 1 }),
      });

      await api.post('/events', postData);

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/events`,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify(postData),
        })
      );
    });

    it('returns created resource', async () => {
      const newEvent = { title: 'New Event' };
      const createdEvent = { id: 'evt-123', ...newEvent };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createdEvent,
      });

      const result = await api.post('/events', newEvent);

      expect(result).toEqual(createdEvent);
    });
  });

  describe('FE-API-004: PATCH Requests', () => {
    it('makes PATCH request with partial data', async () => {
      const updateData = { title: 'Updated Title' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, ...updateData }),
      });

      await api.patch('/events/1', updateData);

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/events/1`,
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(updateData),
        })
      );
    });
  });

  describe('FE-API-005: DELETE Requests', () => {
    it('makes DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.delete('/events/1');

      expect(mockFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/events/1`,
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('FE-API-006: Error Handling', () => {
    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.get('/test')).rejects.toThrow('Network error');
    });

    it('handles 500 server errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(api.get('/test')).rejects.toThrow();
    });

    it('handles 400 validation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Validation error' }),
      });

      await expect(api.post('/events', {})).rejects.toThrow();
    });
  });

  describe('FE-API-007: Query Parameters', () => {
    it('appends query parameters to URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await api.get('/events?calendar_id=123&start_date=2026-04-01');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('calendar_id=123'),
        expect.any(Object)
      );
    });
  });
});
