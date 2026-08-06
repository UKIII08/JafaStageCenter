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
struct PadSettings
{
    float level      = 0.0f;   // linear gain, 0 = layer off
    float cutoffHz   = 1600.0f;
    float attackMs   = 700.0f;
    float releaseMs  = 2200.0f;
    float detuneCents = 12.0f;
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

        // state variable filter
        float ic1 = 0.0f, ic2 = 0.0f;
    };

    inline float polyBlepSaw (float& phase, float inc) noexcept;

    std::array<Voice, maxVoices> voices;
    PadSettings settings;
    double sr = 44100.0;
    bool pedalDown = false;

    float lfoPhase = 0.0f, lfoInc = 0.0f;
    juce::dsp::IIR::Filter<float> dcL, dcR;
};

} // namespace wp
