import { useEffect, useState } from "react";
import { getHealth } from "./api/client";

function App() {
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [detail, setDetail] = useState<string>("");

  useEffect(() => {
    getHealth()
      .then((result) => {
        setStatus("ok");
        setDetail(result.status);
      })
      .catch((error: unknown) => {
        setStatus("error");
        setDetail(error instanceof Error ? error.message : String(error));
      });
  }, []);

  return (
    <main>
      <h1>F1 Race Strategy Game</h1>
      <p>API health check: {status === "checking" ? "checking..." : detail}</p>
    </main>
  );
}

export default App;
