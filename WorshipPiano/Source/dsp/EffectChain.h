#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>
#include <vector>

namespace wp
{

//==============================================================================
/** Delay line with linear interpolation, used by everything downstream. */
class FracDelay
{
public:
    void prepare (int maxSamples)
    {
        const int size = juce::nextPowerOfTwo (juce::jmax (16, maxSamples + 4));
        buffer.assign ((size_t) size, 0.0f);
        mask = size - 1;
        writeIndex = 0;
    }

    void reset() { std::fill (buffer.begin(), buffer.end(), 0.0f); writeIndex = 0; }

    inline void write (float v) noexcept
    {
        buffer[(size_t) writeIndex] = v;
        writeIndex = (writeIndex + 1) & mask;
    }

    inline float read (float delaySamples) const noexcept
    {
        const float pos = (float) writeIndex - juce::jlimit (1.0f, (float) mask - 2.0f, delaySamples);
        int i0 = (int) std::floor (pos);
        const float frac = pos - (float) i0;
        i0 &= mask;
        const int i1 = (i0 + 1) & mask;
        return buffer[(size_t) i0] + frac * (buffer[(size_t) i1] - buffer[(size_t) i0]);
    }

    int getSize() const noexcept { return mask + 1; }

private:
    std::vector<float> buffer;
    int mask = 0, writeIndex = 0;
};

//==============================================================================
/** Crossfaded two tap pitch shifter - the octave up inside the shimmer. */
class OctaveShifter
{
public:
    void prepare (double sampleRate);
    void reset();
    float process (float input) noexcept;

private:
    FracDelay line;
    float windowSamples = 2048.0f;
    float readOffset = 0.0f;
};

//==============================================================================
/** Feedback delay network reverb with an optional octave-up shimmer path. */
class Reverb
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setParameters (float size, float decaySeconds, float tone, float predelayMs, float shimmerAmount);
    void process (float* left, float* right, int numSamples);

private:
    static constexpr int numLines = 8;

    std::array<FracDelay, numLines> lines;
    std::array<float, numLines> baseLength {};
    std::array<float, numLines> currentLength {};
    std::array<float, numLines> feedback {};
    std::array<float, numLines> damper {};
    std::array<float, numLines> lowCut {};
    std::array<float, numLines> lfoPhase {};
    std::array<float, numLines> lfoInc {};

    FracDelay predelayL, predelayR;
    OctaveShifter shifter;
    juce::dsp::IIR::Filter<float> shimmerLP;

    double sr = 44100.0;
    float sizeAmount = 0.6f, decayTime = 3.2f, toneAmount = 0.5f;
    float predelaySamples = 0.0f;
    float shimmer = 0.0f;
    float dampCoef = 0.35f, lowCutCoef = 0.02f;
    float shimmerState = 0.0f;
};

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
/** Four voice stereo ensemble - subtle width, never a 1980s chorus pedal. */
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
    float eqLow = 0.0f, eqMid = 0.0f, eqHigh = 0.0f, eqAir = 2.0f;
    float compAmount = 0.35f, compMix = 1.0f;
    float drive = 0.18f, driveTone = 0.5f;
    float chorusAmount = 0.15f, chorusRate = 0.35f;
    float delayMix = 0.0f, delayFeedback = 0.38f, delayTone = 0.45f, delayPingPong = 0.7f;
    float delaySamplesL = 12000.0f, delaySamplesR = 12000.0f;
    float reverbMix = 0.28f, reverbSize = 0.6f, reverbDecay = 3.2f, reverbTone = 0.5f;
    float reverbPredelay = 20.0f, shimmer = 0.0f;
    float width = 1.0f, outputGain = 1.0f;
};

class EffectChain
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setSettings (const EffectSettings& s);
    void process (juce::AudioBuffer<float>& buffer);

    float getGainReduction() const noexcept { return gainReduction; }

private:
    void updateFilters();

    using Filter = juce::dsp::IIR::Filter<float>;

    std::array<Filter, 2> lowShelf, midPeak, highShelf, airShelf, rumbleCut;
    juce::dsp::Compressor<float> compressor;
    std::unique_ptr<juce::dsp::Oversampling<float>> oversampling;
    Ensemble ensemble;
    StereoDelay delay;
    Reverb reverb;

    juce::AudioBuffer<float> dryBuffer, wetBuffer;

    EffectSettings settings;
    double sr = 44100.0;
    bool filtersDirty = true;
    float gainReduction = 0.0f;
    float smoothedOutput = 1.0f;
    std::array<float, 2> driveState { { 0.0f, 0.0f } };
};

} // namespace wp
