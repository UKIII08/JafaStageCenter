#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

#include "Parameters.h"
#include "dsp/PianoEngine.h"
#include "dsp/PadLayer.h"
#include "dsp/EffectChain.h"

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

    wp::PianoEngine piano;
    wp::PadLayer pad;
    wp::EffectChain effects;

    double sampleRate = 44100.0;
    double hostTempo = 120.0;
    int    currentPreset = 0;
    std::atomic<bool> presetModified { false };
    std::atomic<bool> loadingPreset { false };

    std::atomic<float> outputLevel { 0.0f };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (WorshipPianoProcessor)
};
