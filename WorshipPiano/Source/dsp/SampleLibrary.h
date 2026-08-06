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

      * SFZ, the subset that piano libraries actually use: global/group/region
        inheritance, key and velocity zones, root note, tuning, loop points,
        envelope times, and release-triggered damper samples
      * a plain folder of WAV or FLAC files, where the root note is taken from
        the file name (C4, A#2, or a bare MIDI number)

    Audio is kept as normalised 16 bit rather than float. A big piano library is
    hundreds of samples of ten seconds or more, which as float32 runs to well
    over a gigabyte; normalising each sample to its own peak first means the
    16 bit floor sits far enough down to be inaudible.

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
        std::vector<juce::int16> data;   // interleaved
        int numChannels = 1;
        int numFrames = 0;
        float scale = 1.0f / 32768.0f;   // undoes the normalisation on the way out
        double sourceRate = 44100.0;

        int rootNote = 60;
        int loKey = 0, hiKey = 127;
        int loVel = 1, hiVel = 127;

        bool  loops = false;
        int   loopStart = 0, loopEnd = 0;

        float gain = 1.0f;
        float tuneRatio = 1.0f;
        float releaseSeconds = 0.4f;
        float attackSeconds = 0.0f;
        float rtDecay = 0.0f;            // dB per second of key-down, release samples

        inline float sample (int frame, int channel) const noexcept
        {
            return (float) data[(size_t) (frame * numChannels + (numChannels > 1 ? channel : 0))] * scale;
        }
    };

    /** @returns an error message, or an empty string on success. */
    juce::String loadFrom (const juce::File& fileOrFolder,
                           std::function<void (float)> onProgress = {},
                           const std::atomic<bool>* shouldAbort = nullptr);

    const Region* find (int midiNote, int velocity) const noexcept
    {
        return lookupIn (regions, lookup, midiNote, velocity);
    }

    /** Damper noise sampled separately, played when the key comes back up. */
    const Region* findRelease (int midiNote, int velocity) const noexcept
    {
        return lookupIn (releases, releaseLookup, midiNote, velocity);
    }

    bool isEmpty() const noexcept { return regions.empty(); }
    int  getNumRegions() const noexcept { return (int) regions.size(); }
    int  getNumReleaseRegions() const noexcept { return (int) releases.size(); }
    juce::int64 getMemoryUsage() const noexcept { return memoryBytes; }
    const juce::String& getName() const noexcept { return name; }
    const juce::String& getSourcePath() const noexcept { return sourcePath; }

    /** Level correction that brings this library onto the same level as the
        modelled engine, which is what the rest of the chain is voiced against.
        Libraries are mastered to wildly different levels - a hot one otherwise
        lands inside the output limiter and every attack comes back distorted. */
    float getCalibrationGain() const noexcept { return calibrationGain; }

private:
    static const Region* lookupIn (const std::vector<Region>& list, const std::vector<int>& table,
                                   int midiNote, int velocity) noexcept
    {
        if (table.empty())
            return nullptr;

        const int index = table[(size_t) (juce::jlimit (0, 127, midiNote) * 128
                                          + juce::jlimit (0, 127, velocity))];
        return index >= 0 ? &list[(size_t) index] : nullptr;
    }

    juce::String loadSfz (const juce::File&, std::function<void (float)>&, const std::atomic<bool>*);
    juce::String loadFolder (const juce::File&, std::function<void (float)>&, const std::atomic<bool>*);
    bool readAudio (const juce::File&, Region&, juce::AudioFormatManager&);
    static void buildLookup (const std::vector<Region>&, std::vector<int>&);
    void calibrateLevel() noexcept;

    std::vector<Region> regions, releases;
    std::vector<int> lookup, releaseLookup;
    juce::int64 memoryBytes = 0;
    float calibrationGain = 1.0f;
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

    /*  Must be called from the audio thread every block, whatever source is
        selected. Doing the swap inside render() instead deadlocks: the host only
        renders the sampler once a library is active, and the library only
        becomes active inside render.
    */
    void updateLibrary() noexcept
    {
        if (libraryDirty.exchange (false))
        {
            for (auto& v : voices)
                v = Voice();

            // a plain pointer swap: the previous library is kept alive by the
            // processor, so nothing is freed on the audio thread
            active = pending;
        }
    }

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
    static constexpr int maxVoices = 64;

    /*  Start retiring the quietest voices here rather than at the hard ceiling.
        A piano sample runs for many seconds after it has stopped being audible,
        and with the sustain pedal down - which is how this instrument is
        actually played - those voices pile up until every new note has to evict
        a live one. Evicting a live voice restarts it from sample zero, and that
        discontinuity is a click. Keeping a margin means eviction happens to
        voices that have already faded out, silently.
    */
    static constexpr int softVoiceLimit = 44;

    // ~90 dB below full scale: at this level a voice cannot be heard even with
    // the whole polyphony stacked on top of it
    static constexpr float inaudible = 3.0e-5f;

    struct Voice
    {
        const SampleLibrary::Region* region = nullptr;
        double position = 0.0;
        double increment = 1.0;
        float  gain = 1.0f;
        float  env = 0.0f, envTarget = 0.0f, attackCoef = 1.0f, releaseCoef = 0.01f;
        float  toneStateL = 0.0f, toneStateR = 0.0f, toneCoef = 1.0f;
        int    note = -1;
        int    heldSamples = 0;
        int    quietBlocks = 0;
        bool   held = false, sustained = false, active = false, isRelease = false;
        bool   retiring = false;
        juce::uint32 order = 0;
    };

    Voice* findVoice (int midiNote, bool forRelease);
    void   startRelease (int midiNote, int heldSamples);
    void   retire (Voice&) noexcept;
    int    countActive() const noexcept;
    void   cullToSoftLimit() noexcept;

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
