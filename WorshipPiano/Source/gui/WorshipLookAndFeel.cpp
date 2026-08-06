#include "WorshipLookAndFeel.h"

using namespace juce;

namespace wpui
{

WorshipLookAndFeel::WorshipLookAndFeel()
{
    setColour (ResizableWindow::backgroundColourId, colours::background);
    setColour (Label::textColourId,                 colours::text);
    setColour (Slider::textBoxTextColourId,         colours::text);
    setColour (Slider::textBoxOutlineColourId,      Colours::transparentBlack);
    setColour (Slider::textBoxBackgroundColourId,   Colours::transparentBlack);
    setColour (ComboBox::backgroundColourId,        colours::panel);
    setColour (ComboBox::textColourId,              colours::text);
    setColour (ComboBox::outlineColourId,           colours::panelEdge);
    setColour (ComboBox::arrowColourId,             colours::accent);
    setColour (PopupMenu::backgroundColourId,       colours::panel);
    setColour (PopupMenu::textColourId,             colours::text);
    setColour (PopupMenu::highlightedBackgroundColourId, colours::accentSoft);
    setColour (PopupMenu::highlightedTextColourId,  Colours::white);
    setColour (TextButton::buttonColourId,          colours::panel);
    setColour (TextButton::textColourOnId,          colours::text);
    setColour (TextButton::textColourOffId,         colours::text);
}

void WorshipLookAndFeel::drawRotarySlider (Graphics& g, int x, int y, int width, int height,
                                           float sliderPos, float startAngle, float endAngle,
                                           Slider& slider)
{
    const auto bounds = Rectangle<int> (x, y, width, height).toFloat().reduced (3.0f);
    const auto radius = jmin (bounds.getWidth(), bounds.getHeight()) * 0.5f;
    const auto centre = bounds.getCentre();
    const auto angle = startAngle + sliderPos * (endAngle - startAngle);
    const auto lineWidth = jmax (2.0f, radius * 0.16f);
    const auto arcRadius = radius - lineWidth * 0.5f;

    // body
    g.setColour (colours::panelEdge.darker (0.4f));
    g.fillEllipse (bounds.reduced (lineWidth * 1.35f));

    // track
    Path track;
    track.addCentredArc (centre.x, centre.y, arcRadius, arcRadius, 0.0f, startAngle, endAngle, true);
    g.setColour (colours::track);
    g.strokePath (track, PathStrokeType (lineWidth, PathStrokeType::curved, PathStrokeType::rounded));

    // value arc - bipolar controls fill outwards from the middle
    const bool bipolar = slider.getMinimum() < 0.0 && slider.getMaximum() > 0.0
                         && std::abs (slider.getMinimum() + slider.getMaximum()) < 0.001;
    const float from = bipolar ? (startAngle + endAngle) * 0.5f : startAngle;

    if (std::abs (angle - from) > 0.001f)
    {
        Path value;
        value.addCentredArc (centre.x, centre.y, arcRadius, arcRadius, 0.0f,
                             jmin (from, angle), jmax (from, angle), true);
        g.setColour (slider.isEnabled() ? colours::accent : colours::textDim);
        g.strokePath (value, PathStrokeType (lineWidth, PathStrokeType::curved, PathStrokeType::rounded));
    }

    // pointer
    Path pointer;
    const float pointerLength = radius * 0.52f;
    const float pointerThickness = jmax (1.6f, radius * 0.09f);
    pointer.addRoundedRectangle (-pointerThickness * 0.5f, -radius * 0.86f,
                                 pointerThickness, pointerLength, pointerThickness * 0.5f);
    pointer.applyTransform (AffineTransform::rotation (angle).translated (centre));
    g.setColour (colours::text);
    g.fillPath (pointer);

    g.setColour (colours::panelEdge);
    g.drawEllipse (bounds.reduced (lineWidth * 1.35f), 1.0f);
}

void WorshipLookAndFeel::drawComboBox (Graphics& g, int width, int height, bool,
                                       int, int, int, int, ComboBox& box)
{
    const auto bounds = Rectangle<float> (0.0f, 0.0f, (float) width, (float) height).reduced (0.5f);
    const float corner = 4.0f;

    g.setColour (colours::panel.brighter (box.isMouseOver() ? 0.18f : 0.06f));
    g.fillRoundedRectangle (bounds, corner);
    g.setColour (colours::panelEdge);
    g.drawRoundedRectangle (bounds, corner, 1.0f);

    Path arrow;
    const float cx = (float) width - 14.0f;
    const float cy = (float) height * 0.5f;
    arrow.startNewSubPath (cx - 4.0f, cy - 2.0f);
    arrow.lineTo (cx, cy + 2.5f);
    arrow.lineTo (cx + 4.0f, cy - 2.0f);

    g.setColour (colours::accent);
    g.strokePath (arrow, PathStrokeType (1.6f, PathStrokeType::curved, PathStrokeType::rounded));
}

void WorshipLookAndFeel::drawButtonBackground (Graphics& g, Button& button, const Colour&,
                                               bool shouldDrawButtonAsHighlighted,
                                               bool shouldDrawButtonAsDown)
{
    const auto bounds = button.getLocalBounds().toFloat().reduced (0.5f);
    const bool on = button.getToggleState() || shouldDrawButtonAsDown;

    g.setColour (on ? colours::accentSoft
                    : colours::panel.brighter (shouldDrawButtonAsHighlighted ? 0.2f : 0.06f));
    g.fillRoundedRectangle (bounds, 4.0f);

    g.setColour (on ? colours::accent : colours::panelEdge);
    g.drawRoundedRectangle (bounds, 4.0f, 1.0f);
}

void WorshipLookAndFeel::drawToggleButton (Graphics& g, ToggleButton& button, bool isHighlighted, bool)
{
    const auto bounds = button.getLocalBounds().toFloat().reduced (0.5f);
    const bool on = button.getToggleState();

    g.setColour (on ? colours::accentSoft : colours::panel.brighter (isHighlighted ? 0.2f : 0.06f));
    g.fillRoundedRectangle (bounds, 4.0f);
    g.setColour (on ? colours::accent : colours::panelEdge);
    g.drawRoundedRectangle (bounds, 4.0f, 1.0f);

    g.setColour (on ? Colours::white : colours::textDim);
    g.setFont (Font (FontOptions (jmin (13.0f, bounds.getHeight() * 0.6f))).withStyle (Font::bold));
    g.drawText (button.getButtonText(), bounds, Justification::centred, false);
}

Font WorshipLookAndFeel::getLabelFont (Label& label)
{
    return Font (FontOptions (jlimit (10.0f, 20.0f, (float) label.getHeight() * 0.72f)));
}

Font WorshipLookAndFeel::getComboBoxFont (ComboBox& box)
{
    return Font (FontOptions (jlimit (11.0f, 18.0f, (float) box.getHeight() * 0.55f)));
}

Font WorshipLookAndFeel::getTextButtonFont (TextButton&, int buttonHeight)
{
    return Font (FontOptions (jlimit (11.0f, 16.0f, (float) buttonHeight * 0.5f)));
}

Font WorshipLookAndFeel::getPopupMenuFont()
{
    return Font (FontOptions (14.0f));
}

} // namespace wpui
