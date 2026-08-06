#include "PianoEngine.h"

using namespace juce;

namespace wp
{

namespace
{
    inline double noteToHz (double midiNote) { return 440.0 * std::pow (2.0, (midiNote - 69.0) / 12.0); }
    inline float  lerp (float a, float b, float t) { return a + (b - a) * t; }

    inline float onePoleCoef (double fc, double sampleRate)
    {
        return (float) (1.0 - std::exp (-2.0 * MathConstants<double>::pi * fc / sampleRate));
    }

    /** Undamped ringing time in seconds - long in the bass, short at the top. */
    inline float freeDecayTime (int midiNote)
    {
        return 28.0f * std::exp (-0.03033f * (float) (midiNote - 21));
    }

    /** How long the felt damper takes to kill the string. */
    inline float dampedDecayTime (int midiNote)
    {
        return jmax (0.05f, 0.40f * std::exp (-0.018f * (float) (midiNote - 21)));
    }

    /** Loudness compensation: bass strings move a lot more air. */
    inline float registerGain (int midiNote)
    {
        return std::pow (10.0f, (-0.035f * (float) (midiNote - 60)) / 20.0f);
    }
}

//==============================================================================
void StringResonator::prepare (int maxDelaySamples)
{
    const int size = nextPowerOfTwo (jmax (64, maxDelaySamples + 8));
    buffer.assign ((size_t) size, 0.0f);
    mask = size - 1;
    reset();
}

void StringResonator::reset()
{
    std::fill (buffer.begin(), buffer.end(), 0.0f);
    writeIndex = 0;
    lossState = 0.0f;
    apState.fill (0.0f);
    dcX = dcY = 0.0f;
}

void StringResonator::setTone (double sampleRate, double freq, float t60, float damping, float dispersion)
{
    lastFreq = freq;
    damp = jlimit (0.02f, 0.75f, damping);

    // dispersion allpasses - more sections at the extremes of the keyboard,
    // which is where real strings are the most inharmonic
    apCount = dispersion > 0.001f ? jlimit (0, 4, 1 + (int) (dispersion * 3.0f)) : 0;
    apCoef  = apCount > 0 ? -jlimit (0.0f, 0.45f, dispersion * 0.4f) : 0.0f;

    const float apDelay   = apCount > 0 ? (float) apCount * ((1.0f - apCoef) / (1.0f + apCoef)) : 0.0f;
    const float lossDelay = damp / (1.0f - damp);
    loopDelayCompensation = apDelay + lossDelay;

    const float period = (float) (sampleRate / jmax (8.0, freq));
    delaySamples = jlimit (2.0f, (float) mask - 2.0f, period - loopDelayCompensation);

    setDecayTime (sampleRate, t60);
}

void StringResonator::setDecayTime (double sampleRate, float t60)
{
    const float roundTrips = (float) (sampleRate / jmax (1.0f, delaySamples + loopDelayCompensation)) * jmax (0.01f, t60);
    loopGain = jlimit (0.0f, 0.99995f, std::pow (10.0f, -3.0f / jmax (1.0f, roundTrips)));
}

//==============================================================================
void HammerExciter::trigger (double sampleRate, float velocity, float hardness, float noiseAmount,
                             float periodSamples, int model)
{
    // A hard hit is short and bright, a soft one is long and dull. Model 2 is
    // the felt piano, where a strip of cloth sits between hammer and string.
    float hard = jlimit (0.0f, 1.0f, hardness * 0.45f + velocity * 0.55f);

    if (model == 1) hard *= 0.85f;          // upright
    if (model == 2) hard *= 0.42f;          // felt
    if (model == 3) hard = jmin (1.0f, hard * 1.18f + 0.06f); // bright stage piano

    const float tauMs = lerp (5.5f, 0.55f, hard);
    envCoef = std::exp (-1.0f / jmax (1.0f, (float) (tauMs * 0.001 * sampleRate)));
    env = 1.0f;

    const double cutoff = jmin (sampleRate * 0.45, (double) lerp (620.0f, 9500.0f, hard));
    lpCoef = onePoleCoef (cutoff, sampleRate);
    lpState = 0.0f;

    click = velocity * velocity * (0.25f + 0.75f * hard) * (0.25f + noiseAmount);
    clickCoef = std::exp (-1.0f / jmax (1.0f, (float) (0.4 * 0.001 * sampleRate)));

    samplesLeft = (int) (sampleRate * 0.035);

    combDelay = jlimit (1, 900, (int) (periodSamples * (model == 2 ? 0.11f : 0.125f)));
    std::fill (comb.begin(), comb.end(), 0.0f);
    combIndex = 0;

    amp = 0.55f + 0.45f * velocity;
}

//==============================================================================
void PianoVoice::prepare (double sampleRate, int maxDelaySamples)
{
    ignoreUnused (sampleRate);

    for (auto& s : strings)
        s.prepare (maxDelaySamples);

    reset();
}

void PianoVoice::reset()
{
    for (auto& s : strings)
        s.reset();

    hammer.reset();
    active = keyHeld = sustained = sostenuto = false;
    energy = 0.0f;
    releaseNoise = 0.0f;
}

void PianoVoice::start (int midiNote, float velocity, const EngineSettings& s, double sampleRate,
                        float softPedal)
{
    note = midiNote;
    keyHeld = true;
    sustained = false;
    sostenuto = false;
    active = true;
    energy = 1.0f;
    releaseNoise = 0.0f;

    numStrings = midiNote < 31 ? 1 : (midiNote < 43 ? 2 : 3);

    const double freq = noteToHz ((double) midiNote);
    const float period = (float) (sampleRate / freq);

    // velocity shaping
    const float curveExp = std::pow (4.0f, 0.5f - s.velCurve);
    float v = std::pow (jlimit (0.0f, 1.0f, velocity), curveExp);
    v *= (1.0f - 0.35f * softPedal);

    const float gainDb = (v - 1.0f) * s.dynamicRange;
    amplitude = std::pow (10.0f, gainDb / 20.0f) * registerGain (midiNote) * 0.55f;

    // brightness follows how hard you play, which is most of what makes a
    // modelled piano feel alive
    float damping = 0.16f - s.brightness * 0.10f - v * 0.055f + softPedal * 0.05f;

    switch (s.model)
    {
        case 1: damping += 0.055f; break;                 // upright: shorter, boxier
        case 2: damping += 0.150f; break;                 // felt: very dark
        case 3: damping -= 0.045f; break;                 // stage: open and bright
        default: break;
    }

    damping += 0.055f * jlimit (0.0f, 1.0f, (float) (midiNote - 72) / 36.0f);
    damping = jlimit (0.03f, 0.7f, damping);

    // inharmonicity rises towards both ends of the keyboard
    const float centreDist = std::abs ((float) midiNote - 56.0f) / 46.0f;
    const float dispersion = jlimit (0.0f, 1.0f, s.stretch * (0.16f + 0.72f * centreDist * centreDist));

    float t60 = freeDecayTime (midiNote) * s.decayScale;

    if (s.model == 1) t60 *= 0.78f;
    if (s.model == 2) t60 *= 0.62f;

    for (int i = 0; i < numStrings; ++i)
    {
        // unison spread: the tiny detune between the strings of one note is
        // where the shimmer and the natural double decay come from
        static constexpr float offsets[maxStrings] = { 0.0f, -1.0f, 0.85f };
        const float cents = offsets[i] * s.detuneCents;
        const double f = freq * std::pow (2.0, cents / 1200.0);

        strings[(size_t) i].reset();
        strings[(size_t) i].setTone (sampleRate, f, t60 * (1.0f + 0.14f * offsets[i]),
                                     damping * (1.0f + 0.06f * offsets[i]), dispersion);
    }

    hammer.trigger (sampleRate, v, s.hardness, s.mechNoise, period, s.model);

    // stereo placement by key position
    const float p = jlimit (-1.0f, 1.0f, ((float) midiNote - 60.0f) / 30.0f) * s.spread;
    const float angle = (p * 0.5f + 0.5f) * MathConstants<float>::halfPi;
    panL = std::cos (angle);
    panR = std::sin (angle);

    sympGain = amplitude * (0.4f + 0.6f * v);
}

void PianoVoice::stop (bool pedalHeld, const EngineSettings& s, double sampleRate)
{
    keyHeld = false;

    if (pedalHeld || sostenuto)
    {
        sustained = true;
        return;
    }

    pedalReleased (s, sampleRate);
}

void PianoVoice::pedalReleased (const EngineSettings& s, double sampleRate)
{
    if (! active || keyHeld)
        return;

    sustained = false;

    const float t60 = dampedDecayTime (note);

    for (int i = 0; i < numStrings; ++i)
        strings[(size_t) i].setDecayTime (sampleRate, t60);

    // felt dampers landing on a ringing string make a soft noise of their own
    releaseNoise = 0.04f * s.mechNoise * amplitude * 20.0f;
    releaseNoiseCoef = std::exp (-1.0f / jmax (1.0f, (float) (0.012 * sampleRate)));
}

void PianoVoice::render (float* left, float* right, int numSamples, Random& rng, float* sympSend)
{
    if (! active)
        return;

    const float outL = panL * amplitude;
    const float outR = panR * amplitude;
    const float invStrings = 1.0f / (float) numStrings;

    float localEnergy = energy;

    for (int n = 0; n < numSamples; ++n)
    {
        float exc = hammer.process (rng);

        if (releaseNoise > 1.0e-5f)
        {
            exc += (rng.nextFloat() * 2.0f - 1.0f) * releaseNoise;
            releaseNoise *= releaseNoiseCoef;
        }

        float sum = 0.0f;

        for (int i = 0; i < numStrings; ++i)
        {
            const float sv = strings[(size_t) i].process (exc);
            sum += sv;
        }

        sum *= invStrings;

        left[n]  += sum * outL;
        right[n] += sum * outR;

        if (sympSend != nullptr)
            sympSend[n] += sum * sympGain;

        const float a = std::abs (sum);
        localEnergy += 0.0004f * (a - localEnergy);
    }

    energy = localEnergy;

    if (! keyHeld && ! hammer.isActive() && energy < 2.0e-5f)
    {
        active = false;
        sustained = false;
        sostenuto = false;
    }
}

//==============================================================================
void SympatheticBank::prepare (double sampleRate, int maxDelaySamples)
{
    for (int i = 0; i < numStrings; ++i)
    {
        strings[(size_t) i].prepare (maxDelaySamples);

        // two chromatic octaves of open bass/tenor strings
        const double freq = noteToHz (33.0 + (double) i);
        strings[(size_t) i].setTone (sampleRate, freq, 5.5f, 0.22f, 0.25f);

        const float p = ((float) i / (float) (numStrings - 1)) * 2.0f - 1.0f;
        const float angle = (p * 0.35f * 0.5f + 0.5f) * MathConstants<float>::halfPi;
        panL[(size_t) i] = std::cos (angle);
        panR[(size_t) i] = std::sin (angle);
    }

    reset();
}

void SympatheticBank::reset()
{
    for (auto& s : strings)
        s.reset();

    smoothed = 0.0f;
}

void SympatheticBank::setAmount (float a, double) { amount = jlimit (0.0f, 1.0f, a); }

void SympatheticBank::process (const float* input, float* left, float* right, int numSamples)
{
    if (amount <= 0.0001f && smoothed <= 0.0001f)
        return;

    for (int n = 0; n < numSamples; ++n)
    {
        smoothed += 0.0008f * (amount - smoothed);

        const float in = input[n] * smoothed * 0.055f;

        if (std::abs (in) < 1.0e-12f && smoothed < 1.0e-4f)
            continue;

        float l = 0.0f, r = 0.0f;

        for (int i = 0; i < numStrings; ++i)
        {
            const float v = strings[(size_t) i].process (in);
            l += v * panL[(size_t) i];
            r += v * panR[(size_t) i];
        }

        constexpr float norm = 1.0f / (float) numStrings;
        left[n]  += l * norm;
        right[n] += r * norm;
    }
}

//==============================================================================
PianoEngine::PianoEngine() = default;

void PianoEngine::prepare (double sampleRate, int maxBlockSize)
{
    sr = sampleRate;

    const int maxDelay = (int) (sampleRate / 24.0) + 16;

    for (auto& v : voices)
        v.prepare (sampleRate, maxDelay);

    sympathetic.prepare (sampleRate, maxDelay);
    sympBuffer.assign ((size_t) jmax (16, maxBlockSize), 0.0f);

    const std::array<float, 3> freqs { 108.0f, 235.0f, 480.0f };
    const std::array<float, 3> qs    { 1.1f, 1.6f, 2.2f };
    const std::array<float, 3> gains { 1.35f, 1.20f, 0.85f };

    for (size_t i = 0; i < 3; ++i)
    {
        auto coeffs = dsp::IIR::Coefficients<float>::makePeakFilter (sampleRate, freqs[i], qs[i], gains[i]);
        bodyL[i].coefficients = coeffs;
        bodyR[i].coefficients = coeffs;
        bodyL[i].reset();
        bodyR[i].reset();
    }

    reset();
}

void PianoEngine::reset()
{
    for (auto& v : voices)
        v.reset();

    sympathetic.reset();

    for (auto& f : bodyL) f.reset();
    for (auto& f : bodyR) f.reset();

    activeVoices = 0;
    pedal = 0.0f;
    soft = 0.0f;
    sostenutoDown = false;
}

PianoVoice* PianoEngine::findVoiceToSteal (int midiNote)
{
    // retrigger of the same note always wins
    for (auto& v : voices)
        if (v.isActive() && v.getNote() == midiNote)
            return &v;

    for (auto& v : voices)
        if (! v.isActive())
            return &v;

    // otherwise take the quietest released voice, then the oldest one
    PianoVoice* best = nullptr;
    float lowest = std::numeric_limits<float>::max();

    for (auto& v : voices)
    {
        if (v.isHeld())
            continue;

        if (v.getEnergy() < lowest)
        {
            lowest = v.getEnergy();
            best = &v;
        }
    }

    if (best != nullptr)
        return best;

    PianoVoice* oldest = &voices[0];

    for (auto& v : voices)
        if (v.getStartOrder() < oldest->getStartOrder())
            oldest = &v;

    return oldest;
}

void PianoEngine::noteOn (int midiNote, float velocity)
{
    if (velocity <= 0.0f)
    {
        noteOff (midiNote);
        return;
    }

    auto* voice = findVoiceToSteal (midiNote);
    voice->start (midiNote, velocity, settings, sr, soft);
    voice->startOrder = ++orderCounter;

    if (pedal >= 0.5f)
        voice->sustained = true;
}

void PianoEngine::noteOff (int midiNote)
{
    for (auto& v : voices)
        if (v.isActive() && v.isHeld() && v.getNote() == midiNote)
            v.stop (pedal >= 0.45f, settings, sr);
}

void PianoEngine::sustainPedal (float value)
{
    const float previous = pedal;
    pedal = jlimit (0.0f, 1.0f, value);

    if (previous >= 0.45f && pedal < 0.45f)
        for (auto& v : voices)
            if (v.isActive() && ! v.isHeld() && ! v.isSostenuto())
                v.pedalReleased (settings, sr);
}

void PianoEngine::sostenutoPedal (bool down)
{
    sostenutoDown = down;

    if (down)
    {
        for (auto& v : voices)
            if (v.isActive() && v.isHeld())
                v.setSostenuto (true);
    }
    else
    {
        for (auto& v : voices)
        {
            if (v.isSostenuto())
            {
                v.setSostenuto (false);

                if (! v.isHeld() && pedal < 0.45f)
                    v.pedalReleased (settings, sr);
            }
        }
    }
}

void PianoEngine::softPedal (float value) { soft = jlimit (0.0f, 1.0f, value); }

void PianoEngine::allNotesOff()
{
    for (auto& v : voices)
        if (v.isActive() && v.isHeld())
            v.stop (pedal >= 0.45f, settings, sr);
}

void PianoEngine::panic()
{
    for (auto& v : voices)
        v.reset();

    sympathetic.reset();
    activeVoices = 0;
}

void PianoEngine::render (float* left, float* right, int numSamples)
{
    if ((int) sympBuffer.size() < numSamples)
        sympBuffer.assign ((size_t) numSamples, 0.0f);

    auto* symp = sympBuffer.data();
    std::fill (symp, symp + numSamples, 0.0f);

    sympathetic.setAmount (settings.sympathetic * (0.25f + 0.75f * pedal), sr);

    int count = 0;

    for (auto& v : voices)
    {
        if (! v.isActive())
            continue;

        v.render (left, right, numSamples, rng, settings.sympathetic > 0.001f ? symp : nullptr);
        ++count;
    }

    activeVoices = count;

    if (settings.sympathetic > 0.001f)
        sympathetic.process (symp, left, right, numSamples);


    for (int n = 0; n < numSamples; ++n)
    {
        float l = left[n], r = right[n];

        for (size_t i = 0; i < 3; ++i)
        {
            l = bodyL[i].processSample (l);
            r = bodyR[i].processSample (r);
        }

        left[n] = l;
        right[n] = r;
    }
}

} // namespace wp
