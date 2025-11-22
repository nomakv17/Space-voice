# AI Models Guide - November 2025

Complete guide to the latest and best models for voice agents.

## 🎯 Recommended Stack (Default Configuration)

**Best for Production Voice Agents:**
- **LLM**: gpt-realtime (OpenAI Realtime API)
- **STT**: Deepgram Nova-3
- **TTS**: ElevenLabs Turbo v2.5
- **Telephony**: Telnyx

## 🤖 Language Models (LLM)

### OpenAI - Best for Voice Agents

#### **gpt-realtime** ⭐ RECOMMENDED
- **Type**: End-to-end speech-to-speech
- **Latency**: Native audio pipeline
- **Unique Features**:
  - Built-in SIP support for phone calls
  - No separate STT/TTS needed
  - Native voice mode with interruption handling
  - New voices: Cedar, Marin
  - Better instruction following (30.5% accuracy vs 20.6%)
  - Better function calling (66.5% vs 49.7%)
- **Pricing**: $32/1M input tokens, $64/1M output (20% cheaper than preview)
- **Use Case**: Production voice agents

#### **GPT-4o**
- **Type**: Multimodal (text, vision, audio)
- **Latency**: 232-320ms audio latency
- **Use Case**: Complex reasoning + voice, when you need vision capabilities
- **Pricing**: Standard OpenAI pricing

#### **GPT-4o-mini**
- **Type**: Fast, lightweight
- **Latency**: Near-instant
- **Pricing**: 25x cheaper than GPT-4o
- **Use Case**: Simple voice interactions, cost-sensitive applications

#### **gpt-4o-transcribe** / **gpt-4o-mini-transcribe** (NEW)
- Better word error rate
- Improved language recognition
- Use for standalone transcription

#### **gpt-4o-mini-tts** (NEW)
- Better steerability for voice output

### Anthropic Claude

#### **Claude Sonnet 4.5** ⭐ RECOMMENDED (Sep 2025)
- **Model ID**: `claude-sonnet-4-5`
- **Released**: September 29, 2025
- **Strengths**:
  - Best coding model in the world
  - State-of-the-art agentic capabilities (61.4% OSWorld)
  - Can maintain focus for 30+ hours on complex tasks
  - Superior reasoning and domain knowledge
- **Pricing**: $3/$15 per million tokens (same as Sonnet 4)
- **Note**: NOT native voice (needs separate STT/TTS)
- **Use Case**: Complex agents, advanced customer service, coding assistance

#### **Claude Opus 4.1** (Aug 2025)
- **Released**: August 5, 2025
- **Most capable** Claude model
- 74.5% on SWE-bench Verified
- **Use Case**: Most complex reasoning tasks

#### **Claude Haiku 4.5** (Oct 2025)
- **Released**: October 15, 2025
- **Fastest** and cheapest ($1/$5 per million tokens)
- **Use Case**: High-volume, simple interactions

### Google

#### **Gemini 2.5 Flash**
- **Features**:
  - Native voice mode with 30+ voices
  - Multimodal (voice + vision)
  - Live API for real-time streaming
  - Screen sharing capability
- **Languages**: 24+ languages
- **Use Case**: When you need vision + voice together

## 🎤 Speech-to-Text (STT)

### Deepgram - Best Value & Performance

#### **Nova-3** ⭐ RECOMMENDED
- **WER**: 6.84% median (54% better than competitors)
- **Features**:
  - Multilingual: 10 languages with code-switching (EN, ES, FR, DE, HI, RU, PT, JA, IT, NL)
  - Keyterm prompting: Up to 100 domain terms, 6x accuracy lift
  - PII redaction: 50 entities in real-time (HIPAA compliant)
  - Better acoustic performance in noise
- **Latency**: Sub-300ms
- **Pricing**:
  - Streaming: $0.0077/min
  - Batch: $0.0066/min
- **Use Case**: Production multilingual applications, regulated industries

#### **Nova-2**
- **WER**: 8.4% median (still excellent)
- **Pricing**:
  - Batch: $0.0043/min (25% cheaper than Nova-3)
- **Use Case**: English-only, budget-conscious applications

### OpenAI Whisper
- Good fallback option
- Higher latency than Deepgram
- Use for offline/batch transcription

### Google STT
- Good for Google ecosystem integration

## 🔊 Text-to-Speech (TTS)

### ElevenLabs - Best Quality

#### **Turbo v2.5** ⭐ RECOMMENDED
- **Latency**: ~300ms
- **Quality**: Highest quality for voice agents
- **Languages**: 32 languages
- **Pricing**: 1 credit per 2 characters
- **Use Case**: Primary choice for voice agents (ElevenLabs recommends this over Flash)

#### **Flash v2.5**
- **Latency**: ~75ms (fastest)
- **Quality**: Slightly lower than Turbo
- **Languages**: 32 languages
- **Pricing**: 1 credit per 2 characters
- **Use Case**: Only when latency is absolutely critical (<100ms required)

#### **Multilingual v2**
- **Languages**: 29 languages
- **Use Case**: Non-English primary languages

### OpenAI TTS
- **gpt-4o-mini-tts** (NEW) - better steerability
- Fallback option

