#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>

namespace wpui
{

/** Preset browser: title, previous/next stepping and a categorised menu. */
class PresetBar : public juce::Component
{
public:
    PresetBar();

    void paint (juce::Graphics&) override;
    void resized() override;

    void setPreset (int index, bool modified);

    std::function<void (int)> onPresetChosen;

private:
    void step (int delta);

    juce::TextButton prev { "<" }, next { ">" };
    juce::TextButton chooser;
    juce::Label blurb;

    int currentIndex = 0;
    bool isModified = false;
};

} // namespace wpui
