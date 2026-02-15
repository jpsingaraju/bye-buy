"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  motion,
  AnimatePresence,
  useMotionValue,
  useSpring,
} from "framer-motion";

/* ── Magnetic Button ───────────────────────────────── */
function MagneticButton({
  children,
  href,
}: {
  children: React.ReactNode;
  href: string;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 200, damping: 20 });
  const springY = useSpring(y, { stiffness: 200, damping: 20 });

  function handleMouse(e: React.MouseEvent) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = e.clientX - cx;
    const dy = e.clientY - cy;
    if (Math.sqrt(dx * dx + dy * dy) < 150) {
      x.set(dx * 0.15);
      y.set(dy * 0.15);
    }
  }

  return (
    <motion.div
      onMouseMove={handleMouse}
      onMouseLeave={() => {
        x.set(0);
        y.set(0);
      }}
      className="inline-block"
    >
      <motion.div style={{ x: springX, y: springY }}>
        <Link
          ref={ref}
          href={href}
          className="inline-flex items-center px-10 py-4 text-lg font-bold bg-primary text-white neo-border neo-shadow neo-hover"
        >
          {children}
        </Link>
      </motion.div>
    </motion.div>
  );
}

/* ── Cross-Post Orbit (Step 2) ─────────────────────── */
function CrossPostOrbit() {
  const platforms = [
    "Facebook",
    "eBay",
    "Craigslist",
    "Mercari",
    "OfferUp",
    "Poshmark",
    "Depop",
    "Nextdoor",
    "Swappa",
    "Whatnot",
  ];

  const R = 155;
  const CX = 210;
  const CY = 210;
  const VB = 420;

  return (
    <svg
      viewBox={`0 0 ${VB} ${VB}`}
      className="w-[336px] h-[336px] mx-auto overflow-visible"
    >
      {/* Orbit rings */}
      <circle
        cx={CX}
        cy={CY}
        r={R}
        fill="none"
        stroke="#FF5484"
        strokeWidth="1.5"
        strokeDasharray="6 6"
        opacity="0.25"
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from={`0 ${CX} ${CY}`}
          to={`360 ${CX} ${CY}`}
          dur="30s"
          repeatCount="indefinite"
        />
      </circle>
      <circle
        cx={CX}
        cy={CY}
        r={R - 14}
        fill="none"
        stroke="#5B4CFF"
        strokeWidth="1"
        strokeDasharray="4 8"
        opacity="0.12"
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from={`360 ${CX} ${CY}`}
          to={`0 ${CX} ${CY}`}
          dur="25s"
          repeatCount="indefinite"
        />
      </circle>

      {/* Center AI node */}
      <rect
        x={CX - 32}
        y={CY - 32}
        width="64"
        height="64"
        fill="#5B4CFF"
        stroke="#1A1A2E"
        strokeWidth="2.5"
      >
        <animate
          attributeName="opacity"
          values="1;0.8;1"
          dur="2s"
          repeatCount="indefinite"
        />
      </rect>
      <text
        x={CX}
        y={CY + 8}
        textAnchor="middle"
        fill="white"
        fontSize="22"
        fontWeight="800"
        fontFamily="var(--font-space-grotesk), sans-serif"
      >
        AI
      </text>

      {/* Platform nodes */}
      {platforms.map((name, i) => {
        const angle = (i / platforms.length) * Math.PI * 2 - Math.PI / 2;
        const px = CX + Math.cos(angle) * R;
        const py = CY + Math.sin(angle) * R;

        return (
          <g key={name}>
            <line
              x1={CX}
              y1={CY}
              x2={px}
              y2={py}
              stroke="#FF5484"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              opacity="0.2"
            />

            <motion.g
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                delay: 0.2 + i * 0.08,
                type: "spring",
                stiffness: 300,
                damping: 18,
              }}
            >
              <rect
                x={px - 38}
                y={py - 14}
                width="76"
                height="28"
                rx="0"
                fill="white"
                stroke="#1A1A2E"
                strokeWidth="2"
              />
              <text
                x={px}
                y={py + 5}
                textAnchor="middle"
                fill="#1A1A2E"
                fontSize="12"
                fontWeight="700"
                fontFamily="var(--font-space-grotesk), sans-serif"
              >
                {name}
              </text>
            </motion.g>

            <motion.g
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                delay: 1.5 + i * 0.2,
                type: "spring",
                stiffness: 400,
                damping: 12,
              }}
            >
              <circle
                cx={px + 32}
                cy={py - 10}
                r="8"
                fill="#FF5484"
                stroke="#1A1A2E"
                strokeWidth="1.5"
              />
              <text
                x={px + 32}
                y={py - 6}
                textAnchor="middle"
                fill="white"
                fontSize="10"
                fontWeight="800"
              >
                ✓
              </text>
            </motion.g>
          </g>
        );
      })}
    </svg>
  );
}

