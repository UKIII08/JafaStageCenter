#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>
#include <vector>

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

    /*  Diagnostics. hijacked counts notes started on a voice that was still
        sounding - the artefact, which must stay at zero. stolen counts voices
        taken properly, by fading first, and exists so a test can prove it
        actually exercised the stealing path rather than never filling up.
    */
    int getHijackedVoiceCount() const noexcept { return hijacked; }
    int getStolenVoiceCount() const noexcept { return stolen; }

private:
    /*  Thirty-two, not sixteen. The pad follows every note the piano plays, and
        this instrument is played with the sustain pedal down - so a couple of
        five note chords into a song, sixteen was already full and every new note
        was taking one off something still sounding.
    */
    static constexpr int maxVoices = 32;

    /*  Seven, the way the JP-8000 does it, not three.

        Three detuned saws give one beating; seven with unevenly spaced offsets
        fill the space around every harmonic instead, and that filling is what
        is heard as thickness rather than as chorus. The offsets and the two gain
        curves below are Adam Szabo's reverse engineering of the original
        (Bachelor thesis, "How to Emulate the Super Saw", 2010), which is the
        reference nearly every software supersaw is built from.
    */
    static constexpr int oscsPerVoice = 7;

    // how fast a voice that has to be taken gets out of the way
    static constexpr float stealFadeMs = 6.0f;

    struct Voice
    {
        std::array<float, oscsPerVoice> phase {};
        std::array<float, oscsPerVoice> inc {};

        // running integral, for the characters built by integrating a square
        std::array<float, oscsPerVoice> integrator {};
        float env = 0.0f;
        float target = 0.0f;
        float attackCoef = 0.001f, releaseCoef = 0.001f;
        float panL = 0.7071f, panR = 0.7071f;
        float velocity = 0.8f;
        int   note = -1;
        bool  held = false, sustained = false, active = false;

        /*  A voice being taken for a new note fades out first and starts the new
            one from silence once it is gone. Repitching it where it stands is
            what a listener hears as a blip: the sounding note jumps to another
            frequency at full volume, mid-phase, dragging the filter state with
            it. Six milliseconds of fade is inaudible under a pad that takes the
            better part of a second to swell.
        */
        bool  stealing = false;
        int   pendingNote = -1;
        float pendingVelocity = 0.8f;

        // one state variable filter per side: the oscillators are spread across
        // the stereo field rather than summed and panned as a block
        float ic1L = 0.0f, ic2L = 0.0f, ic1R = 0.0f, ic2R = 0.0f;
    };

    /** Band-limited saw evaluated at a phase, without advancing it. */
    static inline float polyBlepSawAt (float phase, float inc) noexcept;

    inline float oscillator (float& phase, float inc, float& integrator) noexcept;

    /** Points a voice at a note, from silence. */
    void startNote (Voice&, int midiNote, float velocity);

    /*  The oscillators run at twice the host's rate and are filtered back down.

        polyBLEP band-limits a saw, but three of the five characters are made by
        multiplying that saw by itself - squaring for the bell edge, folding
        through abs() for the triangle, a narrow pulse for the breathy one. Every
        one of those doubles the bandwidth, which puts harmonics above Nyquist
        that fold back down and land between the real ones, at frequencies that
        have nothing to do with the note. That is what makes a pad sound gritty
        and cheap rather than bright.

        Generating at 2x moves the fold-back point an octave up, and the
        half-band filter below removes what lands above the host's Nyquist before
        the rate comes back down.
    */
    static constexpr int oversample = 2;
    static constexpr int decimatorTaps = 31;

    struct Decimator
    {
        void reset() noexcept { state.fill (0.0f); index = 0; }

        /** Feeds one oversampled sample; the result is only read every other one. */
        inline float process (float x) noexcept
        {
            state[(size_t) index] = x;
            index = (index + 1) % decimatorTaps;

            float sum = 0.0f;

            for (int i = 0; i < decimatorTaps; ++i)
                sum += state[(size_t) ((index + i) % decimatorTaps)] * coefficients[(size_t) i];

            return sum;
        }

        std::array<float, decimatorTaps> state {};
        int index = 0;
        static const std::array<float, decimatorTaps> coefficients;
    };

    std::array<Voice, maxVoices> voices;
    int hijacked = 0, stolen = 0;
    PadSettings settings;

    // the rate the oscillators run at: twice what the host asked for
    double sr = 44100.0;
    bool pedalDown = false;

    Decimator decimateL, decimateR;
    std::vector<float> scratchL, scratchR;

    // the pad stomp drives level straight to zero, and a pad is a sustained
    // sound - cutting one is far more audible than cutting a decaying note
    juce::SmoothedValue<float> smoothedGain;

    float lfoPhase = 0.0f, lfoInc = 0.0f;
    juce::dsp::IIR::Filter<float> dcL, dcR;
};

} // namespace wp
