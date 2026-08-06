#pragma once

#include <juce_audio_utils/juce_audio_utils.h>

#include "PluginProcessor.h"
#include "gui/WorshipLookAndFeel.h"
#include "gui/PresetBar.h"

//==============================================================================
/** Rotary control with a caption and a live readout underneath. */
class ParamKnob : public juce::Component
{
public:
    ParamKnob (juce::AudioProcessorValueTreeState& apvts, const juce::String& paramID,
               const juce::String& caption);

    void resized() override;

private:
    juce::Slider slider;
    juce::Label name, value;
    juce::RangedAudioParameter* parameter = nullptr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> attachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ParamKnob)
};

//==============================================================================
class LevelMeter : public juce::Component, private juce::Timer
{
public:
    explicit LevelMeter (WorshipPianoProcessor&);
    void paint (juce::Graphics&) override;

private:
    void timerCallback() override;

    WorshipPianoProcessor& processor;
    float displayed = 0.0f;
};

//==============================================================================
class WorshipPianoEditor : public juce::AudioProcessorEditor, private juce::Timer
{
public:
    explicit WorshipPianoEditor (WorshipPianoProcessor&);
    ~WorshipPianoEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;
    void addKnob (juce::OwnedArray<ParamKnob>& group, const juce::String& paramID,
                  const juce::String& caption);
    static void layoutGrid (juce::OwnedArray<ParamKnob>& group, juce::Rectangle<int> area, int columns);

    WorshipPianoProcessor& processor;
    wpui::WorshipLookAndFeel lookAndFeel;
    wpui::PresetBar presetBar;

    juce::OwnedArray<ParamKnob> pianoKnobs, padKnobs, toneKnobs, moveKnobs, spaceKnobs;

    juce::ComboBox modelBox, delayDivBox;
    juce::ToggleButton delaySyncButton { "SYNC" };
    juce::Label tempoLabel;

    std::unique_ptr<juce::AudioProcessorValueTreeState::ComboBoxAttachment> modelAttachment, delayDivAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> delaySyncAttachment;

    LevelMeter meter;
    juce::MidiKeyboardComponent keyboard;

    juce::Rectangle<int> pianoPanel, padPanel, tonePanel, movementPanel, spacePanel;
    int lastPresetIndex = -2;
    bool lastModified = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (WorshipPianoEditor)
};