/* ── Process Animation ─────────────────────────────── */
const STEP_DURATION = 4500;
const STEP_LABELS = ["Sell it", "Cross-post", "Negotiate", "Deal", "Get paid"];

function ProcessAnimation() {
  const [step, setStep] = useState(-1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const goTo = useCallback((s: number) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setStep(s);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setStep(0), 800);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (step < 0) return;
    timerRef.current = setTimeout(() => {
      setStep((s) => (s + 1) % STEP_LABELS.length);
    }, STEP_DURATION);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [step]);

  const enter = { opacity: 0, y: 18, scale: 0.96 };
  const visible = { opacity: 1, y: 0, scale: 1 };
  const exit = { opacity: 0, y: -14, scale: 0.97 };
  const springy = { type: "spring" as const, stiffness: 260, damping: 24 };

  return (
    <div className="relative w-full h-full min-h-[520px] flex flex-col items-center">
      {/* ── Step tabs ────────────────────────────── */}
      <div className="flex gap-0.5 z-20 mb-6">
        {STEP_LABELS.map((label, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            className={`px-2.5 py-1 text-[10px] font-bold border-2 border-ink transition-all cursor-pointer ${
              i === step
                ? "bg-primary text-white neo-shadow-sm"
                : "bg-surface text-ink hover:bg-primary/10"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Animation area ───────────────────────── */}
      <div className="relative flex-1 w-full flex items-center justify-center">
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            background: "radial-gradient(circle, #1A1A2E 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />

        <AnimatePresence mode="wait">
          {/* Step 0: Sell it */}
          {step === 0 && (
            <motion.div
              key="s0"
              initial={enter}
              animate={visible}
              exit={exit}
              transition={springy}
              className="flex flex-col items-center gap-3 z-10"
            >
              <div className="w-[336px] h-[336px] bg-surface neo-border neo-shadow overflow-hidden flex flex-col">
                <div className="flex-1 bg-linear-to-br from-primary/15 to-secondary/10 flex items-center justify-center border-b-2 border-ink">
                  <span className="text-6xl">📱</span>
                </div>
                <div className="p-4">
                  <p className="font-bold text-lg text-ink">iPhone 15 Pro</p>
                  <p className="text-sm text-primary/70 mt-0.5 font-medium">
                    Like New · Seattle
                  </p>
                  <p className="font-black text-2xl text-primary mt-1.5">
                    $450
                  </p>
                </div>
              </div>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="flex items-center gap-2 px-4 py-2 bg-primary/10 neo-border"
              >
                <span className="text-sm font-bold text-ink">
                  Want to sell it?
                </span>
                <span className="text-sm font-black text-primary">
                  We&apos;ll handle everything.
                </span>
              </motion.div>
            </motion.div>
          )}

          {/* Step 1: Cross-post orbit */}
          {step === 1 && (
            <motion.div
              key="s1"
              initial={enter}
              animate={visible}
              exit={exit}
              transition={springy}
              className="flex flex-col items-center z-10"
            >
              <CrossPostOrbit />
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="text-xs font-bold text-ink -mt-2"
              >
                Posted to <span className="text-primary">10+ platforms</span>{" "}
                simultaneously
              </motion.p>
            </motion.div>
          )}

          {/* Step 2: Negotiate */}
          {step === 2 && (
            <motion.div
              key="s2"
              initial={enter}
              animate={visible}
              exit={exit}
              transition={springy}
              className="flex flex-col items-center z-10"
            >
              <div className="w-[336px] h-[336px] bg-surface neo-border neo-shadow overflow-hidden flex flex-col">
                <div className="px-4 py-2.5 bg-primary/10 border-b-2 border-ink flex items-center gap-2 shrink-0">
                  <div className="w-6 h-6 bg-primary neo-border flex items-center justify-center">
                    <span className="text-white text-[9px] font-bold">B</span>
                  </div>
                  <span className="text-sm font-bold text-ink">
                    Buyer · Facebook
                  </span>
                </div>
                <div className="p-3 space-y-2 flex-1 overflow-hidden">
                  {[
                    {
                      from: "buyer",
                      text: "Is this still available?",
                      delay: 0.15,
                    },
                    {
                      from: "agent",
                      text: "Yes! It's in great condition.",
                      delay: 0.5,
                    },
                    { from: "buyer", text: "Would you take $400?", delay: 1.0 },
                    {
                      from: "agent",
                      text: "I can do $420, lowest I'll go.",
                      delay: 1.5,
                    },
                    { from: "buyer", text: "Deal! $420 works.", delay: 2.0 },
                  ].map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: msg.from === "buyer" ? -8 : 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: msg.delay, duration: 0.25 }}
                      className={`flex ${msg.from === "agent" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`px-3 py-1.5 text-sm font-medium max-w-[85%] border-2 border-ink ${
                          msg.from === "agent"
                            ? "bg-secondary/10"
                            : "bg-primary/5"
                        }`}
                      >
                        {msg.from === "agent" && (
                          <span className="text-secondary font-bold text-[10px] block mb-0.5">
                            AI Agent
                          </span>
                        )}
                        <span className="text-ink">{msg.text}</span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 3: Deal */}
          {step === 3 && (
            <motion.div
              key="s3"
              initial={enter}
              animate={visible}
              exit={exit}
              transition={springy}
              className="flex flex-col items-center gap-3 z-10"
            >
              <motion.div
                initial={{ scale: 0.5, rotate: -8 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ ...springy, delay: 0.1 }}
                className="w-[336px] h-[336px] bg-primary/10 neo-border neo-shadow flex flex-col items-center justify-center text-center"
              >
                <div className="text-6xl mb-3">🤝</div>
                <p className="font-black text-xl text-ink">Deal Agreed</p>
                <p className="text-sm text-primary font-medium mt-1">
                  iPhone 15 Pro
                </p>
                <div className="mt-4 flex items-center justify-center gap-3">
                  <span className="line-through text-ink/50 font-bold text-lg">
                    $450
                  </span>
                  <span className="text-3xl font-black text-primary">$420</span>
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="flex items-center gap-2 px-4 py-2 bg-secondary/10 neo-border text-sm font-bold text-ink"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 border-2 border-secondary border-t-transparent rounded-full"
                />
                Sending payment link...
              </motion.div>
            </motion.div>
          )}

          {/* Step 4: Paid */}
          {step === 4 && (
            <motion.div
              key="s4"
              initial={enter}
              animate={visible}
              exit={exit}
              transition={springy}
              className="flex flex-col items-center gap-3 z-10"
            >
              <motion.div
                initial={{ scale: 0.7 }}
                animate={{ scale: 1 }}
                transition={{ ...springy, delay: 0.1 }}
                className="w-[336px] h-[336px] bg-primary/10 neo-border neo-shadow flex flex-col items-center justify-center text-center relative overflow-hidden"
              >
                <motion.div
                  initial={{ y: -30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="absolute top-3 left-4 w-4 h-4 bg-primary/40 border-2 border-ink rotate-12"
                />
                <motion.div
                  initial={{ y: -30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className="absolute top-4 right-5 w-3.5 h-3.5 bg-secondary/40 border-2 border-ink -rotate-6"
                />
                <motion.div
                  initial={{ y: -30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="absolute top-2 right-20 w-3 h-3 bg-primary/30 border-2 border-ink rotate-45"
                />
                <div className="text-6xl mb-3">💰</div>
                <p className="font-black text-3xl text-primary">$420.00</p>
                <p className="text-sm text-ink font-bold mt-1.5">
                  Deposited to your account
                </p>
              </motion.div>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: "21rem" }}
                transition={{ duration: 1.5, ease: "easeOut" as const }}
                className="h-2.5 bg-primary neo-border"
              />
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="text-sm font-bold text-ink"
              >
                Item sold. You just hand it over.
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ── Stagger helpers ──────────────────────────────── */
const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

/* ── Page ──────────────────────────────────────────── */
export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Subtle animated gradient background */}
      <div
        className="absolute inset-0 animate-gradient opacity-20 pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at 20% 50%, #FF5484 0%, transparent 50%), radial-gradient(circle at 80% 50%, #5B4CFF 0%, transparent 50%)",
          backgroundSize: "200% 200%",
        }}
      />

      {/* ── Nav bar ──────────────────────────────── */}
      <header className="relative z-10 px-6 sm:px-10 lg:px-16 py-6">
        <div className="flex items-center gap-2.5">
          <Image
            src="/logo.png"
            alt="bye! buy!"
            width={44}
            height={44}
            className="w-11 h-11"
          />
          <span className="font-wordmark text-[22px] font-bold text-primary tracking-tight">
            bye! buy!
          </span>
        </div>
      </header>

      {/* ── Main content: split layout ────────────── */}
      <main className="relative z-10 flex-1 flex items-center px-6 sm:px-10 lg:px-16 pb-12">
        <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
          {/* Left: Text + CTA */}
          <motion.div variants={stagger} initial="hidden" animate="show">
            <motion.h1
              variants={fadeUp}
              className="text-5xl sm:text-6xl lg:text-6xl xl:text-7xl font-black leading-[1.05] tracking-tight"
            >
              List once.
              <br />
              <span className="text-primary">Sell everywhere.</span>
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="mt-6 text-lg sm:text-xl text-ink/80 leading-relaxed max-w-xl font-medium"
            >
              Our AI agents post your item across every major platform, filter
              out scammers, negotiate the best price, and guarantee instant
              payment. You just deliver.
            </motion.p>

            <motion.div variants={fadeUp} className="mt-10">
              <MagneticButton href="/home">Start Selling &rarr;</MagneticButton>
            </motion.div>
          </motion.div>

          {/* Right: Process Animation */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="hidden lg:block"
          >
            <ProcessAnimation />
          </motion.div>
        </div>
      </main>
    </div>
  );
}
