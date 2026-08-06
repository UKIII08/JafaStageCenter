#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>
#include <vector>

/*
    Commuted waveguide piano.

    Each note is a small bank of coupled string resonators: a fractional delay
    line closed by a damping filter (decay + brightness) and a chain of first
    order allpasses (dispersion, i.e. the sharp upper partials that make a
    piano sound like a piano rather than a harp).

    The hammer is a short velocity dependent noise burst, shaped by a strike
    position comb so the partials that fall on the striking point are missing,
    exactly as they are on a real instrument.

    No samples, so the whole thing is a few hundred kilobytes and every
    parameter is continuous - you can morph between a hard concert grand and a
    felt-muted ambient piano without switching libraries.
*/
namespace wp
{

//==============================================================================
/** Settings shared by every voice, refreshed once per audio block. */
struct EngineSettings
{
    float brightness   = 0.0f;   // -1 .. 1
    float hardness     = 0.5f;   //  0 .. 1
    float decayScale   = 1.0f;   // 0.4 .. 2
    float detuneCents  = 5.0f;
    float stretch      = 1.0f;
    float sympathetic  = 0.35f;
    float mechNoise    = 0.3f;
    float velCurve     = 0.5f;
    float dynamicRange = 26.0f;  // dB
    float spread       = 0.45f;
    int   model        = 0;      // 0 grand, 1 upright, 2 felt, 3 stage
};

//==============================================================================
/** One string: delay line + loop damping filter + dispersion allpass chain. */
class StringResonator
{
public:
    void prepare (int maxDelaySamples);
    void reset();

    /** @param freq         target pitch in Hz
        @param t60          decay time to -60 dB, seconds
        @param damping      0 = bright/no loss, 1 = very dark
        @param dispersion   0 .. 1, amount of inharmonicity
    */
    void setTone (double sampleRate, double freq, float t60, float damping, float dispersion);

    /** Damper drop: recompute the loop gain for a much shorter decay. */
    void setDecayTime (double sampleRate, float t60);

    inline float process (float input) noexcept
    {
        // --- read the delay line with linear interpolation --------------------
        // Wrap into positive territory *before* truncating: a negative read
        // position would otherwise produce a negative fraction, turning the
        // interpolator into an extrapolator with gain above one, which lets the
        // string loop run away every time the buffer wraps.
        float readPos = (float) writeIndex - delaySamples;

        if (readPos < 0.0f)
            readPos += (float) (mask + 1);

        const int   i0 = (int) readPos;
        const float frac = readPos - (float) i0;
        const int   idx0 = i0 & mask;
        const int   idx1 = (i0 + 1) & mask;
        float out = buffer[(size_t) idx0] + frac * (buffer[(size_t) idx1] - buffer[(size_t) idx0]);

        // --- dispersion -------------------------------------------------------
        for (int i = 0; i < apCount; ++i)
        {
            const float v = apCoef * out + apState[(size_t) i];
            apState[(size_t) i] = out - apCoef * v;
            out = v;
        }

        // --- loss filter (one pole lowpass) + loop gain ------------------------
        lossState = out + damp * (lossState - out);
        float fb = lossState * loopGain;

        // --- DC blocker keeps long bass strings from drifting ------------------
        const float dc = fb - dcX + 0.9995f * dcY;
        dcX = fb;
        dcY = dc;
        fb = dc;

        buffer[(size_t) writeIndex] = input + fb;
        writeIndex = (writeIndex + 1) & mask;

        return out;
    }

    float getDelaySamples() const noexcept { return delaySamples; }


private:
    std::vector<float> buffer;
    int   writeIndex = 0;
    int   mask = 0;
    float delaySamples = 100.0f;
    float loopGain = 0.999f;
    float damp = 0.3f;
    float lossState = 0.0f;
    float apCoef = 0.0f;
    int   apCount = 0;
    std::array<float, 4> apState { { 0.0f, 0.0f, 0.0f, 0.0f } };
    float dcX = 0.0f, dcY = 0.0f;
    float loopDelayCompensation = 0.0f;
    double lastFreq = 440.0;
};

//==============================================================================
/** Velocity dependent hammer excitation, band limited and comb shaped. */
class HammerExciter
{
public:
    void trigger (double sampleRate, float velocity, float hardness, float noiseAmount,
                  float periodSamples, int model);
    void reset() { samplesLeft = 0; env = 0.0f; combIndex = 0; std::fill (comb.begin(), comb.end(), 0.0f); }

    bool isActive() const noexcept { return samplesLeft > 0; }

