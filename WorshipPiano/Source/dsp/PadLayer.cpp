#include "PadLayer.h"

using namespace juce;

namespace wp
{

/*  31 tap windowed sinc, cut at 0.23 of the oversampled rate, Blackman window.
    Passes everything the host can represent and reaches about -70 dB by the
    point where anything left would fold back into the audible band.
*/
const std::array<float, PadLayer::decimatorTaps> PadLayer::Decimator::coefficients =
{
    -0.00000000f,  0.00008956f, -0.00002577f, -0.00106467f,
    -0.00041795f,  0.00393584f,  0.00302363f, -0.00972598f,
    -0.01142163f,  0.01851522f,  0.03245010f, -0.02860947f,
    -0.08378579f,  0.03682480f,  0.31019215f,  0.46003991f,
     0.31019215f,  0.03682480f, -0.08378579f, -0.02860947f,
     0.03245010f,  0.01851522f, -0.01142163f, -0.00972598f,
     0.00302363f,  0.00393584f, -0.00041795f, -0.00106467f,
    -0.00002577f,  0.00008956f, -0.00000000f
};

namespace
{
    inline double noteToHz (double n) { return 440.0 * std::pow (2.0, (n - 69.0) / 12.0); }

    inline float envCoefFor (float ms, double sampleRate)
    {
        return 1.0f - std::exp (-1.0f / jmax (1.0f, (float) (ms * 0.001 * sampleRate)));
    }
}

void PadLayer::prepare (double sampleRate, int maxBlockSize)
{
    // everything inside this class runs at the oversampled rate, so every
    // envelope and phase increment derived from sr stays correct on its own
    sr = sampleRate * oversample;
    lfoInc = (float) (0.07 / sr);

    smoothedGain.reset (sr, 0.055);
    smoothedGain.setCurrentAndTargetValue (0.0f);

    scratchL.assign ((size_t) jmax (1, maxBlockSize) * oversample, 0.0f);
    scratchR.assign (scratchL.size(), 0.0f);

    // the DC blocker sits after the rate comes back down, where it belongs:
    // it is correcting the host's output, not the oscillators
    auto hp = dsp::IIR::Coefficients<float>::makeHighPass (sampleRate, 30.0f);
    dcL.coefficients = hp;
    dcR.coefficients = hp;

    reset();
}

void PadLayer::reset()
{
    for (auto& v : voices)
    {
        v = Voice();
        for (int i = 0; i < oscsPerVoice; ++i)
            v.phase[(size_t) i] = Random::getSystemRandom().nextFloat();
    }

    pedalDown = false;
    hijacked = stolen = 0;
    lfoPhase = 0.0f;
    decimateL.reset();
    decimateR.reset();
    dcL.reset();
    dcR.reset();
}

void PadLayer::startNote (Voice& v, int midiNote, float velocity)
{
    /*  Starting a note on a voice that is still sounding is exactly the blip
        this design exists to avoid, so it is counted rather than left to be
        noticed by ear on a Sunday. Re-triggering the same note is fine - that
        keeps the pitch it already had.
    */
    if (v.env > 1.0e-3f && v.note != midiNote)
        ++hijacked;

    v.note = midiNote;
    v.active = true;
    v.held = true;
    v.sustained = false;
    v.stealing = false;
    v.pendingNote = -1;
    v.target = 1.0f;
    v.velocity = jlimit (0.15f, 1.0f, velocity);
    v.attackCoef = envCoefFor (settings.attackMs, sr);
    v.releaseCoef = envCoefFor (settings.releaseMs, sr);

    const double base = noteToHz ((double) midiNote);

    /*  Szabo's offsets: deliberately not evenly spaced, which is what stops the
        seven collapsing into a single audible beat rate the way an even spread
        does. Ratios preserved exactly; only how far they are driven is ours.
    */
    static constexpr float offsets[oscsPerVoice] = {
        -0.11002313f, -0.06288439f, -0.01952356f, 0.0f,
         0.01991221f,  0.06216538f,  0.10745242f
    };

    /*  The detune knob in the original runs 0..1 and reaches nearly two
        semitones wide at the top - a trance lead, not something to put under a
        congregation. The pad's cents setting is mapped into the lower part of
        that range, so the character stays a bed and the outer pair lands around
        a quarter tone out at the widest preset.
    */
    const float x = jlimit (0.0f, 0.75f, settings.detuneCents / 45.0f);

    for (int i = 0; i < oscsPerVoice; ++i)
        v.inc[(size_t) i] = (float) (base * (1.0 + offsets[i] * x) / sr);

    const float p = jlimit (-1.0f, 1.0f, ((float) midiNote - 60.0f) / 36.0f) * 0.5f;
    const float angle = (p * 0.5f + 0.5f) * MathConstants<float>::halfPi;
    v.panL = std::cos (angle);
    v.panR = std::sin (angle);
}

void PadLayer::noteOn (int midiNote, float velocity)
{
    // the same note again: keep the voice it already has, so repeating a chord
    // thickens it rather than starting a second copy beating against the first
    for (auto& v : voices)
    {
        if (v.active && v.note == midiNote && ! v.stealing)
        {
            startNote (v, midiNote, velocity);
            return;
        }
    }

    for (auto& v : voices)
    {
        if (! v.active)
        {
            v.env = 0.0f;
            v.ic1L = v.ic2L = v.ic1R = v.ic2R = 0.0f;
            startNote (v, midiNote, velocity);
            return;
        }
    }

    /*  Everything is busy. Pick the quietest voice that is not under a finger
        and fade it out rather than repitching it where it stands: the new note
        starts from silence a few milliseconds later, in render(), once the old
        one has actually gone.
    */
    Voice* victim = nullptr;
    float quietest = std::numeric_limits<float>::max();

    for (auto& v : voices)
        if (! v.held && ! v.stealing && v.env < quietest) { quietest = v.env; victim = &v; }

    // every voice held down, or already fading: take the quietest of all of them
    if (victim == nullptr)
    {
        quietest = std::numeric_limits<float>::max();

        for (auto& v : voices)
            if (v.env < quietest) { quietest = v.env; victim = &v; }
    }

    if (victim == nullptr)
        return;

    // already silent: nothing to fade, start straight away
    if (victim->env < 1.0e-4f)
    {
        victim->env = 0.0f;
        victim->ic1L = victim->ic2L = victim->ic1R = victim->ic2R = 0.0f;
        startNote (*victim, midiNote, velocity);
        return;
    }

    ++stolen;

    victim->stealing = true;
    victim->held = false;
    victim->sustained = false;
    victim->target = 0.0f;
    victim->releaseCoef = envCoefFor (stealFadeMs, sr);
    victim->pendingNote = midiNote;
    victim->pendingVelocity = velocity;
}

void PadLayer::noteOff (int midiNote)
{
    for (auto& v : voices)
    {
        if (v.active && v.held && v.note == midiNote)
        {
            v.held = false;

            if (pedalDown)
                v.sustained = true;
            else
                v.target = 0.0f;
        }
    }
}

void PadLayer::sustainPedal (bool down)
{
    pedalDown = down;

    if (! down)
        for (auto& v : voices)
            if (v.sustained) { v.sustained = false; v.target = 0.0f; }
}

void PadLayer::allNotesOff()
{
    for (auto& v : voices)
    {
        if (! v.active)
            continue;

        v.held = false;
        v.sustained = false;
        v.target = 0.0f;

        // a note waiting behind a fade must not arrive after everything was
        // told to stop
        v.stealing = false;
        v.pendingNote = -1;
    }
}

/*  Every character is built out of band-limited saws and nothing else.

    A polyBLEP saw has no energy above Nyquist. Multiplying one by itself does -
    squaring doubles the bandwidth, and folding through abs() is a corner, which
    has no bandwidth limit at all. Both of those were how the triangle and the
    pulse used to be made, and both folded energy back down between the
    harmonics, which is heard as grit rather than as brightness.

    A square is two saws half a period apart. A pulse is two saws a fraction of
    a period apart. A triangle is the integral of a square. All three inherit the
    saw's band limiting instead of destroying it, and none of them costs more
    than the multiply they replace.
*/
inline float PadLayer::polyBlepSawAt (float phase, float inc) noexcept
{
    float value = 2.0f * phase - 1.0f;

    // polyBLEP correction around the discontinuity
    if (phase < inc)
    {
        const float t = phase / inc;
        value -= t + t - t * t - 1.0f;
    }
    else if (phase > 1.0f - inc)
    {
        const float t = (phase - 1.0f) / inc;
        value -= t * t + t + t + 1.0f;
    }

    return value;
}

inline float PadLayer::oscillator (float& phase, float inc, float& integrator) noexcept
{
    phase += inc;

    if (phase >= 1.0f)
        phase -= 1.0f;

    const float saw = polyBlepSawAt (phase, inc);

    auto shifted = [phase] (float by)
    {
        float p = phase + by;
        return p >= 1.0f ? p - 1.0f : p;
    };

    switch (settings.voice)
    {
        case PadVoice::softChoir:
        {
            // square, then integrated: a triangle whose harmonics fall away an
            // order faster than a saw's, so it breathes instead of buzzing
            const float square = saw - polyBlepSawAt (shifted (0.5f), inc);

            integrator += 4.0f * inc * square;
            integrator -= 0.0004f * integrator;      // leak, or DC walks away

            return 1.05f * integrator + 0.12f * saw;
        }

        case PadVoice::glass:
        {
            // a touch of second harmonic puts a bell-like edge on top, where it
            // sits above the piano rather than fighting it. Squaring is smooth -
            // no corner - so oversampling is enough to keep it clean.
            const float second = 2.0f * saw * saw - 1.0f;
            return 0.72f * saw + 0.28f * second;
        }

        case PadVoice::airVox:
        {
            // a genuinely narrow pulse: two saws a sixth of a period apart
            const float pulse = saw - polyBlepSawAt (shifted (0.16f), inc);
            return 1.25f * pulse;
        }

        case PadVoice::strings:
        case PadVoice::warmSaw:
        default:
            return saw;
    }
}

void PadLayer::render (float* left, float* right, int numSamples)
{
    // calibrated so that a Pad setting of 0 dB puts the layer at roughly the
    // same level as the piano: the knob then reads as dB below the instrument
    smoothedGain.setTargetValue (settings.level * 1.40f);

    if (settings.level <= 1.0e-5f && ! smoothedGain.isSmoothing())
    {
        bool anyRinging = false;

        for (auto& v : voices)
            if (v.active && v.env > 1.0e-4f) { anyRinging = true; break; }

        if (! anyRinging)
        {
            for (auto& v : voices)
                if (v.active && v.target <= 0.0f) v.active = false;

            return;
        }
    }

    const float res = 0.85f;                       // gentle, no self oscillation
    const float k = 1.0f / jmax (0.05f, res);

    // same mapping as startNote uses, so the gain balance matches the spread
    const float padDetune = jlimit (0.0f, 0.75f, settings.detuneCents / 45.0f);

    const int oversampled = numSamples * oversample;

    if ((int) scratchL.size() < oversampled)
    {
        scratchL.assign ((size_t) oversampled, 0.0f);
        scratchR.assign ((size_t) oversampled, 0.0f);
    }

    for (int n = 0; n < oversampled; ++n)
    {
        lfoPhase += lfoInc;
        if (lfoPhase >= 1.0f) lfoPhase -= 1.0f;

        const float lfo = std::sin (lfoPhase * MathConstants<float>::twoPi);
        const float baseCutoff = jlimit (60.0f, (float) (sr * 0.45),
                                         settings.cutoffHz * (1.0f + 0.12f * lfo));

        float sumL = 0.0f, sumR = 0.0f;

        for (auto& v : voices)
        {
            if (! v.active)
                continue;

            const float coef = v.target > 0.5f ? v.attackCoef : v.releaseCoef;
            v.env += coef * (v.target - v.env);

            // the filter opens as the note swells in, so the pad grows rather
            // than simply getting louder
            const float cutoff = jlimit (60.0f, (float) (sr * 0.45),
                                         baseCutoff * (0.32f + 0.68f * v.env));
            const float g = std::tan (MathConstants<float>::pi * cutoff / (float) sr);
            const float a1 = 1.0f / (1.0f + g * (g + k));

            if (v.target <= 0.0f && v.env < 1.0e-4f)
            {
                v.env = 0.0f;
                v.ic1L = v.ic2L = v.ic1R = v.ic2R = 0.0f;

                // the voice was taken for a new note: it has faded, so the new
                // one can start now, from silence and with its own attack
                if (v.stealing && v.pendingNote >= 0)
                {
                    for (auto& ph : v.phase)
                        ph = Random::getSystemRandom().nextFloat();

                    startNote (v, v.pendingNote, v.pendingVelocity);
                    continue;
                }

                v.active = false;
                v.stealing = false;
                v.pendingNote = -1;
                continue;
            }

            // the three detuned saws are spread hard across the field, which is
            // what turns a pad from a block in the middle into something you can
            // sit inside
            /*  Panned by how far each one is detuned: the centre oscillator sits
                dead centre and the pairs open outwards. Every oscillator is on a
                different frequency, so none of this cancels when a mono desk
                sums the two sides - the width comes from the spread, not from
                phase tricks that fall apart downstream.
            */
            static constexpr float oscPanL[oscsPerVoice] =
                { 0.97f, 0.86f, 0.75f, 0.7071f, 0.66f, 0.51f, 0.24f };
            static constexpr float oscPanR[oscsPerVoice] =
                { 0.24f, 0.51f, 0.66f, 0.7071f, 0.75f, 0.86f, 0.97f };

            // Szabo again: the centre falls away and the sides come up as the
            // detune widens, which is what keeps a wide setting from turning
            // into mush with no note left in the middle of it
            const float centreGain = -0.55366f * padDetune + 0.99785f;
            const float sideGain = -0.73764f * padDetune * padDetune
                                 +  1.28410f * padDetune + 0.044372f;

            float oscL = 0.0f, oscR = 0.0f;

            for (int i = 0; i < oscsPerVoice; ++i)
            {
                const float osc = oscillator (v.phase[(size_t) i], v.inc[(size_t) i],
                                              v.integrator[(size_t) i]);
                const float g = (i == oscsPerVoice / 2) ? centreGain : sideGain;

                oscL += osc * g * oscPanL[i];
                oscR += osc * g * oscPanR[i];
            }

            // normalised by what the gains actually sum to, so widening the
            // detune does not also make the pad louder
            const float oscNorm = 1.0f / jmax (0.5f, centreGain + 6.0f * sideGain);
            oscL *= oscNorm;
            oscR *= oscNorm;

            // TPT state variable lowpass, per side
            const float hpL = (oscL - (k + g) * v.ic1L - v.ic2L) * a1;
            const float bpL = g * hpL + v.ic1L;
            v.ic1L = g * hpL + bpL;
            const float lpL = g * bpL + v.ic2L;
            v.ic2L = g * bpL + lpL;

            const float hpR = (oscR - (k + g) * v.ic1R - v.ic2R) * a1;
            const float bpR = g * hpR + v.ic1R;
            v.ic1R = g * hpR + bpR;
            const float lpR = g * bpR + v.ic2R;
            v.ic2R = g * bpR + lpR;

            const float shape = v.env * v.env * v.velocity;

            sumL += lpL * shape * v.panL;
            sumR += lpR * shape * v.panR;
        }

        const float gain = smoothedGain.getNextValue();
        scratchL[(size_t) n] = sumL * gain;
        scratchR[(size_t) n] = sumR * gain;
    }

    /*  Back down to the host's rate. The filter sees every oversampled sample -
        that is what removes the folded energy - but only every second result is
        kept, which is the decimation itself.
    */
    for (int n = 0; n < numSamples; ++n)
    {
        float outL = 0.0f, outR = 0.0f;

        for (int k2 = 0; k2 < oversample; ++k2)
        {
            outL = decimateL.process (scratchL[(size_t) (n * oversample + k2)]);
            outR = decimateR.process (scratchR[(size_t) (n * oversample + k2)]);
        }

        left[n]  += dcL.processSample (outL);
        right[n] += dcR.processSample (outR);
    }
}

} // namespace wp
