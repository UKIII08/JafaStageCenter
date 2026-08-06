#include "PluginEditor.h"
#include "Presets.h"

using namespace juce;
using namespace wpui;

namespace
{
    constexpr int margin      = 14;
    constexpr int gap         = 10;
    constexpr int topBarH     = 58;
    constexpr int keyboardH   = 58;
    constexpr int panelTitleH = 22;

    void drawPanel (Graphics& g, Rectangle<int> area, const String& title)
    {
        if (area.isEmpty())
            return;

        const auto bounds = area.toFloat();

        g.setColour (colours::panel);
        g.fillRoundedRectangle (bounds, 7.0f);
        g.setColour (colours::panelEdge);
        g.drawRoundedRectangle (bounds.reduced (0.5f), 7.0f, 1.0f);

        if (title.isEmpty())
            return;

        g.setColour (colours::accent.withAlpha (0.85f));
        g.setFont (Font (FontOptions (11.5f)).withStyle (Font::bold));
        g.drawText (title.toUpperCase(), area.reduced (14, 6).removeFromTop (panelTitleH - 6),
                    Justification::topLeft, false);

        g.setColour (colours::panelEdge);
        g.fillRect (area.getX() + 14, area.getY() + panelTitleH, area.getWidth() - 28, 1);
    }

    String noteName (int midiNote)
    {
        return MidiMessage::getMidiNoteName (midiNote, true, true, 4);
    }
}

//==============================================================================
ParamKnob::ParamKnob (AudioProcessorValueTreeState& apvts, const String& paramID,
                      const String& caption, int maxDia)
    : maxDiameter (maxDia)
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

void ParamKnob::setCaptionSize (float points)
{
    captionSize = points;
    name.setFont (Font (FontOptions (points)).withStyle (Font::bold));
    name.setColour (Label::textColourId, colours::text);
    value.setFont (Font (FontOptions (points - 1.0f)));
    resized();
}

