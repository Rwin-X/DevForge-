import React, { useState, useRef, useEffect, useCallback } from "react";
import * as Tone from "tone";

// ---------------------------------------------------------------------------
// CONSTANTS
// ---------------------------------------------------------------------------
const STEPS = 16;
const DRUM_VOICES = ["KICK", "CLAP", "HAT-C", "HAT-O"];
const CHOP_SLOTS = 8; // 8 auto-sliced regions from the loaded sample
const BASS_STEPS = 16;

const COLORS = {
  bg: "#0a0a0a",
  bgPanel: "#111311",
  bgInset: "#0d0f0d",
  line: "#232823",
  lineBright: "#39FF88",
  text: "#e8e8e0",
  textDim: "#6b756b",
  green: "#39FF88",
  amber: "#FFB347",
  cyan: "#3FD4E8",
  red: "#FF5C5C",
};

const NOTE_OPTIONS = ["C2", "D#2", "F2", "G2", "A#2", "C3", "D#3", "F3"];

// ---------------------------------------------------------------------------
// SMALL UI PRIMITIVES
// ---------------------------------------------------------------------------
function Knob({ label, value, min, max, step = 0.01, onChange, unit = "", color = COLORS.green }) {
  const ref = useRef(null);
  const dragging = useRef(false);
  const startY = useRef(0);
  const startVal = useRef(0);

  const pct = (value - min) / (max - min);
  const angle = -135 + pct * 270;

  const onPointerDown = (e) => {
    dragging.current = true;
    startY.current = e.clientY;
    startVal.current = value;
    e.target.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e) => {
    if (!dragging.current) return;
    const dy = startY.current - e.clientY;
    const range = max - min;
    const next = Math.min(max, Math.max(min, startVal.current + (dy / 150) * range));
    const snapped = Math.round(next / step) * step;
    onChange(snapped);
  };
  const onPointerUp = () => (dragging.current = false);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, userSelect: "none" }}>
      <div
        ref={ref}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        style={{
          width: 44,
          height: 44,
          borderRadius: "50%",
          background: `conic-gradient(${color} ${pct * 270}deg, ${COLORS.line} ${pct * 270}deg 270deg, transparent 270deg 360deg)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "ns-resize",
          border: `1px solid ${COLORS.line}`,
          position: "relative",
        }}
      >
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: "50%",
            background: COLORS.bgInset,
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 4,
              left: "50%",
              width: 2,
              height: 12,
              background: color,
              transform: `translateX(-50%) rotate(${angle}deg)`,
              transformOrigin: "1px 13px",
            }}
          />
        </div>
      </div>
      <div style={{ fontSize: 9, letterSpacing: 0.5, color: COLORS.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
        {label}
      </div>
      <div style={{ fontSize: 9, color: color, fontFamily: "'JetBrains Mono', monospace" }}>
        {typeof value === "number" ? value.toFixed(step < 1 ? 2 : 0) : value}
        {unit}
      </div>
    </div>
  );
}

function Toggle({ active, onClick, children, color = COLORS.green, small }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? color : "transparent",
        color: active ? "#0a0a0a" : color,
        border: `1px solid ${color}`,
        borderRadius: 2,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: small ? 10 : 11,
        padding: small ? "4px 8px" : "6px 12px",
        cursor: "pointer",
        letterSpacing: 0.5,
        transition: "background 60ms linear, color 60ms linear",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </button>
  );
}

function Step({ active, current, onClick, color, dim, accent }) {
  return (
    <div
      onClick={onClick}
      style={{
        width: "100%",
        aspectRatio: "1",
        minWidth: 16,
        background: active ? color : COLORS.bgInset,
        border: `1px solid ${current ? COLORS.text : accent ? COLORS.line : COLORS.line}`,
        outline: current ? `1px solid ${COLORS.text}` : "none",
        outlineOffset: current ? -2 : 0,
        cursor: "pointer",
        opacity: dim ? 0.35 : 1,
        transition: "background 40ms linear",
      }}
    />
  );
}

// ---------------------------------------------------------------------------
// MAIN APP
// ---------------------------------------------------------------------------
export default function App() {
  // transport
  const [isPlaying, setIsPlaying] = useState(false);
  const [bpm, setBpm] = useState(140);
  const [swing, setSwing] = useState(0.08);
  const [currentStep, setCurrentStep] = useState(-1);
  const [audioReady, setAudioReady] = useState(false);

  // drum grid: 4 voices x 16 steps
  const [drumGrid, setDrumGrid] = useState(() =>
    DRUM_VOICES.map(() => Array(STEPS).fill(false))
  );
  const [fourOnFloor, setFourOnFloor] = useState(true);

  // bass grid
  const [bassGrid, setBassGrid] = useState(() => Array(BASS_STEPS).fill(false));
  const [bassNote, setBassNote] = useState("C2");
  const [bassWave, setBassWave] = useState("sawtooth");

  // vocal chop engine
  const [sampleBuffer, setSampleBuffer] = useState(null);
  const [sampleName, setSampleName] = useState(null);
  const [chopGrid, setChopGrid] = useState(() => Array(STEPS).fill(-1)); // -1 = empty, else slot index
  const [slotPitch, setSlotPitch] = useState(() => Array(CHOP_SLOTS).fill(0)); // semitones
  const [loadingSample, setLoadingSample] = useState(false);

  // macro / character controls
  const [sidechainDepth, setSidechainDepth] = useState(0.65);
  const [saturation, setSaturation] = useState(0.3);
  const [reverbSend, setReverbSend] = useState(0.35);
  const [masterVol, setMasterVol] = useState(-6);

  const fileInputRef = useRef(null);

  // ---- Tone.js node refs (persist across renders) ----
  const nodesRef = useRef(null);
  const stateRef = useRef({});
  stateRef.current = {
    drumGrid,
    fourOnFloor,
    bassGrid,
    bassNote,
    chopGrid,
    slotPitch,
    sampleBuffer,
  };

  // build audio graph once
  useEffect(() => {
    const master = new Tone.Volume(masterVol).toDestination();

    const saturator = new Tone.Distortion(0.15).connect(master);
    const compBus = new Tone.Compressor(-18, 4).connect(saturator);

    // sidechain-able reverb return
    const reverb = new Tone.Reverb({ decay: 2.4, wet: 1 });
    const reverbGain = new Tone.Volume(0).connect(compBus);
    reverb.connect(reverbGain);

    // drum voices
    const kick = new Tone.MembraneSynth({
      pitchDecay: 0.04,
      octaves: 6,
      envelope: { attack: 0.001, decay: 0.35, sustain: 0.01, release: 0.4 },
    }).connect(compBus);

    const clap = new Tone.NoiseSynth({
      noise: { type: "pink" },
      envelope: { attack: 0.001, decay: 0.18, sustain: 0 },
    }).connect(compBus);

    const hatClosed = new Tone.MetalSynth({
      envelope: { attack: 0.001, decay: 0.045, release: 0.01 },
      harmonicity: 5.1,
      modulationIndex: 32,
      resonance: 4000,
      octaves: 1.5,
    }).connect(compBus);

    const hatOpen = new Tone.MetalSynth({
      envelope: { attack: 0.001, decay: 0.25, release: 0.05 },
      harmonicity: 5.1,
      modulationIndex: 32,
      resonance: 4000,
      octaves: 1.5,
    }).connect(compBus);

    // bass
    const bassFilter = new Tone.Filter(900, "lowpass").connect(compBus);
    const bass = new Tone.MonoSynth({
      oscillator: { type: "sawtooth" },
      envelope: { attack: 0.01, decay: 0.15, sustain: 0.4, release: 0.2 },
      filterEnvelope: { attack: 0.01, decay: 0.2, sustain: 0.3, release: 0.3, baseFrequency: 200, octaves: 3 },
    }).connect(bassFilter);

    // chop sampler player pool (one Player per trigger, created on the fly)
    const chopBus = new Tone.Channel({ volume: -2 }).connect(compBus);
    const chopReverbSend = new Tone.Channel({ volume: -6 }).connect(reverb);

    // sidechain LFO driving the reverb return gain — this is the
    // "duck the send, not the source" trick: automate depth on the wet bus
    const duckSignal = new Tone.Signal(0, "decibels");
    duckSignal.connect(reverbGain.volume);

    nodesRef.current = {
      master,
      saturator,
      compBus,
      reverb,
      reverbGain,
      duckSignal,
      kick,
      clap,
      hatClosed,
      hatOpen,
      bassFilter,
      bass,
      chopBus,
      chopReverbSend,
    };

    Tone.Transport.bpm.value = bpm;

    return () => {
      Object.values(nodesRef.current || {}).forEach((n) => {
        if (n && typeof n.dispose === "function") n.dispose();
      });
      Tone.Transport.stop();
      Tone.Transport.cancel();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // live-update simple params
  useEffect(() => {
    if (nodesRef.current) nodesRef.current.master.volume.value = masterVol;
  }, [masterVol]);
  useEffect(() => {
    if (nodesRef.current) nodesRef.current.saturator.distortion = saturation;
  }, [saturation]);
  useEffect(() => {
    if (nodesRef.current) nodesRef.current.chopReverbSend.volume.value = Tone.gainToDb(reverbSend);
  }, [reverbSend]);
  useEffect(() => {
    Tone.Transport.bpm.value = bpm;
  }, [bpm]);
  useEffect(() => {
    Tone.Transport.swing = swing;
    Tone.Transport.swingSubdivision = "16n";
  }, [swing]);

  // duck the reverb return whenever a kick fires — the "sidechain the
  // effect return, automate the depth" technique
  const duckReverb = useCallback(
    (time) => {
      const d = nodesRef.current;
      if (!d) return;
      const depthDb = -sidechainDepth * 24; // deeper knob = harder pump
      d.duckSignal.setValueAtTime(depthDb, time);
      d.duckSignal.linearRampToValueAtTime(0, time + (60 / bpm) * 0.7);
    },
    [sidechainDepth, bpm]
  );

  // main sequencer loop
  useEffect(() => {
    const seq = new Tone.Sequence(
      (time, step) => {
        const s = stateRef.current;
        const d = nodesRef.current;
        setCurrentStep(step);

        // drums
        const kickHit = s.fourOnFloor ? step % 4 === 0 : s.drumGrid[0][step];
        if (kickHit) {
          d.kick.triggerAttackRelease("C1", "8n", time);
          duckReverb(time);
        }
        if (s.drumGrid[1][step]) d.clap.triggerAttackRelease("16n", time);
        if (s.drumGrid[2][step]) d.hatClosed.triggerAttackRelease("32n", time);
        if (s.drumGrid[3][step]) d.hatOpen.triggerAttackRelease("8n", time);

        // bass
        if (s.bassGrid[step]) {
          d.bass.triggerAttackRelease(s.bassNote, "16n", time);
        }

        // vocal chop
        const slot = s.chopGrid[step];
        if (slot !== -1 && s.sampleBuffer) {
          const total = s.sampleBuffer.duration;
          const regionLen = total / CHOP_SLOTS;
          const offset = slot * regionLen;
          const semis = s.slotPitch[slot] || 0;
          const rate = Math.pow(2, semis / 12);
          const player = new Tone.Player(s.sampleBuffer).connect(d.chopBus);
          player.connect(d.chopReverbSend);
          player.playbackRate = rate;
          player.fadeOut = 0.02;
          const playDuration = regionLen / rate;
          player.start(time, offset, playDuration);
          // dispose after playback finishes rather than relying on an
          // onstop callback (not available on this Player build)
          Tone.Transport.scheduleOnce(() => {
            player.dispose();
          }, time + playDuration + 0.1);
        }
      },
      Array.from({ length: STEPS }, (_, i) => i),
      "16n"
    );
    seq.start(0);
    return () => seq.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duckReverb]);

  // ---- transport controls ----
  const togglePlay = async () => {
    if (!audioReady) {
      await Tone.start();
      setAudioReady(true);
    }
    if (isPlaying) {
      Tone.Transport.pause();
      setIsPlaying(false);
    } else {
      Tone.Transport.start();
      setIsPlaying(true);
    }
  };

  const stopAll = () => {
    Tone.Transport.stop();
    setIsPlaying(false);
    setCurrentStep(-1);
  };

  // ---- grid interaction ----
  const toggleDrumStep = (voiceIdx, stepIdx) => {
    setDrumGrid((g) => {
      const next = g.map((row) => [...row]);
      next[voiceIdx][stepIdx] = !next[voiceIdx][stepIdx];
      return next;
    });
  };

  const toggleBassStep = (stepIdx) => {
    setBassGrid((g) => {
      const next = [...g];
      next[stepIdx] = !next[stepIdx];
      return next;
    });
  };

  const cycleChopStep = (stepIdx) => {
    setChopGrid((g) => {
      const next = [...g];
      next[stepIdx] = next[stepIdx] >= CHOP_SLOTS - 1 ? -1 : next[stepIdx] + 1;
      return next;
    });
  };

  // ---- sample loading ----
  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoadingSample(true);
    try {
      const arrayBuf = await file.arrayBuffer();
      const audioBuf = await Tone.getContext().rawContext.decodeAudioData(arrayBuf.slice(0));
      const toneBuf = new Tone.ToneAudioBuffer(audioBuf);
      setSampleBuffer(toneBuf);
      setSampleName(file.name);
      setChopGrid(Array(STEPS).fill(-1));
      setSlotPitch(Array(CHOP_SLOTS).fill(0));
    } catch (err) {
      console.error("decode failed", err);
    }
    setLoadingSample(false);
  };

  // "found sound" scramble — randomize which chop slot plays on which
  // active step, and randomize pitch per slot. This is the deliberate
  // chance-driven rearrangement Fred again.. applies to sampled speech.
  const scrambleChops = () => {
    if (!sampleBuffer) return;
    setChopGrid((g) =>
      g.map((v) => (v === -1 ? -1 : Math.floor(Math.random() * CHOP_SLOTS)))
    );
    setSlotPitch((p) => p.map(() => Math.floor(Math.random() * 9) - 4));
  };

  const randomizeChopPattern = () => {
    if (!sampleBuffer) return;
    setChopGrid(
      Array.from({ length: STEPS }, () =>
        Math.random() < 0.35 ? Math.floor(Math.random() * CHOP_SLOTS) : -1
      )
    );
  };

  const clearAll = () => {
    setDrumGrid(DRUM_VOICES.map(() => Array(STEPS).fill(false)));
    setBassGrid(Array(BASS_STEPS).fill(false));
    setChopGrid(Array(STEPS).fill(-1));
  };

  const chopColorForSlot = (slot) => {
    const hues = [COLORS.amber, "#FFD08A", "#FF9E5E", "#FFC46B"];
    return hues[slot % hues.length] || COLORS.amber;
  };

  return (
    <div
      style={{
        fontFamily: "'JetBrains Mono', monospace",
        background: COLORS.bg,
        color: COLORS.text,
        minHeight: "100vh",
        padding: 20,
        boxSizing: "border-box",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
        * { box-sizing: border-box; }
        input[type="file"] { display: none; }
      `}</style>

      {/* HEADER / TRANSPORT */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: `1px solid ${COLORS.line}`,
          paddingBottom: 14,
          marginBottom: 16,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: COLORS.green, letterSpacing: 1 }}>
            fwd_engine
          </div>
          <div style={{ fontSize: 10, color: COLORS.textDim }}>found-sound sequencer</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <Toggle active={isPlaying} onClick={togglePlay} color={COLORS.green}>
            {isPlaying ? "❚❚ pause" : "▶ play"}
          </Toggle>
          <Toggle active={false} onClick={stopAll} color={COLORS.red}>
            ■ stop
          </Toggle>
          <Toggle active={false} onClick={clearAll} color={COLORS.textDim} small>
            clear all
          </Toggle>

          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 10, color: COLORS.textDim }}>bpm</span>
            <input
              type="number"
              value={bpm}
              min={60}
              max={200}
              onChange={(e) => setBpm(Number(e.target.value))}
              style={{
                width: 52,
                background: COLORS.bgInset,
                border: `1px solid ${COLORS.line}`,
                color: COLORS.green,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12,
                padding: "4px 6px",
              }}
            />
          </div>

          <Knob label="SWING" value={swing} min={0} max={0.5} step={0.01} onChange={setSwing} />
        </div>
      </div>

      {/* MAIN GRID + SIDE RAIL */}
      <div style={{ display: "flex", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* LEFT: sequencer lanes */}
        <div style={{ flex: "1 1 560px", minWidth: 320, display: "flex", flexDirection: "column", gap: 18 }}>
          {/* step ruler */}
          <div style={{ display: "grid", gridTemplateColumns: `90px repeat(${STEPS}, 1fr)`, gap: 4 }}>
            <div />
            {Array.from({ length: STEPS }).map((_, i) => (
              <div
                key={i}
                style={{
                  textAlign: "center",
                  fontSize: 8,
                  color: i === currentStep ? COLORS.green : COLORS.textDim,
                  fontWeight: i % 4 === 0 ? 700 : 400,
                }}
              >
                {i + 1}
              </div>
            ))}
          </div>

          {/* DRUM LANES */}
          <div>
            <div style={{ fontSize: 10, color: COLORS.cyan, letterSpacing: 1, marginBottom: 8, display: "flex", justifyContent: "space-between" }}>
              <span>DRUM ENGINE</span>
              <Toggle active={fourOnFloor} onClick={() => setFourOnFloor((v) => !v)} color={COLORS.cyan} small>
                4-on-floor lock
              </Toggle>
            </div>
            {DRUM_VOICES.map((voice, vIdx) => (
              <div
                key={voice}
                style={{
                  display: "grid",
                  gridTemplateColumns: `90px repeat(${STEPS}, 1fr)`,
                  gap: 4,
                  marginBottom: 5,
                  alignItems: "center",
                }}
              >
                <div style={{ fontSize: 10, color: COLORS.textDim }}>{voice}</div>
                {Array.from({ length: STEPS }).map((_, sIdx) => {
                  const forcedKick = vIdx === 0 && fourOnFloor;
                  const active = forcedKick ? sIdx % 4 === 0 : drumGrid[vIdx][sIdx];
                  return (
                    <Step
                      key={sIdx}
                      active={active}
                      current={sIdx === currentStep}
                      dim={forcedKick}
                      color={COLORS.cyan}
                      onClick={() => !forcedKick && toggleDrumStep(vIdx, sIdx)}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          {/* BASS LANE */}
          <div>
            <div style={{ fontSize: 10, color: COLORS.green, letterSpacing: 1, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>SUB / REESE BASS</span>
              <div style={{ display: "flex", gap: 6 }}>
                {NOTE_OPTIONS.map((n) => (
                  <Toggle key={n} active={bassNote === n} onClick={() => setBassNote(n)} color={COLORS.green} small>
                    {n}
                  </Toggle>
                ))}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: `90px repeat(${STEPS}, 1fr)`, gap: 4, alignItems: "center" }}>
              <div style={{ fontSize: 10, color: COLORS.textDim }}>BASS</div>
              {Array.from({ length: BASS_STEPS }).map((_, sIdx) => (
                <Step
                  key={sIdx}
                  active={bassGrid[sIdx]}
                  current={sIdx === currentStep}
                  color={COLORS.green}
                  onClick={() => toggleBassStep(sIdx)}
                />
              ))}
            </div>
          </div>

          {/* VOCAL CHOP ENGINE */}
          <div>
            <div style={{ fontSize: 10, color: COLORS.amber, letterSpacing: 1, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
              <span>FOUND-SOUND / VOCAL CHOP</span>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <Toggle active={false} onClick={() => fileInputRef.current?.click()} color={COLORS.amber} small>
                  {loadingSample ? "loading…" : sampleName ? "swap sample" : "load sample"}
                </Toggle>
                <Toggle active={false} onClick={randomizeChopPattern} color={COLORS.amber} small>
                  seed pattern
                </Toggle>
                <Toggle active={false} onClick={scrambleChops} color={COLORS.amber} small>
                  scramble ⟳
                </Toggle>
                <input ref={fileInputRef} type="file" accept="audio/*" onChange={handleFile} />
              </div>
            </div>

            {!sampleBuffer && (
              <div
                style={{
                  border: `1px dashed ${COLORS.line}`,
                  padding: "14px 10px",
                  fontSize: 10,
                  color: COLORS.textDim,
                  textAlign: "center",
                  marginBottom: 8,
                }}
              >
                load a vocal / found-sound clip — a voice note, a phone recording, anything —
                it auto-slices into {CHOP_SLOTS} regions you can retrigger and pitch per step
              </div>
            )}

            {sampleBuffer && (
              <div style={{ fontSize: 9, color: COLORS.textDim, marginBottom: 6 }}>
                {sampleName} · {sampleBuffer.duration.toFixed(2)}s · {CHOP_SLOTS} slices
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: `90px repeat(${STEPS}, 1fr)`, gap: 4, alignItems: "center" }}>
              <div style={{ fontSize: 10, color: COLORS.textDim }}>CHOP</div>
              {Array.from({ length: STEPS }).map((_, sIdx) => {
                const slot = chopGrid[sIdx];
                return (
                  <Step
                    key={sIdx}
                    active={slot !== -1}
                    current={sIdx === currentStep}
                    color={slot !== -1 ? chopColorForSlot(slot) : COLORS.amber}
                    onClick={() => cycleChopStep(sIdx)}
                  />
                );
              })}
            </div>
            <div style={{ fontSize: 8, color: COLORS.textDim, marginTop: 4 }}>
              click a cell to cycle through the {CHOP_SLOTS} slice slots · click again to clear
            </div>

            {sampleBuffer && (
              <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
                {Array.from({ length: CHOP_SLOTS }).map((_, slotIdx) => (
                  <div key={slotIdx} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                    <div style={{ fontSize: 8, color: chopColorForSlot(slotIdx) }}>S{slotIdx + 1}</div>
                    <Knob
                      label="PITCH"
                      value={slotPitch[slotIdx]}
                      min={-12}
                      max={12}
                      step={1}
                      unit="st"
                      color={chopColorForSlot(slotIdx)}
                      onChange={(v) =>
                        setSlotPitch((p) => {
                          const next = [...p];
                          next[slotIdx] = v;
                          return next;
                        })
                      }
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: macro rail */}
        <div
          style={{
            flex: "0 0 190px",
            background: COLORS.bgPanel,
            border: `1px solid ${COLORS.line}`,
            padding: 16,
            display: "flex",
            flexDirection: "column",
            gap: 18,
          }}
        >
          <div style={{ fontSize: 10, color: COLORS.textDim, letterSpacing: 1 }}>CHARACTER</div>

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <Knob label="SIDECHAIN" value={sidechainDepth} min={0} max={1} onChange={setSidechainDepth} color={COLORS.cyan} />
            <Knob label="SATURATE" value={saturation} min={0} max={1} onChange={setSaturation} color={COLORS.amber} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <Knob label="RVB SEND" value={reverbSend} min={0} max={1} onChange={setReverbSend} color={COLORS.green} />
            <Knob
              label="MASTER"
              value={masterVol}
              min={-30}
              max={0}
              step={1}
              unit="dB"
              onChange={setMasterVol}
              color={COLORS.text}
            />
          </div>

          <div style={{ borderTop: `1px solid ${COLORS.line}`, paddingTop: 12, fontSize: 8, color: COLORS.textDim, lineHeight: 1.6 }}>
            sidechain ducks the reverb return on every kick — the effect's
            wet tail pumps, not the dry signal. that's the pump you hear
            under the pads.
            <br />
            <br />
            saturate adds grit to the whole bus post-mix so nothing sits
            too clean — texture over clarity.
          </div>

          <div style={{ borderTop: `1px solid ${COLORS.line}`, paddingTop: 12 }}>
            <div style={{ fontSize: 10, color: COLORS.textDim, letterSpacing: 1, marginBottom: 8 }}>STATUS</div>
            <div style={{ fontSize: 9, color: audioReady ? COLORS.green : COLORS.textDim }}>
              {audioReady ? "● audio engine live" : "○ press play to init audio"}
            </div>
            <div style={{ fontSize: 9, color: COLORS.textDim, marginTop: 4 }}>
              step {currentStep === -1 ? "--" : currentStep + 1} / {STEPS}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
