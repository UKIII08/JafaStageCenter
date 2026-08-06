#include "PluginEditor.h"
#include "Presets.h"

using namespace juce;
using namespace wpui;

namespace
{
    constexpr int margin      = 12;
    constexpr int gap         = 10;
    constexpr int presetBarH  = 52;
    constexpr int keyboardH   = 58;
    constexpr int panelTitleH = 22;

    void drawPanel (Graphics& g, Rectangle<int> area, const String& title)
    {
        const auto bounds = area.toFloat();

        g.setColour (colours::panel);
        g.fillRoundedRectangle (bounds, 6.0f);
        g.setColour (colours::panelEdge);
        g.drawRoundedRectangle (bounds.reduced (0.5f), 6.0f, 1.0f);

        g.setColour (colours::accent.withAlpha (0.85f));
        g.setFont (Font (FontOptions (11.5f)).withStyle (Font::bold));
        g.drawText (title.toUpperCase(), area.reduced (14, 6).removeFromTop (panelTitleH - 6),
                    Justification::topLeft, false);

        g.setColour (colours::panelEdge);
        g.fillRect (area.getX() + 14, area.getY() + panelTitleH, area.getWidth() - 28, 1);
    }
}

//==============================================================================
ParamKnob::ParamKnob (AudioProcessorValueTreeState& apvts, const String& paramID, const String& caption)
{
    parameter = apvts.getParameter (paramID);

    slider.setSliderStyle (Slider::RotaryHorizontalVerticalDrag);
    slider.setTextBoxStyle (Slider::NoTextBox, false, 0, 0);
    slider.setDoubleClickReturnValue (true, parameter != nullptr
                                              ? parameter->convertFrom0to1 (parameter->getDefaultValue())
                                              : 0.0);
    addAndMakeVisible (slider);

    name.setText (caption, dontSendNotification);
    name.setJustificationType (Justification::centred);
    name.setColour (Label::textColourId, colours::textDim);
    name.setInterceptsMouseClicks (false, false);
    addAndMakeVisible (name);

    value.setJustificationType (Justification::centred);
    value.setColour (Label::textColourId, colours::text);
    value.setInterceptsMouseClicks (false, false);
    addAndMakeVisible (value);

    auto refresh = [this]
    {
        if (parameter != nullptr)
            value.setText (parameter->getCurrentValueAsText(), dontSendNotification);
    };

    slider.onValueChange = refresh;
    attachment = std::make_unique<AudioProcessorValueTreeState::SliderAttachment> (apvts, paramID, slider);
    refresh();
}

void ParamKnob::resized()
{
    // keep the dial square and capped, so a wide cell in one panel does not
    // produce a knob twice the size of the one next to it, and keep the caption
    // and readout hugging the dial instead of drifting to the cell edges
    constexpr int textHeight = 13;

    auto area = getLocalBounds().reduced (1, 2);
    const int diameter = jmin (area.getWidth(), area.getHeight() - 2 * textHeight, 64);

    auto block = area.withSizeKeepingCentre (area.getWidth(), diameter + 2 * textHeight);
    name.setBounds (block.removeFromTop (textHeight));
    value.setBounds (block.removeFromBottom (textHeight));
    slider.setBounds (block.withSizeKeepingCentre (diameter, diameter));
}

//==============================================================================
LevelMeter::LevelMeter (WorshipPianoProcessor& p) : processor (p)
{
    startTimerHz (30);
}

void LevelMeter::timerCallback()
{
    const float level = processor.getOutputLevel();
    displayed = level > displayed ? level : displayed * 0.86f;
    repaint();
}

void LevelMeter::paint (Graphics& g)
{
    auto area = getLocalBounds().reduced (2).toFloat();

    g.setColour (colours::track);
    g.fillRoundedRectangle (area, 3.0f);

    const float db = Decibels::gainToDecibels (jmax (1.0e-5f, displayed));
    const float norm = jlimit (0.0f, 1.0f, (db + 54.0f) / 60.0f);

    auto filled = area.reduced (2.0f);
    filled = filled.removeFromBottom (filled.getHeight() * norm);

    g.setColour (db > -1.0f ? Colours::orangered
                            : (db > -8.0f ? colours::accent : colours::highlight));
    g.fillRoundedRectangle (filled, 2.0f);

    g.setColour (colours::panelEdge);
    g.drawRoundedRectangle (area, 3.0f, 1.0f);
}

