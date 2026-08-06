#include "PadLayer.h"

using namespace juce;

namespace wp
{

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
    ignoreUnused (maxBlockSize);
    sr = sampleRate;
    lfoInc = (float) (0.07 / sampleRate);

    smoothedGain.reset (sampleRate, 0.055);
    smoothedGain.setCurrentAndTargetValue (0.0f);

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
    lfoPhase = 0.0f;
    dcL.reset();
    dcR.reset();
}

void PadLayer::noteOn (int midiNote, float velocity)
{
    Voice* voice = nullptr;

    for (auto& v : voices)
        if (v.active && v.note == midiNote)
            voice = &v;

    if (voice == nullptr)
        for (auto& v : voices)
            if (! v.active) { voice = &v; break; }

    if (voice == nullptr)
    {
        float quietest = std::numeric_limits<float>::max();

        for (auto& v : voices)
            if (! v.held && v.env < quietest) { quietest = v.env; voice = &v; }

        if (voice == nullptr)
            voice = &voices[0];
    }

    voice->note = midiNote;
    voice->active = true;
    voice->held = true;
    voice->sustained = false;
    voice->target = 1.0f;
    voice->velocity = jlimit (0.15f, 1.0f, velocity);
    voice->attackCoef = envCoefFor (settings.attackMs, sr);
    voice->releaseCoef = envCoefFor (settings.releaseMs, sr);

    const double base = noteToHz ((double) midiNote);
    static constexpr float spread[oscsPerVoice] = { 0.0f, -1.0f, 1.0f };

    for (int i = 0; i < oscsPerVoice; ++i)
    {
        const double f = base * std::pow (2.0, (spread[i] * settings.detuneCents) / 1200.0);
        voice->inc[(size_t) i] = (float) (f / sr);
    }

    const float p = jlimit (-1.0f, 1.0f, ((float) midiNote - 60.0f) / 36.0f) * 0.5f;
    const float angle = (p * 0.5f + 0.5f) * MathConstants<float>::halfPi;
    voice->panL = std::cos (angle);
    voice->panR = std::sin (angle);
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
        if (v.active) { v.held = false; v.sustained = false; v.target = 0.0f; }
}

/*  One oscillator per pad character. All of them are built out of the same
    band-limited saw so nothing aliases: folding a saw into a triangle keeps the
    band limiting, and subtracting a phase-shifted copy gives a pulse whose
    discontinuities are already corrected.
*/
inline float PadLayer::oscillator (float& phase, float inc) noexcept
{
    const float saw = polyBlepSaw (phase, inc);

    switch (settings.voice)
    {
        case PadVoice::softChoir:
        {
            // integrating a saw gives a triangle: same harmonics, falling off
            // an order faster, so it breathes instead of buzzing
            const float tri = 2.0f * std::abs (saw) - 1.0f;
            return 0.5f * tri + 0.2f * saw;
        }

        case PadVoice::glass:
        {
            // a touch of second harmonic to put a bell-like edge on top, where
            // it will sit above the piano rather than fight it
            const float second = 2.0f * saw * saw - 1.0f;
            return 0.72f * saw + 0.28f * second;
        }

        case PadVoice::airVox:
        {
            // a narrow pulse is saw minus a delayed saw; approximate the delay
            // with the squared term so the result stays band limited
            const float pulse = saw - (saw * std::abs (saw));
            return 1.35f * pulse;
        }

        case PadVoice::strings:
        case PadVoice::warmSaw:
        default:
            return saw;
    }
}

inline float PadLayer::polyBlepSaw (float& phase, float inc) noexcept
{
    phase += inc;

    if (phase >= 1.0f)
        phase -= 1.0f;

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

    for (int n = 0; n < numSamples; ++n)
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
                v.active = false;
                v.env = 0.0f;
                v.ic1L = v.ic2L = v.ic1R = v.ic2R = 0.0f;
                continue;
            }

            // the three detuned saws are spread hard across the field, which is
            // what turns a pad from a block in the middle into something you can
            // sit inside
            static constexpr float oscPanL[oscsPerVoice] = { 0.92f, 0.70f, 0.36f };
            static constexpr float oscPanR[oscsPerVoice] = { 0.36f, 0.70f, 0.92f };

            float oscL = 0.0f, oscR = 0.0f;

            for (int i = 0; i < oscsPerVoice; ++i)
            {
                const float osc = oscillator (v.phase[(size_t) i], v.inc[(size_t) i]);
                oscL += osc * oscPanL[i];
                oscR += osc * oscPanR[i];
            }

            constexpr float oscNorm = 1.0f / (float) oscsPerVoice;
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
        left[n]  += dcL.processSample (sumL * gain);
        right[n] += dcR.processSample (sumR * gain);
    }
}

} // namespace wp
