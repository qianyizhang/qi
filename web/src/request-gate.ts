export type RequestTicket = { generation: number; signal: AbortSignal };

/** Only the latest request may publish a result, even if cancellation is ignored. */
export class RequestGate {
  private generation = 0;
  private controller: AbortController | null = null;

  start(): RequestTicket {
    this.cancel();
    this.controller = new AbortController();
    return { generation: this.generation, signal: this.controller.signal };
  }

  isCurrent(ticket: RequestTicket): boolean {
    return ticket.generation === this.generation && !ticket.signal.aborted;
  }

  cancel(ticket?: RequestTicket): boolean {
    if (ticket && !this.isCurrent(ticket)) return false;
    this.controller?.abort();
    this.controller = null;
    this.generation += 1;
    return true;
  }
}

/** Release client ownership promptly even when a transport ignores abort. */
export function abortable<T>(
  operation: Promise<T>,
  signal: AbortSignal,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const cancelled = () =>
      reject(new DOMException("Request cancelled", "AbortError"));
    operation
      .then(resolve, reject)
      .finally(() => signal.removeEventListener("abort", cancelled));
    if (signal.aborted) cancelled();
    else signal.addEventListener("abort", cancelled, { once: true });
  });
}
