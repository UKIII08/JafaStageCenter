#pragma once

#include <juce_audio_utils/juce_audio_utils.h>

#include "PluginProcessor.h"
#include "gui/WorshipLookAndFeel.h"
#include "Presets.h"

//==============================================================================
/** Rotary control with a caption and a live readout underneath. */
class ParamKnob : public juce::Component
{
public:
    ParamKnob (juce::AudioProcessorValueTreeState& apvts, const juce::String& paramID,
               const juce::String& caption, int maxDiameter = 64);

    void resized() override;
    void setCaptionSize (float points);

private:
    juce::Slider slider;
    juce::Label name, value;
    juce::RangedAudioParameter* parameter = nullptr;
    int maxDiameter = 64;
    float captionSize = 0.0f;
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
/** The preset browser: a real list, because scrolling one at a time with arrows
    is no way to find a sound between two songs. */
class PresetList : public juce::Component, private juce::ListBoxModel
{
public:
    PresetList();

    int getNumRows() override;
    void paintListBoxItem (int row, juce::Graphics&, int width, int height, bool selected) override;
    void listBoxItemClicked (int row, const juce::MouseEvent&) override;

    void resized() override;
    void setSelected (int index);

    /** Re-reads the user presets from disk and keeps the selection if it can. */
    void refreshUserPresets();

    /** Rows past the factory list are the user's own. */
    bool isUserRow (int row) const noexcept { return row >= (int) presets::factory().size(); }
    juce::String userNameForRow (int row) const;
    int rowForUserName (const juce::String& name) const;

    std::function<void (int)> onPresetChosen;

private:
    juce::ListBox list { "presets", this };
    juce::StringArray userNames;
    int selected = 0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PresetList)
};

//==============================================================================
/** One stomp: a big latching switch that lights up, like a pedal on a board. */
class StompButton : public juce::Button
{
public:
    StompButton (juce::AudioProcessorValueTreeState&, const juce::String& paramID,
                 const juce::String& caption, juce::Colour lit);

    void paintButton (juce::Graphics&, bool highlighted, bool down) override;

private:
    juce::String caption;
    juce::Colour lit;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> attachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (StompButton)
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
    void savePreset();
    void deletePreset();
    void applyUserPreset (const juce::String& name);
    void setLiveMode (bool shouldBeLive);
    void setPresetListShown (bool shouldBeShown);
    void addKnob (juce::OwnedArray<ParamKnob>& group, const juce::String& paramID,
                  const juce::String& caption, int maxDiameter = 64);
    static void layoutGrid (juce::OwnedArray<ParamKnob>& group, juce::Rectangle<int> area, int columns);

    void layoutLive (juce::Rectangle<int> area);
    void layoutEdit (juce::Rectangle<int> area);

    WorshipPianoProcessor& processor;
    wpui::WorshipLookAndFeel lookAndFeel;

    bool liveMode = true;

    /*  The full preset list can be folded away, leaving the quick bar as the only
        way to change sound. Playing a set is six buttons, not twenty rows.
    */
    bool showPresetList = true;

    //---- top bar -------------------------------------------------------------
    juce::TextButton liveTab { "LIVE" }, editTab { "EDIT" }, panicButton { "PANIC" };
    juce::TextButton presetPrev { "<" }, presetNext { ">" };
    juce::TextButton savePresetButton { "ZAPISZ" }, deletePresetButton { "USUN" };
    juce::TextButton favouriteButton { "*" };

    //---- the pedalboard ------------------------------------------------------
    juce::OwnedArray<StompButton> stomps;
    juce::Rectangle<int> stompPanel;

    //---- quick access --------------------------------------------------------
    juce::OwnedArray<juce::TextButton> quickButtons;
    juce::TextButton presetListButton { "PRESETY" };
    juce::Rectangle<int> quickPanel;
    juce::StringArray quickNames;
    void refreshQuickAccess();
    void toggleFavourite();
    juce::String currentUserPreset;
    std::unique_ptr<juce::AlertWindow> nameWindow;
    juce::Label presetName, presetBlurb;

    //---- live view -----------------------------------------------------------
    PresetList presetList;
    std::unique_ptr<ParamKnob> soakKnob;
    juce::OwnedArray<ParamKnob> liveKnobs;

    juce::TextButton transposeDown { "-" }, transposeUp { "+" };
    juce::Label transposeValue, transposeCaption;
    juce::ToggleButton splitButton { "SPLIT" };
    juce::Slider splitPointSlider;
    juce::Label splitPointLabel;
    juce::ToggleButton freezeButton { "FREEZE" };

    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> splitAttachment, freezeAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> splitPointAttachment;

    //---- edit view -----------------------------------------------------------
    juce::OwnedArray<ParamKnob> pianoKnobs, padKnobs, toneKnobs, moveKnobs, ambienceKnobs, outputKnobs;

    juce::ComboBox delayDivBox, machineBox, shimmerModeBox, revTimeBox, pedalBox, padTypeBox;
    juce::ToggleButton delaySyncButton { "SYNC" };
    juce::TextButton loadButton { "Sample library..." };
    juce::Label tempoLabel, libraryLabel;
    std::unique_ptr<juce::FileChooser> chooser;

    std::unique_ptr<juce::AudioProcessorValueTreeState::ComboBoxAttachment>
        delayDivAttachment, machineAttachment, shimmerModeAttachment,
        revTimeAttachment, pedalAttachment, padTypeAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> delaySyncAttachment;

    //---- shared --------------------------------------------------------------
    LevelMeter meter;
    juce::MidiKeyboardComponent keyboard;

    juce::Rectangle<int> pianoPanel, padPanel, tonePanel, movementPanel, ambiencePanel, soakPanel;
    juce::Rectangle<int> livePresetPanel, liveMixPanel, livePerformPanel;

    int lastPresetIndex = -2;
    bool lastModified = false;
    bool lastLibraryLive = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (WorshipPianoEditor)
};