//==============================================================================
WorshipPianoEditor::WorshipPianoEditor (WorshipPianoProcessor& p)
    : AudioProcessorEditor (&p), processor (p), meter (p),
      keyboard (p.keyboardState, MidiKeyboardComponent::horizontalKeyboard)
{
    setLookAndFeel (&lookAndFeel);

    addAndMakeVisible (presetBar);
    presetBar.onPresetChosen = [this] (int index) { processor.loadPreset (index); };

    // ---- piano -------------------------------------------------------------
    addAndMakeVisible (modelBox);
    modelBox.addItemList ({ "Smooth Grand", "Bright Grand", "Warm Upright", "Felt Piano" }, 1);
    modelAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::model, modelBox);

    addKnob (pianoKnobs, pid::tone,         "Tone");
    addKnob (pianoKnobs, pid::attack,       "Attack");
    addKnob (pianoKnobs, pid::decayTime,    "Sustain");
    addKnob (pianoKnobs, pid::dynamicRange, "Dynamics");
    addKnob (pianoKnobs, pid::pianoLevel,   "Level");

    // ---- pad ---------------------------------------------------------------
    addKnob (padKnobs, pid::padLevel,   "Pad");
    addKnob (padKnobs, pid::padTone,    "Tone");
    addKnob (padKnobs, pid::padAttack,  "Swell");
    addKnob (padKnobs, pid::padRelease, "Release");

    // ---- tone & drive ------------------------------------------------------
    addKnob (toneKnobs, pid::eqLow,      "Warmth");
    addKnob (toneKnobs, pid::eqHigh,     "Presence");
    addKnob (toneKnobs, pid::eqAir,      "Air");
    addKnob (toneKnobs, pid::compAmount, "Compress");
    addKnob (toneKnobs, pid::drive,      "Drive");

    // ---- movement & delay --------------------------------------------------
    addKnob (moveKnobs, pid::chorusAmount, "Chorus");
    addKnob (moveKnobs, pid::delayMix,     "Delay");
    addKnob (moveKnobs, pid::delayFeedback,"Feedback");

    addAndMakeVisible (delaySyncButton);
    delaySyncAttachment = std::make_unique<AudioProcessorValueTreeState::ButtonAttachment> (
        processor.apvts, pid::delaySync, delaySyncButton);

    addAndMakeVisible (delayDivBox);
    delayDivBox.addItemList ({ "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16" }, 1);
    delayDivAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::delayDiv, delayDivBox);

    addAndMakeVisible (tempoLabel);
    tempoLabel.setJustificationType (Justification::centred);
    tempoLabel.setColour (Label::textColourId, colours::textDim);

    // ---- space & output ----------------------------------------------------
    addKnob (spaceKnobs, pid::reverbMix,   "Reverb");
    addKnob (spaceKnobs, pid::reverbSize,  "Size");
    addKnob (spaceKnobs, pid::reverbDecay, "Decay");
    addKnob (spaceKnobs, pid::shimmer,     "Shimmer");
    addKnob (spaceKnobs, pid::width,       "Width");
    addKnob (spaceKnobs, pid::outputGain,  "Output");

    addAndMakeVisible (meter);

    keyboard.setAvailableRange (36, 96);
    keyboard.setColour (MidiKeyboardComponent::shadowColourId, Colours::transparentBlack);
    keyboard.setColour (MidiKeyboardComponent::keySeparatorLineColourId, colours::background);
    keyboard.setColour (MidiKeyboardComponent::keyDownOverlayColourId, colours::accent.withAlpha (0.8f));
    addAndMakeVisible (keyboard);

    setResizable (true, true);
    setResizeLimits (860, 600, 1500, 1000);
    setSize (940, 660);

    startTimerHz (10);
    timerCallback();
}

WorshipPianoEditor::~WorshipPianoEditor()
{
    setLookAndFeel (nullptr);
}

void WorshipPianoEditor::addKnob (OwnedArray<ParamKnob>& group, const String& paramID, const String& caption)
{
    auto* knob = group.add (new ParamKnob (processor.apvts, paramID, caption));
    addAndMakeVisible (knob);
}

void WorshipPianoEditor::layoutGrid (OwnedArray<ParamKnob>& group, Rectangle<int> area, int columns)
{
    if (group.isEmpty() || columns <= 0)
        return;

    const int rows = (group.size() + columns - 1) / columns;
    const int cellW = area.getWidth() / columns;
    const int cellH = area.getHeight() / jmax (1, rows);

    for (int i = 0; i < group.size(); ++i)
    {
        const int row = i / columns;
        const int col = i % columns;

        group[i]->setBounds (area.getX() + col * cellW,
                             area.getY() + row * cellH,
                             cellW, cellH);
    }
}

