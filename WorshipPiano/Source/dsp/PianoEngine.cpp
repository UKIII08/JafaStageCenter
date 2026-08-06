#include "PianoEngine.h"

using namespace juce;

namespace wp
{

namespace
{
    inline double noteToHz (double midiNote) { return 440.0 * std::pow (2.0, (midiNote - 69.0) / 12.0); }
    inline float  lerp (float a, float b, float t) { return a + (b - a) * t; }

    /** Per sample multiplier that reaches -60 dB after t60 seconds. */
    inline float decayPerSample (float t60, double sampleRate)
    {
        return std::pow (10.0f, -3.0f / jmax (1.0f, (float) (jmax (0.01f, t60) * sampleRate)));
    }

    /** Ringing time of the fundamental: very long in the bass, short at the top. */
    inline float fundamentalT60 (int midiNote)
    {
        return 32.0f * std::exp (-0.026f * (float) (midiNote - 21));
    }

    /** How fast the damper kills the note once the key is released. */
    inline float damperT60 (int midiNote)
    {
        return jmax (0.06f, 0.38f * std::exp (-0.017f * (float) (midiNote - 21)));
    }

    /** Bass notes move more air than the top octave. */
    inline float registerGain (int midiNote)
    {
        return std::pow (10.0f, (-0.05f * (float) (midiNote - 60)) / 20.0f);
    }
}

//==============================================================================
const Voicing& voicingFor (int model)
{
    // tilt, tiltLoud, cutoffHz, cutoffOct, decay, inharm, strike, noise, thump
    static const Voicing voicings[4] =
    {
        // Smooth Grand - the default. Round, dark-ish attack, very long sustain.
        { 1.55f, 1.12f, 1250.0f, 2.15f, 1.15f, 0.85f, 0.125f, 0.30f, 0.55f },
        // Bright Grand - more upper partials, quicker felt, still a big piano.
        { 1.32f, 0.92f, 2100.0f, 2.30f, 1.00f, 1.00f, 0.115f, 0.45f, 0.50f },
        // Warm Upright - shorter strings, more stiffness, boxier and drier.
        { 1.48f, 1.10f, 1500.0f, 2.00f, 0.68f, 1.90f, 0.145f, 0.62f, 0.85f },
        // Felt - cloth over the hammers: dull, soft, short.
        { 1.95f, 1.62f,  620.0f, 1.15f, 0.86f, 0.85f, 0.135f, 0.55f, 0.75f },
    };

    return voicings[(size_t) jlimit (0, 3, model)];
}

//==============================================================================
void PianoVoice::reset()
{
    for (auto& p : partials)
        p = Partial();

    numPartials = numBeats = topActive = 0;
    noiseAmp = thumpAmp = 0.0f;
    active = keyHeld = sustained = sostenuto = false;
}

void PianoVoice::addPartial (int index, double freq, double sampleRate, float amp,
                             float t60, float fastFraction)
{
    auto& p = partials[(size_t) index];

    const double w = MathConstants<double>::twoPi * freq / sampleRate;
    p.cosW = (float) std::cos (w);
    p.sinW = (float) std::sin (w);

    // start the rotation at a random-ish phase so a chord does not build a
    // single fat click out of every partial starting at zero together
    const double phase = std::fmod (freq * 0.017, MathConstants<double>::twoPi);
    p.x = (float) std::cos (phase);
    p.y = (float) std::sin (phase);

    p.aFast = amp * fastFraction;
    p.aSlow = amp * (1.0f - fastFraction);
    p.dFast = decayPerSample (t60 * 0.30f, sampleRate);
    p.dSlow = decayPerSample (t60, sampleRate);
}

void PianoVoice::start (int midiNote, float velocity, const EngineSettings& s, double sampleRate)
{
    const auto& v = voicingFor (s.model);

    note = midiNote;
    active = true;
    keyHeld = true;
    sustained = sostenuto = false;

    const double f0 = noteToHz ((double) midiNote);
    const float vel = jlimit (0.03f, 1.0f, velocity);

    // ---- spectrum shape ---------------------------------------------------
    const float tone = jlimit (-1.0f, 1.0f, s.tone);

    // roll off exponent: small = bright, large = dark
    float tilt = lerp (v.tilt, v.tiltLoud, vel) - tone * 0.30f;
    tilt = jlimit (0.55f, 2.6f, tilt);

    // the felt lowpass: opens up with velocity, and the Tone knob slides it
    double cutoff = (double) v.cutoffHz * std::pow (2.0, (double) (v.cutoffOctaves * vel + tone * 1.25f));
    cutoff = jlimit (150.0, sampleRate * 0.40, cutoff);

    // string stiffness. Small numbers - this is the gentle stretch of a real
    // piano, not the metallic dispersion of a delay line.
    const double B = std::exp (-10.7 + 0.045 * (double) midiNote) * (double) v.inharmonicity;

    // Bass strings are excited into far more modes than treble ones, so the
    // roll off has to flatten out as you go down the keyboard. Without this the
    // bottom octaves are all fundamental and sound like an organ.
    tilt *= jmap (jlimit (0.0f, 1.0f, (float) (midiNote - 21) / 66.0f), 0.52f, 1.0f);

    const float alpha = v.strikePos;
    const float t60Base = fundamentalT60 (midiNote) * s.decayScale * v.decayScale;

    const double nyquist = sampleRate * 0.47;
    const int wanted = jlimit (6, maxPartials, (int) (12000.0 / f0));

    // ---- build the partials ------------------------------------------------
    std::array<double, maxPartials> freqs {};
    std::array<float, maxPartials> amps {};
    std::array<float, maxPartials> t60s {};

    int count = 0;
    double energy = 0.0;

    for (int k = 1; k <= wanted; ++k)
    {
        const double freq = (double) k * f0 * std::sqrt (1.0 + B * (double) k * (double) k);

        if (freq >= nyquist)
            break;

        // hammer strike position: partials with a node under the hammer are
        // weakened rather than removed - a real hammer is not a point
        const float strike = 0.24f + 0.76f * std::abs (std::sin ((float) k * MathConstants<float>::pi * alpha));

        const float roll = std::pow ((float) k, -tilt);
        const double r = freq / cutoff;
        const float felt = (float) (1.0 / (1.0 + r * r));

        // A soundboard is a poor radiator down at the bottom of its range. This
        // is why the lowest notes of a real piano get their pitch from the
        // second and third partial rather than from the fundamental.
        const float radiation = (float) (freq / (freq + 130.0));

        const float amp = strike * roll * felt * radiation;

        freqs[(size_t) count] = freq;
        amps[(size_t) count] = amp;
        t60s[(size_t) count] = jmax (0.12f, t60Base * std::pow ((float) k, -0.55f));

        energy += (double) amp * amp;
        ++count;
    }

    if (count == 0)
    {
        active = false;
        return;
    }

    // constant loudness whatever the spectrum looks like, so the Tone knob
    // changes colour and not level
    const float norm = (float) (1.0 / std::sqrt (jmax (1.0e-9, energy)));

    const float gainDb = (vel - 1.0f) * s.dynamicRange;
    amplitude = std::pow (10.0f, gainDb / 20.0f) * registerGain (midiNote) * 0.42f;

    numPartials = count;
    topActive = count;
    numBeats = jmin (maxBeats, count);

    // half a cent of unison detune - the slow shimmer of two strings pulling
    // against each other, and the reason a piano never sounds static
    const double detune = std::pow (2.0, 0.5 / 1200.0);

    for (int i = 0; i < count; ++i)
    {
        const int k = i + 1;
        const float fastFraction = jmax (0.15f, 0.52f - 0.028f * (float) (k - 1));
        const bool doubled = i < numBeats;
        const float share = doubled ? 0.62f : 1.0f;

        addPartial (i, freqs[(size_t) i], sampleRate, amps[(size_t) i] * norm * share,
                    t60s[(size_t) i], fastFraction);

        if (doubled)
            addPartial (maxPartials + i, freqs[(size_t) i] * detune, sampleRate,
                        amps[(size_t) i] * norm * 0.38f,
                        t60s[(size_t) i] * 1.18f, fastFraction);
    }

    // ---- attack transient --------------------------------------------------
    // Deliberately small. This is the sound of felt meeting wire, not a pluck.
    const float attackAmount = jlimit (0.0f, 1.0f, s.attack);

    noiseAmp = v.noise * attackAmount * std::pow (vel, 1.6f) * 0.14f;
    noiseDecay = decayPerSample (0.022f, sampleRate);
    noiseState = 0.0f;
    noiseCoef = (float) jlimit (0.02, 0.9, 1.0 - std::exp (-2.0 * MathConstants<double>::pi
                                                           * (700.0 + 2600.0 * vel) / sampleRate));

    thumpAmp = v.thump * attackAmount * vel * 0.05f;
    thumpDecay = decayPerSample (0.045f, sampleRate);
    thumpPhase = 0.0f;
    thumpInc = (float) (jmax (55.0, jmin (150.0, f0 * 1.4)) / sampleRate);

    // ---- placement ---------------------------------------------------------
    const float p = jlimit (-1.0f, 1.0f, ((float) midiNote - 60.0f) / 32.0f) * s.spread;
    const float angle = (p * 0.5f + 0.5f) * MathConstants<float>::halfPi;
    panL = std::cos (angle);
    panR = std::sin (angle);
}

void PianoVoice::release (bool pedalHeld, double sampleRate)
{
    keyHeld = false;

    if (pedalHeld || sostenuto)
    {
        sustained = true;
        return;
    }

    damp (sampleRate);
}

void PianoVoice::damp (double sampleRate)
{
    if (! active || keyHeld)
        return;

    sustained = false;

    const float d = decayPerSample (damperT60 (note), sampleRate);

    auto applyTo = [d] (Partial& p)
    {
        p.dFast = jmin (p.dFast, d);
        p.dSlow = jmin (p.dSlow, d);
    };

    for (int i = 0; i < numPartials; ++i)
        applyTo (partials[(size_t) i]);

    for (int i = 0; i < numBeats; ++i)
        applyTo (partials[(size_t) (maxPartials + i)]);
}

void PianoVoice::render (float* scratch, float* left, float* right, int numSamples, Random& rng)
{
    if (! active)
        return;

    std::fill (scratch, scratch + numSamples, 0.0f);

    auto renderPartial = [scratch, numSamples] (Partial& p)
    {
        if (p.aFast + p.aSlow < 1.0e-7f)
            return;

        float x = p.x, y = p.y, af = p.aFast, as = p.aSlow;
        const float c = p.cosW, s = p.sinW, df = p.dFast, ds = p.dSlow;

        for (int i = 0; i < numSamples; ++i)
        {
            const float nx = x * c - y * s;
            y = x * s + y * c;
            x = nx;

            scratch[i] += y * (af + as);

            af *= df;
            as *= ds;
        }

        // one Newton step back onto the unit circle: float rotation drifts, and
        // over a twenty second bass note that drift would be audible
        const float correction = 1.5f - 0.5f * (x * x + y * y);
        p.x = x * correction;
        p.y = y * correction;
        p.aFast = af;
        p.aSlow = as;
    };

    for (int i = 0; i < topActive; ++i)
        renderPartial (partials[(size_t) i]);

    for (int i = 0; i < numBeats; ++i)
        renderPartial (partials[(size_t) (maxPartials + i)]);

    // ---- attack transient --------------------------------------------------
    if (noiseAmp > 1.0e-6f || thumpAmp > 1.0e-6f)
    {
        for (int i = 0; i < numSamples; ++i)
        {
            if (noiseAmp > 1.0e-6f)
            {
                const float white = rng.nextFloat() * 2.0f - 1.0f;
                noiseState += noiseCoef * (white - noiseState);
                scratch[i] += noiseState * noiseAmp;
                noiseAmp *= noiseDecay;
            }

            if (thumpAmp > 1.0e-6f)
            {
                thumpPhase += thumpInc;
                if (thumpPhase >= 1.0f) thumpPhase -= 1.0f;

                scratch[i] += std::sin (thumpPhase * MathConstants<float>::twoPi) * thumpAmp;
                thumpAmp *= thumpDecay;
            }
        }
    }

    // ---- out ----------------------------------------------------------------
    const float gL = panL * amplitude;
    const float gR = panR * amplitude;

    for (int i = 0; i < numSamples; ++i)
    {
        left[i]  += scratch[i] * gL;
        right[i] += scratch[i] * gR;
    }

    // retire silent partials from the top so a long held bass note gets cheaper
    while (topActive > 1
           && partials[(size_t) (topActive - 1)].aFast + partials[(size_t) (topActive - 1)].aSlow < 1.0e-7f)
        --topActive;

    if (getLevel() < 1.0e-6f && noiseAmp < 1.0e-6f && thumpAmp < 1.0e-6f)
    {
        active = false;
        sustained = sostenuto = false;
    }
}

//==============================================================================
void PianoEngine::prepare (double sampleRate, int maxBlockSize)
{
    sr = sampleRate;
    scratch.assign ((size_t) jmax (64, maxBlockSize), 0.0f);

    // soundboard: a little warmth, a dip where a piano gets boxy, and some
    // definition where the hammers speak
    const std::array<float, 4> freqs { 120.0f, 260.0f, 700.0f, 2800.0f };
    const std::array<float, 4> qs    { 0.9f, 1.2f, 1.4f, 0.8f };
    const std::array<float, 4> gains { 1.20f, 1.15f, 0.82f, 1.15f };

    for (size_t i = 0; i < 4; ++i)
    {
        auto coeffs = dsp::IIR::Coefficients<float>::makePeakFilter (sampleRate, freqs[i], qs[i], gains[i]);
        bodyL[i].coefficients = coeffs;
        bodyR[i].coefficients = coeffs;
    }

    reset();
}

void PianoEngine::reset()
{
    for (auto& v : voices)
        v.reset();

    for (auto& f : bodyL) f.reset();
    for (auto& f : bodyR) f.reset();

    pedal = soft = 0.0f;
}

PianoVoice* PianoEngine::findVoiceToSteal (int midiNote)
{
    for (auto& v : voices)
        if (v.isActive() && v.getNote() == midiNote)
            return &v;

    for (auto& v : voices)
        if (! v.isActive())
            return &v;

    PianoVoice* best = nullptr;
    float lowest = std::numeric_limits<float>::max();

    for (auto& v : voices)
    {
        if (v.isHeld())
            continue;

        if (v.getLevel() < lowest)
        {
            lowest = v.getLevel();
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

    auto settingsForNote = settings;

    // the soft pedal moves the hammer sideways: quieter and noticeably darker
    if (soft > 0.001f)
        settingsForNote.tone -= 0.45f * soft;

    auto* voice = findVoiceToSteal (midiNote);
    voice->start (midiNote, velocity * (1.0f - 0.30f * soft), settingsForNote, sr);
    voice->startOrder = ++orderCounter;

    if (pedal >= 0.45f)
        voice->sustained = true;
}

void PianoEngine::noteOff (int midiNote)
{
    for (auto& v : voices)
        if (v.isActive() && v.isHeld() && v.getNote() == midiNote)
            v.release (pedal >= 0.45f, sr);
}

void PianoEngine::sustainPedal (float value)
{
    const float previous = pedal;
    pedal = jlimit (0.0f, 1.0f, value);

    if (previous >= 0.45f && pedal < 0.45f)
        for (auto& v : voices)
            if (v.isActive() && ! v.isHeld() && ! v.isSostenuto())
                v.damp (sr);
}

void PianoEngine::sostenutoPedal (bool down)
{
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
                    v.damp (sr);
            }
        }
    }
}

void PianoEngine::softPedal (float value) { soft = jlimit (0.0f, 1.0f, value); }

void PianoEngine::allNotesOff()
{
    for (auto& v : voices)
        if (v.isActive() && v.isHeld())
            v.release (pedal >= 0.45f, sr);
}

void PianoEngine::panic()
{
    for (auto& v : voices)
        v.reset();
}

void PianoEngine::render (float* left, float* right, int numSamples)
{
    if ((int) scratch.size() < numSamples)
        scratch.assign ((size_t) numSamples, 0.0f);

    for (auto& v : voices)
        v.render (scratch.data(), left, right, numSamples, rng);

    for (int n = 0; n < numSamples; ++n)
    {
        float l = left[n], r = right[n];

        for (size_t i = 0; i < 4; ++i)
        {
            l = bodyL[i].processSample (l);
            r = bodyR[i].processSample (r);
        }

        left[n] = l;
        right[n] = r;
    }
}

} // namespace wp
