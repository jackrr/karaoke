export function capitalize(str: string): string {
  if (!str.length) return str;
  return str[0].toUpperCase() + str.slice(1);
}

export function formatPasscode(code: string): string {
  return code.match(/.{1,2}/g)?.join("-") ?? code;
}
