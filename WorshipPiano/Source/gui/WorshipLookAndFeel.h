#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

namespace wpui
{
    namespace colours
    {
        const juce::Colour background   { 0xff14161b };
        const juce::Colour panel        { 0xff1c1f27 };
        const juce::Colour panelEdge    { 0xff2a2e39 };
        const juce::Colour text         { 0xffd6d9e0 };
        const juce::Colour textDim      { 0xff7c8290 };
        const juce::Colour accent       { 0xffd8a24a };   // warm brass
        const juce::Colour accentSoft   { 0xff8a6b3a };
        const juce::Colour track        { 0xff2e3341 };
        const juce::Colour highlight    { 0xff6fa8dc };
    }

    class WorshipLookAndFeel : public juce::LookAndFeel_V4
    {
    public:
        WorshipLookAndFeel();

        void drawRotarySlider (juce::Graphics&, int x, int y, int width, int height,
                               float sliderPos, float startAngle, float endAngle,
                               juce::Slider&) override;

        void drawComboBox (juce::Graphics&, int width, int height, bool isButtonDown,
                           int buttonX, int buttonY, int buttonW, int buttonH,
                           juce::ComboBox&) override;

        void drawButtonBackground (juce::Graphics&, juce::Button&, const juce::Colour& backgroundColour,
                                   bool shouldDrawButtonAsHighlighted, bool shouldDrawButtonAsDown) override;

        void drawToggleButton (juce::Graphics&, juce::ToggleButton&,
                               bool shouldDrawButtonAsHighlighted, bool shouldDrawButtonAsDown) override;

        juce::Font getLabelFont (juce::Label&) override;
        juce::Font getComboBoxFont (juce::ComboBox&) override;
        juce::Font getTextButtonFont (juce::TextButton&, int buttonHeight) override;
        juce::Font getPopupMenuFont() override;
    };
}
