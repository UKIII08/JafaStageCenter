#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>
#include <vector>

/*
    Additive (modal) piano.

    A struck piano string is not a plucked one, so this does not run a waveguide
    loop. Instead every note is built partial by partial from the physics that
    actually shape a piano tone:

      * partial k sits at k*f0*sqrt(1 + B*k^2) - the stiffness of a real string
        pushes the upper partials sharp, and B is small (1e-4 ish) rather than
        the heavy dispersion a delay line gives you
      * the hammer strikes about one eighth along the string, so partials with a
        node there are weakened - softened, not notched out
      * the felt acts as a lowpass whose corner opens up the harder you play,
        which is where nearly all of the "dynamics" of a piano lives
      * each partial decays at its own rate, fast up top, and carries a two
        stage envelope: the quick initial fall and the long aftersound
      * the lowest partials are doubled and detuned by half a cent, the way the
        two or three strings of one unison are, giving the slow shimmer

    The result is smooth and controllable: no comb filtering, no pluck, and the
    spectrum can be moved between a soft grand and a felt piano continuously.
*/
namespace wp
{

//==============================================================================
struct EngineSettings
{
    int   model        = 0;      // 0 smooth grand, 1 bright grand, 2 upright, 3 felt
    float tone         = 0.0f;   // -1 dark .. +1 bright
    float attack       = 0.35f;  // hammer noise and thump
    float decayScale   = 1.0f;   // 0.5 .. 2
    float dynamicRange = 26.0f;  // dB between softest and loudest
    float spread       = 0.40f;  // stereo spread by key position
};

//==============================================================================
/** Voicing of one piano model: everything that separates a grand from a felt. */
struct Voicing
{
    float tilt;          // spectral roll off exponent at low velocity
    float tiltLoud;      // ... and at full velocity
    float cutoffHz;      // hammer lowpass corner at low velocity
    float cutoffOctaves; // how far that corner opens by full velocity
    float decayScale;    // overall sustain multiplier
    float inharmonicity; // multiplier on B
    float strikePos;     // hammer position along the string
    float noise;         // attack noise level
    float thump;         // key/action thump level
};

const Voicing& voicingFor (int model);

//==============================================================================
class PianoVoice
{
public:
    static constexpr int maxPartials = 72;
    static constexpr int maxBeats    = 10;

    void reset();

    void start (int midiNote, float velocity, const EngineSettings& s, double sampleRate);
    void release (bool pedalHeld, double sampleRate);
    void damp (double sampleRate);

    /** Adds this voice into a mono scratch buffer, then pans it out. */
    void render (float* scratch, float* left, float* right, int numSamples, juce::Random& rng);

    bool isActive() const noexcept { return active; }
    bool isHeld() const noexcept   { return keyHeld; }
    bool isSustained() const noexcept { return sustained; }
    bool isSostenuto() const noexcept { return sostenuto; }
    void setSostenuto (bool s) noexcept { sostenuto = s; }
    int  getNote() const noexcept  { return note; }
    float getLevel() const noexcept { return partials[0].aFast + partials[0].aSlow; }
    juce::uint32 getStartOrder() const noexcept { return startOrder; }

private:
    /** One decaying sinusoid: an exact rotation plus a two stage envelope. */
    struct Partial
    {
        float cosW = 1.0f, sinW = 0.0f;
        float x = 1.0f, y = 0.0f;
        float aFast = 0.0f, aSlow = 0.0f;
        float dFast = 0.9f, dSlow = 0.99f;
    };

    void addPartial (int index, double freq, double sampleRate, float amplitude,
                     float t60, float fastFraction);

    // main partials live at [0, numPartials); the detuned unison twins of the
    // lowest few sit in a fixed block at [maxPartials, maxPartials + numBeats)
    // so that retiring silent high partials never disturbs them
    std::array<Partial, maxPartials + maxBeats> partials;
    int numPartials = 0;
    int numBeats = 0;
    int topActive = 0;

    // attack transient
    float noiseAmp = 0.0f, noiseDecay = 0.0f, noiseState = 0.0f, noiseCoef = 0.4f;
    float thumpAmp = 0.0f, thumpDecay = 0.0f, thumpPhase = 0.0f, thumpInc = 0.0f;

    int   note = 60;
    bool  active = false, keyHeld = false, sustained = false, sostenuto = false;
    float panL = 0.7071f, panR = 0.7071f;
    float amplitude = 1.0f;
    juce::uint32 startOrder = 0;

    friend class PianoEngine;
};

//==============================================================================
class PianoEngine
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    void setSettings (const EngineSettings& s) { settings = s; }

    void noteOn (int midiNote, float velocity);
    void noteOff (int midiNote);
    void sustainPedal (float value);
    void sostenutoPedal (bool down);
    void softPedal (float value);
    void allNotesOff();
    void panic();

    void render (float* left, float* right, int numSamples);

private:
    static constexpr int maxVoices = 32;

    PianoVoice* findVoiceToSteal (int midiNote);

    std::array<PianoVoice, maxVoices> voices;
    std::vector<float> scratch;

    EngineSettings settings;
    double sr = 44100.0;
    float pedal = 0.0f;
    float soft = 0.0f;
    juce::uint32 orderCounter = 0;
    juce::Random rng { 20250406 };

    // soundboard colouration on the summed piano bus
    std::array<juce::dsp::IIR::Filter<float>, 4> bodyL, bodyR;
};

} // namespace wp
