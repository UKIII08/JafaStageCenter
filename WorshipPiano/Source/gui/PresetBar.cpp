#include "PresetBar.h"
#include "WorshipLookAndFeel.h"
#include "../Presets.h"

using namespace juce;

namespace wpui
{

PresetBar::PresetBar()
{
    addAndMakeVisible (prev);
    addAndMakeVisible (next);
    addAndMakeVisible (chooser);
    addAndMakeVisible (blurb);

    prev.onClick = [this] { step (-1); };
    next.onClick = [this] { step (1); };

    chooser.setTriggeredOnMouseDown (true);
    chooser.onClick = [this]
    {
        PopupMenu menu;
        const auto& list = presets::factory();

        String category;
        int itemId = 1;

        for (const auto& p : list)
        {
            if (p.category != category)
            {
                category = p.category;
                menu.addSectionHeader (category);
            }

            PopupMenu::Item item (p.name);
            item.itemID = itemId;
            item.isTicked = (itemId - 1) == currentIndex;
            menu.addItem (item);
            ++itemId;
        }

        menu.showMenuAsync (PopupMenu::Options().withTargetComponent (chooser)
                                                .withMinimumWidth (chooser.getWidth())
                                                .withStandardItemHeight (24),
                            [this] (int result)
                            {
                                if (result > 0 && onPresetChosen != nullptr)
                                    onPresetChosen (result - 1);
                            });
    };

    blurb.setJustificationType (Justification::centredLeft);
    blurb.setInterceptsMouseClicks (false, false);
    blurb.setColour (Label::textColourId, colours::textDim);

    setPreset (0, false);
}

void PresetBar::step (int delta)
{
    const int count = (int) presets::factory().size();

    if (count == 0 || onPresetChosen == nullptr)
        return;

    onPresetChosen ((currentIndex + delta + count) % count);
}

void PresetBar::setPreset (int index, bool modified)
{
    const auto& list = presets::factory();

    currentIndex = jlimit (0, jmax (0, (int) list.size() - 1), index);
    isModified = modified;

    if (! list.empty())
    {
        chooser.setButtonText (list[(size_t) currentIndex].name + (modified ? String (" *") : String()));
        blurb.setText (list[(size_t) currentIndex].blurb, dontSendNotification);
    }

    repaint();
}

void PresetBar::paint (Graphics& g)
{
    auto bounds = getLocalBounds().toFloat();

    g.setColour (colours::panel);
    g.fillRoundedRectangle (bounds, 6.0f);
    g.setColour (colours::panelEdge);
    g.drawRoundedRectangle (bounds.reduced (0.5f), 6.0f, 1.0f);

    g.setColour (colours::accent);
    g.setFont (Font (FontOptions (13.0f)).withStyle (Font::bold));
    g.drawText ("JAFA WORSHIP PIANO", bounds.removeFromLeft (200.0f).reduced (14.0f, 0.0f),
                Justification::centredLeft, false);
}

void PresetBar::resized()
{
    auto area = getLocalBounds().reduced (8, 8);
    area.removeFromLeft (192);

    const int buttonWidth = 30;
    prev.setBounds (area.removeFromLeft (buttonWidth).reduced (2));
    chooser.setBounds (area.removeFromLeft (jmin (230, area.getWidth() / 2)).reduced (2));
    next.setBounds (area.removeFromLeft (buttonWidth).reduced (2));

    blurb.setBounds (area.reduced (10, 0));
}

} // namespace wpui
