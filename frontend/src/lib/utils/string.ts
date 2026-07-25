export function formatCode(code: string): string {
  return code.match(/.{1,3}/g)?.join(" ") ?? code;
}
