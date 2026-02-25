"use client";

import { useState } from "react";

export function CoreFeatureCounter() {
  const [count, setCount] = useState(0);

  return (
    <section className="counter">
      <p>Core feature count: {count}</p>
      <button onClick={() => setCount((value) => value + 1)}>Increment</button>
    </section>
  );
}
