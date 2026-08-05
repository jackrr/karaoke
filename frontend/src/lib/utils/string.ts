export function formatCode(code: string): string {
  return code.match(/.{1,3}/g)?.join(" ") ?? code;
}

export function buildJoinUrl(origin: string, code: string): string {
  return `${origin}/join?code=${code}`;
}
