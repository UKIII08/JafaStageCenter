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
    feedback = jlimit (0.0f, 0.92f, fb);
    pingPongAmount = jlimit (0.0f, 1.0f, pingPong);

    lpCoef = onePole (jmap ((double) jlimit (0.0f, 1.0f, tone), 900.0, 12000.0), sr);
    hpCoef = onePole (jmap (1.0 - (double) jlimit (0.0f, 1.0f, tone), 60.0, 500.0), sr);
}

void StereoDelay::process (float* left, float* right, int numSamples, float mix)
{
    if (mix <= 0.0001f)
    {
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
    latencySamples = roundToInt (oversampling->getLatencyInSamples());

    ensemble.prepare (sampleRate);
    delay.prepare (sampleRate, maxBlockSize);
    reverse.prepare (sampleRate);
    ambience.prepare (sampleRate, maxBlockSize);

    dryBuffer.setSize (2, maxBlockSize, false, false, true);
    sendBuffer.setSize (2, maxBlockSize, false, false, true);
    wetBuffer.setSize (2, maxBlockSize, false, false, true);
    reverseBuffer.setSize (2, maxBlockSize, false, false, true);

    filtersDirty = true;
    updateFilters();
    reset();
}

void EffectChain::reset()
{
    for (auto& f : lowShelf)  f.reset();
    for (auto& f : highShelf) f.reset();
    for (auto& f : airShelf)  f.reset();
    for (auto& f : rumbleCut) f.reset();

    compressor.reset();

    if (oversampling != nullptr)
        oversampling->reset();

    ensemble.reset();
    delay.reset();
    reverse.reset();
    ambience.reset();

    driveState.fill (0.0f);
    smoothedOutput = settings.outputGain;
    smoothedReverbMix = settings.reverbMix;
    smoothedReverseMix = settings.reverseMix;
}

void EffectChain::setSettings (const EffectSettings& s)
{
    const bool eqChanged = s.eqLow != settings.eqLow || s.eqHigh != settings.eqHigh
                        || s.eqAir != settings.eqAir;

    settings = s;

    if (eqChanged || filtersDirty)
        updateFilters();

    compressor.setThreshold (jmap (settings.compAmount, 0.0f, 1.0f, -6.0f, -34.0f));
    compressor.setRatio (jmap (settings.compAmount, 0.0f, 1.0f, 1.2f, 5.5f));

    ensemble.setParameters (settings.chorusAmount, settings.chorusRate);
    delay.setParameters (settings.delaySamplesL, settings.delaySamplesR,
                         settings.delayFeedback, settings.delayTone, settings.delayPingPong);
    reverse.setWindow (settings.reverseWindow);
}

void EffectChain::updateFilters()
{
    auto low  = dsp::IIR::Coefficients<float>::makeLowShelf  (sr, 180.0f, 0.7f, Decibels::decibelsToGain (settings.eqLow));
    auto high = dsp::IIR::Coefficients<float>::makeHighShelf (sr, 3600.0f, 0.7f, Decibels::decibelsToGain (settings.eqHigh));
    auto air  = dsp::IIR::Coefficients<float>::makeHighShelf (sr, (float) jmin (14000.0, sr * 0.42), 0.6f,
                                                              Decibels::decibelsToGain (settings.eqAir));
    auto rumble = dsp::IIR::Coefficients<float>::makeHighPass (sr, 26.0f);

    for (int ch = 0; ch < 2; ++ch)
    {
        lowShelf[(size_t) ch].coefficients  = low;
        highShelf[(size_t) ch].coefficients = high;
        airShelf[(size_t) ch].coefficients  = air;
        rumbleCut[(size_t) ch].coefficients = rumble;
    }

    filtersDirty = false;
}

void EffectChain::process (AudioBuffer<float>& buffer, const AudioBuffer<float>& padBuffer)
{
    const int numSamples = buffer.getNumSamples();
    const int numChannels = jmin (2, buffer.getNumChannels());

    if (numSamples <= 0)
        return;

    if (dryBuffer.getNumSamples() < numSamples)
    {
        dryBuffer.setSize (2, numSamples, false, false, true);
        sendBuffer.setSize (2, numSamples, false, false, true);
        wetBuffer.setSize (2, numSamples, false, false, true);
        reverseBuffer.setSize (2, numSamples, false, false, true);
    }

    auto* l = buffer.getWritePointer (0);
    auto* r = numChannels > 1 ? buffer.getWritePointer (1) : l;

    // ---- tone (piano only) --------------------------------------------------
    for (int ch = 0; ch < numChannels; ++ch)
    {
        auto* d = buffer.getWritePointer (ch);
        const size_t c = (size_t) ch;

        for (int n = 0; n < numSamples; ++n)
        {
            float x = rumbleCut[c].processSample (d[n]);
            x = lowShelf[c].processSample (x);
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

        for (int ch = 0; ch < numChannels; ++ch)
        {
            auto* wet = buffer.getWritePointer (ch);

            for (int n = 0; n < numSamples; ++n)
                wet[n] *= makeup;
        }
    }

    // ---- saturation ---------------------------------------------------------
    // Always run, so the reported latency never changes underneath the host.
    if (numChannels == 2)
    {
        const float k = 1.0f + settings.drive * 14.0f;
        const float comp = 1.0f / std::sqrt (k);
        const float bias = 0.06f * settings.drive;
        const float biasOffset = std::tanh (bias);

        // Blend towards the shaper rather than always running it. tanh is not
        // the identity at unity gain, so without this the Drive knob at zero
        // still put a compressed, odd-harmonic curve across everything.
        const float wet = jmin (1.0f, settings.drive * 2.5f);

        dsp::AudioBlock<float> block (buffer.getArrayOfWritePointers(), (size_t) numChannels, (size_t) numSamples);
        auto up = oversampling->processSamplesUp (block);

        for (size_t ch = 0; ch < up.getNumChannels(); ++ch)
        {
            auto* d = up.getChannelPointer (ch);
            const auto n = (int) up.getNumSamples();

            for (int i = 0; i < n; ++i)
            {
                const float x = d[i];
                const float shaped = (std::tanh (x * k + bias) - biasOffset) * comp;
                d[i] = x + wet * (shaped - x);
            }
        }

        oversampling->processSamplesDown (block);
    }

    // ---- reverse -------------------------------------------------------------
    // Fed from the shaped piano only: reversing the pad as well would just
    // smear an already smeared signal.
    auto* revL = reverseBuffer.getWritePointer (0);
    auto* revR = reverseBuffer.getWritePointer (1);
    reverse.process (l, r, revL, revR, numSamples);

    // ---- fold the pad in ----------------------------------------------------
    const auto* padL = padBuffer.getNumChannels() > 0 ? padBuffer.getReadPointer (0) : nullptr;
    const auto* padR = padBuffer.getNumChannels() > 1 ? padBuffer.getReadPointer (1) : padL;

    if (padL != nullptr)
    {
        for (int n = 0; n < numSamples; ++n)
        {
            l[n] += padL[n];
            r[n] += padR[n];
        }
    }

    // ---- movement -----------------------------------------------------------
    ensemble.process (l, r, numSamples);
    delay.process (l, r, numSamples, settings.delayMix);

    // ---- ambience -----------------------------------------------------------
    // The pad goes in hotter than the piano: that difference is what makes the
    // pad read as a wash sitting behind the instrument rather than beside it.
    auto* sendL = sendBuffer.getWritePointer (0);
    auto* sendR = sendBuffer.getWritePointer (1);

    for (int n = 0; n < numSamples; ++n)
    {
        sendL[n] = l[n];
        sendR[n] = r[n];
    }

    if (settings.reverseMix > 0.0005f || smoothedReverseMix > 0.0005f)
    {
        for (int n = 0; n < numSamples; ++n)
        {
            smoothedReverseMix += 0.0015f * (settings.reverseMix - smoothedReverseMix);

            const float wl = revL[n] * smoothedReverseMix;
            const float wr = revR[n] * smoothedReverseMix;

            l[n] += wl;
            r[n] += wr;

            // a reverse swell wants to live inside the space, not in front of it
            sendL[n] += wl * 1.6f;
            sendR[n] += wr * 1.6f;
        }
    }

    if (padL != nullptr && settings.padSend > 0.001f)
    {
        for (int n = 0; n < numSamples; ++n)
        {
            sendL[n] += padL[n] * settings.padSend;
            sendR[n] += padR[n] * settings.padSend;
        }
    }

    ambience.process (sendL, sendR, l, r,
                      wetBuffer.getWritePointer (0), wetBuffer.getWritePointer (1), numSamples);

    const auto* wl = wetBuffer.getReadPointer (0);
    const auto* wr = wetBuffer.getReadPointer (1);

    // ---- width, output, safety ---------------------------------------------
    const float w = settings.width;

    for (int n = 0; n < numSamples; ++n)
    {
        smoothedReverbMix += 0.0015f * (settings.reverbMix - smoothedReverbMix);
        smoothedOutput += 0.002f * (settings.outputGain - smoothedOutput);

        const float ol = l[n] + wl[n] * smoothedReverbMix;
        const float orr = r[n] + wr[n] * smoothedReverbMix;

        const float mid = (ol + orr) * 0.5f;
        const float side = (ol - orr) * 0.5f * w;

        l[n] = softClip ((mid + side) * smoothedOutput);
        r[n] = softClip ((mid - side) * smoothedOutput);
    }

    if (numChannels == 1)
        buffer.copyFrom (0, 0, l, numSamples);
}

} // namespace wp
