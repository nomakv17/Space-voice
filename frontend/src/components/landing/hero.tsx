"use client";

import { useState, useRef } from "react";
import { Phone, Play, Pause, ArrowRight, Zap, Clock, Shield, Volume2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  icon: React.ReactNode;
  value: string;
  label: string;
  delay?: number;
}

function MetricCard({ icon, value, label, delay = 0 }: MetricCardProps) {
  return (
    <div
      className="bg-white rounded-xl px-4 py-3 flex items-center gap-3 animate-fade-in-up shadow-lg border border-gray-100"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="p-2 rounded-lg bg-cyan-50 text-cyan-600">{icon}</div>
      <div>
        <div className="text-lg font-bold text-gray-900">{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  );
}

export function HeroSection() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(75); // 1:15 default duration
  const [audioAvailable, setAudioAvailable] = useState(true);
  const audioRef = useRef<HTMLAudioElement>(null);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        void audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-b from-gray-50 to-white">
      {/* Grid pattern */}
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage: `linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Gradient orbs */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-cyan-200/30 rounded-full blur-[120px]" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-200/30 rounded-full blur-[100px]" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left column - Content */}
          <div className="text-center lg:text-left">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-700 text-sm font-medium mb-8 animate-fade-in">
              <Zap className="w-4 h-4" />
              <span>AI-Powered Voice Agents</span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-gray-900 mb-6 animate-fade-in-up">
              AI Voice Agents for Home Services{" "}
              <span className="bg-gradient-to-r from-cyan-600 via-cyan-500 to-purple-600 bg-clip-text text-transparent">
                That Actually Convert
              </span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg sm:text-xl text-gray-600 mb-8 max-w-xl mx-auto lg:mx-0 animate-fade-in-up delay-100">
              Stop losing HVAC & plumbing calls to voicemail. SpaceVoice answers 24/7, triages
              emergencies, and books appointments—automatically.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start mb-12 animate-fade-in-up delay-200">
              <button
                onClick={() => document.getElementById("demo-form")?.scrollIntoView()}
                className="group inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold text-lg shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-105 transition-all duration-300"
              >
                <Phone className="w-5 h-5" />
                Try Live Demo
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>

              <button className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl border-2 border-gray-200 text-gray-700 font-semibold text-lg hover:bg-gray-50 hover:border-gray-300 transition-all duration-300">
                <Play className="w-5 h-5" />
                Watch Demo
              </button>
            </div>

            {/* Metrics */}
            <div className="flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 justify-center lg:justify-start">
              <MetricCard
                icon={<Phone className="w-4 h-4" />}
                value="10,000+"
                label="Calls Handled"
                delay={300}
              />
              <MetricCard
                icon={<Clock className="w-4 h-4" />}
                value="<200ms"
                label="Response Time"
                delay={400}
              />
              <MetricCard
                icon={<Shield className="w-4 h-4" />}
                value="24/7"
                label="Availability"
                delay={500}
              />
            </div>
          </div>

          {/* Right column - Audio Demo */}
          <div className="relative">
            {/* Audio sample player card */}
            <div
              id="demo-form"
              className="bg-white rounded-3xl p-8 max-w-md mx-auto animate-scale-in shadow-2xl border border-gray-100"
            >
              {/* Hidden audio element */}
              <audio
                ref={audioRef}
                src="/audio/demo-call-sample.mp3?v=5"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={handleEnded}
                onError={() => setAudioAvailable(false)}
              />

              {/* Voice visualization - animated when playing */}
              <div className="flex items-center justify-center gap-1 mb-6">
                {[
                  { height: 35, duration: 900 },
                  { height: 50, duration: 1100 },
                  { height: 25, duration: 850 },
                  { height: 45, duration: 1000 },
                  { height: 30, duration: 950 },
                ].map((bar, i) => (
                  <div
                    key={i}
                    className={cn(
                      "w-1.5 bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-full transition-all",
                      isPlaying ? "animate-pulse" : ""
                    )}
                    style={{
                      height: isPlaying ? `${bar.height}px` : "12px",
                      animationDelay: `${i * 100}ms`,
                      animationDuration: `${bar.duration}ms`,
                    }}
                  />
                ))}
              </div>

              <div className="flex items-center gap-2 justify-center mb-2">
                <Volume2 className="w-5 h-5 text-cyan-600" />
                <h3 className="text-2xl font-bold text-gray-900">
                  Hear SpaceVoice in Action
                </h3>
              </div>
              <p className="text-gray-600 text-center mb-6">
                Listen to a real call sample. This is exactly how SpaceVoice handles HVAC inquiries.
              </p>

              {/* Audio player controls */}
              {audioAvailable ? (
                <div className="bg-gray-50 rounded-2xl p-6 mb-6">
                  {/* Play button and progress */}
                  <div className="flex items-center gap-4 mb-4">
                    <button
                      onClick={togglePlay}
                      className="w-14 h-14 rounded-full bg-gradient-to-r from-cyan-600 to-cyan-500 text-white flex items-center justify-center hover:shadow-lg hover:shadow-cyan-500/25 transition-all flex-shrink-0"
                    >
                      {isPlaying ? (
                        <Pause className="w-6 h-6" />
                      ) : (
                        <Play className="w-6 h-6 ml-1" />
                      )}
                    </button>

                    <div className="flex-1">
                      {/* Progress bar */}
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 transition-all duration-100"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      {/* Time display */}
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>{formatTime(currentTime)}</span>
                        <span>{formatTime(duration)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Sample call transcript preview */}
                  <div className="text-sm text-gray-600 italic border-l-2 border-cyan-400 pl-3">
                    &quot;Hi there, CoolAir HVAC, this is Sarah. How can I help you?&quot;
                  </div>
                </div>
              ) : (
                <div className="bg-gray-50 rounded-2xl p-6 mb-6 text-center">
                  {/* Fallback when audio is unavailable */}
                  <div className="text-sm text-gray-600 italic border-l-2 border-cyan-400 pl-3 text-left mb-4">
                    &quot;Hi there, CoolAir HVAC, this is Sarah. How can I help you?&quot;
                  </div>
                  <p className="text-sm text-gray-500">
                    Audio demo coming soon • Contact us for a live demonstration
                  </p>
                </div>
              )}

              {/* CTA Buttons */}
              <div className="space-y-3">
                <a
                  href="https://dashboard.spacevoice.ai/signup"
                  className="flex items-center justify-center gap-2 w-full py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                >
                  <Phone className="w-5 h-5" />
                  Get Started
                  <ArrowRight className="w-5 h-5" />
                </a>
                <a
                  href="mailto:hello@spacevoice.ai"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-xl border-2 border-gray-200 text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-300 transition-all"
                >
                  Talk to Sales
                </a>
              </div>

              <p className="text-xs text-gray-500 text-center mt-4">
                30-day money-back guarantee • Cancel anytime
              </p>
            </div>

            {/* Floating testimonial */}
            <div className="absolute -bottom-4 -left-4 bg-white rounded-xl px-4 py-3 max-w-[220px] shadow-lg border border-gray-100 hidden lg:block">
              <div className="flex items-center gap-2 mb-1">
                {[...Array(5)].map((_, i) => (
                  <span key={i} className="text-yellow-400 text-sm">
                    ★
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-700">
                &quot;Recovered $8,500/month in missed calls&quot;
              </p>
              <p className="text-xs text-gray-500 mt-1">— HVAC Pro Services</p>
            </div>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <div className="w-6 h-10 rounded-full border-2 border-gray-300 flex items-start justify-center p-2">
          <div className="w-1 h-2 bg-gray-400 rounded-full animate-pulse" />
        </div>
      </div>
    </section>
  );
}