void ParamKnob::resized()
{
    // keep the dial square and capped, so a wide cell in one panel does not
    // produce a knob twice the size of the one next to it, and keep the caption
    // and readout hugging the dial instead of drifting to the cell edges
    const int textHeight = captionSize > 0.0f ? roundToInt (captionSize + 5.0f) : 13;

    auto area = getLocalBounds().reduced (1, 2);
    const int diameter = jmin (area.getWidth(), area.getHeight() - 2 * textHeight, maxDiameter);

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
StompButton::StompButton (AudioProcessorValueTreeState& apvts, const String& paramID,
                          const String& text, Colour litColour)
    : Button (text), caption (text), lit (litColour)
{
    setClickingTogglesState (true);
    attachment = std::make_unique<AudioProcessorValueTreeState::ButtonAttachment> (apvts, paramID, *this);
}

void StompButton::paintButton (Graphics& g, bool highlighted, bool down)
{
    auto area = getLocalBounds().toFloat().reduced (2.0f);
    const bool on = getToggleState();

    // the body: dark when bypassed, lit from within when engaged, so the state
    // reads from across a stage rather than from a foot away
    g.setColour (on ? lit.withAlpha (0.30f) : colours::track);
    g.fillRoundedRectangle (area, 6.0f);

    g.setColour (on ? lit : colours::panelEdge);
    g.drawRoundedRectangle (area.reduced (0.5f), 6.0f, on ? 1.8f : 1.0f);

    if (highlighted || down)
    {
        g.setColour (Colours::white.withAlpha (down ? 0.14f : 0.07f));
        g.fillRoundedRectangle (area, 6.0f);
    }

    // the lamp, because a pedal you cannot read in a dark room is no use
    auto lamp = area.removeFromTop (area.getHeight() * 0.42f)
                    .withSizeKeepingCentre (9.0f, 9.0f);

    g.setColour (on ? lit : colours::panelEdge.brighter (0.1f));
    g.fillEllipse (lamp);

    if (on)
    {
        g.setColour (lit.withAlpha (0.35f));
        g.fillEllipse (lamp.expanded (3.5f));
    }

    g.setColour (on ? Colours::white : colours::textDim);
    g.setFont (Font (FontOptions (11.0f)).withStyle (Font::bold));
    g.drawText (caption, area, Justification::centred, false);
}

//==============================================================================
PresetList::PresetList()
{
    refreshUserPresets();
    list.setRowHeight (34);
    list.setColour (ListBox::backgroundColourId, Colours::transparentBlack);
    list.setColour (ListBox::outlineColourId, Colours::transparentBlack);
    addAndMakeVisible (list);
}

int PresetList::getNumRows() { return (int) presets::factory().size() + userNames.size(); }

void PresetList::refreshUserPresets()
{
    const auto keep = userNameForRow (selected);
    userNames = presets::userPresetNames();
    list.updateContent();

    if (keep.isNotEmpty())
    {
        const int row = rowForUserName (keep);
        selected = row >= 0 ? row : 0;
    }

    list.repaint();
}

String PresetList::userNameForRow (int row) const
{
    const int i = row - (int) presets::factory().size();
    return isPositiveAndBelow (i, userNames.size()) ? userNames[i] : String();
}

int PresetList::rowForUserName (const String& name) const
{
    const int i = userNames.indexOf (name);
    return i < 0 ? -1 : (int) presets::factory().size() + i;
}

void PresetList::paintListBoxItem (int row, Graphics& g, int width, int height, bool)
{
    const auto& all = presets::factory();

    if (! isPositiveAndBelow (row, getNumRows()))
        return;

    const bool user = isUserRow (row);
    const String name = user ? userNameForRow (row) : all[(size_t) row].name;
    const String category = user ? "MOJE" : all[(size_t) row].category.toUpperCase();

    auto area = Rectangle<int> (0, 0, width, height).reduced (6, 2);

    if (row == selected)
    {
        g.setColour (colours::accentSoft.withAlpha (0.55f));
        g.fillRoundedRectangle (area.toFloat(), 5.0f);
        g.setColour (colours::accent);
        g.drawRoundedRectangle (area.toFloat().reduced (0.5f), 5.0f, 1.0f);
    }

    auto text = area.reduced (10, 0);

    // the category reads as a quiet tag on the right, so the eye lands on the name
    g.setColour (row == selected ? colours::textDim.brighter (0.4f) : colours::textDim.darker (0.2f));
    g.setFont (Font (FontOptions (10.5f)));
    g.drawText (category, text.removeFromRight (62), Justification::centredRight, false);

    g.setColour (row == selected ? Colours::white : colours::text);
    g.setFont (Font (FontOptions (14.5f)).withStyle (row == selected ? Font::bold : Font::plain));
    g.drawText (name, text, Justification::centredLeft, true);
}

void PresetList::listBoxItemClicked (int row, const MouseEvent&)
{
    if (onPresetChosen != nullptr)
        onPresetChosen (row);
}

void PresetList::setSelected (int index)
{
    if (selected == index)
        return;

    selected = index;
    list.selectRow (index, true, true);
    list.repaint();
}

void PresetList::resized() { list.setBounds (getLocalBounds()); }

//==============================================================================
WorshipPianoEditor::WorshipPianoEditor (WorshipPianoProcessor& p)
    : AudioProcessorEditor (&p), processor (p), meter (p),
      keyboard (p.keyboardState, MidiKeyboardComponent::horizontalKeyboard)
{
    setLookAndFeel (&lookAndFeel);

    //---- top bar -------------------------------------------------------------
    addAndMakeVisible (liveTab);
    addAndMakeVisible (editTab);
    liveTab.onClick = [this] { setLiveMode (true); };
    editTab.onClick = [this] { setLiveMode (false); };

    addAndMakeVisible (panicButton);
    panicButton.setColour (TextButton::textColourOffId, Colours::orangered.brighter (0.3f));
    panicButton.onClick = [this] { processor.panic(); };

    addAndMakeVisible (presetPrev);
    addAndMakeVisible (presetNext);

    auto step = [this] (int delta)
    {
        const int count = (int) presets::factory().size();

        if (count > 0)
            processor.loadPreset ((processor.getPresetIndex() + delta + count) % count);
    };

    presetPrev.onClick = [step] { step (-1); };
    presetNext.onClick = [step] { step (1); };

    addAndMakeVisible (presetName);
    presetName.setFont (Font (FontOptions (21.0f)).withStyle (Font::bold));
    presetName.setColour (Label::textColourId, colours::text);
    presetName.setJustificationType (Justification::centredLeft);

    addAndMakeVisible (presetBlurb);
    presetBlurb.setFont (Font (FontOptions (12.5f)));
    presetBlurb.setColour (Label::textColourId, colours::textDim);
    presetBlurb.setJustificationType (Justification::centredLeft);

    //---- live view -----------------------------------------------------------
    addAndMakeVisible (presetList);
    presetList.onPresetChosen = [this] (int index)
    {
        if (presetList.isUserRow (index))
        {
            const auto name = presetList.userNameForRow (index);

            if (presets::applyUser (processor.apvts, name))
            {
                currentUserPreset = name;
                lastPresetIndex = -2;       // force the header to refresh
            }
        }
        else
        {
            currentUserPreset = {};
            processor.loadPreset (index);
        }
    };

    addAndMakeVisible (savePresetButton);
    savePresetButton.onClick = [this] { savePreset(); };

    addAndMakeVisible (deletePresetButton);
    deletePresetButton.onClick = [this] { deletePreset(); };

    soakKnob = std::make_unique<ParamKnob> (processor.apvts, pid::soak, "SOAK", 150);
    soakKnob->setCaptionSize (14.0f);
    addAndMakeVisible (soakKnob.get());

    auto addLive = [this] (const char* id, const char* caption)
    {
        auto* knob = liveKnobs.add (new ParamKnob (processor.apvts, id, caption, 86));
        knob->setCaptionSize (13.0f);
        addAndMakeVisible (knob);
    };

    addLive (pid::pianoLevel, "Piano");
    addLive (pid::padLevel,   "Pad");
    addLive (pid::reverbMix,  "Reverb");
    addLive (pid::delayMix,   "Delay");
    addLive (pid::tone,       "Tone");

    for (auto* k : liveKnobs)
        k->setCaptionSize (13.0f);

    addAndMakeVisible (transposeDown);
    addAndMakeVisible (transposeUp);

    auto nudgeTranspose = [this] (int delta)
    {
        if (auto* param = processor.apvts.getParameter (pid::transpose))
        {
            const auto& range = param->getNormalisableRange();
            const float current = range.convertFrom0to1 (param->getValue());
            param->setValueNotifyingHost (range.convertTo0to1 (jlimit (-12.0f, 12.0f, current + (float) delta)));
        }
    };

    transposeDown.onClick = [nudgeTranspose] { nudgeTranspose (-1); };
    transposeUp.onClick   = [nudgeTranspose] { nudgeTranspose (1); };

    addAndMakeVisible (transposeValue);
    transposeValue.setJustificationType (Justification::centred);
    transposeValue.setFont (Font (FontOptions (19.0f)).withStyle (Font::bold));
    transposeValue.setColour (Label::textColourId, colours::text);

    addAndMakeVisible (transposeCaption);
    transposeCaption.setText ("TRANSPOSE", dontSendNotification);
    transposeCaption.setJustificationType (Justification::centred);
    transposeCaption.setFont (Font (FontOptions (11.0f)).withStyle (Font::bold));
    transposeCaption.setColour (Label::textColourId, colours::textDim);

    addAndMakeVisible (splitButton);
    splitAttachment = std::make_unique<AudioProcessorValueTreeState::ButtonAttachment> (
        processor.apvts, pid::splitOn, splitButton);

    addAndMakeVisible (splitPointSlider);
    splitPointSlider.setSliderStyle (Slider::LinearBar);
    splitPointSlider.setTextBoxStyle (Slider::NoTextBox, false, 0, 0);
    splitPointSlider.textFromValueFunction = [] (double v) { return noteName ((int) v); };
    splitPointSlider.setColour (Slider::trackColourId, colours::accentSoft.withAlpha (0.40f));
    splitPointSlider.setColour (Slider::backgroundColourId, colours::track);
    splitPointSlider.setColour (Slider::textBoxTextColourId, colours::text);
    splitPointSlider.setTooltip ("Ponizej tego klawisza gra tylko pad");
    splitPointAttachment = std::make_unique<AudioProcessorValueTreeState::SliderAttachment> (
        processor.apvts, pid::splitPoint, splitPointSlider);

    // the bar itself is draggable; the note name rides on top of it so it stays
    // readable on a dark stage whatever the bar is doing underneath
    addAndMakeVisible (splitPointLabel);
    splitPointLabel.setJustificationType (Justification::centred);
    splitPointLabel.setFont (Font (FontOptions (15.0f)).withStyle (Font::bold));
    splitPointLabel.setColour (Label::textColourId, Colours::white);
    splitPointLabel.setInterceptsMouseClicks (false, false);

    splitPointSlider.onValueChange = [this]
    {
        splitPointLabel.setText (noteName ((int) splitPointSlider.getValue()), dontSendNotification);
    };
    splitPointSlider.onValueChange();

    /*  The pedalboard. Order runs left to right the way the signal does, so the
        board reads like the chain it is driving.
    */
    struct StompSpec { const char* id; const char* caption; uint32 colour; };

    static const StompSpec board[] = {
        { pid::tackOn,    "TACK",    0xffe0b050 },
        { pid::driveOn,   "DRIVE",   0xffe08050 },
        { pid::padOn,     "PAD",     0xff70c090 },
        { pid::chorusOn,  "CHORUS",  0xff60b0d0 },
        { pid::delayOn,   "DELAY",   0xff8090e0 },
        { pid::reverseOn, "REVERSE", 0xffb080e0 },
        { pid::reverbOn,  "REVERB",  0xff70a0e0 },
        { pid::soakOn,    "SOAK",    0xffd070c0 },
    };

    for (const auto& spec : board)
    {
        auto* b = stomps.add (new StompButton (processor.apvts, spec.id, spec.caption,
                                               Colour (spec.colour)));
        addAndMakeVisible (b);
    }

    //---- quick access: the handful of presets you actually play --------------
    for (int i = 0; i < 6; ++i)
    {
        auto* b = quickButtons.add (new TextButton());
        b->setConnectedEdges (Button::ConnectedOnLeft | Button::ConnectedOnRight);
        b->onClick = [this, i]
        {
            if (isPositiveAndBelow (i, quickNames.size()))
            {
                const auto name = quickNames[i];
                const int factoryIndex = presets::indexForName (name);

                if (factoryIndex >= 0)
                {
                    currentUserPreset = {};
                    processor.loadPreset (factoryIndex);
                }
                else if (presets::applyUser (processor.apvts, name))
                {
                    currentUserPreset = name;
                }

                lastPresetIndex = -2;
            }
        };
        addAndMakeVisible (b);
    }

    addAndMakeVisible (favouriteButton);
    favouriteButton.setTooltip ("Dodaj lub usun z szybkiego dostepu");
    favouriteButton.onClick = [this] { toggleFavourite(); };
    refreshQuickAccess();

    addAndMakeVisible (freezeButton);
    freezeAttachment = std::make_unique<AudioProcessorValueTreeState::ButtonAttachment> (
        processor.apvts, pid::reverbFreeze, freezeButton);

    //---- edit view: piano ----------------------------------------------------
    addAndMakeVisible (loadButton);
    loadButton.setTriggeredOnMouseDown (true);
    loadButton.onClick = [this] { showLibraryMenu(); };

    addAndMakeVisible (libraryLabel);
    libraryLabel.setJustificationType (Justification::centredLeft);
    libraryLabel.setColour (Label::textColourId, colours::textDim);
    libraryLabel.setInterceptsMouseClicks (false, false);

    addKnob (pianoKnobs, pid::tone,         "Tone");
    addKnob (pianoKnobs, pid::attack,       "Attack");
    addKnob (pianoKnobs, pid::decayTime,    "Sustain");
    addKnob (pianoKnobs, pid::dynamicRange, "Dynamics");
    addKnob (pianoKnobs, pid::pianoLevel,   "Level");

    addChildComponent (padTypeBox);
    padTypeBox.addItemList ({ "Warm Saw", "Soft Choir", "Glass", "Strings", "Air Vox" }, 1);
    padTypeAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::padType, padTypeBox);

    addKnob (padKnobs, pid::padLevel,   "Pad");
    addKnob (padKnobs, pid::padTone,    "Tone");
    addKnob (padKnobs, pid::padAttack,  "Swell");
    addKnob (padKnobs, pid::padRelease, "Release");

    addKnob (toneKnobs, pid::eqLow,      "Warmth");
    addKnob (toneKnobs, pid::eqHigh,     "Presence");
    addKnob (toneKnobs, pid::eqAir,      "Air");
    addKnob (toneKnobs, pid::compAmount, "Compress");
    addKnob (toneKnobs, pid::drive,      "Drive");
    addKnob (toneKnobs, pid::tackAmount, "Tack");

    addKnob (moveKnobs, pid::chorusAmount, "Chorus");
    addKnob (moveKnobs, pid::delayMix,     "Delay");
    addKnob (moveKnobs, pid::delayFeedback,"Feedback");

    addChildComponent (delaySyncButton);
    delaySyncAttachment = std::make_unique<AudioProcessorValueTreeState::ButtonAttachment> (
        processor.apvts, pid::delaySync, delaySyncButton);

    addChildComponent (delayDivBox);
    delayDivBox.addItemList ({ "1/4", "1/4T", "1/8.", "1/8", "1/8T", "1/16.", "1/16" }, 1);
    delayDivAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::delayDiv, delayDivBox);

    addChildComponent (tempoLabel);
    tempoLabel.setJustificationType (Justification::centred);
    tempoLabel.setColour (Label::textColourId, colours::textDim);

    addChildComponent (machineBox);
    machineBox.addItemList ({ "Room", "Hall", "Plate", "Cloud", "Bloom", "Shimmer" }, 1);
    machineAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::reverbMachine, machineBox);

    addChildComponent (shimmerModeBox);
    shimmerModeBox.addItemList ({ "Octave Up", "Octave + 5th", "Octave Down", "Up & Down" }, 1);
    shimmerModeAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::shimmerMode, shimmerModeBox);

    addChildComponent (revTimeBox);
    revTimeBox.addItemList ({ "1/2 bar", "1 bar", "2 bars", "4 bars" }, 1);
    revTimeAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::reverseTime, revTimeBox);

    addChildComponent (pedalBox);
    pedalBox.addItemList ({ "Pedal: Off", "Pedal: CC11", "Pedal: CC1" }, 1);
    pedalAttachment = std::make_unique<AudioProcessorValueTreeState::ComboBoxAttachment> (
        processor.apvts, pid::pedalTarget, pedalBox);

    addKnob (ambienceKnobs, pid::reverbMix,    "Reverb");
    addKnob (ambienceKnobs, pid::reverbSize,   "Size");
    addKnob (ambienceKnobs, pid::reverbDecay,  "Decay");
    addKnob (ambienceKnobs, pid::shimmer,      "Shimmer");
    addKnob (ambienceKnobs, pid::reverseMix,   "Reverse");
    addKnob (ambienceKnobs, pid::reverbLowCut, "Low Cut");
    addKnob (ambienceKnobs, pid::reverbDuck,   "Duck");

    addKnob (outputKnobs, pid::width,      "Width");
    addKnob (outputKnobs, pid::outputGain, "Output");

    addAndMakeVisible (meter);

    keyboard.setAvailableRange (36, 96);
    keyboard.setColour (MidiKeyboardComponent::shadowColourId, Colours::transparentBlack);
    keyboard.setColour (MidiKeyboardComponent::keySeparatorLineColourId, colours::background);
    keyboard.setColour (MidiKeyboardComponent::keyDownOverlayColourId, colours::accent.withAlpha (0.8f));
    addAndMakeVisible (keyboard);

    setResizable (true, true);
    setResizeLimits (900, 620, 1700, 1150);
    setSize (1060, 760);

    setLiveMode (true);
    startTimerHz (12);
    timerCallback();
}

