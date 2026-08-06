#include "EffectChain.h"

using namespace juce;

namespace wp
{

namespace
{
    inline float onePole (double fc, double sampleRate)
    {
        return (float) jlimit (0.0, 0.999, 1.0 - std::exp (-2.0 * MathConstants<double>::pi * fc / sampleRate));
    }

    /** Safety soft clip: transparent below -3 dBFS, catches the peaks that a long
        reverb tail stacked on a big chord can throw at the converter. */
    inline float softClip (float x) noexcept
    {
        constexpr float knee = 0.7f;

        if (x > -knee && x < knee)
            return x;

        const float sign = x < 0.0f ? -1.0f : 1.0f;
        return sign * (knee + (1.0f - knee) * std::tanh ((std::abs (x) - knee) / (1.0f - knee)));
    }
}

//==============================================================================
void OctaveShifter::prepare (double sampleRate)
{
    windowSamples = (float) (sampleRate * 0.045);   // ~45 ms grains
    line.prepare ((int) windowSamples * 2 + 64);
    reset();
}

void OctaveShifter::reset()
{
    line.reset();
    readOffset = windowSamples * 0.5f;
}

float OctaveShifter::process (float input) noexcept
{
    line.write (input);

    // one octave up means the read pointer has to travel twice as fast, i.e.
    // the delay shrinks by exactly one sample per sample
    readOffset -= 1.0f;

    if (readOffset < 0.0f)
        readOffset += windowSamples;

    const float d1 = readOffset + 2.0f;
    float o2 = readOffset + windowSamples * 0.5f;

    if (o2 >= windowSamples)
        o2 -= windowSamples;

    const float d2 = o2 + 2.0f;

    const float g1 = 0.5f * (1.0f - std::cos (MathConstants<float>::twoPi * readOffset / windowSamples));

    return line.read (d1) * g1 + line.read (d2) * (1.0f - g1);
}

//==============================================================================
void Reverb::prepare (double sampleRate, int maxBlockSize)
{
    ignoreUnused (maxBlockSize);
    sr = sampleRate;

    // mutually prime-ish lengths keep the modal density smooth
    static constexpr float lengthsMs[numLines] = { 23.7f, 29.3f, 37.1f, 43.7f, 53.3f, 61.9f, 71.3f, 79.7f };

    for (int i = 0; i < numLines; ++i)
    {
        baseLength[(size_t) i] = (float) (lengthsMs[i] * 0.001 * sampleRate);
        lines[(size_t) i].prepare ((int) (baseLength[(size_t) i] * 1.8f) + 256);
        lfoPhase[(size_t) i] = (float) i / (float) numLines;
        lfoInc[(size_t) i] = (float) ((0.09 + 0.037 * i) / sampleRate);
    }

    const int maxPredelay = (int) (0.25 * sampleRate) + 64;
    predelayL.prepare (maxPredelay);
    predelayR.prepare (maxPredelay);

    shifter.prepare (sampleRate);
    shimmerLP.coefficients = dsp::IIR::Coefficients<float>::makeLowPass (sampleRate, 3800.0f);

    reset();
    setParameters (sizeAmount, decayTime, toneAmount, 20.0f, 0.0f);
}

void Reverb::reset()
{
    for (auto& l : lines) l.reset();
    damper.fill (0.0f);
    lowCut.fill (0.0f);
    predelayL.reset();
    predelayR.reset();
    shifter.reset();
    shimmerLP.reset();
    shimmerState = 0.0f;
}

void Reverb::setParameters (float size, float decaySeconds, float tone, float predelayMs, float shimmerAmount)
{
    sizeAmount = jlimit (0.0f, 1.0f, size);
    decayTime = jmax (0.2f, decaySeconds);
    toneAmount = jlimit (0.0f, 1.0f, tone);
    shimmer = jlimit (0.0f, 1.0f, shimmerAmount);
    predelaySamples = jmax (1.0f, (float) (predelayMs * 0.001 * sr));

    const float scale = 0.45f + sizeAmount * 1.15f;

    for (int i = 0; i < numLines; ++i)
    {
        currentLength[(size_t) i] = baseLength[(size_t) i] * scale;
        const float loops = currentLength[(size_t) i] / (float) sr;
        feedback[(size_t) i] = jlimit (0.0f, 0.9995f, std::pow (10.0f, -3.0f * loops / decayTime));
    }

    dampCoef = onePole (jmap ((double) toneAmount, 1400.0, 15000.0), sr);
    lowCutCoef = onePole (jmap (1.0 - (double) toneAmount, 40.0, 320.0), sr);
}

void Reverb::process (float* left, float* right, int numSamples)
{
    std::array<float, numLines> node {};

    for (int n = 0; n < numSamples; ++n)
    {
        predelayL.write (left[n]);
        predelayR.write (right[n]);

        const float inL = predelayL.read (predelaySamples);
        const float inR = predelayR.read (predelaySamples);

        // --- read the network -------------------------------------------------
        for (int i = 0; i < numLines; ++i)
        {
            lfoPhase[(size_t) i] += lfoInc[(size_t) i];
            if (lfoPhase[(size_t) i] >= 1.0f) lfoPhase[(size_t) i] -= 1.0f;

            const float mod = std::sin (lfoPhase[(size_t) i] * MathConstants<float>::twoPi)
                              * (2.0f + 5.0f * sizeAmount);

            node[(size_t) i] = lines[(size_t) i].read (currentLength[(size_t) i] + mod);
        }

        float outL = 0.0f, outR = 0.0f;

        for (int i = 0; i < numLines; ++i)
            ((i & 1) == 0 ? outL : outR) += node[(size_t) i];

        outL *= 0.35f;
        outR *= 0.35f;

        // --- octave up fed back into the tail ---------------------------------
        float shimmerIn = 0.0f;

        if (shimmer > 0.001f)
        {
            const float mono = (outL + outR) * 0.5f;
            shimmerState = shimmerLP.processSample (shifter.process (mono));
            shimmerIn = shimmerState * shimmer * 0.42f;
        }

        // --- Hadamard mixing (in place butterflies) ---------------------------
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

        constexpr float norm = 0.35355339f;   // 1 / sqrt(8)

        for (int i = 0; i < numLines; ++i)
        {
            float v = node[(size_t) i] * norm;

            // damping
            damper[(size_t) i] += dampCoef * (v - damper[(size_t) i]);
            v = damper[(size_t) i];

            // low cut, so the tail does not turn into mud
            lowCut[(size_t) i] += lowCutCoef * (v - lowCut[(size_t) i]);
            v -= lowCut[(size_t) i];

            v *= feedback[(size_t) i];

            const float src = ((i & 1) == 0 ? inL : inR) * 0.5f + shimmerIn;
            lines[(size_t) i].write (v + src);
        }

        left[n] = outL;
        right[n] = outR;
    }
}

//==============================================================================
void StereoDelay::prepare (double sampleRate, int)
{
    sr = sampleRate;
    const int maxSamples = (int) (sampleRate * 2.5) + 64;
    lineL.prepare (maxSamples);
    lineR.prepare (maxSamples);
    reset();
}

void StereoDelay::reset()
{
    lineL.reset();
    lineR.reset();
    lpL = lpR = hpL = hpR = 0.0f;
    currentL = targetL;
    currentR = targetR;
}

void StereoDelay::setParameters (float delaySamplesL, float delaySamplesR, float fb, float tone, float pingPong)
{
    targetL = jlimit (8.0f, (float) lineL.getSize() - 8.0f, delaySamplesL);
    targetR = jlimit (8.0f, (float) lineR.getSize() - 8.0f, delaySamplesR);
    feedback = jlimit (0.0f, 0.95f, fb);
    pingPongAmount = jlimit (0.0f, 1.0f, pingPong);

    lpCoef = onePole (jmap ((double) jlimit (0.0f, 1.0f, tone), 900.0, 12000.0), sr);
    hpCoef = onePole (jmap (1.0 - (double) jlimit (0.0f, 1.0f, tone), 60.0, 500.0), sr);
}

void StereoDelay::process (float* left, float* right, int numSamples, float mix)
{
    if (mix <= 0.0001f)
    {
        // keep the lines fed so turning the knob up does not reveal old audio
        for (int n = 0; n < numSamples; ++n) { lineL.write (0.0f); lineR.write (0.0f); }
        return;
    }

    for (int n = 0; n < numSamples; ++n)
    {
        currentL += 0.0004f * (targetL - currentL);
        currentR += 0.0004f * (targetR - currentR);

        float dl = lineL.read (currentL);
        float dr = lineR.read (currentR);

        lpL += lpCoef * (dl - lpL);  dl = lpL;
        lpR += lpCoef * (dr - lpR);  dr = lpR;
        hpL += hpCoef * (dl - hpL);  dl -= hpL;
        hpR += hpCoef * (dr - hpR);  dr -= hpR;

        const float crossL = dl * (1.0f - pingPongAmount) + dr * pingPongAmount;
        const float crossR = dr * (1.0f - pingPongAmount) + dl * pingPongAmount;

        lineL.write (left[n] + crossL * feedback);
        lineR.write (right[n] + crossR * feedback);

        left[n]  += dl * mix;
        right[n] += dr * mix;
    }
}

//==============================================================================
void Ensemble::prepare (double sampleRate)
{
    sr = sampleRate;
    lineL.prepare ((int) (sampleRate * 0.06) + 64);
    lineR.prepare ((int) (sampleRate * 0.06) + 64);
    reset();
}

void Ensemble::reset()
{
    lineL.reset();
    lineR.reset();
    phase = 0.0f;
}

void Ensemble::setParameters (float a, float rateHz)
{
    amount = jlimit (0.0f, 1.0f, a);
    inc = (float) (jlimit (0.01f, 8.0f, rateHz) / sr);
}

void Ensemble::process (float* left, float* right, int numSamples)
{
    if (amount <= 0.0005f)
    {
        for (int n = 0; n < numSamples; ++n) { lineL.write (left[n]); lineR.write (right[n]); }
        return;
    }

    const float baseDelay = (float) (0.011 * sr);
    const float depth = (float) (0.0035 * sr) * amount;
    const float wet = amount * 0.5f;

    for (int n = 0; n < numSamples; ++n)
    {
        phase += inc;
        if (phase >= 1.0f) phase -= 1.0f;

        const float a = std::sin (phase * MathConstants<float>::twoPi);
        const float b = std::sin ((phase + 0.25f) * MathConstants<float>::twoPi);

        lineL.write (left[n]);
        lineR.write (right[n]);

        const float wl = lineL.read (baseDelay + depth * a);
        const float wr = lineR.read (baseDelay + depth * b);

        left[n]  = left[n]  * (1.0f - wet * 0.5f) + wl * wet;
        right[n] = right[n] * (1.0f - wet * 0.5f) + wr * wet;
    }
}

//==============================================================================
void EffectChain::prepare (double sampleRate, int maxBlockSize)
{
    sr = sampleRate;

    dsp::ProcessSpec spec { sampleRate, (uint32) maxBlockSize, 2 };

    compressor.prepare (spec);
    compressor.setAttack (12.0f);
    compressor.setRelease (180.0f);

    oversampling = std::make_unique<dsp::Oversampling<float>> (
        2, 1, dsp::Oversampling<float>::filterHalfBandPolyphaseIIR, true, false);
    oversampling->initProcessing ((size_t) maxBlockSize);

    ensemble.prepare (sampleRate);
    delay.prepare (sampleRate, maxBlockSize);
    reverb.prepare (sampleRate, maxBlockSize);

    dryBuffer.setSize (2, maxBlockSize, false, false, true);
    wetBuffer.setSize (2, maxBlockSize, false, false, true);

    filtersDirty = true;
    updateFilters();
    reset();
}

void EffectChain::reset()
{
    for (auto& f : lowShelf)  f.reset();
    for (auto& f : midPeak)   f.reset();
    for (auto& f : highShelf) f.reset();
    for (auto& f : airShelf)  f.reset();
    for (auto& f : rumbleCut) f.reset();

    compressor.reset();

    if (oversampling != nullptr)
        oversampling->reset();

    ensemble.reset();
    delay.reset();
    reverb.reset();

    driveState.fill (0.0f);
    gainReduction = 0.0f;
    smoothedOutput = settings.outputGain;
}

void EffectChain::setSettings (const EffectSettings& s)
{
    const bool eqChanged = s.eqLow != settings.eqLow || s.eqMid != settings.eqMid
                        || s.eqHigh != settings.eqHigh || s.eqAir != settings.eqAir;

    settings = s;

    if (eqChanged || filtersDirty)
        updateFilters();

    const float thresholdDb = jmap (settings.compAmount, 0.0f, 1.0f, -6.0f, -34.0f);
    const float ratio = jmap (settings.compAmount, 0.0f, 1.0f, 1.2f, 5.5f);
    compressor.setThreshold (thresholdDb);
    compressor.setRatio (ratio);

    ensemble.setParameters (settings.chorusAmount, settings.chorusRate);
    delay.setParameters (settings.delaySamplesL, settings.delaySamplesR,
                         settings.delayFeedback, settings.delayTone, settings.delayPingPong);
    reverb.setParameters (settings.reverbSize, settings.reverbDecay, settings.reverbTone,
                          settings.reverbPredelay, settings.shimmer);
}

void EffectChain::updateFilters()
{
    auto low  = dsp::IIR::Coefficients<float>::makeLowShelf  (sr, 180.0f, 0.7f, Decibels::decibelsToGain (settings.eqLow));
    auto mid  = dsp::IIR::Coefficients<float>::makePeakFilter (sr, 900.0f, 0.8f, Decibels::decibelsToGain (settings.eqMid));
    auto high = dsp::IIR::Coefficients<float>::makeHighShelf (sr, 3600.0f, 0.7f, Decibels::decibelsToGain (settings.eqHigh));
    auto air  = dsp::IIR::Coefficients<float>::makeHighShelf (sr, (float) jmin (14000.0, sr * 0.42), 0.6f,
                                                              Decibels::decibelsToGain (settings.eqAir));
    auto rumble = dsp::IIR::Coefficients<float>::makeHighPass (sr, 26.0f);

    for (int ch = 0; ch < 2; ++ch)
    {
        lowShelf[(size_t) ch].coefficients  = low;
        midPeak[(size_t) ch].coefficients   = mid;
        highShelf[(size_t) ch].coefficients = high;
        airShelf[(size_t) ch].coefficients  = air;
        rumbleCut[(size_t) ch].coefficients = rumble;
    }

    filtersDirty = false;
}

void EffectChain::process (AudioBuffer<float>& buffer)
{
    const int numSamples = buffer.getNumSamples();
    const int numChannels = jmin (2, buffer.getNumChannels());

    if (numSamples <= 0)
        return;

    if (dryBuffer.getNumSamples() < numSamples)
    {
        dryBuffer.setSize (2, numSamples, false, false, true);
        wetBuffer.setSize (2, numSamples, false, false, true);
    }

    auto* l = buffer.getWritePointer (0);
    auto* r = numChannels > 1 ? buffer.getWritePointer (1) : l;

    // ---- tone ---------------------------------------------------------------
    for (int ch = 0; ch < numChannels; ++ch)
    {
        auto* d = buffer.getWritePointer (ch);
        const size_t c = (size_t) ch;

        for (int n = 0; n < numSamples; ++n)
        {
            float x = rumbleCut[c].processSample (d[n]);
            x = lowShelf[c].processSample (x);
            x = midPeak[c].processSample (x);
            x = highShelf[c].processSample (x);
            x = airShelf[c].processSample (x);
            d[n] = x;
        }
    }

    // ---- compression (parallel) ---------------------------------------------
    if (settings.compAmount > 0.001f)
    {
        for (int ch = 0; ch < numChannels; ++ch)
            dryBuffer.copyFrom (ch, 0, buffer, ch, 0, numSamples);

        dsp::AudioBlock<float> block (buffer.getArrayOfWritePointers(), (size_t) numChannels, (size_t) numSamples);
        dsp::ProcessContextReplacing<float> ctx (block);
        compressor.process (ctx);

        const float makeup = Decibels::decibelsToGain (settings.compAmount * 6.0f);
        const float mix = settings.compMix;

        float dryPeak = 0.0f, wetPeak = 0.0f;

        for (int ch = 0; ch < numChannels; ++ch)
        {
            auto* wet = buffer.getWritePointer (ch);
            const auto* dry = dryBuffer.getReadPointer (ch);

            for (int n = 0; n < numSamples; ++n)
            {
                dryPeak = jmax (dryPeak, std::abs (dry[n]));
                wetPeak = jmax (wetPeak, std::abs (wet[n]));
                wet[n] = dry[n] * (1.0f - mix) + wet[n] * makeup * mix;
            }
        }

        const float gr = dryPeak > 1.0e-4f ? jlimit (0.0f, 1.0f, 1.0f - wetPeak / dryPeak) : 0.0f;
        gainReduction += 0.25f * (gr - gainReduction);
    }
    else
    {
        gainReduction *= 0.8f;
    }

    // ---- saturation ---------------------------------------------------------
    if (settings.drive > 0.001f && numChannels == 2)
    {
        const float k = 1.0f + settings.drive * 14.0f;
        const float comp = 1.0f / std::sqrt (k);
        const float bias = 0.06f * settings.drive;
        const float biasOffset = std::tanh (bias);
        const float tilt = (settings.driveTone - 0.5f) * 2.0f;
        const float tiltCoef = onePole (900.0, sr);

        dsp::AudioBlock<float> block (buffer.getArrayOfWritePointers(), (size_t) numChannels, (size_t) numSamples);
        auto up = oversampling->processSamplesUp (block);

        for (size_t ch = 0; ch < up.getNumChannels(); ++ch)
        {
            auto* d = up.getChannelPointer (ch);
            const auto n = (int) up.getNumSamples();
            float& state = driveState[jmin ((size_t) 1, ch)];

            for (int i = 0; i < n; ++i)
            {
                float x = d[i];
                state += tiltCoef * (x - state);
                x += tilt * (x - state) * 0.8f;                 // pre emphasis
                d[i] = (std::tanh (x * k + bias) - biasOffset) * comp;
            }
        }

        oversampling->processSamplesDown (block);
    }

    // ---- movement -----------------------------------------------------------
    ensemble.process (l, r, numSamples);

    // ---- delay --------------------------------------------------------------
    delay.process (l, r, numSamples, settings.delayMix);

    // ---- reverb (parallel) --------------------------------------------------
    if (settings.reverbMix > 0.0005f)
    {
        wetBuffer.clear (0, numSamples);
        wetBuffer.copyFrom (0, 0, l, numSamples);
        wetBuffer.copyFrom (1, 0, r, numSamples);

        reverb.process (wetBuffer.getWritePointer (0), wetBuffer.getWritePointer (1), numSamples);

        const auto* wl = wetBuffer.getReadPointer (0);
        const auto* wr = wetBuffer.getReadPointer (1);
        const float mix = settings.reverbMix;

        for (int n = 0; n < numSamples; ++n)
        {
            l[n] += wl[n] * mix;
            r[n] += wr[n] * mix;
        }
    }

    // ---- width + output -----------------------------------------------------
    const float w = settings.width;

    for (int n = 0; n < numSamples; ++n)
    {
        smoothedOutput += 0.002f * (settings.outputGain - smoothedOutput);

        const float mid = (l[n] + r[n]) * 0.5f;
        const float side = (l[n] - r[n]) * 0.5f * w;

        l[n] = softClip ((mid + side) * smoothedOutput);
        r[n] = softClip ((mid - side) * smoothedOutput);
    }

    if (numChannels == 1)
        buffer.copyFrom (0, 0, l, numSamples);
}

} // namespace wp
