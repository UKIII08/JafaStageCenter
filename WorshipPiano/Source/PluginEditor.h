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
               const juce::String& caption, int maxDiameter = 64);

    void resized() override;

private:
    juce::Slider slider;
    juce::Label name, value;
    juce::RangedAudioParameter* parameter = nullptr;
    int maxDiameter = 64;
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
    void showLibraryMenu();
    void addKnob (juce::OwnedArray<ParamKnob>& group, const juce::String& paramID,
                  const juce::String& caption, int maxDiameter = 64);
    static void layoutGrid (juce::OwnedArray<ParamKnob>& group, juce::Rectangle<int> area, int columns);

    WorshipPianoProcessor& processor;
    wpui::WorshipLookAndFeel lookAndFeel;
    wpui::PresetBar presetBar;

    juce::OwnedArray<ParamKnob> pianoKnobs, padKnobs, toneKnobs, moveKnobs, ambienceKnobs, outputKnobs;
    std::unique_ptr<ParamKnob> soakKnob;

    juce::ComboBox modelBox, delayDivBox, machineBox, shimmerModeBox, sourceBox, revTimeBox;
    juce::ToggleButton delaySyncButton { "SYNC" }, freezeButton { "FREEZE" };
    juce::TextButton loadButton { "Sample library..." };
    juce::Label tempoLabel, libraryLabel;
    std::unique_ptr<juce::FileChooser> chooser;

    std::unique_ptr<juce::AudioProcessorValueTreeState::ComboBoxAttachment>
        modelAttachment, delayDivAttachment, machineAttachment, shimmerModeAttachment,
        sourceAttachment, revTimeAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment>
        delaySyncAttachment, freezeAttachment;

    LevelMeter meter;
    juce::MidiKeyboardComponent keyboard;

    juce::Rectangle<int> pianoPanel, padPanel, tonePanel, movementPanel, ambiencePanel, soakPanel;
    int lastPresetIndex = -2;
    bool lastModified = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (WorshipPianoEditor)
};