WorshipPianoEditor::~WorshipPianoEditor()
{
    setLookAndFeel (nullptr);
}

void WorshipPianoEditor::addKnob (OwnedArray<ParamKnob>& group, const String& paramID,
                                  const String& caption, int maxDiameter)
{
    auto* knob = group.add (new ParamKnob (processor.apvts, paramID, caption, maxDiameter));
    addChildComponent (knob);
}

void WorshipPianoEditor::layoutGrid (OwnedArray<ParamKnob>& group, Rectangle<int> area, int columns)
{
    if (group.isEmpty() || columns <= 0)
        return;

    const int rows = (group.size() + columns - 1) / columns;
    const int cellW = area.getWidth() / columns;
    const int cellH = area.getHeight() / jmax (1, rows);

    for (int i = 0; i < group.size(); ++i)
        group[i]->setBounds (area.getX() + (i % columns) * cellW,
                             area.getY() + (i / columns) * cellH,
                             cellW, cellH);
}

void WorshipPianoEditor::setLiveMode (bool shouldBeLive)
{
    liveMode = shouldBeLive;

    liveTab.setToggleState (liveMode, dontSendNotification);
    editTab.setToggleState (! liveMode, dontSendNotification);

    presetList.setVisible (liveMode);
    savePresetButton.setVisible (liveMode);
    deletePresetButton.setVisible (liveMode);
    favouriteButton.setVisible (liveMode);

    for (auto* b : quickButtons)
        b->setVisible (liveMode);

    // the board stays on the LIVE page: EDIT is for building a sound, LIVE is
    // for playing it
    for (auto* b : stomps)
        b->setVisible (liveMode);
    soakKnob->setVisible (liveMode);
    transposeDown.setVisible (liveMode);
    transposeUp.setVisible (liveMode);
    transposeValue.setVisible (liveMode);
    transposeCaption.setVisible (liveMode);
    splitButton.setVisible (liveMode);
    splitPointSlider.setVisible (liveMode);
    splitPointLabel.setVisible (liveMode);
    freezeButton.setVisible (liveMode);

    for (auto* k : liveKnobs)
        k->setVisible (liveMode);

    for (auto* group : { &pianoKnobs, &padKnobs, &toneKnobs, &moveKnobs, &ambienceKnobs, &outputKnobs })
        for (auto* k : *group)
            k->setVisible (! liveMode);

    const std::initializer_list<Component*> editOnly
    {
        &padTypeBox, &delaySyncButton, &delayDivBox,
        &tempoLabel, &machineBox, &shimmerModeBox, &revTimeBox, &pedalBox
    };

    for (auto* c : editOnly)
        c->setVisible (! liveMode);

    resized();
    repaint();
}

