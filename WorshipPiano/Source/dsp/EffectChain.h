#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>

#include "Ambience.h"

namespace wp
{

//==============================================================================
/** Tempo synced stereo delay with ping pong and a filtered feedback path. */
class StereoDelay
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setParameters (float delaySamplesL, float delaySamplesR, float fb, float tone, float pingPong);
    void process (float* left, float* right, int numSamples, float mix);

private:
    FracDelay lineL, lineR;
    double sr = 44100.0;
    float targetL = 12000.0f, targetR = 12000.0f;
    float currentL = 12000.0f, currentR = 12000.0f;
    float feedback = 0.38f, pingPongAmount = 0.7f;
    float lpCoef = 0.5f, hpCoef = 0.01f;
    float lpL = 0.0f, lpR = 0.0f, hpL = 0.0f, hpR = 0.0f;
};

//==============================================================================
/** Subtle stereo ensemble - width and drift, never a 1980s chorus pedal. */
class Ensemble
{
public:
    void prepare (double sampleRate);
    void reset();
    void setParameters (float amount, float rateHz);
    void process (float* left, float* right, int numSamples);

private:
    FracDelay lineL, lineR;
    double sr = 44100.0;
    float amount = 0.15f;
    float phase = 0.0f, inc = 0.0f;
};

//==============================================================================
struct EffectSettings
{
    float eqLow = 0.0f, eqHigh = 0.0f, eqAir = 2.0f;
    float compAmount = 0.30f;
    float drive = 0.12f;
    float chorusAmount = 0.10f, chorusRate = 0.32f;
    float delayMix = 0.0f, delayFeedback = 0.38f, delayTone = 0.45f, delayPingPong = 0.80f;
    float delaySamplesL = 12000.0f, delaySamplesR = 12000.0f;
    float reverbMix = 0.26f;
    float reverseMix = 0.0f;
    float reverseWindow = 24000.0f;   // samples
    float padSend = 0.9f;        // extra reverb send for the pad layer
    float width = 1.0f, outputGain = 1.0f;
};

class EffectChain
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setSettings (const EffectSettings& s);
    void setAmbience (const AmbienceSettings& s) { ambience.setSettings (s); }

    /** @param buffer  the piano, replaced in place by the finished mix
        @param padBuffer  the pad layer, mixed in and sent to the ambience     */
    void process (juce::AudioBuffer<float>& buffer, const juce::AudioBuffer<float>& padBuffer);

    int getLatencySamples() const noexcept { return latencySamples; }

private:
    void updateFilters();

    using Filter = juce::dsp::IIR::Filter<float>;

    std::array<Filter, 2> lowShelf, highShelf, airShelf, rumbleCut;
    juce::dsp::Compressor<float> compressor;
    std::unique_ptr<juce::dsp::Oversampling<float>> oversampling;
    Ensemble ensemble;
    StereoDelay delay;
    Reverse reverse;
    Ambience ambience;

    juce::AudioBuffer<float> dryBuffer, sendBuffer, wetBuffer, reverseBuffer;

    EffectSettings settings;
    double sr = 44100.0;
    bool filtersDirty = true;
    int latencySamples = 0;
    float smoothedOutput = 1.0f;
    float smoothedReverbMix = 0.0f;
    float smoothedReverseMix = 0.0f;
    std::array<float, 2> driveState { { 0.0f, 0.0f } };
};

} // namespace wp
