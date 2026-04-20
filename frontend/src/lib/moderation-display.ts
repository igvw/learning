export function reviewBadge(status: string, verified: boolean): string {
  return verified ? 'Verified' : status.replace('_', ' ');
}