/*  Saving is asynchronous because a plugin editor must never block the host's
    message thread with a modal loop - some hosts deadlock, and Reaper will stop
    painting until the window goes away.
*/
void WorshipPianoEditor::savePreset()
{
    nameWindow = std::make_unique<AlertWindow> ("Zapisz preset",
                                                "Pod jaka nazwa?",
                                                MessageBoxIconType::NoIcon);

    // offer the current name so overwriting your own preset is one click
    const auto suggested = currentUserPreset.isNotEmpty() ? currentUserPreset
                                                          : presetName.getText().upToFirstOccurrenceOf (" *", false, false);

    nameWindow->addTextEditor ("name", suggested, "Nazwa:");
    nameWindow->addButton ("Zapisz", 1, KeyPress (KeyPress::returnKey));
    nameWindow->addButton ("Anuluj", 0, KeyPress (KeyPress::escapeKey));

    nameWindow->enterModalState (true, ModalCallbackFunction::create ([this] (int result)
    {
        if (result != 1 || nameWindow == nullptr)
        {
            nameWindow.reset();
            return;
        }

        const auto name = nameWindow->getTextEditorContents ("name");
        nameWindow.reset();

        const auto error = presets::saveUser (processor.apvts, name);

        if (error.isNotEmpty())
        {
            NativeMessageBox::showAsync (MessageBoxOptions()
                                             .withIconType (MessageBoxIconType::WarningIcon)
                                             .withTitle ("Nie zapisano")
                                             .withMessage (error)
                                             .withButton ("OK"),
                                         nullptr);
            return;
        }

        currentUserPreset = presets::sanitiseName (name);
        presetList.refreshUserPresets();
        lastPresetIndex = -2;
    }), true);
}

