#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <vector>

#include "Parameters.h"
#include "dsp/PadLayer.h"
#include "dsp/EffectChain.h"
#include "dsp/SampleLibrary.h"

class WorshipPianoProcessor : public juce::AudioProcessor,
                              private juce::AudioProcessorValueTreeState::Listener
{
public:
    WorshipPianoProcessor();
    ~WorshipPianoProcessor() override;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return JucePlugin_Name; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 12.0; }

    int getNumPrograms() override;
    int getCurrentProgram() override;
    void setCurrentProgram (int index) override;
    const juce::String getProgramName (int index) override;
    void changeProgramName (int, const juce::String&) override {}

    /*  Hosts call this to clear tails - on transport stop, and between passes of
        an offline bounce. Not implementing it meant a reverb tail leaked from
        one render into the next.
    */
    void reset() override;

    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    juce::AudioProcessorValueTreeState apvts;

    /** -1 when the user has moved a knob since the preset was loaded. */
    int getPresetIndex() const noexcept { return currentPreset; }
    void loadPreset (int index);
    void markPresetModified() noexcept { presetModified = true; }
    bool isPresetModified() const noexcept { return presetModified.load(); }

    float getOutputLevel() const noexcept { return outputLevel.load(); }
    double getHostTempo() const noexcept { return hostTempo; }

    juce::MidiKeyboardState keyboardState;

    /** Live value of the expression pedal, 0 when no pedal is being used. */
    float getPedalSoak() const noexcept { return pedalSoak.load(); }
    void panic();

    //--------------------------------------------------------------------------
    /*  Sample library: loaded on a background thread, swapped in as a pointer.

        Once loaded a library stays in memory, so asking for one that has already
        been read is an instant pointer swap rather than another minute of disk.
        That is what makes a per-preset library usable at all - a preset button
        that stopped the stage for a re-read of a gigabyte would never be pressed
        twice.
    */
    void loadSampleLibrary (const juce::File& fileOrFolder);
    void clearSampleLibrary();

    /** Path the current library came from, empty when none is loaded. */
    juce::String getLibraryPath() const;

    juce::String getLibraryStatus() const;
    float getLoadProgress() const noexcept { return loadProgress.load(); }
    bool  isLoadingLibrary() const noexcept { return loader != nullptr && loader->isThreadRunning(); }

    /** True once a loaded library has actually reached the audio thread. */
    bool isSampleSourceActive() const noexcept { return sampler.hasLibrary(); }

private:
    void parameterChanged (const juce::String& id, float newValue) override;
    void updateSettings();
    void renderSegment (juce::AudioBuffer<float>& buffer, int start, int numSamples);
    void handleMidiMessage (const juce::MidiMessage& m);
    float delaySamplesForDivision (int division) const;

    template <typename T = float>
    T param (const char* id) const
    {
        return (T) apvts.getRawParameterValue (id)->load();
    }

    wp::PadLayer pad;
    wp::EffectChain effects;

    double sampleRate = 44100.0;
    double hostTempo = 120.0;
    int    currentPreset = 0;
    std::atomic<bool> presetModified { false };
    std::atomic<bool> loadingPreset { false };

    std::atomic<float> outputLevel { 0.0f };
    std::atomic<float> pedalSoak { 0.0f };
    std::atomic<bool> panicRequested { false };

    // A key can be released after the transpose has moved, so the shift used
    // when it went down has to be remembered per key.
    std::array<int8_t, 128> noteTranspose {};
    std::array<bool, 128> notePadOnly {};

    // the pad is rendered separately so it can be sent into the ambience much
    // harder than the piano is - that difference is the whole soaking layer
    juce::AudioBuffer<float> padBuffer;

    //--------------------------------------------------------------------------
    class LibraryLoader : public juce::Thread
    {
    public:
        LibraryLoader (WorshipPianoProcessor& p, juce::File f)
            : juce::Thread ("Worship Piano sample loader"), owner (p), source (std::move (f)) {}

        void run() override;

        std::atomic<bool> abort { false };

    private:
        WorshipPianoProcessor& owner;
        juce::File source;
    };

    void libraryLoaded (wp::SampleLibrary::Ptr library, const juce::String& error);

    /** Points the sampler at a library that is already in memory. */
    void activateLibrary (wp::SampleLibrary::Ptr library);

    wp::SampleLibrary::Ptr findCachedLibrary (const juce::String& path);
    void trimLibraryCache();

    wp::SamplerEngine sampler;
    std::unique_ptr<LibraryLoader> loader;

    /*  Every library that has been read this session, newest use last. Doubles as
        what keeps them alive: the audio thread's reference is never the last one,
        so nothing is ever freed on it.
    */
    struct CachedLibrary
    {
        wp::SampleLibrary::Ptr library;
        juce::uint32 lastUsed = 0;
    };

    std::vector<CachedLibrary> libraryCache;
    juce::uint32 libraryUseCounter = 0;

    // two full piano libraries in memory at once is already a lot to ask of a
    // laptop; past this the least recently played one goes
    static constexpr juce::int64 maxCachedLibraryBytes = 2LL * 1024 * 1024 * 1024;

    juce::CriticalSection statusLock;
    juce::String libraryStatus { "Brak biblioteki - silnik modelowany" };
    juce::String libraryPath;
    std::atomic<float> loadProgress { 0.0f };

    JUCE_DECLARE_WEAK_REFERENCEABLE (WorshipPianoProcessor)
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (WorshipPianoProcessor)
};