void WorshipPianoEditor::timerCallback()
{
    const int index = processor.getPresetIndex();
    const bool modified = processor.isPresetModified();

    if (index != lastPresetIndex || modified != lastModified)
    {
        lastPresetIndex = index;
        lastModified = modified;
        presetBar.setPreset (index, modified);
    }

    tempoLabel.setText (String (roundToInt (processor.getHostTempo())) + " BPM", dontSendNotification);
}

void WorshipPianoEditor::paint (Graphics& g)
{
    g.fillAll (colours::background);

    // a very slight vertical gradient keeps a flat dark UI from looking dead
    g.setGradientFill (ColourGradient (colours::background.brighter (0.05f), 0.0f, 0.0f,
                                       colours::background.darker (0.35f), 0.0f, (float) getHeight(), false));
    g.fillRect (getLocalBounds());

    drawPanel (g, pianoPanel,    "Piano");
    drawPanel (g, padPanel,      "Pad layer");
    drawPanel (g, tonePanel,     "Tone & drive");
    drawPanel (g, movementPanel, "Movement & delay");
    drawPanel (g, spacePanel,    "Space & output");
}

void WorshipPianoEditor::resized()
{
    auto area = getLocalBounds().reduced (margin);

    presetBar.setBounds (area.removeFromTop (presetBarH));
    area.removeFromTop (gap);

    keyboard.setBounds (area.removeFromBottom (keyboardH));
    keyboard.setKeyWidth (jmax (12.0f, (float) keyboard.getWidth() / 36.0f));   // 36 white keys, C2 - C7
    area.removeFromBottom (gap);

    // the last row holds a single row of dials, so it needs less height
    const int usable = area.getHeight() - gap * 2;
    const int rowHeight = roundToInt ((float) usable / 2.85f);

    // --- row one: piano + pad ------------------------------------------------
    auto rowA = area.removeFromTop (rowHeight);
    area.removeFromTop (gap);

    pianoPanel = rowA.removeFromLeft (roundToInt (rowA.getWidth() * 0.655f));
    rowA.removeFromLeft (gap);
    padPanel = rowA;

    auto pianoInner = pianoPanel.reduced (10, 6);
    pianoInner.removeFromTop (panelTitleH);
    modelBox.setBounds (pianoInner.removeFromTop (28).reduced (2, 2));
    pianoInner.removeFromTop (6);
    layoutGrid (pianoKnobs, pianoInner, 5);

    auto padInner = padPanel.reduced (10, 6);
    padInner.removeFromTop (panelTitleH + 34);
    layoutGrid (padKnobs, padInner, 4);

    // --- row two: tone + movement -------------------------------------------
    auto rowB = area.removeFromTop (rowHeight);
    area.removeFromTop (gap);

    tonePanel = rowB.removeFromLeft (roundToInt (rowB.getWidth() * 0.48f));
    rowB.removeFromLeft (gap);
    movementPanel = rowB;

    auto toneInner = tonePanel.reduced (10, 6);
    toneInner.removeFromTop (panelTitleH + 6);
    layoutGrid (toneKnobs, toneInner, 5);

    auto moveInner = movementPanel.reduced (10, 6);
    moveInner.removeFromTop (panelTitleH + 6);

    // the delay section mixes knobs with a sync switch, so it is placed by hand
    {
        const int cells = 4;
        const int cellW = moveInner.getWidth() / cells;

        for (int i = 0; i < moveKnobs.size(); ++i)
            moveKnobs[i]->setBounds (moveInner.getX() + i * cellW, moveInner.getY(),
                                     cellW, moveInner.getHeight());

        auto sync = Rectangle<int> (moveInner.getX() + 3 * cellW, moveInner.getY(),
                                    cellW, moveInner.getHeight()).reduced (10, 0);
        sync = sync.withSizeKeepingCentre (sync.getWidth(), 70);

        delaySyncButton.setBounds (sync.removeFromTop (24));
        sync.removeFromTop (4);
        delayDivBox.setBounds (sync.removeFromTop (24));
        sync.removeFromTop (2);
        tempoLabel.setBounds (sync.removeFromTop (16));
    }

    // --- row three: space + output ------------------------------------------
    spacePanel = area;

    auto spaceInner = spacePanel.reduced (10, 6);
    spaceInner.removeFromTop (panelTitleH + 6);

    auto meterArea = spaceInner.removeFromRight (34);
    meter.setBounds (meterArea.reduced (6, 4));

    layoutGrid (spaceKnobs, spaceInner, 6);
}