void WorshipPianoEditor::deletePreset()
{
    if (currentUserPreset.isEmpty())
    {
        NativeMessageBox::showAsync (MessageBoxOptions()
                                         .withIconType (MessageBoxIconType::InfoIcon)
                                         .withTitle ("Nie ma czego usunac")
                                         .withMessage ("Usuwac mozna tylko wlasne presety - te oznaczone MOJE.")
                                         .withButton ("OK"),
                                     nullptr);
        return;
    }

    const auto name = currentUserPreset;

    NativeMessageBox::showAsync (MessageBoxOptions()
                                     .withIconType (MessageBoxIconType::QuestionIcon)
                                     .withTitle ("Usunac preset?")
                                     .withMessage ("\"" + name + "\" zniknie z dysku na dobre.")
                                     .withButton ("Usun")
                                     .withButton ("Anuluj"),
                                 [this, name] (int result)
                                 {
                                     if (result != 0)
                                         return;

                                     presets::deleteUser (name);
                                     currentUserPreset = {};
                                     presetList.refreshUserPresets();
                                     processor.loadPreset (processor.getPresetIndex());
                                     lastPresetIndex = -2;
                                 });
}

void WorshipPianoEditor::refreshQuickAccess()
{
    quickNames = presets::favourites();

    for (int i = 0; i < quickButtons.size(); ++i)
    {
        const bool used = isPositiveAndBelow (i, quickNames.size());
        auto* b = quickButtons[i];

        b->setButtonText (used ? quickNames[i] : String ("-"));
        b->setEnabled (used);
        b->setColour (TextButton::textColourOffId, used ? colours::text : colours::textDim.darker (0.4f));
    }
}

