import {
    monthNames, RAINBOW, pad, keyOf, minutesToLabel, timeToMinutes,
    parseISODate, prettyDow, prettyMonth, formatUpcomingDate,
    nowTimeHHMM, roundUpTimeHHMM, uniq, addDaysISO, dayHeaderLabel,
    tokenize, uid, clamp
} from '../app/utils';

describe('utils', () => {
    it('initializes constants', () => {
        expect(monthNames).toHaveLength(12);
        expect(RAINBOW).toHaveLength(7);
    });

    it('pad', () => {
        expect(pad(5)).toBe('05');
        expect(pad(10)).toBe('10');
    });

    it('keyOf', () => {
        const d = new Date(2023, 0, 1); // Jan 1 2023
        expect(keyOf(d)).toBe('2023-01-01');
    });

    it('minutesToLabel', () => {
        expect(minutesToLabel(60)).toBe('01:00AM');
        // wait, 60 mins = 1 hour. 1 < 12 => AM?
        // Let's check logic: const h = Math.floor(mins / 60);
        // 60/60 = 1. ap = "AM".
        // hh = 1 % 12 = 1.
        // return 01:00AM.
        // Wait, default logic. 
        expect(minutesToLabel(0)).toBe('12:00AM');
        expect(minutesToLabel(60)).toBe('01:00AM');
        expect(minutesToLabel(720)).toBe('12:00PM'); // 12 * 60 = 720
        expect(minutesToLabel(780)).toBe('01:00PM'); // 13 * 60 = 780
    });

    it('timeToMinutes', () => {
        expect(timeToMinutes('01:00')).toBe(60);
        expect(timeToMinutes('00:00')).toBe(0);
    });

    it('parseISODate', () => {
        const d = parseISODate('2023-01-01');
        expect(d.getFullYear()).toBe(2023);
        expect(d.getMonth()).toBe(0);
        expect(d.getDate()).toBe(1);
    });

    it('prettyDow', () => {
        const d = new Date(2023, 0, 1); // Sunday
        expect(prettyDow(d)).toBe('Sunday');
    });

    it('prettyMonth', () => {
        const d = new Date(2023, 0, 1);
        expect(prettyMonth(d)).toBe('January');
    });

    it('formatUpcomingDate', () => {
        expect(formatUpcomingDate('2023-01-01')).toBe('1 Jan 2023');
    });

    it('nowTimeHHMM', () => {
        // Mock date
        jest.useFakeTimers();
        jest.setSystemTime(new Date(2023, 0, 1, 10, 30));
        expect(nowTimeHHMM()).toBe('10:30');
        jest.useRealTimers();
    });

    it('roundUpTimeHHMM', () => {
        expect(roundUpTimeHHMM('10:01')).toBe('10:05');
        expect(roundUpTimeHHMM('10:00')).toBe('10:00');
        expect(roundUpTimeHHMM('23:56')).toBe('23:59'); // logic caps at 23:59
    });

    it('uniq', () => {
        expect(uniq(['a', 'b', 'a'])).toEqual(['a', 'b']);
    });

    it('addDaysISO', () => {
        expect(addDaysISO('2023-01-01', 1)).toBe('2023-01-02');
    });

    it('dayHeaderLabel', () => {
        // 2023-01-01 -> 1 JANUARY 2023
        expect(dayHeaderLabel('2023-01-01')).toBe('1 JANUARY 2023');
    });

    it('tokenize', () => {
        expect(tokenize('hello, world!')).toEqual(['hello', ',', 'world', '!']);
        expect(tokenize('')).toEqual([]);
    });

    it('uid', () => {
        expect(uid()).toContain('id_');
        expect(uid('test')).toContain('test_');
    });

    it('clamp', () => {
        expect(clamp(10, 0, 5)).toBe(5);
        expect(clamp(-5, 0, 5)).toBe(0);
        expect(clamp(3, 0, 5)).toBe(3);
    });
});
