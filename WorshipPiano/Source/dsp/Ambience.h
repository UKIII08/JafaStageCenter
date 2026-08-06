#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>
#include <vector>

/*
    The ambience engine: the part that turns a piano into something you can sink
    into.

    Three things separate a reverb that flows from one that just adds a tail:

      * density. A bare feedback delay network with a handful of lines flutters
        on long decays. Four modulated allpass diffusers in front of the tank
        smear every transient into a cloud before it ever reaches the feedback,
        and the tank itself runs sixteen lines instead of eight.
      * movement. Every delay line is read through its own slow LFO, so the tail
        drifts instead of standing still.
      * the octave. The shimmer path pitch shifts the tank output, diffuses it
        again, filters it and feeds it back in, so the octave rises into the
        tail gradually rather than appearing on top of it.

    On top of that sit the two things that make it playable: bloom, which fades
    the wet in slowly so the wash swells up behind what you played, and freeze,
    which locks the tank at unity and lets you play over a held chord.
*/
namespace wp
{

//==============================================================================
/** Delay line with linear interpolation. */
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
        float pos = (float) writeIndex - juce::jlimit (1.0f, (float) mask - 2.0f, delaySamples);

        if (pos < 0.0f)
            pos += (float) (mask + 1);

        const int i0 = (int) pos;
        const float frac = pos - (float) i0;
        const int a = i0 & mask;
        const int b = (i0 + 1) & mask;

        return buffer[(size_t) a] + frac * (buffer[(size_t) b] - buffer[(size_t) a]);
    }

    int getSize() const noexcept { return mask + 1; }

private:
    std::vector<float> buffer;
    int mask = 0, writeIndex = 0;
};

//==============================================================================
/** Schroeder allpass: smears a transient without colouring the magnitude. */
class Allpass
{
public:
    void prepare (int maxSamples) { line.prepare (maxSamples); }
    void reset() { line.reset(); }

    void set (float delaySamples, float gain) noexcept
    {
        delay = delaySamples;
        g = juce::jlimit (0.0f, 0.85f, gain);
    }

    inline float process (float x, float modulation = 0.0f) noexcept
    {
        const float d = line.read (delay + modulation);
        const float v = x + g * d;
        line.write (v);
        return d - g * v;
    }

private:
    FracDelay line;
    float delay = 100.0f, g = 0.6f;
};

//==============================================================================
/** Crossfaded two tap pitch shifter, any ratio. */
class PitchShifter
{
public:
    void prepare (double sampleRate);
    void reset();
    void setRatio (float r) noexcept { step = r - 1.0f; }
    float process (float input) noexcept;

private:
    FracDelay line;
    float windowSamples = 2048.0f;
    float readOffset = 0.0f;
    float step = 1.0f;
};

//==============================================================================
/*  Reverse piano.

    Audio is written into a circular buffer continuously. Two grains read back
    out of it *backwards*, each covering one window, offset by half a window and
    windowed with a raised cosine so their sum is constant. The result is the
    classic reverse swell: every phrase arrives blooming into itself, with no
    gap and no click where the grains change over.
*/
class Reverse
{
public:
    void prepare (double sampleRate);
    void reset();

    /** Window length in samples: how far back each swell reaches. */
    void setWindow (float samples) noexcept;

    void process (const float* inL, const float* inR,
                  float* outL, float* outR, int numSamples);

private:
    std::vector<float> bufferL, bufferR;
    int mask = 0, writeIndex = 0;

    struct Grain { int age = 0; int capture = 0; };
    std::array<Grain, 2> grains;

    float window = 24000.0f, targetWindow = 24000.0f;
    float tone = 0.0f;
    float lpL = 0.0f, lpR = 0.0f;
};

//==============================================================================
/** One reverb character: what BigSky would call a machine. */
struct AmbienceMachine
{
    const char* name;
    float diffusion;     // allpass gain in the input diffuser
    int   stages;        // how many diffuser stages are used (1..4)
    float sizeScale;     // multiplier on the tank delay lengths
    float modDepth;      // samples of delay modulation
    float modRate;       // base LFO rate, Hz
    float damping;       // 0 open .. 1 dark
    float lowCutHz;      // high pass inside the feedback
    float bloomMs;       // how slowly the wet fades in
    float shimmerScale;  // how strongly this machine takes shimmer
};

const AmbienceMachine& machineFor (int index);
int numMachines();

//==============================================================================
struct AmbienceSettings
{
    int   machine     = 1;      // 0 Room, 1 Hall, 2 Plate, 3 Cloud, 4 Bloom, 5 Shimmer
    float size        = 0.55f;
    float decay       = 3.0f;   // seconds
    float shimmer     = 0.0f;
    int   shimmerMode = 0;      // 0 up, 1 up + fifth, 2 down, 3 up and down
    float duck        = 0.0f;
    bool  freeze      = false;
};

class Ambience
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setSettings (const AmbienceSettings& s);

    /** @param sendL/R  what goes into the tank
        @param dryL/R   used only for the ducking detector
        @param outL/R   written, not added                                    */
    void process (const float* sendL, const float* sendR,
                  const float* dryL, const float* dryR,
                  float* outL, float* outR, int numSamples);

private:
    static constexpr int numLines = 16;
    static constexpr int numDiffusers = 4;

    void updateFeedback();

    std::array<FracDelay, numLines> lines;
    std::array<float, numLines> baseLength {};
    std::array<float, numLines> length {};
    std::array<float, numLines> feedback {};
    std::array<float, numLines> damper {};
    std::array<float, numLines> lowCut {};
    std::array<float, numLines> lfoPhase {};
    std::array<float, numLines> lfoInc {};

    std::array<Allpass, numDiffusers> diffuseL, diffuseR;
    std::array<float, numDiffusers> diffusePhase {}, diffuseInc {};

    FracDelay predelayL, predelayR;

    PitchShifter shifterA, shifterB;
    std::array<Allpass, 2> shimmerDiffuse;
    float shimmerLP = 0.0f, shimmerHP = 0.0f;

    AmbienceSettings settings;
    double sr = 44100.0;

    float predelaySamples = 64.0f;
    float dampCoef = 0.3f, lowCutCoef = 0.02f;
    float modDepth = 3.0f;
    float freezeAmount = 0.0f;     // smoothed 0..1
    float bloomEnv = 0.0f, bloomAttack = 0.001f, bloomRelease = 0.0002f;
    float duckEnv = 0.0f;
};

} // namespace wp