void WorshipPianoEditor::toggleFavourite()
{
    const auto name = currentUserPreset.isNotEmpty()
                        ? currentUserPreset
                        : presetName.getText().upToFirstOccurrenceOf (" *", false, false);

    if (name.isEmpty())
        return;

    presets::setFavourite (name, ! presets::isFavourite (name));
    refreshQuickAccess();
    lastPresetIndex = -2;
}

void WorshipPianoEditor::showLibraryMenu()
{
    PopupMenu menu;
    menu.addSectionHeader ("Biblioteka sampli");
    menu.addItem (1, "Wczytaj plik .sfz...");
    menu.addItem (2, "Wczytaj folder z samplami...");
    menu.addSeparator();
    menu.addItem (3, "Wyczysc (wroc do silnika modelowanego)");

    menu.showMenuAsync (PopupMenu::Options().withTargetComponent (loadButton)
                                            .withStandardItemHeight (26),
                        [this] (int result)
    {
        if (result == 3)
        {
            processor.clearSampleLibrary();
            return;
        }

        if (result != 1 && result != 2)
            return;

        const bool wantFolder = result == 2;

        chooser = std::make_unique<FileChooser> (wantFolder ? "Wybierz folder z samplami"
                                                            : "Wybierz plik SFZ",
                                                 File::getSpecialLocation (File::userMusicDirectory),
                                                 wantFolder ? String() : String ("*.sfz"));

        const auto flags = FileBrowserComponent::openMode
                         | (wantFolder ? FileBrowserComponent::canSelectDirectories
                                       : FileBrowserComponent::canSelectFiles);

        chooser->launchAsync (flags, [this] (const FileChooser& fc)
        {
            const auto file = fc.getResult();

            if (file != File())
            {
                processor.loadSampleLibrary (file);
            }
        });
    });
}

void WorshipPianoEditor::timerCallback()
{
    const int index = processor.getPresetIndex();
    const bool modified = processor.isPresetModified();

    if (index != lastPresetIndex || modified != lastModified)
    {
        lastPresetIndex = index;
        lastModified = modified;

        const auto& all = presets::factory();

        if (currentUserPreset.isNotEmpty())
        {
            presetName.setText (currentUserPreset + (modified ? String (" *") : String()),
                                dontSendNotification);
            presetBlurb.setText ("Twoj preset", dontSendNotification);
            presetList.setSelected (presetList.rowForUserName (currentUserPreset));
        }
        else if (isPositiveAndBelow (index, (int) all.size()))
        {
            presetName.setText (all[(size_t) index].name + (modified ? String (" *") : String()),
                                dontSendNotification);
            presetBlurb.setText (all[(size_t) index].blurb, dontSendNotification);
            presetList.setSelected (index);
        }
    }

    if (liveMode)
    {
        const int shift = (int) processor.apvts.getRawParameterValue (pid::transpose)->load();
        transposeValue.setText (shift > 0 ? "+" + String (shift) : String (shift), dontSendNotification);
        transposeValue.setColour (Label::textColourId, shift != 0 ? colours::accent : colours::text);
    }
    else
    {
        tempoLabel.setText (String (roundToInt (processor.getHostTempo())) + " BPM", dontSendNotification);
    }

    // the library lives in the top bar now, so it has to keep up in both views
    {
        auto status = processor.getLibraryStatus();

        if (processor.isLoadingLibrary())
            status += "  " + String (roundToInt (processor.getLoadProgress() * 100.0f)) + " %";

        if (libraryLabel.getText() != status)
            libraryLabel.setText (status, dontSendNotification);

        // the "no samples" banner is painted, not a component, so it needs a
        // nudge when the library finally arrives
        const bool live = processor.isSampleSourceActive();

        if (live != lastLibraryLive)
        {
            lastLibraryLive = live;
            repaint();
        }
    }
}

//==============================================================================
void WorshipPianoEditor::paint (Graphics& g)
{
    g.fillAll (colours::background);

    g.setGradientFill (ColourGradient (colours::background.brighter (0.05f), 0.0f, 0.0f,
                                       colours::background.darker (0.35f), 0.0f, (float) getHeight(), false));
    g.fillRect (getLocalBounds());

    // top bar
    auto bar = getLocalBounds().reduced (margin).removeFromTop (topBarH);
    drawPanel (g, bar, {});

    g.setColour (colours::accent);
    g.setFont (Font (FontOptions (12.0f)).withStyle (Font::bold));
    g.drawText ("JAFA WORSHIP PIANO", bar.reduced (16, 0).removeFromLeft (150),
                Justification::centredLeft, false);

    if (liveMode)
    {
        drawPanel (g, livePresetPanel, "Presets");
        drawPanel (g, liveMixPanel,    "Mix");
        drawPanel (g, livePerformPanel,"Performance");
        drawPanel (g, quickPanel,      {});
        drawPanel (g, stompPanel,      {});
    }
    else
    {
        drawPanel (g, pianoPanel,    "Piano");
        drawPanel (g, padPanel,      "Pad layer");
        drawPanel (g, tonePanel,     "Tone & drive");
        drawPanel (g, movementPanel, "Movement & delay");
        drawPanel (g, ambiencePanel, "Ambience");
        drawPanel (g, soakPanel,     "Output");
    }

    /*  Without a library the instrument makes no sound at all. Saying so plainly
        beats letting someone conclude the plugin is broken - that is exactly the
        conclusion anyone would draw from a piano that answers nothing.
    */
    if (! processor.isSampleSourceActive() && ! processor.isLoadingLibrary())
    {
        auto banner = getLocalBounds().reduced (margin, 0)
                          .withTop (topBarH + 4).withHeight (46);

        g.setColour (Colours::orangered.withAlpha (0.16f));
        g.fillRoundedRectangle (banner.toFloat(), 7.0f);
        g.setColour (Colours::orangered.withAlpha (0.55f));
        g.drawRoundedRectangle (banner.toFloat().reduced (0.5f), 7.0f, 1.0f);

        g.setColour (Colours::white);
        g.setFont (Font (FontOptions (14.0f)).withStyle (Font::bold));
        g.drawText ("Brak biblioteki sampli - wtyczka nie wyda dzwieku",
                    banner.reduced (16, 0).removeFromTop (24), Justification::bottomLeft, false);

        g.setColour (colours::textDim.brighter (0.3f));
        g.setFont (Font (FontOptions (12.0f)));
        g.drawText ("Kliknij \"Sample library...\" u gory i wskaz rozpakowany folder z samplami.",
                    banner.reduced (16, 0).removeFromBottom (20), Justification::topLeft, false);
    }
}