    inline float process (juce::Random& rng) noexcept
    {
        if (samplesLeft <= 0)
            return 0.0f;

        --samplesLeft;

        float x = rng.nextFloat() * 2.0f - 1.0f;
        x = x * env + click;

        env   *= envCoef;
        click *= clickCoef;

        // hammer felt = lowpass; the harder you play the further it opens up
        lpState += lpCoef * (x - lpState);
        float y = lpState;

        // strike position comb: cancels the partials with a node at the hammer
        const int readIdx = (combIndex - combDelay + (int) comb.size()) & combMask;
        const float delayed = comb[(size_t) readIdx];
        comb[(size_t) combIndex] = y;
        combIndex = (combIndex + 1) & combMask;
        y -= 0.92f * delayed;

        return y * amp;
    }


private:
    std::array<float, 1024> comb { {} };
    static constexpr int combMask = 1023;
    int   combIndex = 0;
    int   combDelay = 8;
    int   samplesLeft = 0;
    float env = 0.0f, envCoef = 0.99f;
    float click = 0.0f, clickCoef = 0.6f;
    float lpState = 0.0f, lpCoef = 0.3f;
    float amp = 1.0f;
};

//==============================================================================
class PianoVoice
{
public:
    void prepare (double sampleRate, int maxDelaySamples);
    void reset();

    void start (int midiNote, float velocity, const EngineSettings& s, double sampleRate,
                float softPedal);
    void stop (bool pedalHeld, const EngineSettings& s, double sampleRate);
    void pedalReleased (const EngineSettings& s, double sampleRate);

    void render (float* left, float* right, int numSamples, juce::Random& rng, float* sympSend);

    bool  isActive() const noexcept   { return active; }
    bool  isHeld() const noexcept     { return keyHeld; }
    bool  isSustained() const noexcept{ return sustained; }
    int   getNote() const noexcept    { return note; }
    float getEnergy() const noexcept  { return energy; }
    juce::uint32 getStartOrder() const noexcept { return startOrder; }

    void setSostenuto (bool s) noexcept { sostenuto = s; }
    bool isSostenuto() const noexcept   { return sostenuto; }

private:
    static constexpr int maxStrings = 3;

    std::array<StringResonator, maxStrings> strings;
    HammerExciter hammer;

    int   numStrings = 3;
    int   note = 60;
    bool  active = false, keyHeld = false, sustained = false, sostenuto = false;
    float panL = 0.7071f, panR = 0.7071f;
    float amplitude = 1.0f;
    float energy = 0.0f;
    float sympGain = 0.0f;
    juce::uint32 startOrder = 0;

    // damper noise on key release
    float releaseNoise = 0.0f, releaseNoiseCoef = 0.0f;

    friend class PianoEngine;
};

//==============================================================================
/** Undamped strings that ring in sympathy while the sustain pedal is down. */
class SympatheticBank
{
public:
    void prepare (double sampleRate, int maxDelaySamples);
    void reset();
    void setAmount (float amount, double sampleRate);
    void process (const float* input, float* left, float* right, int numSamples);

private:
    static constexpr int numStrings = 24;
    std::array<StringResonator, numStrings> strings;
    std::array<float, numStrings> panL {}, panR {};
    float amount = 0.0f;
    float smoothed = 0.0f;
};

//==============================================================================
class PianoEngine
{
public:
    PianoEngine();

    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setSettings (const EngineSettings& s) { settings = s; }

    void noteOn (int midiNote, float velocity);
    void noteOff (int midiNote);
    void sustainPedal (float value);   // 0 .. 1 (half pedalling supported)
    void sostenutoPedal (bool down);
    void softPedal (float value);
    void allNotesOff();
    void panic();

    /** Renders into (and adds to) the given stereo buffers. */
    void render (float* left, float* right, int numSamples);

    bool isSilent() const noexcept { return activeVoices == 0; }

private:
    static constexpr int maxVoices = 32;

    PianoVoice* findVoiceToSteal (int midiNote);

    std::array<PianoVoice, maxVoices> voices;
    SympatheticBank sympathetic;

    EngineSettings settings;
    double sr = 44100.0;
    float pedal = 0.0f;
    float soft = 0.0f;
    bool  sostenutoDown = false;
    int   activeVoices = 0;
    juce::uint32 orderCounter = 0;
    juce::Random rng { 20250406 };

    std::vector<float> sympBuffer;

    // gentle soundboard body resonances on the summed piano bus
    std::array<juce::dsp::IIR::Filter<float>, 3> bodyL, bodyR;
};

} // namespace wp