### Google Gemini TTS
- Part of Gemini 2.5 Flash Live API
- 30+ voices

## 📊 Model Comparison Matrix

| Use Case | LLM | STT | TTS | Total Latency |
|----------|-----|-----|-----|---------------|
| **Production (Recommended)** | gpt-realtime | Built-in | Built-in | ~232-320ms |
| **Custom Pipeline** | GPT-4o | Nova-3 | Turbo v2.5 | ~530ms |
| **Budget** | GPT-4o-mini | Nova-2 | Flash v2.5 | ~375ms |
| **Multilingual** | gpt-realtime | Nova-3 | Turbo v2.5 | ~300ms |
| **Complex Reasoning** | Claude 3.7 | Nova-3 | Turbo v2.5 | ~600ms |
| **Vision + Voice** | Gemini 2.5 | Built-in | Built-in | ~400ms |

## 💰 Cost Comparison (Per Minute of Call)

**Cheapest Stack:**
- STT: Deepgram Nova-2 ($0.0043/min)
- TTS: ElevenLabs (~$0.002/min)
- LLM: GPT-4o-mini (~$0.001/min)
- Telephony: Telnyx ($0.0075/min)
- **Total**: ~$0.0148/min = **$0.89/hour**

**Recommended Stack:**
- LLM: gpt-realtime ($0.032/min estimated)
- Telephony: Telnyx ($0.0075/min)
- **Total**: ~$0.0395/min = **$2.37/hour**

**Premium Stack:**
- STT: Deepgram Nova-3 ($0.0077/min)
- TTS: ElevenLabs Turbo v2.5 (~$0.003/min)
- LLM: GPT-4o (~$0.015/min)
- Telephony: Telnyx ($0.0075/min)
- **Total**: ~$0.0332/min = **$1.99/hour**

## 🎛️ Configuration Recommendations

### For Customer Support
```
LLM: gpt-realtime
STT: Built-in (Realtime API)
TTS: Built-in (Realtime API)
Temperature: 0.7
Max Tokens: 2000
```

### For Sales/Outbound
```
LLM: Claude Sonnet 4.5 or GPT-4o
STT: Deepgram Nova-3
TTS: ElevenLabs Turbo v2.5
Temperature: 0.9 (more creative)
Max Tokens: 3000
```

### For Multilingual
```
LLM: gpt-realtime or Gemini 2.5
STT: Deepgram Nova-3 (10 language code-switching)
TTS: ElevenLabs Multilingual v2
Temperature: 0.7
Max Tokens: 2000
```

### For Healthcare/Compliance
```
LLM: gpt-4o
STT: Deepgram Nova-3 (PII redaction)
TTS: ElevenLabs Turbo v2.5
Temperature: 0.5 (more focused)
Max Tokens: 1500
Enable: Recording, Transcripts, PII Redaction
```

## 🚫 Models NOT Recommended for Voice

- **o1, o3-mini, o4-mini**: Reasoning models too slow for real-time (seconds of thinking time)
- **GPT-3.5-turbo**: Outdated, superseded by GPT-4o-mini
- **GPT-4, GPT-4-turbo**: Superseded by GPT-4o

## 🔄 When to Use Each Provider

### Use OpenAI Realtime API When:
- You want the simplest setup (one API for everything)
- Need SIP support for direct phone integration
- Want lowest latency end-to-end
- Don't need to swap providers

### Use Pipecat Custom Pipeline When:
- Need flexibility to switch providers
- Want cost optimization (mix & match)
- Require custom business logic between STT/LLM/TTS
- Need data ownership and compliance
- Want A/B testing of different models

## 📚 Sources

- [OpenAI gpt-realtime](https://openai.com/index/introducing-gpt-realtime/)
- [OpenAI Next-Gen Audio Models](https://openai.com/index/introducing-our-next-generation-audio-models/)
- [Deepgram Nova-3 vs Nova-2](https://deepgram.com/learn/model-comparison-when-to-use-nova-2-vs-nova-3-for-devs)
- [Deepgram Nova-3 Announcement](https://deepgram.com/learn/introducing-nova-3-speech-to-text-api)
- [ElevenLabs Models](https://elevenlabs.io/docs/models)
- [ElevenLabs Turbo v2.5](https://elevenlabs.io/blog/introducing-turbo-v2-5)
- [Claude Sonnet 4.5](https://www.anthropic.com/news/claude-sonnet-4-5)
- [Claude Opus 4.1](https://www.anthropic.com/news/claude-opus-4-1)
- [Claude 4 Release](https://www.anthropic.com/news/claude-4)
- [Gemini 2.5 Flash](https://blog.google/technology/google-deepmind/google-gemini-updates-io-2025/)
- [GPT-4o Models](https://www.kommunicate.io/blog/chatgpt-models-explained/)

## 🎯 Key Takeaway

**For most voice agent use cases, use:**
- **gpt-realtime** for simplicity and production-ready voice
- **Custom Pipecat pipeline** (Nova-3 + GPT-4o + Turbo v2.5) for flexibility and cost control

Your platform now supports both approaches! 🚀