void WorshipPianoEditor::resized()
{
    auto area = getLocalBounds().reduced (margin);

    //---- top bar -------------------------------------------------------------
    auto bar = area.removeFromTop (topBarH);
    area.removeFromTop (gap);

    {
        auto inner = bar.reduced (14, 10);
        inner.removeFromLeft (150);

        // tabs and panic sit on the right, away from the preset stepping
        auto right = inner.removeFromRight (210);
        panicButton.setBounds (right.removeFromRight (74).reduced (2, 0));
        right.removeFromRight (8);
        editTab.setBounds (right.removeFromRight (62).reduced (2, 0));
        liveTab.setBounds (right.removeFromRight (62).reduced (2, 0));

        inner.removeFromRight (14);

        auto libraryArea = inner.removeFromRight (250);
        loadButton.setBounds (libraryArea.removeFromTop (libraryArea.getHeight() / 2).reduced (2, 1));
        libraryLabel.setBounds (libraryArea.reduced (4, 0));

        inner.removeFromRight (14);

        presetPrev.setBounds (inner.removeFromLeft (34).reduced (2, 0));
        inner.removeFromLeft (6);
        presetNext.setBounds (inner.removeFromLeft (34).reduced (2, 0));
        inner.removeFromLeft (12);

        auto text = inner;
        presetName.setBounds (text.removeFromTop (text.getHeight() * 6 / 10));
        presetBlurb.setBounds (text);
    }

    //---- keyboard ------------------------------------------------------------
    keyboard.setBounds (area.removeFromBottom (keyboardH));
    keyboard.setKeyWidth (jmax (12.0f, (float) keyboard.getWidth() / 36.0f));
    area.removeFromBottom (gap);

    if (liveMode)
        layoutLive (area);
    else
        layoutEdit (area);
}

void WorshipPianoEditor::layoutLive (Rectangle<int> area)
{
    pianoPanel = padPanel = tonePanel = movementPanel = ambiencePanel = soakPanel = {};

    // the board spans the full width across the bottom, where a foot would
    // find it, and where the eye can take all eight lamps in at once
    stompPanel = area.removeFromBottom (72);
    area.removeFromBottom (gap);

    quickPanel = area.removeFromTop (40);
    area.removeFromTop (gap);

    livePresetPanel = area.removeFromLeft (roundToInt (area.getWidth() * 0.34f));
    area.removeFromLeft (gap);

    auto right = area;
    livePerformPanel = right.removeFromBottom (roundToInt (right.getHeight() * 0.34f));
    right.removeFromBottom (gap);
    liveMixPanel = right;

    {
        auto panel = livePresetPanel.reduced (10, 8).withTrimmedTop (panelTitleH - 6);
        auto buttons = panel.removeFromBottom (30);
        panel.removeFromBottom (6);

        favouriteButton.setBounds (buttons.removeFromRight (34).reduced (2));
        savePresetButton.setBounds (buttons.removeFromLeft (roundToInt (buttons.getWidth() * 0.58f)).reduced (2));
        deletePresetButton.setBounds (buttons.reduced (2));

        presetList.setBounds (panel);
    }

    //---- quick access -------------------------------------------------------
    {
        auto inner = quickPanel.reduced (10, 5);
        const int each = jmax (1, inner.getWidth() / jmax (1, quickButtons.size()));

        for (auto* b : quickButtons)
            b->setBounds (inner.removeFromLeft (each).reduced (1, 0));
    }

    //---- the pedalboard -----------------------------------------------------
    {
        auto inner = stompPanel.reduced (10, 8);
        const int each = jmax (1, inner.getWidth() / jmax (1, stomps.size()));

        for (auto* b : stomps)
            b->setBounds (inner.removeFromLeft (each).reduced (3, 0));
    }

    //---- mix: one big macro plus the five things you actually reach for ------
    {
        auto inner = liveMixPanel.reduced (14, 8);
        inner.removeFromTop (panelTitleH);

        auto meterArea = inner.removeFromRight (26);
        meter.setBounds (meterArea.reduced (6, 10));

        auto soakArea = inner.removeFromLeft (roundToInt (inner.getWidth() * 0.34f));
        soakKnob->setBounds (soakArea.reduced (4));

        layoutGrid (liveKnobs, inner.reduced (4, 0), jmax (1, liveKnobs.size()));
    }

    //---- performance: transpose, split, freeze -------------------------------
    {
        auto inner = livePerformPanel.reduced (14, 8);
        inner.removeFromTop (panelTitleH);

        const int rowHeight = jmin (46, inner.getHeight() - 22);
        const int total = inner.getWidth();

        auto transposeArea = inner.removeFromLeft (roundToInt (total * 0.30f)).reduced (8, 0);
        transposeCaption.setBounds (transposeArea.removeFromTop (16));
        transposeArea.removeFromTop (4);

        auto transposeRow = transposeArea.removeFromTop (rowHeight);
        const int buttonWidth = jmin (56, transposeRow.getWidth() / 3);
        transposeDown.setBounds (transposeRow.removeFromLeft (buttonWidth).reduced (2, 0));
        transposeUp.setBounds (transposeRow.removeFromRight (buttonWidth).reduced (2, 0));
        transposeValue.setBounds (transposeRow);

        auto splitArea = inner.removeFromLeft (roundToInt (total * 0.38f)).reduced (8, 0);
        splitArea.removeFromTop (20);
        auto splitRow = splitArea.removeFromTop (rowHeight);
        splitButton.setBounds (splitRow.removeFromLeft (roundToInt (splitRow.getWidth() * 0.46f)).reduced (2, 0));
        splitRow.removeFromLeft (8);
        splitPointSlider.setBounds (splitRow.reduced (0, 4));
        splitPointLabel.setBounds (splitPointSlider.getBounds());

        auto freezeArea = inner.reduced (8, 0);
        freezeArea.removeFromTop (20);
        freezeButton.setBounds (freezeArea.removeFromTop (rowHeight)
                                          .withSizeKeepingCentre (jmin (150, freezeArea.getWidth()), rowHeight));
    }
}

