import { describe, it, expect } from 'vitest';
import { capitalize, formatPasscode } from './string';

describe('capitalize', () => {
  it('capitalizes the first letter', () => {
    expect(capitalize('hello')).toBe('Hello');
  });

  it('handles empty strings', () => {
    expect(capitalize('')).toBe('');
  });

  it('handles single characters', () => {
    expect(capitalize('a')).toBe('A');
  });
});

describe('formatPasscode', () => {
  it('formats a 6-digit passcode', () => {
    expect(formatPasscode('123456')).toBe('12-34-56');
  });

  it('handles shorter passcodes', () => {
    expect(formatPasscode('12')).toBe('12');
    expect(formatPasscode('123')).toBe('12-3');
  });
});
