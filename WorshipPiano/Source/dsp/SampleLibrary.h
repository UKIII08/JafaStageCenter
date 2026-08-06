#pragma once

#include <juce_audio_formats/juce_audio_formats.h>
#include <atomic>
#include <vector>

/*
    A sampled piano source.

    The modelled engine has a ceiling: a struck piano string is a chaotic,
    non-linear event and additive synthesis will not fool anybody on the attack.
    So the plugin can also play a real sample library, and everything downstream
    - the pad, the ambience, the shimmer, the soaking layer - works on that
    instead.

    Two formats are understood:

      * SFZ, the subset that piano libraries actually use (key and velocity
        zones, root note, tuning, loop points, release times)
      * a plain folder of WAV or FLAC files, where the root note is taken from
        the file name (C4, A#2, or a bare MIDI number)

    Loading happens on a background thread. The audio thread only ever sees a
    library that is already complete, swapped in as a single pointer.
*/
namespace wp
{

class SampleLibrary : public juce::ReferenceCountedObject
{
public:
    using Ptr = juce::ReferenceCountedObjectPtr<SampleLibrary>;

    // the non-copyable macro below declares a copy constructor, which would
    // otherwise suppress the implicit default one
    SampleLibrary() = default;

    struct Region
    {
        juce::AudioBuffer<float> audio;
        double sourceRate = 44100.0;

        int rootNote = 60;
        int loKey = 0, hiKey = 127;
        int loVel = 1, hiVel = 127;

        bool  loops = false;
        int   loopStart = 0, loopEnd = 0;

        float gain = 1.0f;          // from volume=
        float tuneRatio = 1.0f;     // from tune= / transpose=
        float releaseSeconds = 0.4f;
        float attackSeconds = 0.0f;
    };

    /** @returns an error message, or an empty string on success. */
    juce::String loadFrom (const juce::File& fileOrFolder,
                           std::function<void (float)> onProgress = {},
                           const std::atomic<bool>* shouldAbort = nullptr);

    /** Best matching region for a note and velocity, or nullptr. */
    const Region* find (int midiNote, int velocity) const noexcept
    {
        const int index = lookup[(size_t) (juce::jlimit (0, 127, midiNote) * 128
                                           + juce::jlimit (0, 127, velocity))];
        return index >= 0 ? &regions[(size_t) index] : nullptr;
    }

    bool isEmpty() const noexcept { return regions.empty(); }
    int  getNumRegions() const noexcept { return (int) regions.size(); }
    juce::int64 getMemoryUsage() const noexcept { return memoryBytes; }
    const juce::String& getName() const noexcept { return name; }
    const juce::String& getSourcePath() const noexcept { return sourcePath; }

private:
    juce::String loadSfz (const juce::File&, std::function<void (float)>&, const std::atomic<bool>*);
    juce::String loadFolder (const juce::File&, std::function<void (float)>&, const std::atomic<bool>*);
    bool readAudio (const juce::File&, Region&, juce::AudioFormatManager&);
    void buildLookup();

    std::vector<Region> regions;
    std::vector<int> lookup;          // 128 notes x 128 velocities
    juce::int64 memoryBytes = 0;
    juce::String name, sourcePath;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (SampleLibrary)
};

//==============================================================================
/** Polyphonic playback of a SampleLibrary, with the same pedal behaviour as the
    modelled engine so the two are interchangeable. */
class SamplerEngine
{
public:
    void prepare (double sampleRate, int maxBlockSize);
    void reset();

    /** Called from the message thread; the audio thread picks it up next block. */
    void setLibrary (SampleLibrary::Ptr newLibrary) { pending = std::move (newLibrary); libraryDirty = true; }
    SampleLibrary::Ptr getLibrary() const { return active; }

    void setDynamics (float rangeDb) noexcept { dynamicRange = rangeDb; }
    void setTone (float t) noexcept { tone = t; }
    void setReleaseScale (float s) noexcept { releaseScale = s; }

    void noteOn (int midiNote, float velocity);
    void noteOff (int midiNote);
    void sustainPedal (float value);
    void softPedal (float value);
    void allNotesOff();
    void panic();

    void render (float* left, float* right, int numSamples);

    bool hasLibrary() const noexcept { return active != nullptr && ! active->isEmpty(); }

private:
    static constexpr int maxVoices = 48;

    struct Voice
    {
        const SampleLibrary::Region* region = nullptr;
        double position = 0.0;
        double increment = 1.0;
        float  gain = 1.0f;
        float  env = 0.0f, envTarget = 0.0f, attackCoef = 1.0f, releaseCoef = 0.01f;
        float  toneStateL = 0.0f, toneStateR = 0.0f, toneCoef = 1.0f;
        int    note = -1;
        bool   held = false, sustained = false, active = false;
        juce::uint32 order = 0;
    };

    Voice* findVoice (int midiNote);

    std::array<Voice, maxVoices> voices;

    SampleLibrary::Ptr active, pending;
    std::atomic<bool> libraryDirty { false };

    double sr = 44100.0;
    float pedal = 0.0f, soft = 0.0f;
    float dynamicRange = 26.0f;
    float tone = 0.0f;
    float releaseScale = 1.0f;
    juce::uint32 orderCounter = 0;
};

} // namespace wp