void WorshipPianoEditor::layoutEdit (Rectangle<int> area)
{
    livePresetPanel = liveMixPanel = livePerformPanel = quickPanel = stompPanel = {};

    const int usable = area.getHeight() - gap * 2;
    const int rowHeight = roundToInt ((float) usable / 2.9f);

    //---- row one: piano + pad ------------------------------------------------
    auto rowA = area.removeFromTop (rowHeight);
    area.removeFromTop (gap);

    pianoPanel = rowA.removeFromLeft (roundToInt (rowA.getWidth() * 0.655f));
    rowA.removeFromLeft (gap);
    padPanel = rowA;

    auto pianoInner = pianoPanel.reduced (10, 6);
    pianoInner.removeFromTop (panelTitleH);

    layoutGrid (pianoKnobs, pianoInner, 5);

    auto padInner = padPanel.reduced (10, 6);
    padInner.removeFromTop (panelTitleH);
    padTypeBox.setBounds (padInner.removeFromTop (26).reduced (2, 2));
    padInner.removeFromTop (4);
    layoutGrid (padKnobs, padInner, 4);

    //---- row two: tone + movement -------------------------------------------
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

    {
        const int cells = 4;
        const int cellW = moveInner.getWidth() / cells;

        for (int i = 0; i < moveKnobs.size(); ++i)
            moveKnobs[i]->setBounds (moveInner.getX() + i * cellW, moveInner.getY(),
                                     cellW, moveInner.getHeight());

        auto sync = Rectangle<int> (moveInner.getX() + 3 * cellW, moveInner.getY(),
                                    cellW, moveInner.getHeight()).reduced (10, 0);
        sync = sync.withSizeKeepingCentre (sync.getWidth(), 88);

        delaySyncButton.setBounds (sync.removeFromTop (22));
        sync.removeFromTop (3);
        delayDivBox.setBounds (sync.removeFromTop (22));
        sync.removeFromTop (3);
        pedalBox.setBounds (sync.removeFromTop (22));
        sync.removeFromTop (2);
        tempoLabel.setBounds (sync.removeFromTop (14));
    }

    //---- row three: ambience + output ---------------------------------------
    auto rowC = area;

    ambiencePanel = rowC.removeFromLeft (roundToInt (rowC.getWidth() * 0.76f));
    rowC.removeFromLeft (gap);
    soakPanel = rowC;

    auto ambInner = ambiencePanel.reduced (10, 6);
    ambInner.removeFromTop (panelTitleH);

    auto ambTop = ambInner.removeFromTop (26).reduced (2, 2);
    machineBox.setBounds (ambTop.removeFromLeft (roundToInt (ambTop.getWidth() * 0.32f)));
    ambTop.removeFromLeft (5);
    revTimeBox.setBounds (ambTop.removeFromRight (86));
    ambTop.removeFromRight (5);
    shimmerModeBox.setBounds (ambTop);

    ambInner.removeFromTop (4);
    layoutGrid (ambienceKnobs, ambInner, 7);

    auto outInner = soakPanel.reduced (10, 6);
    outInner.removeFromTop (panelTitleH + 4);

    // the meter lives in whichever panel is on screen, otherwise it stays put
    // from the other layout and lands on top of something
    meter.setBounds (outInner.removeFromRight (26).reduced (6, 6));
    layoutGrid (outputKnobs, outInner, 2);
}
