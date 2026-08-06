#include "Ambience.h"

using namespace juce;

namespace wp
{

namespace
{
    inline float onePole (double fc, double sampleRate)
    {
        return (float) jlimit (0.0, 0.999, 1.0 - std::exp (-2.0 * MathConstants<double>::pi * fc / sampleRate));
    }

    // Sixteen mutually prime-ish lengths in milliseconds. The spread matters
    // more than the absolute values: too close together and the tail rings.
    constexpr float tankLengthsMs[16] =
    {
        20.3f, 24.7f, 29.5f, 33.1f, 38.9f, 43.7f, 49.3f, 54.1f,
        60.7f, 65.3f, 71.9f, 77.3f, 83.9f, 90.1f, 97.7f, 104.3f
    };

    // Short, dense, prime-ish diffuser lengths.
    constexpr float diffuseLeftMs[4]  = {  4.77f,  9.31f, 15.73f, 22.13f };
    constexpr float diffuseRightMs[4] = {  5.41f, 10.19f, 17.11f, 24.29f };
}

//==============================================================================
const AmbienceMachine& machineFor (int index)
{
    // name, diffusion, stages, sizeScale, modDepth, modRate, damping, lowCut, bloomMs, shimmerScale
    static const AmbienceMachine machines[6] =
    {
        { "Room",    0.62f, 2, 0.40f,  1.5f, 0.35f, 0.55f, 120.0f,    0.0f, 0.6f },
        { "Hall",    0.70f, 3, 0.85f,  3.0f, 0.18f, 0.42f,  80.0f,   25.0f, 0.8f },
        { "Plate",   0.76f, 4, 0.55f,  2.0f, 0.55f, 0.30f, 180.0f,    0.0f, 0.9f },
        { "Cloud",   0.78f, 4, 1.15f,  9.0f, 0.09f, 0.50f,  60.0f,  120.0f, 1.0f },
        { "Bloom",   0.74f, 4, 1.00f,  6.0f, 0.13f, 0.46f,  70.0f,  650.0f, 1.0f },
        { "Shimmer", 0.75f, 4, 1.05f,  5.0f, 0.11f, 0.38f,  90.0f,  260.0f, 1.35f },
    };

    return machines[(size_t) jlimit (0, 5, index)];
}

int numMachines() { return 6; }

//==============================================================================
void PitchShifter::prepare (double sampleRate)
{
    // long grains: short ones chatter, and the whole point here is smoothness
    windowSamples = (float) (sampleRate * 0.085);
    line.prepare ((int) windowSamples * 2 + 128);
    reset();
}

void PitchShifter::reset()
{
    line.reset();
    readOffset = windowSamples * 0.5f;
}

float PitchShifter::process (float input) noexcept
{
    line.write (input);

    // shifting up means the read pointer must outrun the write pointer, so the
    // delay shrinks; shifting down means it grows
    readOffset -= step;

    if (readOffset < 0.0f)          readOffset += windowSamples;
    else if (readOffset >= windowSamples) readOffset -= windowSamples;

    const float d1 = readOffset + 2.0f;
    float o2 = readOffset + windowSamples * 0.5f;

    if (o2 >= windowSamples)
        o2 -= windowSamples;

    const float g1 = 0.5f * (1.0f - std::cos (MathConstants<float>::twoPi * readOffset / windowSamples));

    return line.read (d1) * g1 + line.read (o2 + 2.0f) * (1.0f - g1);
}

//==============================================================================
void Ambience::prepare (double sampleRate, int maxBlockSize)
{
    ignoreUnused (maxBlockSize);
    sr = sampleRate;

    for (int i = 0; i < numLines; ++i)
    {
        baseLength[(size_t) i] = (float) (tankLengthsMs[i] * 0.001 * sampleRate);
        lines[(size_t) i].prepare ((int) (baseLength[(size_t) i] * 2.2f) + 512);

        lfoPhase[(size_t) i] = (float) i * 0.0619f;
        lfoInc[(size_t) i] = (float) ((0.07 + 0.041 * (double) i) / sampleRate);
    }

    for (int i = 0; i < numDiffusers; ++i)
    {
        diffuseL[(size_t) i].prepare ((int) (diffuseLeftMs[i] * 0.001 * sampleRate) + 256);
        diffuseR[(size_t) i].prepare ((int) (diffuseRightMs[i] * 0.001 * sampleRate) + 256);
        diffusePhase[(size_t) i] = (float) i * 0.23f;
        diffuseInc[(size_t) i] = (float) ((0.11 + 0.07 * (double) i) / sampleRate);
    }

    const int maxPredelay = (int) (0.30 * sampleRate) + 128;
    predelayL.prepare (maxPredelay);
    predelayR.prepare (maxPredelay);

    shifterA.prepare (sampleRate);
    shifterB.prepare (sampleRate);

    for (int i = 0; i < 2; ++i)
    {
        shimmerDiffuse[(size_t) i].prepare ((int) ((0.021 + 0.013 * i) * sampleRate) + 128);
        shimmerDiffuse[(size_t) i].set ((float) ((0.021 + 0.013 * i) * sampleRate), 0.68f);
    }

    reset();
    setSettings (settings);
}

void Ambience::reset()
{
    for (auto& l : lines) l.reset();
    for (auto& d : diffuseL) d.reset();
    for (auto& d : diffuseR) d.reset();
    for (auto& d : shimmerDiffuse) d.reset();

    damper.fill (0.0f);
    lowCut.fill (0.0f);

    predelayL.reset();
    predelayR.reset();
    shifterA.reset();
    shifterB.reset();

    shimmerLP = shimmerHP = 0.0f;
    bloomEnv = duckEnv = 0.0f;
    freezeAmount = 0.0f;
}

void Ambience::updateFeedback()
{
    const auto& m = machineFor (settings.machine);
    const float scale = m.sizeScale * (0.45f + 1.25f * jlimit (0.0f, 1.0f, settings.size));

    for (int i = 0; i < numLines; ++i)
    {
        length[(size_t) i] = baseLength[(size_t) i] * scale;
        const float loop = length[(size_t) i] / (float) sr;
        feedback[(size_t) i] = jlimit (0.0f, 0.9993f,
                                       std::pow (10.0f, -3.0f * loop / jmax (0.2f, settings.decay)));
    }
}

void Ambience::setSettings (const AmbienceSettings& s)
{
    settings = s;

    const auto& m = machineFor (settings.machine);

    updateFeedback();

    // predelay grows with the room, which is what actually sells the size
    predelaySamples = jmax (1.0f, (float) ((0.008 + 0.075 * (double) settings.size) * sr));

    dampCoef = onePole (jmap (1.0 - (double) m.damping, 1200.0, 16000.0), sr);
    lowCutCoef = onePole ((double) m.lowCutHz, sr);
    modDepth = m.modDepth;

    for (int i = 0; i < numDiffusers; ++i)
    {
        const float gain = i < m.stages ? m.diffusion : 0.0f;
        diffuseL[(size_t) i].set ((float) (diffuseLeftMs[i] * 0.001 * sr), gain);
        diffuseR[(size_t) i].set ((float) (diffuseRightMs[i] * 0.001 * sr), gain);
    }

    // bloom: how long the wet takes to come up behind what you played
    bloomAttack = m.bloomMs < 1.0f ? 1.0f
                                   : 1.0f - std::exp (-1.0f / (float) (m.bloomMs * 0.001 * sr));
    bloomRelease = 1.0f - std::exp (-1.0f / (float) (0.35 * sr));

    switch (settings.shimmerMode)
    {
        case 1: shifterA.setRatio (2.0f); shifterB.setRatio (3.0f);  break;  // octave + fifth
        case 2: shifterA.setRatio (0.5f); shifterB.setRatio (0.5f);  break;  // octave down
        case 3: shifterA.setRatio (2.0f); shifterB.setRatio (0.5f);  break;  // both ways
        default: shifterA.setRatio (2.0f); shifterB.setRatio (2.0f); break;  // octave up
    }
}

void Ambience::process (const float* sendL, const float* sendR,
                        const float* dryL, const float* dryR,
                        float* outL, float* outR, int numSamples)
{
    const auto& m = machineFor (settings.machine);

    const float shimmerAmount = jlimit (0.0f, 1.0f, settings.shimmer) * m.shimmerScale;
    const bool  useShimmer = shimmerAmount > 0.001f;
    const bool  dualShimmer = settings.shimmerMode != 0 && settings.shimmerMode != 2;

    const float duckAmount = jlimit (0.0f, 1.0f, settings.duck);
    const float duckAttack = 1.0f - std::exp (-1.0f / (float) (0.008 * sr));
    const float duckRelease = 1.0f - std::exp (-1.0f / (float) (0.45 * sr));

    const float freezeTarget = settings.freeze ? 1.0f : 0.0f;
    const float freezeRate = 1.0f - std::exp (-1.0f / (float) (0.06 * sr));

    std::array<float, numLines> node {};

    for (int n = 0; n < numSamples; ++n)
    {
        // crossfade in and out of freeze so it never clicks
        freezeAmount += freezeRate * (freezeTarget - freezeAmount);
        const float inputGate = 1.0f - freezeAmount;

        // ---- input: predelay, then diffusion into a cloud -------------------
        predelayL.write (sendL[n] * inputGate);
        predelayR.write (sendR[n] * inputGate);

        float dl = predelayL.read (predelaySamples);
        float dr = predelayR.read (predelaySamples);

        for (int i = 0; i < numDiffusers; ++i)
        {
            diffusePhase[(size_t) i] += diffuseInc[(size_t) i];
            if (diffusePhase[(size_t) i] >= 1.0f) diffusePhase[(size_t) i] -= 1.0f;

            const float mod = std::sin (diffusePhase[(size_t) i] * MathConstants<float>::twoPi) * 1.6f;

            dl = diffuseL[(size_t) i].process (dl, mod);
            dr = diffuseR[(size_t) i].process (dr, -mod);
        }

        // ---- bloom: hold the transient back so the wash builds instead of -----
        // splashing. This has to shape what goes *into* the tank; putting it on
        // the output would gate the tail off the moment you stop playing.
        {
            const float drive = jmax (std::abs (sendL[n]), std::abs (sendR[n]));
            const float target = jmin (1.0f, drive * 9.0f);
            bloomEnv += (target > bloomEnv ? bloomAttack : bloomRelease) * (target - bloomEnv);
        }

        if (bloomAttack < 1.0f)
        {
            const float g = jlimit (0.0f, 1.0f, bloomEnv);
            dl *= g;
            dr *= g;
        }

        // ---- read the tank ---------------------------------------------------
        for (int i = 0; i < numLines; ++i)
        {
            lfoPhase[(size_t) i] += lfoInc[(size_t) i];
            if (lfoPhase[(size_t) i] >= 1.0f) lfoPhase[(size_t) i] -= 1.0f;

            const float mod = std::sin (lfoPhase[(size_t) i] * MathConstants<float>::twoPi) * modDepth;
            node[(size_t) i] = lines[(size_t) i].read (length[(size_t) i] + mod);
        }

        float wetL = 0.0f, wetR = 0.0f;

        for (int i = 0; i < numLines; ++i)
            ((i & 1) == 0 ? wetL : wetR) += node[(size_t) i];

        constexpr float outNorm = 0.25f;
        wetL *= outNorm;
        wetR *= outNorm;

        // ---- shimmer: pitch shift, diffuse again, filter, feed back ----------
        float shimmerIn = 0.0f;

        if (useShimmer)
        {
            const float mono = (wetL + wetR) * 0.5f;

            float shifted = shifterA.process (mono);

            if (dualShimmer)
                shifted = 0.6f * shifted + 0.6f * shifterB.process (mono);

            shifted = shimmerDiffuse[0].process (shifted);
            shifted = shimmerDiffuse[1].process (shifted);

            shimmerLP += 0.16f * (shifted - shimmerLP);
            shimmerHP += 0.004f * (shimmerLP - shimmerHP);

            // the saturator is what keeps an octave inside a feedback loop from
            // running away, and it also stops the shimmer sounding brittle
            shimmerIn = std::tanh ((shimmerLP - shimmerHP) * shimmerAmount * 0.85f) * 0.55f;
        }

        // ---- Hadamard mixing -------------------------------------------------
        for (int stride = 1; stride < numLines; stride <<= 1)
        {
            for (int i = 0; i < numLines; i += stride << 1)
            {
                for (int j = i; j < i + stride; ++j)
                {
                    const float a = node[(size_t) j];
                    const float b = node[(size_t) (j + stride)];
                    node[(size_t) j] = a + b;
                    node[(size_t) (j + stride)] = a - b;
                }
            }
        }

        constexpr float mixNorm = 0.25f;   // 1 / sqrt(16)

        for (int i = 0; i < numLines; ++i)
        {
            float v = node[(size_t) i] * mixNorm;

            damper[(size_t) i] += dampCoef * (v - damper[(size_t) i]);
            v = damper[(size_t) i];

            lowCut[(size_t) i] += lowCutCoef * (v - lowCut[(size_t) i]);
            v -= lowCut[(size_t) i];

            // freeze pushes the loop to unity and stops new energy going in
            const float g = feedback[(size_t) i] + (1.0f - feedback[(size_t) i]) * freezeAmount;

            const float src = (((i & 1) == 0 ? dl : dr) * 0.25f + shimmerIn) * inputGate;
            lines[(size_t) i].write (v * g + src);
        }

        // ---- duck: get out of the way while the piano is actually playing ----
        float duckGain = 1.0f;

        if (duckAmount > 0.001f)
        {
            const float level = jmax (std::abs (dryL[n]), std::abs (dryR[n]));
            duckEnv += (level > duckEnv ? duckAttack : duckRelease) * (level - duckEnv);
            duckGain = 1.0f - duckAmount * jlimit (0.0f, 1.0f, duckEnv * 4.0f);
        }

        outL[n] = wetL * duckGain;
        outR[n] = wetR * duckGain;
    }
}

} // namespace wp
