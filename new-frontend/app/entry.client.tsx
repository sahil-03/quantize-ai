import { RemixBrowser } from "@remix-run/react";
import { startTransition, StrictMode, useEffect } from "react";
import { hydrateRoot } from "react-dom/client";

// Intercept WebSocket connection attempts
const originalWebSocket = window.WebSocket;
window.WebSocket = function(url, protocols) {
  // Check if this is the problematic WebSocket connection
  if (url === 'ws://localhost:8002/socket') {
    console.log('Blocked WebSocket connection attempt to ws://localhost:8002/socket');
    // Return a mock WebSocket object that does nothing
    return {
      url,
      readyState: 3, // CLOSED
      protocol: '',
      extensions: '',
      bufferedAmount: 0,
      onopen: null,
      onerror: null,
      onclose: null,
      onmessage: null,
      close: () => {},
      send: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false
    };
  }
  
  // For all other WebSocket connections, proceed normally
  return new originalWebSocket(url, protocols);
};

function hydrate() {
  startTransition(() => {
    hydrateRoot(
      document,
      <StrictMode>
        <RemixBrowser />
      </StrictMode>
    );
  });
}

if (typeof requestIdleCallback === "function") {
  requestIdleCallback(hydrate);
} else {
  // Safari doesn't support requestIdleCallback
  // https://caniuse.com/requestidlecallback
  setTimeout(hydrate, 1);
}