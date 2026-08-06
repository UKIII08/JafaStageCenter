#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>

namespace wp
{

/*
    The pad that sits underneath the piano on almost every modern worship
    record: a slow, detuned, heavily filtered swell that never draws attention
    to itself but glues the whole part together.
*/
/*  Five characters rather than one. The same swell envelope and the same
    stereo spread underneath, but a different waveform and a different amount of
    filtering on top, because "pad" covers everything from a warm analogue bed to
    a glass bell to a breathy vocal wash - and a set only has to sound different
    enough that the player reaches for a particular one.
*/
enum class PadVoice
{
    warmSaw = 0,    // detuned saws, the classic analogue bed
    softChoir,      // triangle-ish, no top end, breathes rather than buzzes
    glass,          // bright and bell-like, sits above the piano
    strings,        // more detune, slower swell, a section rather than a synth
    airVox          // narrow pulse through a formant-ish peak, breathy
};

struct PadSettings
{
    float level      = 0.0f;   // linear gain, 0 = layer off
    float cutoffHz   = 1600.0f;
    float attackMs   = 700.0f;
    float releaseMs  = 2200.0f;
    float detuneCents = 12.0f;
    PadVoice voice   = PadVoice::warmSaw;
};

class PadLayer
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setSettings (const PadSettings& s) { settings = s; }

    void noteOn (int midiNote, float velocity);
    void noteOff (int midiNote);
    void sustainPedal (bool down);
    void allNotesOff();

    void render (float* left, float* right, int numSamples);

private:
    static constexpr int maxVoices = 16;
    static constexpr int oscsPerVoice = 3;

    struct Voice
    {
        std::array<float, oscsPerVoice> phase {};
        std::array<float, oscsPerVoice> inc {};
        float env = 0.0f;
        float target = 0.0f;
        float attackCoef = 0.001f, releaseCoef = 0.001f;
        float panL = 0.7071f, panR = 0.7071f;
        float velocity = 0.8f;
        int   note = -1;
        bool  held = false, sustained = false, active = false;

        // one state variable filter per side: the oscillators are spread across
        // the stereo field rather than summed and panned as a block
        float ic1L = 0.0f, ic2L = 0.0f, ic1R = 0.0f, ic2R = 0.0f;
    };

    inline float polyBlepSaw (float& phase, float inc) noexcept;
    inline float oscillator (float& phase, float inc) noexcept;

    std::array<Voice, maxVoices> voices;
    PadSettings settings;
    double sr = 44100.0;
    bool pedalDown = false;

    // the pad stomp drives level straight to zero, and a pad is a sustained
    // sound - cutting one is far more audible than cutting a decaying note
    juce::SmoothedValue<float> smoothedGain;

    float lfoPhase = 0.0f, lfoInc = 0.0f;
    juce::dsp::IIR::Filter<float> dcL, dcR;
};

} // namespace wp
