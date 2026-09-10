import assert from "node:assert/strict";
import test from "node:test";
import { RequestGate } from "../.test-build/request-gate.js";

test("new work aborts the old request and rejects its eventual result", async () => {
  const gate = new RequestGate();
  const first = gate.start();
  let resolveOld;
  const late = new Promise((resolve) => {
    resolveOld = resolve;
  });
  const published = [];
  const task = late.then((result) => {
    if (gate.isCurrent(first)) published.push(result);
  });
  const current = gate.start();
  assert.equal(first.signal.aborted, true);
  resolveOld("stale game");
  await task;
  assert.deepEqual(published, []);
  assert.equal(gate.isCurrent(current), true);
});

test("cleanup for a stale effect cannot cancel newer work", () => {
  const gate = new RequestGate();
  const first = gate.start();
  const next = gate.start();
  assert.equal(gate.cancel(first), false);
  assert.equal(next.signal.aborted, false);
  assert.equal(gate.isCurrent(next), true);
});

test("cancel invalidates results even without a replacement request", () => {
  const gate = new RequestGate();
  const request = gate.start();
  gate.cancel();
  assert.equal(gate.isCurrent(request), false);
  assert.equal(request.signal.aborted, true);
});

test("abort releases ownership before a transport settles", async () => {
  const { abortable } = await import("../.test-build/request-gate.js");
  const gate = new RequestGate();
  const ticket = gate.start();
  let complete;
  const transport = new Promise((resolve) => {
    complete = resolve;
  });
  const operation = abortable(transport, ticket.signal);
  gate.cancel();
  await assert.rejects(operation, { name: "AbortError" });
  complete("late response");
  assert.equal(gate.isCurrent(ticket), false);
});

test("an already cancelled operation still handles its transport rejection", async () => {
  const { abortable } = await import("../.test-build/request-gate.js");
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    abortable(Promise.reject(new Error("transport failed")), controller.signal),
    { name: "AbortError" },
  );
});
