"use client";

import { useState, useEffect } from "react";
import { Wifi, Check } from "lucide-react";
import type { Dictionary } from "../dictionaries";

/**
 * Animated captive portal screen for the iPhone mockup.
 * Cycles: ad countdown (5s) → button tap → connected (3s) → restart
 */
export default function PortalScreen({ dict }: { dict: Dictionary }) {
  const TOTAL = 5;
  const [secondsLeft, setSecondsLeft] = useState(TOTAL);
  const [phase, setPhase] = useState<"ad" | "ready" | "connecting" | "done">("ad");

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;

    if (phase === "ad" && secondsLeft > 0) {
      timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    } else if (phase === "ad" && secondsLeft === 0) {
      setPhase("ready");
      timer = setTimeout(() => setPhase("connecting"), 1200);
    } else if (phase === "connecting") {
      timer = setTimeout(() => setPhase("done"), 1000);
    } else if (phase === "done") {
      timer = setTimeout(() => {
        setPhase("ad");
        setSecondsLeft(TOTAL);
      }, 3500);
    }

    return () => clearTimeout(timer);
  }, [phase, secondsLeft]);

  const progress = ((TOTAL - secondsLeft) / TOTAL) * 100;
  const isDone = phase === "done";
  const isReady = phase === "ready" || phase === "connecting";

  return (
    <div style={{
      width: "100%", height: "100%", background: "#fff",
      display: "flex", flexDirection: "column",
      padding: "48px 20px 20px", alignItems: "center", gap: 12,
      fontFamily: "-apple-system, 'SF Pro Text', system-ui, sans-serif",
    }}>
      {/* Brand badge */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "6px 14px", borderRadius: 20,
        background: isDone ? "rgba(34,197,94,0.08)" : "rgba(27,79,138,0.07)",
        border: `1px solid ${isDone ? "rgba(34,197,94,0.15)" : "rgba(27,79,138,0.1)"}`,
        transition: "all 0.5s ease",
      }}>
        {isDone
          ? <Check size={13} color="#22c55e" />
          : <Wifi size={13} color="#1B4F8A" />
        }
        <span style={{
          fontSize: 13, fontWeight: 700,
          color: isDone ? "#22c55e" : "#1B4F8A",
          transition: "color 0.5s ease",
        }}>
          AbotKamay WiFi
        </span>
      </div>

      {/* Title — changes on connected */}
      <div style={{ textAlign: "center", minHeight: 44 }}>
        <div style={{
          fontSize: isDone ? 20 : 17, fontWeight: 800,
          color: isDone ? "#22c55e" : "#1a1a1a",
          lineHeight: 1.3, transition: "all 0.5s ease",
        }}>
          {isDone ? dict.hero.phoneConnected : dict.hero.phoneTitle}
        </div>
        <div style={{ fontSize: 11, color: "#7a7a7a", marginTop: 3, transition: "all 0.5s ease" }}>
          {isDone ? dict.hero.phoneConnectedSub : dict.hero.phoneSubtitle}
        </div>
      </div>

      {/* Ad area / Connected checkmark */}
      {isDone ? (
        <div style={{
          width: "100%", height: 110, borderRadius: 16,
          background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.12)",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8,
          animation: "fadeIn 0.5s ease",
        }}>
          <div style={{
            width: 44, height: 44, borderRadius: "50%", background: "#22c55e",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Check size={24} color="white" strokeWidth={3} />
          </div>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#22c55e" }}>
            {dict.hero.phoneStatus}
          </span>
        </div>
      ) : (
        <div style={{
          width: "100%", height: 110, borderRadius: 16,
          overflow: "hidden", position: "relative",
          background: "#0a0a12",
        }}>
          {/* Animated gradient simulating video ad */}
          <div style={{
            position: "absolute", inset: 0,
            background: "linear-gradient(135deg, #1B4F8A 0%, #0099DB 40%, #F58220 70%, #1B4F8A 100%)",
            backgroundSize: "300% 300%",
            animation: "adShimmer 4s ease infinite",
            opacity: 0.85,
          }} />
          {/* Fake ad content — brand-style visual */}
          <div style={{
            position: "relative", zIndex: 1, width: "100%", height: "100%",
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4,
          }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: "white", letterSpacing: "0.02em", textShadow: "0 1px 8px rgba(0,0,0,0.3)" }}>
              SMART 5G
            </div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.75)", fontWeight: 500 }}>
              Unli Data Starts at ₱99
            </div>
          </div>
          {/* Top-right "AD" badge */}
          <div style={{
            position: "absolute", top: 6, right: 6, zIndex: 2,
            padding: "2px 6px", borderRadius: 4,
            background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)",
          }}>
            <span style={{ fontSize: 8, fontWeight: 700, color: "rgba(255,255,255,0.8)" }}>AD</span>
          </div>
        </div>
      )}

      {/* Progress bar (hidden when done) */}
      {!isDone && (
        <div style={{ width: "100%" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: "#7a7a7a" }}>
              {phase === "ad" ? dict.hero.phoneAdPlaying : ""}
            </span>
            <span style={{ fontSize: 10, color: "#1B4F8A", fontWeight: 700 }}>
              {phase === "ad" ? `${secondsLeft}s` : "✓"}
            </span>
          </div>
          <div style={{ width: "100%", height: 4, borderRadius: 10, background: "rgba(0,0,0,0.06)" }}>
            <div style={{
              width: `${phase === "ad" ? progress : 100}%`,
              height: "100%", borderRadius: 10,
              background: isReady
                ? "linear-gradient(90deg, #22c55e, #4ade80)"
                : "linear-gradient(90deg, #1B4F8A, #0099DB)",
              transition: "width 0.8s ease, background 0.5s ease",
            }} />
          </div>
        </div>
      )}

      {/* CTA button */}
      {!isDone && (
        <div style={{
          width: "100%", padding: "13px 0", borderRadius: 14, textAlign: "center",
          background: isReady ? "#22c55e" : "#1B4F8A",
          boxShadow: isReady
            ? "0 4px 16px rgba(34,197,94,0.35)"
            : "0 4px 12px rgba(27,79,138,0.2)",
          opacity: phase === "ad" && secondsLeft > 0 ? 0.5 : 1,
          transform: phase === "connecting" ? "scale(0.96)" : "scale(1)",
          transition: "all 0.4s ease",
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "white" }}>
            {dict.hero.phoneCta}
          </span>
        </div>
      )}

      {/* Status indicator */}
      {isDone && (
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "10px 16px", borderRadius: 12,
          background: "rgba(34,197,94,0.06)",
          animation: "fadeIn 0.5s ease",
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%", background: "#22c55e",
            animation: "pulse 2s ease-in-out infinite",
          }} />
          <span style={{ fontSize: 11, fontWeight: 600, color: "#22c55e" }}>
            {dict.hero.phoneStatus}
          </span>
        </div>
      )}
    </div>
  );
}
